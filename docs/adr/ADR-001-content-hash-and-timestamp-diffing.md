---
status: "accepted (pre-validation)"
date: 2026-10-01
decision-makers: project owner
original-decision-date: "unknown (TODO: expand from source)"
---

# ADR-001 — Content-hash + timestamp diffing for incremental sync

## Context and Problem Statement

TODO: expand from source.

## Decision Outcome

Incremental sync detects change by **content hash plus timestamp**. A **Bloom filter is explicitly banned.**

Stated rationale (owner summary, 2026-10-01): exact comparison is cheap at wiki scale, and false positives buy nothing.

### Consequences

TODO: expand from source.

## Provenance

- Decision text and status: the project owner's ADR-history follow-up, 2026-10-01 (one-liner only).
- Context, drivers, options, consequences: `TODO: expand from source`. `docs/source/conflict-radar-v3-addendum.md` and
  `docs/source/wiki-gardener-prompt-set.md` are not yet in the repo ([`../source/README.md`](../source/README.md)). Nothing
  here is reconstructed from memory beyond the one-liner.
