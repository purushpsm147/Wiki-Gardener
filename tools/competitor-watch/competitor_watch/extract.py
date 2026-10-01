"""Turn a fetched page into facts. Three layers, from most to least reliable:

1. the visible text, scanned for keywords and sentences of interest (survives any layout change);
2. structured data the page embeds (JSON-LD, `__NEXT_DATA__`), searched by key name, not by position;
3. regular expressions over the visible text, for what is left (the weakest; every value says how it was found).

None of this has seen a real Marketplace page: the sandbox that wrote it cannot reach atlassian.com. The tests use clearly labelled
synthetic fixtures, and `watch.py run --raw-dir` saves real pages so they can replace them.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Iterator
from urllib.parse import urljoin

BLOCK_TAGS = frozenset(
    "address article aside blockquote br dd details div dl dt fieldset figcaption figure form h1 h2 h3 h4 h5 h6 header hr li main ol p pre section summary table td th tr ul".split()
)
SKIP_TAGS = frozenset("script style noscript template svg nav footer".split())
HEADING_TAGS = frozenset("h1 h2 h3 h4 h5 h6".split())
JSON_SCRIPT_TYPES = ("application/ld+json", "application/json")
BOT_WALL = re.compile(
    r"verify you are (?:a )?human|are you a robot|captcha|access denied|attention required|just a moment|enable javascript and cookies|request blocked|unusual traffic",
    re.I,
)


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def short_hash(s: str, n: int = 12) -> str:
    return hashlib.sha1(normalize(s).lower().encode("utf-8")).hexdigest()[:n]


@dataclass
class Page:
    title: str | None = None
    meta: dict[str, str] = field(default_factory=dict)
    blocks: list[str] = field(default_factory=list)
    headings: list[tuple[str, str]] = field(default_factory=list)
    list_items: list[str] = field(default_factory=list)
    links: list[tuple[str, str]] = field(default_factory=list)
    json_blobs: list[Any] = field(default_factory=list)
    json_errors: int = 0
    script_count: int = 0

    @property
    def text(self) -> str:
        return "\n".join(self.blocks)

    @property
    def js_shell(self) -> bool:
        """Almost no readable text and several scripts: the content is drawn by JavaScript, which this tool does not run."""
        return len(self.text) < 400 and self.script_count >= 2

    @property
    def bot_wall(self) -> bool:
        return len(self.text) < 2500 and bool(BOT_WALL.search(self.text + " " + (self.title or "")))


class _Parser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.page = Page()
        self._title: list[str] = []
        self._in_title = False
        self._buf: list[str] = []
        self._skip: list[str] = []
        self._json_script = False
        self._json_buf: list[str] = []
        self._captures: list[tuple[str, list[str]]] = []
        self._link: tuple[str, list[str]] | None = None

    def _flush(self) -> None:
        text = normalize("".join(self._buf))
        if text:
            self.page.blocks.append(text)
        self._buf = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "script":
            self.page.script_count += 1
            if a.get("type", "").lower() in JSON_SCRIPT_TYPES or a.get("id") == "__NEXT_DATA__":
                self._json_script, self._json_buf = True, []
        if tag in SKIP_TAGS:
            self._skip.append(tag)
            return
        if self._skip:
            return
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or a.get("itemprop") or "").lower()
            if key and a.get("content") and key not in self.page.meta:
                self.page.meta[key] = normalize(a["content"])
        if tag in BLOCK_TAGS:
            self._flush()
        if tag == "li" or tag in HEADING_TAGS:
            self._captures.append((tag, []))
        if tag == "a" and a.get("href"):
            self._link = (urljoin(self.base_url, a["href"]), [])

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS:
            if tag in self._skip:
                idx = len(self._skip) - 1 - self._skip[::-1].index(tag)
                del self._skip[idx:]
            if tag == "script" and self._json_script:
                raw = "".join(self._json_buf).strip()
                self._json_script, self._json_buf = False, []
                try:
                    self.page.json_blobs.append(json.loads(raw))
                except (ValueError, RecursionError):
                    self.page.json_errors += 1
            return
        if self._skip:
            return
        if tag == "title":
            self._in_title = False
            self.page.title = normalize("".join(self._title)) or None
        if tag in BLOCK_TAGS:
            self._flush()
        if self._captures and self._captures[-1][0] == tag:
            _, parts = self._captures.pop()
            text = normalize(" ".join(parts))
            if text:
                if tag == "li":
                    self.page.list_items.append(text)
                else:
                    self.page.headings.append((tag, text))
        if tag == "a" and self._link is not None:
            href, parts = self._link
            self.page.links.append((href, normalize(" ".join(parts))))
            self._link = None

    def handle_data(self, data: str) -> None:
        if self._json_script:
            self._json_buf.append(data)
            return
        if self._skip:
            return
        if self._in_title:
            self._title.append(data)
            return
        self._buf.append(data)
        for _, parts in self._captures:
            parts.append(data)
        if self._link is not None:
            self._link[1].append(data)

    def close(self) -> None:
        super().close()
        self._flush()


def parse_html(html: str, base_url: str = "") -> Page:
    parser = _Parser(base_url)
    parser.feed(html)
    parser.close()
    return parser.page


def text_sha256(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------------------------------------------- keywords


def scan_keywords(text: str, classes: dict[str, tuple[str, ...]], width: int = 120, max_hits: int = 25) -> dict[str, dict[str, Any]]:
    """For each class of patterns: how many times it matched, and a few snippets of context so a human can judge each one."""
    out: dict[str, dict[str, Any]] = {}
    for cls, patterns in classes.items():
        hits: list[dict[str, str]] = []
        count = 0
        if patterns:
            rx = re.compile("|".join(f"(?:{p})" for p in patterns), re.I)
            covered = -1
            seen: set[str] = set()
            for m in rx.finditer(text):
                count += 1
                if m.start() < covered:
                    continue  # the previous snippet already shows this one
                start, end = max(0, m.start() - width), min(len(text), m.end() + width)
                covered = end
                snippet = normalize(text[start:end])
                sha = short_hash(snippet)
                if sha in seen or len(hits) >= max_hits:
                    continue
                seen.add(sha)
                hits.append({"term": m.group(0).lower(), "snippet": snippet, "sha": sha})
        out[cls] = {"count": count, "hits": hits}
    return out


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])|\n+")


def find_mentions(text: str, mentions: tuple[Any, ...], max_each: int = 30) -> dict[str, list[dict[str, str]]]:
    """Sentences containing every term of `all` and any term of `any`, per configured mention."""
    sentences = [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]
    out: dict[str, list[dict[str, str]]] = {}
    for m in mentions:
        found: dict[str, dict[str, str]] = {}
        for s in sentences:
            low = s.lower()
            if all(t.lower() in low for t in m.all) and (not m.any or any(t.lower() in low for t in m.any)):
                sha = short_hash(s)
                found.setdefault(sha, {"text": normalize(s)[:400], "sha": sha})
        out[m.id] = list(found.values())[:max_each]
    return out


# -------------------------------------------------------------------------------------------------------------- features


def extract_features(page: Page, limit: int = 60) -> list[str]:
    """List items of a plausible length, in page order and without repeats. Site navigation is already skipped by the parser."""
    seen: set[str] = set()
    out: list[str] = []
    for item in page.list_items:
        if 12 <= len(item) <= 220 and item.lower() not in seen:
            seen.add(item.lower())
            out.append(item)
    return out[:limit]


def extract_headings(page: Page, limit: int = 40) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for tag, text in page.headings:
        if tag in ("h2", "h3") and 3 <= len(text) <= 120 and text.lower() not in seen:
            seen.add(text.lower())
            out.append(text)
    return out[:limit]


# ----------------------------------------------------------------------------------------------------------------- fields


def parse_count(value: Any) -> int | None:
    """'1,234' -> 1234, '1.2k' -> 1200, '10,000+' -> 10000, 5 -> 5. Anything else is None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if value >= 0 else None
    if not isinstance(value, str):
        return None
    m = re.fullmatch(r"\s*(\d[\d,]*(?:\.\d+)?)\s*([kKmM]?)\s*\+?\s*", value)
    if not m:
        return None
    n = float(m.group(1).replace(",", ""))
    n *= {"": 1, "k": 1_000, "m": 1_000_000}[m.group(2).lower()]
    return int(n)


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None
    return None


