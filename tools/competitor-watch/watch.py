#!/usr/bin/env python3
"""Entry point: python tools/competitor-watch/watch.py run | render | check-config. Python standard library only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from competitor_watch.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
