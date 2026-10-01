#!/usr/bin/env python3
"""Print the Spike S1 sensitivity tables.

    python tools/cost-model/run.py            print to stdout
    python tools/cost-model/run.py --write    rewrite tools/cost-model/SENSITIVITY.md
    python tools/cost-model/run.py --check    exit 1 if SENSITIVITY.md is stale
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import report  # noqa: E402

TARGET = HERE / "SENSITIVITY.md"


def main(argv: list[str]) -> int:
    text = report.render_report()
    if "--write" in argv:
        TARGET.write_text(text, encoding="utf-8")
        print(f"wrote {TARGET}")
        return 0
    if "--check" in argv:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != text:
            print("SENSITIVITY.md is stale: run `python tools/cost-model/run.py --write`", file=sys.stderr)
            return 1
        print("SENSITIVITY.md is up to date")
        return 0
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