def walk_json(obj: Any, path: str = "$", parent: str = "", depth: int = 0) -> Iterator[tuple[str, str, Any, str]]:
    """Every (path, lower-cased key, value, lower-cased parent key) in a JSON document, scalars and containers alike."""
    if depth > 14:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k)
            yield f"{path}.{key}", key.lower(), v, parent
            yield from walk_json(v, f"{path}.{key}", key.lower(), depth + 1)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:200]):
            yield from walk_json(v, f"{path}[{i}]", parent, depth + 1)


INSTALL_KEYS = ("totalinstalls", "installs", "installcount", "activeinstalls", "installations", "totalinstallations")
DOWNLOAD_KEYS = ("downloads", "downloadcount", "totaldownloads")
RATING_KEYS = ("ratingvalue", "averagestars", "averagerating", "averagescore")
REVIEW_KEYS = ("reviewcount", "ratingcount", "reviewscount", "numberofreviews", "totalreviews")
UPDATED_KEYS = ("lastmodified", "datemodified", "lastupdated", "updatedat", "modifieddate", "lastupdateddate")
VERSION_KEYS = ("softwareversion", "version", "versionname")
PRICE_KEYS = ("price", "lowprice", "highprice", "monthlyprice", "unitprice")
VENDOR_KEYS = ("vendor", "author", "publisher", "manufacturer")
APP_TYPES = ("softwareapplication", "webapplication", "mobileapplication", "product")


