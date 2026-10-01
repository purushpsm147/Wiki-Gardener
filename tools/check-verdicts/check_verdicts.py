#!/usr/bin/env python3
"""Check that every spike document ends with a well-formed verdict block.

The block format is defined in docs/spikes/README.md. Rules enforced here:

* the last level-2 heading of the file is exactly "## Verdict";
* inside it, in this order: "Decision:", "Criteria evaluated:",
  "Unverified assumptions carried forward:", "What would flip this verdict:";
* the first word after "Decision:" is PROCEED, PROCEED-WITH-CONSTRAINT or KILL;
* "Criteria evaluated:" is followed by bullets, each marked PASS or FAIL;
* spikes 02-04 carry a "GATE-S<n>:" line;
* spikes 01-02 end with an "Implication for ADR-013:" line (the last non-empty line).

Usage: python check_verdicts.py [DIR ...]      default: docs/spikes
Exit status: 0 when every spike doc is well formed (or there are none), 1 otherwise.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DECISIONS = {"PROCEED", "PROCEED-WITH-CONSTRAINT", "KILL"}
FIELD_ORDER = [
    "Decision",
    "Criteria evaluated",
    "Unverified assumptions carried forward",
    "What would flip this verdict",
]
GATE_SPIKES = {2, 3, 4}
ADR013_SPIKES = {1, 2}

_FENCE = re.compile(r"^\s*(```|~~~)")
_BULLET = re.compile(r"^\s*[-*]\s+")
_PASS_FAIL = re.compile(r"\b(PASS|FAIL)\b")


def _field_re(label: str) -> re.Pattern[str]:
    # tolerate **bold** wrapping of the label, nothing else
    return re.compile(rf"^\*{{0,2}}{re.escape(label)}:\*{{0,2}}\s*(.*)$")


def _last_h2(lines: list[str]) -> int | None:
    in_fence = False
    last = None
    for i, line in enumerate(lines):
        if _FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            last = i
    return last


def check_file(path: Path) -> list[str]:
    """Return a list of human-readable problems (empty when the file is fine)."""
    problems: list[str] = []
    m = re.match(r"^(\d{2})-", path.name)
    spike = int(m.group(1)) if m else None
    lines = path.read_text(encoding="utf-8").splitlines()

    idx = _last_h2(lines)
    if idx is None or lines[idx].strip() != "## Verdict":
        return [f"{path}: the last '## ' heading must be '## Verdict'"]
    block = lines[idx + 1 :]

    # locate each required field; they must all exist and appear in order
    positions: dict[str, int] = {}
    for label in FIELD_ORDER:
        pat = _field_re(label)
        for j, line in enumerate(block):
            if pat.match(line):
                positions[label] = j
                break
        else:
            problems.append(f"{path}: verdict block is missing '{label}:'")
    if problems:
        return problems
    order = [positions[label] for label in FIELD_ORDER]
    if order != sorted(order):
        problems.append(f"{path}: verdict fields are out of order (expected {', '.join(FIELD_ORDER)})")

    # Decision value
    decision = _field_re("Decision").match(block[positions["Decision"]]).group(1).strip()  # type: ignore[union-attr]
    first = decision.split()[0] if decision else ""
    if first not in DECISIONS:
        problems.append(
            f"{path}: 'Decision:' must start with one of {sorted(DECISIONS)}, got {decision!r}"
        )

    # Criteria: bullets between "Criteria evaluated:" and the next field
    start = positions["Criteria evaluated"] + 1
    end = positions["Unverified assumptions carried forward"]
    bullets = [ln for ln in block[start:end] if _BULLET.match(ln)]
    if not bullets:
        problems.append(f"{path}: 'Criteria evaluated:' needs at least one bullet")
    for ln in bullets:
        if not _PASS_FAIL.search(ln):
            problems.append(f"{path}: criterion not marked PASS or FAIL: {ln.strip()[:80]!r}")

    if spike in GATE_SPIKES:
        gate = re.compile(rf"^\*{{0,2}}GATE-S{spike}:\*{{0,2}}\s*\S")
        if not any(gate.match(ln) for ln in block):
            problems.append(f"{path}: spike {spike:02d} needs a 'GATE-S{spike}:' line in the verdict block")

    if spike in ADR013_SPIKES:
        non_empty = [ln for ln in block if ln.strip()]
        last = non_empty[-1] if non_empty else ""
        if not re.match(r"^\*{0,2}Implication for ADR-013:\*{0,2}\s*\S", last):
            problems.append(
                f"{path}: spike {spike:02d} must end with an 'Implication for ADR-013:' line"
            )
    return problems


def spike_docs(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("[0-9][0-9]-*.md") if p.is_file())


def main(argv: list[str]) -> int:
    dirs = [Path(a) for a in argv] or [Path("docs/spikes")]
    problems: list[str] = []
    checked = 0
    for d in dirs:
        for doc in spike_docs(d):
            checked += 1
            problems.extend(check_file(doc))
    for p in problems:
        print(f"ERROR {p}")
    print(f"checked {checked} spike document(s); {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
