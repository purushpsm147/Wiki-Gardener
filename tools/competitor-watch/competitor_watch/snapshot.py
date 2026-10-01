"""Build one snapshot entry per source from what was fetched, judge its health, and merge with the previous snapshot.

A source that fails this week keeps its last good facts, marked stale, so a flaky page never reads as "the competitor removed every
feature". Health problems are reported, never swallowed: a source with nothing usable is `failed`, one with something missing is
`partial`.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from . import __version__
from .config import Config, Source
from .extract import (
    extract_features,
    extract_fields,
    extract_headings,
    find_candidates,
    find_mentions,
    parse_html,
    scan_keywords,
    text_sha256,
)
from .fetch import FetchResult, decode_body

SCHEMA = 1
# Present in a snapshot but not a reason to rewrite it: they change on every run without the world having changed.
VOLATILE_KEYS = frozenset({"taken_at", "fetched_at", "bytes", "text_sha256", "http_status", "final_url", "attempts", "at"})


@dataclass
class Fetched:
    url: str
    result: FetchResult
    optional: bool = False


def _problem(entry: dict[str, Any], optional: bool, message: str) -> None:
    entry["warnings" if optional else "problems"].append(message)


def build_entry(source: Source, fetched: list[Fetched], cfg: Config) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": source.name,
        "kind": source.kind,
        "role": source.role,
        "kill_clause_subject": source.kill_clause_subject,
        "provenance": source.provenance,
        "note": source.note,
        "status": "ok",
        "problems": [],
        "warnings": [],
        "pages": [],
        "fields": {},
        "features": [],
        "headings": [],
        "keywords": {},
        "mentions": {},
        "discovery": None,
        "title": None,
    }
    texts: list[str] = []
    usable_required = 0
    required = 0
    features: dict[str, None] = {}
    headings: dict[str, None] = {}

    for f in fetched:
        r = f.result
        record: dict[str, Any] = {"url": f.url, "optional": f.optional, "ok": r.ok, "http_status": r.status, "final_url": r.final_url, "fetched_at": r.fetched_at, "attempts": r.attempts, "error": r.error}
        entry["pages"].append(record)
        if not f.optional:
            required += 1
        if not r.ok:
            _problem(entry, f.optional, f"{f.url}: {r.error}")
            continue
        page = parse_html(decode_body(r.body, r.content_type), base_url=r.final_url or f.url)
        text = page.text
        record.update({"bytes": len(r.body), "text_chars": len(text), "text_sha256": text_sha256(text), "js_shell": page.js_shell, "bot_wall": page.bot_wall, "json_blobs": len(page.json_blobs), "json_errors": page.json_errors})
        usable = True
        if page.bot_wall:
            _problem(entry, f.optional, f"{f.url}: looks like a bot wall or an access-denied page, not the real content")
            usable = False
        elif page.js_shell:
            _problem(entry, f.optional, f"{f.url}: the page is drawn by JavaScript and has no readable text (this tool does not run a browser)")
            usable = False
        elif len(text) < source.min_text_chars:
            _problem(entry, f.optional, f"{f.url}: only {len(text)} characters of text (expected at least {source.min_text_chars})")
            usable = False
        if not usable:
            continue
        if not f.optional:
            usable_required += 1
        if entry["title"] is None:
            entry["title"] = page.title
        texts.append("\n".join([page.title or "", page.meta.get("description", ""), text]))
        for k, v in extract_fields(page).items():
            entry["fields"].setdefault(k, v)
        for item in extract_features(page):
            features.setdefault(item)
        for item in extract_headings(page):
            headings.setdefault(item)
        if source.kind == "search" and entry["discovery"] is None:
            entry["discovery"] = find_candidates(page, source.expect_text or "")

    combined = "\n".join(texts)
    entry["features"] = list(features)
    entry["headings"] = list(headings)
    entry["keywords"] = scan_keywords(combined, cfg.keywords)
    if source.mentions:
        entry["mentions"] = find_mentions(combined, source.mentions)

    if source.kind == "marketplace-listing" and usable_required and source.require_any_field and not any(k in entry["fields"] for k in source.require_any_field):
        entry["problems"].append(f"no structured fact found (looked for {', '.join(source.require_any_field)}): the layout may have changed, or the facts are drawn by JavaScript")
    if source.kind == "search" and usable_required:
        if entry["discovery"] is None or not entry["discovery"]["readable"]:
            entry["problems"].append("the search page showed no readable results, so 'not found' cannot be concluded")

    if required and usable_required == 0:
        entry["status"] = "failed"
    elif entry["problems"]:
        entry["status"] = "partial"
    return entry


def new_snapshot(entries: dict[str, dict[str, Any]], taken_at: str) -> dict[str, Any]:
    return {"schema": SCHEMA, "taken_at": taken_at, "tool": {"name": "competitor-watch", "version": __version__}, "sources": entries}


def carry_over(snapshot: dict[str, Any], previous: dict[str, Any] | None) -> None:
    """Replace each failed entry by the last good one, marked stale, so a bad week does not look like a change."""
    if not previous:
        return
    for sid, entry in snapshot["sources"].items():
        old = previous.get("sources", {}).get(sid)
        if entry["status"] != "failed" or old is None:
            continue
        if old.get("status") == "failed" and not old.get("stale"):
            continue  # nothing good to keep
        carried = copy.deepcopy(old)
        carried["status"] = "failed"
        carried["stale"] = True
        carried["last_good_at"] = old.get("last_good_at") or previous.get("taken_at")
        carried["last_attempt"] = {"at": snapshot["taken_at"], "problems": entry["problems"]}
        snapshot["sources"][sid] = carried


def canonical(obj: Any) -> Any:
    """The snapshot without the fields that change on every run, for deciding whether anything is worth writing."""
    if isinstance(obj, dict):
        return {k: canonical(v) for k, v in obj.items() if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [canonical(v) for v in obj]
    return obj
