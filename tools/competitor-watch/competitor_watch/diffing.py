"""What changed between two snapshots, and how much it matters.

material: something a strategist should read this week (a competitor's claims, pricing, features, a new mention, a listing found);
routine:  the numbers that drift (installs, reviews, rating, version, last updated), reported only past a threshold.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import Config

MATERIAL_FIELDS = frozenset({"name", "summary", "vendor", "price_text", "free_tier", "price_samples", "price_currency"})
COUNT_FIELDS = frozenset({"installs", "downloads", "review_count"})
THESIS_CLASSES = frozenset({"contradiction", "change_time"})


@dataclass
class Change:
    source: str
    severity: str  # "material" | "routine"
    kind: str  # field | feature | heading | keyword | mention | discovery | source | title
    summary: str
    before: Any = None
    after: Any = None


def _value(entry: dict[str, Any], name: str) -> Any:
    f = entry.get("fields", {}).get(name)
    return f["value"] if f else None


def _pct(old: float, new: float) -> float:
    return abs(new - old) / max(abs(old), 1.0) * 100.0


def diff_entry(sid: str, old: dict[str, Any], new: dict[str, Any], cfg: Config) -> list[Change]:
    out: list[Change] = []
    names = sorted(set(old.get("fields", {})) | set(new.get("fields", {})))
    for name in names:
        a, b = _value(old, name), _value(new, name)
        if a == b:
            continue
        if name in MATERIAL_FIELDS:
            out.append(Change(sid, "material", "field", f"{name} changed", a, b))
        elif name in COUNT_FIELDS:
            if a is None or b is None or _pct(a, b) >= cfg.numeric_change_pct:
                out.append(Change(sid, "routine", "field", f"{name}: {a} to {b}", a, b))
        elif name == "rating":
            if a is None or b is None or abs(a - b) >= cfg.rating_change:
                out.append(Change(sid, "routine", "field", f"rating: {a} to {b}", a, b))
        else:  # last_updated, version, anything new the extractor learns
            out.append(Change(sid, "routine", "field", f"{name}: {a} to {b}", a, b))

    for key, label, severity in (("features", "feature", "material"), ("headings", "heading", "routine")):
        before, after = old.get(key, []), new.get(key, [])
        added = [x for x in after if x not in before]
        removed = [x for x in before if x not in after]
        if added:
            out.append(Change(sid, severity, label, f"{len(added)} {label}(s) added", None, added))
        if removed:
            out.append(Change(sid, severity, label, f"{len(removed)} {label}(s) removed", removed, None))

    for cls in sorted(set(old.get("keywords", {})) | set(new.get("keywords", {}))):
        before = {h["sha"]: h for h in old.get("keywords", {}).get(cls, {}).get("hits", [])}
        after = {h["sha"]: h for h in new.get("keywords", {}).get(cls, {}).get("hits", [])}
        severity = "material" if cls in THESIS_CLASSES else "routine"
        for sha, h in after.items():
            if sha not in before:
                out.append(Change(sid, severity, "keyword", f"new '{cls}' mention: \"{h['term']}\"", None, h["snippet"]))
        for sha, h in before.items():
            if sha not in after:
                out.append(Change(sid, severity, "keyword", f"'{cls}' mention gone: \"{h['term']}\"", h["snippet"], None))

    for mid in sorted(set(old.get("mentions", {})) | set(new.get("mentions", {}))):
        before = {h["sha"]: h for h in old.get("mentions", {}).get(mid, [])}
        after = {h["sha"]: h for h in new.get("mentions", {}).get(mid, [])}
        for sha, h in after.items():
            if sha not in before:
                out.append(Change(sid, "material", "mention", f"new '{mid}' sentence", None, h["text"]))
        for sha, h in before.items():
            if sha not in after:
                out.append(Change(sid, "material", "mention", f"'{mid}' sentence gone", h["text"], None))

    od, nd = old.get("discovery") or {}, new.get("discovery") or {}
    if nd.get("found") and (not od.get("found") or od.get("candidates") != nd.get("candidates")):
        out.append(Change(sid, "material", "discovery", "a listing matching the name was found", od.get("candidates"), nd.get("candidates")))
    elif od.get("found") and not nd.get("found") and nd.get("readable"):
        out.append(Change(sid, "material", "discovery", "the listing found earlier is no longer in the results", od.get("candidates"), nd.get("candidates")))

    if old.get("title") != new.get("title") and (old.get("title") or new.get("title")):
        out.append(Change(sid, "routine", "title", "page title changed", old.get("title"), new.get("title")))
    return out


def _has_content(entry: dict[str, Any]) -> bool:
    """A failed entry has content only when it carries the last good data over (stale)."""
    return entry.get("status") != "failed" or bool(entry.get("stale"))


def diff_snapshots(old: dict[str, Any] | None, new: dict[str, Any], cfg: Config) -> list[Change]:
    """Empty for a baseline (no previous snapshot). A source that failed this run is skipped (a failed fetch is a health matter, not a
    change), and so is one whose previous entry holds nothing to compare with; one that was stale is compared against its last good data."""
    if old is None:
        return []
    changes: list[Change] = []
    old_sources, new_sources = old.get("sources", {}), new.get("sources", {})
    for sid in new_sources:
        if sid not in old_sources:
            changes.append(Change(sid, "material", "source", "source added to the watch list (its baseline is this snapshot)"))
        elif new_sources[sid].get("status") != "failed" and _has_content(old_sources[sid]):
            changes.extend(diff_entry(sid, old_sources[sid], new_sources[sid], cfg))
    for sid in old_sources:
        if sid not in new_sources:
            changes.append(Change(sid, "material", "source", "source removed from the watch list"))
    rank = {"material": 0, "routine": 1}
    order = {sid: i for i, sid in enumerate(new_sources)}
    changes.sort(key=lambda c: (rank[c.severity], order.get(c.source, 10_000)))
    return changes


def should_open_issue(changes: list[Change], cfg: Config) -> bool:
    if cfg.issue_on == "material":
        return any(c.severity == "material" for c in changes)
    return bool(changes)


def health_lines(old: dict[str, Any] | None, new: dict[str, Any]) -> list[str]:
    """One line per source that is failing, partial or has just recovered."""
    lines: list[str] = []
    for sid, e in new.get("sources", {}).items():
        was = (old or {}).get("sources", {}).get(sid, {}).get("status")
        if e["status"] == "failed":
            since = f" (showing last good data from {e['last_good_at']})" if e.get("stale") else " (nothing usable and no earlier data)"
            lines.append(f"FAILED {sid}{since}: " + "; ".join(e.get("problems", []) or ["no reason recorded"]))
        elif e["status"] == "partial":
            lines.append(f"PARTIAL {sid}: " + "; ".join(e.get("problems", [])))
        elif was in ("failed", "partial"):
            lines.append(f"RECOVERED {sid}: was {was}, now ok")
    return lines
