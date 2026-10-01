# Phase −1 spikes

Four hostile fact-finding spikes. Their job is to try to kill the idea cheaply, and each one ends in a written
verdict. They exist because [ADR-000](../adr/ADR-000-phase-minus-1-fact-finding-precedes-invariants.md) forbids
product pipeline code until the wedge is validated with real admins.

| # | File | Gate | Feeds |
|---|---|---|---|
| S1 | `01-forge-llm-cost-model.md` | — (kill criterion: LLM cost > ~30 % of plausible revenue at 50k pages ⇒ KILL-OR-REDESIGN) | [ADR-013](../adr/ADR-013-forge-only-vs-remote-compute.md), ADR-011 |
| S2 | `02-forge-only-compute-feasibility.md` | **GATE-S2** | [ADR-013](../adr/ADR-013-forge-only-vs-remote-compute.md), ADR-006, ADR-007 |
| S3 | `03-change-time-trigger-poc.md` | **GATE-S3** | A3 shape, ADR-008 |
| S4 | `04-competitor-watch.md` | **GATE-S4** | differentiation thesis |

The spike documents arrive with their own pull requests, so some links above resolve only after those merge.

## Gates

Defined by the project owner (the v3 addendum, which is **not yet in the repo**, is the authoritative text; the wording
below is from the owner's summary of 2026-10-01):

- **GATE-S2** — a written verdict of the form *"Forge-only supports up to N pages with architecture X"* or
  *"Forge-only impossible beyond N because Y (measured)"*. If "measured" is impossible from the environment, say
  **estimated** and show the arithmetic.
- **GATE-S3** — the demo of *"editor changes '90 days' to '30 days' on a procedure page → within minutes, a logged conflict
  against the approved policy page, with both quotes and offsets."*
- **GATE-S4** — with a kill clause: *if Evergreen ships change-time prevention before our decision point, the
  differentiation thesis is re-argued from scratch in writing.*

## Verdict block (every spike must end with this)

Rendered as one field per paragraph, in this order. `GATE-S#:` (S2–S4) and `Implication for ADR-013:` (S1–S2, last
line) are required additions. `tools/check-verdicts` enforces the shape in CI.

```
## Verdict

Decision: PROCEED | PROCEED-WITH-CONSTRAINT | KILL

GATE-S#: <one-sentence gate result>                    (S2, S3, S4 only)

Criteria evaluated:
- <criterion> — PASS|FAIL — <evidence>

Unverified assumptions carried forward: <list or "none">

What would flip this verdict: <one or two concrete observations>

Implication for ADR-013: <one or two sentences>         (S1, S2 only; must be the last line)
```

## Evidence grades

See the [README](../../README.md#evidence-grades): **VERIFIED** (primary source read here, cited with URL/package and UTC
date) or **ASSUMED**, with `ASSUMED (search-reported: <url>, <date>)` for claims that rest on a web-search summary. Numbers
are additionally **MEASURED** or **ESTIMATED**.

Environment note: while these spikes were written, `*.atlassian.com` was blocked by the sandbox egress policy. Each spike
therefore ends with a "confirm locally" table of exact URLs and the claim each one must support.
