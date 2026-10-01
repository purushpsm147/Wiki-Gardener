#!/usr/bin/env python3
"""Print the Spike S2 budget tables.

    python tools/compute-budget/run.py            print to stdout
    python tools/compute-budget/run.py --write    rewrite tools/compute-budget/BUDGET.md
    python tools/compute-budget/run.py --check    exit 1 if BUDGET.md is stale

Regenerate the measurements first, if you want fresh ones:
    node --expose-gc tools/compute-budget/bench/minhash-bench.mjs --out tools/compute-budget/bench/results.json
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import report  # noqa: E402

TARGET = HERE / "BUDGET.md"


def main(argv: list[str]) -> int:
    text = report.render_report()
    if "--write" in argv:
        TARGET.write_text(text, encoding="utf-8")
        print(f"wrote {TARGET}")
        return 0
    if "--check" in argv:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != text:
            print("BUDGET.md is stale: run `python tools/compute-budget/run.py --write`", file=sys.stderr)
            return 1
        print("BUDGET.md is up to date")
        return 0
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
