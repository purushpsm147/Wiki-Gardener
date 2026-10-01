---
status: "accepted (pre-validation), contingent on ADR-013"
date: 2026-10-01
decision-makers: project owner
original-decision-date: "unknown (TODO: expand from source)"
---

# ADR-006 — Single Postgres with row-level security on tenant_id

## Context and Problem Statement

TODO: expand from source.

## Decision Outcome

One **Postgres** instance, with **row-level security on `tenant_id`.** Revisit around **200 tenants.**

### Consequences

TODO: expand from source.

## Status notes

**Contingent on [ADR-013](ADR-013-forge-only-vs-remote-compute.md): a Forge-only outcome removes the Postgres layer
entirely.** Until ADR-013 closes, this ADR describes the remote-compute branch only.

## Provenance

- Decision text and status: the project owner's ADR-history follow-up, 2026-10-01 (one-liner and note only).
- Context, drivers, options, consequences: `TODO: expand from source` ([`../source/README.md`](../source/README.md)). Nothing here
  is reconstructed from memory beyond the one-liner.
