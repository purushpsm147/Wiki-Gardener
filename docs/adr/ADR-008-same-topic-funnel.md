---
status: "accepted (pre-validation); amended by A1–A11 where the addendum says so"
date: 2026-10-01
decision-makers: project owner
original-decision-date: "unknown (TODO: expand from source)"
---

# ADR-008 — Same-topic funnel: TF-IDF cosine first

## Context and Problem Statement

TODO: expand from source.

## Decision Outcome

The same-topic funnel starts with **TF-IDF cosine.** **Local MiniLM embeddings are used only if the funnel precision gate
fails.** **The LLM is never used for funneling.**

### Consequences

TODO: expand from source.

## Status notes

Amended by the v3 addendum's amendments (A1–A11) **where the addendum says so**. Which amendments touch this ADR is
`TODO: expand from source`. By topic, [A01](amendments/A01.md), [A02](amendments/A02.md), [A03](amendments/A03.md) and
[A04](amendments/A04.md) are the likely ones (*inferred; confirm from source; amendment numbers other than A3 are provisional*).

The Spike 3 proof of concept uses TF-IDF cosine for sentence alignment, consistent with this ADR, and **has no upper
similarity cut-off** (see [A03](amendments/A03.md)).

## Provenance

- Decision text and status: the project owner's ADR-history follow-up, 2026-10-01 (one-liner and note only).
- Context, drivers, options, consequences: `TODO: expand from source` ([`../source/README.md`](../source/README.md)). Nothing here
  is reconstructed from memory beyond the one-liner.
