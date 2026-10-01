"""Load and validate sources.json. Every problem is reported at once, naming the source, so a bad edit is fixed in one go."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

KINDS = ("marketplace-listing", "page", "search")
ROLES = ("competitor", "atlassian", "lead")
ISSUE_ON = ("routine", "material")


class ConfigError(Exception):
    """sources.json is not usable. The message lists every problem found."""


@dataclass(frozen=True)
class Mention:
    """Select sentences that contain every term of `all` and, when given, at least one of `any` (case-insensitive substrings)."""

    id: str
    all: tuple[str, ...]
    any: tuple[str, ...] = ()


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    kind: str
    role: str
    enabled: bool
    urls: tuple[str, ...]
    optional_urls: tuple[str, ...] = ()
    require_any_field: tuple[str, ...] = ()
    min_text_chars: int = 300
    expect_text: str | None = None
    kill_clause_subject: bool = False
    mentions: tuple[Mention, ...] = ()
    provenance: str = ""
    note: str = ""


@dataclass(frozen=True)
class Config:
    user_agent: str
    keywords: dict[str, tuple[str, ...]]
    sources: tuple[Source, ...]
    numeric_change_pct: float = 5.0
    rating_change: float = 0.1
    issue_on: str = "routine"
    problems: list[str] = field(default_factory=list, compare=False)

    def enabled_sources(self) -> list[Source]:
        return [s for s in self.sources if s.enabled]


def _strs(value: Any, where: str, problems: list[str]) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        problems.append(f"{where} must be a list of strings")
        return ()
    return tuple(value)


def parse_config(obj: Any) -> Config:
    problems: list[str] = []
    if not isinstance(obj, dict):
        raise ConfigError("sources.json must be a JSON object")
    if obj.get("schema") != 1:
        problems.append("schema must be 1")
    user_agent = obj.get("user_agent")
    if not isinstance(user_agent, str) or not user_agent.strip():
        problems.append("user_agent must be a non-empty string that says who is fetching and where to complain")
        user_agent = ""

    keywords: dict[str, tuple[str, ...]] = {}
    raw_keywords = obj.get("keywords")
    if not isinstance(raw_keywords, dict) or not raw_keywords:
        problems.append("keywords must be an object of class name to list of regular expressions")
    else:
        for cls, patterns in raw_keywords.items():
            pats = _strs(patterns, f"keywords.{cls}", problems)
            for p in pats:
                try:
                    re.compile(p)
                except re.error as e:
                    problems.append(f"keywords.{cls}: {p!r} is not a valid regular expression ({e})")
            keywords[cls] = pats
        for needed in ("contradiction", "change_time"):
            if needed not in keywords:
                problems.append(f"keywords.{needed} is required (the differentiation-thesis table is built from it)")

    issue_on = obj.get("issue_on", "routine")
    if issue_on not in ISSUE_ON:
        problems.append(f"issue_on must be one of {ISSUE_ON}")

    sources: list[Source] = []
    seen: set[str] = set()
    raw_sources = obj.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        problems.append("sources must be a non-empty list")
        raw_sources = []
    for i, raw in enumerate(raw_sources):
        sid = raw.get("id") if isinstance(raw, dict) else None
        where = f"sources[{i}]" + (f" ({sid})" if isinstance(sid, str) else "")
        if not isinstance(raw, dict):
            problems.append(f"{where} must be an object")
            continue
        if not isinstance(sid, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", sid):
            problems.append(f"{where}: id must be lower-case letters, digits and hyphens")
            continue
        if sid in seen:
            problems.append(f"{where}: duplicate id")
        seen.add(sid)
        kind = raw.get("kind")
        if kind not in KINDS:
            problems.append(f"{where}: kind must be one of {KINDS}")
        role = raw.get("role", "competitor")
        if role not in ROLES:
            problems.append(f"{where}: role must be one of {ROLES}")
        urls = _strs(raw.get("urls"), f"{where}.urls", problems)
        optional = _strs(raw.get("optional_urls"), f"{where}.optional_urls", problems)
        if raw.get("enabled", True) and not urls:
            problems.append(f"{where}: an enabled source needs at least one url")
        for u in urls + optional:
            if not u.startswith("https://"):
                problems.append(f"{where}: {u!r} must be an https URL")
        if kind == "search" and not raw.get("expect_text"):
            problems.append(f"{where}: a search source needs expect_text, the name it is looking for")
        mentions: list[Mention] = []
        for m in raw.get("mentions", []) or []:
            if not isinstance(m, dict) or not isinstance(m.get("id"), str) or not m.get("all"):
                problems.append(f"{where}: each mention needs an id and a non-empty 'all' list")
                continue
            mentions.append(Mention(m["id"], _strs(m["all"], f"{where}.mentions.{m['id']}.all", problems), _strs(m.get("any"), f"{where}.mentions.{m['id']}.any", problems)))
        sources.append(
            Source(
                id=sid,
                name=str(raw.get("name", sid)),
                kind=str(kind),
                role=str(role),
                enabled=bool(raw.get("enabled", True)),
                urls=urls,
                optional_urls=optional,
                require_any_field=_strs(raw.get("require_any_field"), f"{where}.require_any_field", problems),
                min_text_chars=int(raw.get("min_text_chars", 300)),
                expect_text=raw.get("expect_text"),
                kill_clause_subject=bool(raw.get("kill_clause_subject", False)),
                mentions=tuple(mentions),
                provenance=str(raw.get("provenance", "")),
                note=str(raw.get("note", "")),
            )
        )
    if problems:
        raise ConfigError("sources.json has problems:\n- " + "\n- ".join(problems))
    return Config(
        user_agent=user_agent,
        keywords=keywords,
        sources=tuple(sources),
        numeric_change_pct=float(obj.get("numeric_change_pct", 5.0)),
        rating_change=float(obj.get("rating_change", 0.1)),
        issue_on=issue_on,
    )


def load_config(path: str | Path) -> Config:
    try:
        obj = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"{path} does not exist") from None
    except json.JSONDecodeError as e:
        raise ConfigError(f"{path} is not valid JSON: {e}") from None
    return parse_config(obj)