def _set(fields: dict[str, dict[str, Any]], name: str, value: Any, source: str) -> None:
    if name not in fields and value not in (None, ""):
        fields[name] = {"value": value, "source": source}


def json_fields(blobs: list[Any]) -> dict[str, dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    prices: list[dict[str, Any]] = []
    for blob in blobs:
        for path, key, value, parent in walk_json(blob):
            src = f"json:{path}"
            if key in INSTALL_KEYS and parse_count(value) is not None:
                _set(fields, "installs", parse_count(value), src)
            elif key in DOWNLOAD_KEYS and parse_count(value) is not None:
                _set(fields, "downloads", parse_count(value), src)
            elif key in RATING_KEYS or (key in ("rating", "stars") and not isinstance(value, (dict, list))):
                n = _num(value)
                if n is not None and 0 <= n <= 5:
                    _set(fields, "rating", round(n, 2), src)
            elif key in REVIEW_KEYS or (key == "count" and "review" in parent):
                if parse_count(value) is not None:
                    _set(fields, "review_count", parse_count(value), src)
            elif key in UPDATED_KEYS and isinstance(value, str):
                _set(fields, "last_updated", value, src)
            elif key in VERSION_KEYS and isinstance(value, (str, int, float)) and not isinstance(value, bool) and re.fullmatch(r"v?\d+(?:\.\d+){0,3}", str(value)):
                _set(fields, "version", str(value), src)
            elif key in PRICE_KEYS and _num(value) is not None and len(prices) < 6:
                prices.append({"key": key, "value": _num(value), "source": src})
            elif key == "pricecurrency" and isinstance(value, str):
                _set(fields, "price_currency", value, src)
            elif key in VENDOR_KEYS:
                name = value.get("name") if isinstance(value, dict) else value
                if isinstance(name, str):
                    _set(fields, "vendor", name, src)
            elif key == "name" and isinstance(value, str):
                holder = _holder(blob, path)
                if holder is not None and str(holder.get("@type", "")).lower() in APP_TYPES:
                    _set(fields, "name", value, src)
            elif key == "description" and isinstance(value, str) and len(value) > 20:
                holder = _holder(blob, path)
                if holder is not None and str(holder.get("@type", "")).lower() in APP_TYPES:
                    _set(fields, "summary", normalize(value)[:500], src)
    if prices:
        fields["price_samples"] = {"value": [{"key": p["key"], "value": p["value"]} for p in prices], "source": prices[0]["source"].rsplit(".", 1)[0] + ".*"}
    return fields


def _holder(blob: Any, path: str) -> dict[str, Any] | None:
    """The dict that owns the key at `path`, found by walking the path again (paths come from walk_json)."""
    node = blob
    for part in re.findall(r"\.([^.\[\]]+)|\[(\d+)\]", path)[:-1]:
        key, idx = part
        try:
            node = node[key] if key else node[int(idx)]
        except (KeyError, IndexError, TypeError):
            return None
    return node if isinstance(node, dict) else None


_DATE = (
    r"(?:(?:[A-Z][a-z]{2,8}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})"
    r"|(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?[A-Z][a-z]{2,8}\.?,?\s+\d{4})"
    r"|(?:\d{4}-\d{2}-\d{2}))"
)
TEXT_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("installs", re.compile(r"(?P<v>\d[\d,\.]*\s*[kKmM]?)\+?\s+(?:active\s+)?(?:installs?|installations)\b", re.I), "count"),
    ("installs", re.compile(r"\b(?:installs?|installations)\s*[:\-]?\s*(?P<v>\d[\d,\.]*\s*[kKmM]?)\b", re.I), "count"),
    ("downloads", re.compile(r"(?P<v>\d[\d,\.]*\s*[kKmM]?)\+?\s+downloads?\b", re.I), "count"),
    ("review_count", re.compile(r"(?P<v>\d[\d,]*)\s+(?:user\s+)?(?:reviews?|ratings?)\b", re.I), "count"),
    ("rating", re.compile(r"(?P<v>\d(?:\.\d+)?)\s*(?:/\s*5\b|out of 5\b|stars?\b)", re.I), "rating"),
    ("last_updated", re.compile(rf"\b(?i:last\s+(?:updated|modified)|updated|released)(?i:\s+on)?\s*[:\-]?\s*(?P<v>{_DATE})"), "str"),
    ("version", re.compile(r"\bversion\s*[:\-]?\s*v?(?P<v>\d+(?:\.\d+){1,3})\b", re.I), "str"),
    ("price_text", re.compile(r"(?P<v>(?:US)?\$\s?\d+(?:\.\d{1,2})?(?:\s*USD)?\s*(?:per|/)\s*(?:user\s*)?(?:/\s*)?(?:month|mo|year|yr|user)\b)", re.I), "str"),
    ("free_tier", re.compile(r"\b(?P<v>free\s+(?:for\s+)?(?:up\s+to\s+)?\d+\s+users)\b", re.I), "str"),
)


