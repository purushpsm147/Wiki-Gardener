---
status: "deferred"
date: 2026-10-01
decision-makers: project owner
original-decision-date: "unknown (TODO: expand from source)"
---

# ADR-009 — Staleness as a prior, modulated by hard signals

## Context and Problem Statement

TODO: expand from source.

## Decision Outcome

Staleness is scored as `S = I·(1 − e^(−λt))`, used **as a prior**, and **modulated by hard signals**: broken links,
departed author, superseded references, past dates. **Age alone caps at medium severity.**

The symbols `I`, `λ` and `t` are not defined in the owner's summary. `TODO: expand from source`; they are not guessed here.

### Consequences

TODO: expand from source.

## Status notes

**Out of Conflict Radar scope. Status: Deferred.** Atlassian's Rovo Documentation Agent is reported to cover staleness
natively (project brief; **ASSUMED**, re-checked by Spike 4).

## Provenance

- Decision text and status: the project owner's ADR-history follow-up, 2026-10-01 (one-liner and note only).
- Context, drivers, options, consequences: `TODO: expand from source` ([`../source/README.md`](../source/README.md)). Nothing here
  is reconstructed from memory beyond the one-liner.
