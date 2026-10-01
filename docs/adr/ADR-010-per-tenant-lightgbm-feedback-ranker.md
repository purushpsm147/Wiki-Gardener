---
status: "post-validation reference — do not implement"
date: 2026-10-01
decision-makers: project owner
original-decision-date: "unknown (TODO: expand from source)"
---

# ADR-010 — Per-tenant LightGBM feedback ranker

> **Post-validation reference. Do not implement.** Out of scope for Phase −1.

## Context and Problem Statement

TODO: expand from source.

## Decision Outcome

A **per-tenant LightGBM feedback ranker** trained on admin accept/dismiss signals, with a **global-prior fallback below
N = 200 labels.** It **reorders only and never suppresses.** It is the **intended moat.** **Log features from day one.**

### Consequences

TODO: expand from source.

## Status notes

**The "log features from day one" clause applies only once there is a product.** There is none in Phase −1, so nothing is
logged and no ranker is built.

## Provenance

- Decision text and status: the project owner's ADR-history follow-up, 2026-10-01 (one-liner and note only).
- Context, drivers, options, consequences: `TODO: expand from source` ([`../source/README.md`](../source/README.md)). Nothing here
  is reconstructed from memory beyond the one-liner.