def text_fields(text: str) -> dict[str, dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    for name, rx, kind in TEXT_RULES:
        if name in fields:
            continue
        m = rx.search(text)
        if not m:
            continue
        raw = m.group("v").strip()
        value: Any
        if kind == "count":
            value = parse_count(raw)
        elif kind == "rating":
            n = _num(raw)
            value = round(n, 2) if n is not None and 0 <= n <= 5 else None
        else:
            value = normalize(raw)
        _set(fields, name, value, f"text:{name}")
    return fields


def extract_fields(page: Page) -> dict[str, dict[str, Any]]:
    """JSON first, then meta tags, then text patterns for whatever is still missing. Each value records how it was found."""
    fields = json_fields(page.json_blobs)
    description = page.meta.get("description") or page.meta.get("og:description")
    if description:
        _set(fields, "summary", description[:500], "meta:description")
    og_title = page.meta.get("og:title")
    if og_title:
        _set(fields, "name", og_title, "meta:og:title")
    for k, v in text_fields(page.text).items():
        _set(fields, k, v["value"], v["source"])
    return fields


# ---------------------------------------------------------------------------------------------------------------- discovery


def find_candidates(page: Page, expect_text: str, limit: int = 5) -> dict[str, Any]:
    """On a search-results page: links to apps whose text contains `expect_text`. `readable` says whether the page showed results at all."""
    want = expect_text.lower()
    app_links = [(href, text) for href, text in page.links if "/apps/" in href]
    candidates = []
    for href, text in app_links:
        if want in text.lower() and href not in candidates:
            candidates.append(href)
    readable = bool(app_links) or bool(re.search(r"\bno (?:apps|results)\b", page.text, re.I))
    return {"found": bool(candidates), "readable": readable, "candidates": candidates[:limit]}
