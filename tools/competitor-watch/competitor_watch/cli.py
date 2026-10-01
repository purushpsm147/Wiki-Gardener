"""Command line: run (fetch, snapshot, diff, write), render (markdown from a snapshot), check-config."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .config import Config, ConfigError, load_config
from .diffing import diff_snapshots, health_lines, should_open_issue
from .fetch import FetchResult, Fetcher
from .render import render_changes, render_snapshot
from .snapshot import Fetched, build_entry, canonical, carry_over, new_snapshot

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "sources.json"
DEFAULT_SNAPSHOTS = "docs/competitors/snapshots"


def raw_name(source_id: str, index: int) -> str:
    return f"{source_id}__{index}.html"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_raw(directory: Path, source_id: str, index: int, url: str) -> FetchResult:
    """Offline mode: pages saved earlier by `--raw-dir` (or by hand, from a browser) under the same names."""
    path = directory / raw_name(source_id, index)
    if not path.is_file():
        return FetchResult(url, False, None, None, None, b"", f"no saved file {path.name} in {directory}", _now(), 0)
    return FetchResult(url, True, 200, url, "text/html; charset=utf-8", path.read_bytes(), None, _now(), 1)


def write_github_output(path: str, values: dict[str, str]) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        for k, v in values.items():
            fh.write(f"{k}={' '.join(str(v).split())}\n")


def run(args: argparse.Namespace, cfg: Config, loader: Callable[[str, str, int], FetchResult] | None = None, now: Callable[[], str] = _now) -> int:
    sources = [s for s in cfg.enabled_sources() if not args.only or s.id in args.only]
    if args.only and len(sources) != len(set(args.only)):
        missing = set(args.only) - {s.id for s in sources}
        print(f"unknown or disabled source id(s): {', '.join(sorted(missing))}", file=sys.stderr)
        return 1
    if loader is None:
        if args.from_dir:
            directory = Path(args.from_dir)
            loader = lambda url, sid, i: read_raw(directory, sid, i, url)  # noqa: E731
        else:
            fetcher = Fetcher(cfg.user_agent, timeout=args.timeout, retries=args.retries, respect_robots=not args.no_robots)
            loader = lambda url, sid, i: fetcher.fetch(url)  # noqa: E731
    raw_dir = Path(args.raw_dir) if args.raw_dir else None
    if raw_dir:
        raw_dir.mkdir(parents=True, exist_ok=True)

    entries = {}
    for s in sources:
        fetched = []
        urls = [(u, False) for u in s.urls] + [(u, True) for u in s.optional_urls]
        for i, (url, optional) in enumerate(urls):
            result = loader(url, s.id, i)
            if raw_dir and result.ok:
                (raw_dir / raw_name(s.id, i)).write_bytes(result.body)
            fetched.append(Fetched(url, result, optional))
        entries[s.id] = build_entry(s, fetched, cfg)
        print(f"{entries[s.id]['status']:8} {s.id}" + (f"  ({'; '.join(entries[s.id]['problems'])})" if entries[s.id]["problems"] else ""))

    snap_dir = Path(args.snapshots)
    latest = snap_dir / "latest.json"
    previous = json.loads(latest.read_text(encoding="utf-8")) if latest.is_file() else None
    snapshot = new_snapshot(entries, now())
    carry_over(snapshot, previous)
    changes = diff_snapshots(previous, snapshot, cfg)
    health = health_lines(previous, snapshot)
    failed = any(e["status"] == "failed" for e in snapshot["sources"].values())
    nothing_usable = all(e["status"] == "failed" for e in snapshot["sources"].values())
    baseline = previous is None and not nothing_usable
    # Never write a snapshot with no content at all: the next run would take it for a baseline and report everything as new.
    snapshot_changed = False if previous is None and nothing_usable else (previous is None or canonical(previous) != canonical(snapshot))
    open_issue = should_open_issue(changes, cfg)
    material = any(c.severity == "material" for c in changes)

    if snapshot_changed and not args.dry_run:
        snap_dir.mkdir(parents=True, exist_ok=True)
        latest.write_text(json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        (snap_dir / "latest.md").write_text(render_snapshot(snapshot, cfg), encoding="utf-8")
    if args.report:
        Path(args.report).write_text(render_changes(changes, health, previous, snapshot, cfg), encoding="utf-8")

    if previous is None and nothing_usable:
        summary = "no baseline: every source failed"
    elif baseline:
        summary = "baseline taken"
    else:
        summary = f"{len(changes)} change(s), {sum(c.severity == 'material' for c in changes)} material"
    if args.github_output:
        write_github_output(
            args.github_output,
            {
                "baseline": str(baseline).lower(),
                "changed": str(open_issue).lower(),
                "material": str(material).lower(),
                "failed": str(failed).lower(),
                "snapshot_changed": str(snapshot_changed and not args.dry_run).lower(),
                "issue_title": f"competitor-watch: {summary} ({snapshot['taken_at'][:10]})",
                "summary": summary,
            },
        )
    print(f"\n{summary}; snapshot {'written' if snapshot_changed and not args.dry_run else 'unchanged' if not snapshot_changed else 'not written (dry run)'}; {'health problems: ' + str(len(health)) if health else 'all sources healthy'}")
    return 2 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="watch.py", description="Snapshot competitor pages and report what changed.")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="fetch every enabled source, diff against the last snapshot, write the new one")
    r.add_argument("--config", default=str(DEFAULT_CONFIG))
    r.add_argument("--snapshots", default=DEFAULT_SNAPSHOTS, help="directory holding latest.json and latest.md")
    r.add_argument("--raw-dir", help="also save every fetched page here (for debugging, and to turn into test fixtures)")
    r.add_argument("--from-dir", help="do not touch the network: read pages saved earlier with --raw-dir, or by hand from a browser, as <source-id>__<n>.html")
    r.add_argument("--report", help="write the change report (an issue body) to this file")
    r.add_argument("--github-output", help="append key=value lines for later workflow steps (the path of $GITHUB_OUTPUT)")
    r.add_argument("--only", nargs="+", metavar="ID", help="only these source ids")
    r.add_argument("--dry-run", action="store_true", help="fetch and diff, but write no snapshot")
    r.add_argument("--no-robots", action="store_true", help="do not consult robots.txt (only if you have decided that is acceptable)")
    r.add_argument("--timeout", type=float, default=20.0)
    r.add_argument("--retries", type=int, default=2)
    d = sub.add_parser("render", help="print (or --write) the markdown for an existing latest.json")
    d.add_argument("--config", default=str(DEFAULT_CONFIG))
    d.add_argument("--snapshots", default=DEFAULT_SNAPSHOTS)
    d.add_argument("--write", action="store_true")
    c = sub.add_parser("check-config", help="validate sources.json and list what it watches")
    c.add_argument("--config", default=str(DEFAULT_CONFIG))
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        print(e, file=sys.stderr)
        return 1
    if args.command == "check-config":
        for s in cfg.sources:
            print(f"{'on ' if s.enabled else 'off'} {s.id:28} {s.kind:20} {s.role:11} {len(s.urls)}+{len(s.optional_urls)} url(s)")
        return 0
    if args.command == "render":
        path = Path(args.snapshots) / "latest.json"
        if not path.is_file():
            print(f"{path} does not exist: no baseline has been taken yet", file=sys.stderr)
            return 1
        text = render_snapshot(json.loads(path.read_text(encoding="utf-8")), cfg)
        if args.write:
            (Path(args.snapshots) / "latest.md").write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0
    return run(args, cfg)
