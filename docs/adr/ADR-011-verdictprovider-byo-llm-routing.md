---
status: "post-validation reference"
date: 2026-10-01
decision-makers: project owner
original-decision-date: "unknown (TODO: expand from source)"
---

# ADR-011 — VerdictProvider abstraction and BYO-LLM routing

> **Post-validation reference.** Out of scope for Phase −1.

## Context and Problem Statement

TODO: expand from source.

## Decision Outcome

A **`VerdictProvider` abstraction with BYO-LLM routing.**

- `RovoProvider` is the **default (in-tenant).**
- `AnthropicProvider` is the **fallback.**
- `CopilotProvider` and `GenericOpenAICompat` come **later.**

**Invariant:** the funnel, budget, cache, schema validation and quote verification **wrap every provider identically**, and
**provider + model_version are stored on every verdict.**

### Consequences

TODO: expand from source.

## Status notes

The brief's original framing was "Rovo-first". Whether a Rovo-hosted verdict is billed to the tenant or to the app developer
is exactly the unverified assumption that demoted the v2 plan ([ADR-000](ADR-000-phase-minus-1-fact-finding-precedes-invariants.md)).
Spike S1 records what could and could not be established about Forge LLM billing.

## Provenance

- Decision text and status: the project owner's ADR-history follow-up, 2026-10-01 (one-liner and note only).
- Context, drivers, options, consequences: `TODO: expand from source` ([`../source/README.md`](../source/README.md)). Nothing here
  is reconstructed from memory beyond the one-liner.
