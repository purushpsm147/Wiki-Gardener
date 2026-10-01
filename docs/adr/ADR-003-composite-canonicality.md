---
status: "accepted (pre-validation)"
date: 2026-10-01
decision-makers: project owner
original-decision-date: "unknown (TODO: expand from source)"
---

# ADR-003 — Composite canonicality over pure PageRank

## Context and Problem Statement

TODO: expand from source.

## Decision Outcome

Canonicality (which page is the authoritative one) is scored as a **composite**, not by PageRank alone. Hierarchy, recency
and views are co-signals alongside link-graph rank.

Stated rationale (owner summary, 2026-10-01): sparse wiki graphs make rank alone non-discriminative.

### Consequences

TODO: expand from source.

## Status notes

**Canonicality is out of Conflict Radar scope; it is retained for the proceed case.** See also
[A05](amendments/A05.md) (canonicality demotion and recall honesty; provisional number).

## Provenance

- Decision text and status: the project owner's ADR-history follow-up, 2026-10-01 (one-liner and note only).
- Context, drivers, options, consequences: `TODO: expand from source` ([`../source/README.md`](../source/README.md)). Nothing here
  is reconstructed from memory beyond the one-liner.
