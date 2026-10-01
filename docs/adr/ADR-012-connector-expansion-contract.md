---
status: "post-validation reference"
date: 2026-10-01
decision-makers: project owner
original-decision-date: "unknown (TODO: expand from source)"
---

# ADR-012 — Connector expansion contract

> **Post-validation reference.** Out of scope for Phase −1 (no connector other than Confluence).

## Context and Problem Statement

TODO: expand from source.

## Decision Outcome

New sources implement a **`SourceConnector` plus a capability matrix**, and **the pipeline is untouched.**

Sequence: **Confluence → Notion → SharePoint → Zendesk. Build none until Confluence clears its gate.**

### Consequences

TODO: expand from source.

## Provenance

- Decision text and status: the project owner's ADR-history follow-up, 2026-10-01 (one-liner only).
- Context, drivers, options, consequences: `TODO: expand from source` ([`../source/README.md`](../source/README.md)). Nothing here
  is reconstructed from memory beyond the one-liner.
- Note: the original Phase −1 bootstrap brief gave no title for ADR-012. An earlier draft plan guessed "compute placement";
  that guess was wrong (compute placement is [ADR-013](ADR-013-forge-only-vs-remote-compute.md)). See
  [`../RECONCILIATION.md`](../RECONCILIATION.md) §4.
