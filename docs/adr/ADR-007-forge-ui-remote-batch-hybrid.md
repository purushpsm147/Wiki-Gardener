---
status: "superseded pending ADR-013"
date: 2026-10-01
decision-makers: project owner
original-decision-date: "unknown (TODO: expand from source)"
---

# ADR-007 — Forge UI + remote batch backend (hybrid)

## Context and Problem Statement

TODO: expand from source.

## Decision Outcome

A **hybrid**: Forge for the UI, with a **remote batch backend** for the heavy work. The original record reads
**"expected: remote."**

### Consequences

TODO: expand from source.

## Status notes

**Superseded pending [ADR-013](ADR-013-forge-only-vs-remote-compute.md).** Whether compute runs remotely or inside Forge is
the open fork. The original brief's framing of Forge-only as the default, with remote compute as a fallback, differs from
this ADR's original "expected: remote"; ADR-013 holds the live decision. If a remote backend survives, see
[A07](amendments/A07.md) (chunked, checkpointed worker for Forge Remote token lifetime; provisional number).

## Provenance

- Decision text and status: the project owner's ADR-history follow-up, 2026-10-01 (one-liner and note only).
- Context, drivers, options, consequences: `TODO: expand from source` ([`../source/README.md`](../source/README.md)). Nothing here
  is reconstructed from memory beyond the one-liner.
