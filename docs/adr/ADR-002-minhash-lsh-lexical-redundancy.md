---
status: "accepted (pre-validation)"
date: 2026-10-01
decision-makers: project owner
original-decision-date: "unknown (TODO: expand from source)"
---

# ADR-002 — MinHash/LSH, lexical, not embeddings, for redundancy

## Context and Problem Statement

TODO: expand from source.

## Decision Outcome

Redundancy detection uses **MinHash/LSH over lexical features, not embeddings.**

Stated rationale (owner summary, 2026-10-01): dedup is a copy-paste problem, so determinism, cost and explainability
decide it.

### Consequences

TODO: expand from source.

## Related

Likely touched by amendments [A01](amendments/A01.md) (containment joins), [A02](amendments/A02.md) (cohesion-constrained
clustering) and [A03](amendments/A03.md) (near-duplicate divergence). *Inferred from the amendment topics; confirm
from source.* The S2 spike sizes the MinHash/LSH state this ADR implies.

## Provenance

- Decision text and status: the project owner's ADR-history follow-up, 2026-10-01 (one-liner only).
- Context, drivers, options, consequences: `TODO: expand from source` ([`../source/README.md`](../source/README.md)). Nothing here
  is reconstructed from memory beyond the one-liner.
