---
status: "accepted"
date: 2026-10-01
decision-makers: project owner
original-decision-date: "unknown (TODO: expand from source)"
---

# ADR-004 — Suggest-only by default

## Context and Problem Statement

TODO: expand from source.

## Decision Outcome

The system is **suggest-only by default.** Any write requires all of: a **dry-run**, an **explicit confirm**, an **audit
entry** and an **undo**, and is executed **Forge-side under Atlassian auth.**

### Consequences

TODO: expand from source.

## Status notes

**Conflict Radar is read-only, so this ADR is currently a non-issue. Keep it for the proceed case.**

## Provenance

- Decision text and status: the project owner's ADR-history follow-up, 2026-10-01 (one-liner and note only).
- Context, drivers, options, consequences: `TODO: expand from source` ([`../source/README.md`](../source/README.md)). Nothing here
  is reconstructed from memory beyond the one-liner.
