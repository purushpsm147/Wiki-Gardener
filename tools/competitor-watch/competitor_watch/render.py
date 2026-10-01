"""Markdown for people: the snapshot, the thesis table that watches GATE-S4's kill clause, and the change report that becomes an issue."""
from __future__ import annotations

import json
from typing import Any

from .config import Config
from .diffing import Change

KILL_CLAUSE = "If Evergreen ships change-time prevention before our decision point, the differentiation thesis is re-argued from scratch in writing."
THESIS_FILE = "docs/competitors/differentiation-thesis.md"
ISSUE_LIMIT = 60_000


def cell(value: Any, limit: int = 160) -> str:
    if isinstance(value, (list, dict)):
        value = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    text = " ".join(str(value).split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _ordered(snapshot: dict[str, Any], cfg: Config) -> list[tuple[str, dict[str, Any]]]:
    sources = snapshot["sources"]
    ids = [s.id for s in cfg.sources if s.id in sources] + sorted(i for i in sources if i not in {s.id for s in cfg.sources})
    return [(i, sources[i]) for i in ids]


def thesis_rows(snapshot: dict[str, Any], cfg: Config) -> list[dict[str, str]]:
    """One row per competitor: have its pages started to use contradiction words or change-time words? A human judges the snippets."""
    rows = []
    for sid, e in _ordered(snapshot, cfg):
        if e.get("role") != "competitor":
            continue
        kw = e.get("keywords", {})
        contradiction = kw.get("contradiction", {}).get("count", 0)
        change_time = kw.get("change_time", {}).get("count", 0)
        located = "yes"
        if e.get("kind") == "search":
            d = e.get("discovery") or {}
            located = "yes" if d.get("found") else ("NO" if d.get("readable") else "unknown (search page unreadable)")
        if e.get("status") == "failed":
            located = "unknown (source failed)" if located == "yes" else located
        if e.get("kind") == "search" and located != "yes":
            indicator = "UNKNOWN: not located, so the kill clause cannot be evaluated"
        elif e.get("status") == "failed":
            indicator = "UNKNOWN: source failed" + (" (last good data shown)" if e.get("stale") else "")
        elif contradiction and change_time:
            indicator = "REVIEW NOW: contradiction words and change-time words both present"
        elif contradiction:
            indicator = "contradiction words present: read the snippets"
        elif change_time:
            indicator = "change-time words present: read the snippets"
        else:
            indicator = "not seen"
        rows.append({"id": sid, "name": e.get("name", sid), "located": located, "contradiction": str(contradiction), "change_time": str(change_time), "indicator": indicator, "subject": "yes" if e.get("kill_clause_subject") else ""})
    return rows


def render_thesis(snapshot: dict[str, Any], cfg: Config) -> str:
    rows = thesis_rows(snapshot, cfg)
    lines = [
        "## Differentiation thesis status (generated)",
        "",
        f"GATE-S4 kill clause: *{KILL_CLAUSE}*",
        "",
        "This table is mechanical: it counts words on the pages that were fetched. It cannot tell a claim from a mention; a person reads the snippets below.",
        f"The thesis, the decision point and the written re-argument live in [`{THESIS_FILE}`](../differentiation-thesis.md) (this file is generated into `docs/competitors/snapshots/`).",
        "",
        "| Competitor | Kill-clause subject | Listing located | Contradiction words | Change-time words | Indicator |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {cell(r['name'])} | {r['subject']} | {cell(r['located'])} | {r['contradiction']} | {r['change_time']} | {cell(r['indicator'], 120)} |")
    if not any(r["subject"] for r in rows):
        lines += ["", "**No source is marked `kill_clause_subject`, so the clause as written (about Evergreen) is not being watched.**"]
    return "\n".join(lines)


def render_snapshot(snapshot: dict[str, Any], cfg: Config) -> str:
    out = [
        "# Competitor snapshot",
        "",
        f"Taken {snapshot['taken_at']} by competitor-watch {snapshot['tool']['version']}. Generated: do not edit; run `python tools/competitor-watch/watch.py render --write`.",
        "A value found in structured data (`json:`, `meta:`) is more reliable than one found by a text pattern (`text:`), which is a heuristic.",
        "",
        "## Health",
        "",
        "| Source | Status | Notes |",
        "|---|---|---|",
    ]
    for sid, e in _ordered(snapshot, cfg):
        if e.get("stale"):
            notes = f"showing last good data from {e.get('last_good_at')}; this run: " + "; ".join(e.get("last_attempt", {}).get("problems", []))
        else:
            notes = "; ".join(e.get("problems", []) + e.get("warnings", []))
        out.append(f"| `{sid}` | {e['status']} | {cell(notes, 300)} |")
    out += ["", render_thesis(snapshot, cfg)]

    for sid, e in _ordered(snapshot, cfg):
        out += ["", f"## {e.get('name', sid)}", "", f"`{sid}` · {e.get('kind')} · {e.get('role')} · status **{e['status']}**" + (" · **stale**" if e.get("stale") else "")]
        if e.get("provenance"):
            out.append(f"\nWhy it is watched: {e['provenance']}")
        if e.get("note"):
            out.append(f"\n{e['note']}")
        for p in e.get("pages", []):
            ok = f"HTTP {p.get('http_status')}" if p.get("ok") else f"not fetched: {p.get('error')}"
            out.append(f"\n- {p['url']}: {ok}" + (" (optional)" if p.get("optional") else ""))
        if e.get("stale"):
            out.append(f"\n**Failed this run; everything below is from {e.get('last_good_at')}.** " + "; ".join(e.get("last_attempt", {}).get("problems", [])))
        elif e.get("problems"):
            out.append("\n**Problems:** " + "; ".join(e["problems"]))
        if e.get("fields"):
            out += ["", "| Fact | Value | How found |", "|---|---|---|"]
            for name in sorted(e["fields"]):
                f = e["fields"][name]
                out.append(f"| {name} | {cell(f['value'])} | `{cell(f['source'], 90)}` |")
        d = e.get("discovery")
        if d:
            out.append(f"\nSearch: found={d['found']}, readable={d['readable']}" + (f", candidates {', '.join(d['candidates'])}" if d["candidates"] else ""))
        if e.get("features"):
            out += ["", f"Features ({len(e['features'])}):"] + [f"- {cell(x, 200)}" for x in e["features"][:25]]
            if len(e["features"]) > 25:
                out.append(f"- … and {len(e['features']) - 25} more in latest.json")
        for cls, kw in e.get("keywords", {}).items():
            if kw["count"]:
                out += ["", f"**`{cls}`**: {kw['count']} match(es)"] + [f"- \"{h['term']}\": …{cell(h['snippet'], 260)}…" for h in kw["hits"][:6]]
        for mid, items in e.get("mentions", {}).items():
            if items:
                out += ["", f"**Mentions `{mid}`** ({len(items)}):"] + [f"- {cell(i['text'], 260)}" for i in items[:8]]
    return "\n".join(out) + "\n"


def render_changes(changes: list[Change], health: list[str], old: dict[str, Any] | None, new: dict[str, Any], cfg: Config) -> str:
    material = [c for c in changes if c.severity == "material"]
    routine = [c for c in changes if c.severity == "routine"]
    if old is None:
        head = [f"# competitor-watch: baseline taken {new['taken_at']}", "", "No earlier snapshot existed, so there is nothing to compare. Later runs diff against this one."]
    elif not changes and health:
        head = ["# competitor-watch: a source could not be read", "", f"Snapshot {old['taken_at']} to {new['taken_at']}. Nothing is known to have changed; the sources below need attention."]
    else:
        flag = " (MATERIAL)" if material else ""
        head = [f"# competitor-watch: {len(changes)} change(s){flag}", "", f"Snapshot {old['taken_at']} to {new['taken_at']}."]
    out = head

    def block(title: str, items: list[Change]) -> None:
        if not items:
            return
        out.extend(["", f"## {title}", ""])
        for c in items:
            out.append(f"- **{c.source}**: {c.summary}")
            for label, v in (("before", c.before), ("after", c.after)):
                if v in (None, [], ""):
                    continue
                if isinstance(v, list):
                    out.extend(f"  - {label}: {cell(x, 240)}" for x in v[:12])
                    if len(v) > 12:
                        out.append(f"  - {label}: … and {len(v) - 12} more")
                else:
                    out.append(f"  - {label}: {cell(v, 400)}")

    block("Material", material)
    block("Routine", routine)
    if health:
        out += ["", "## Health", ""] + [f"- {line}" for line in health]
    if material:
        out += ["", "## What to do", "", f"- Read the material items. If any competitor now claims contradiction detection, or change-time prevention, say so at the top of the next summary and follow the kill clause in `{THESIS_FILE}`."]
    text = "\n".join(out) + "\n"
    if len(text) > ISSUE_LIMIT:
        text = text[:ISSUE_LIMIT] + "\n\n(report truncated; the full diff is the commit that updates `docs/competitors/snapshots/latest.json`)\n"
    return text
