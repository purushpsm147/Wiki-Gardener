---
status: "open"
date: 2026-10-01
decision-makers: project owner
---

# ADR-013 — Forge-only vs remote compute

## Context and Problem Statement

Where does the compute run: **entirely inside Forge**, or on a **remote backend**? This is the open fork in the architecture.

- The Forge-only branch keeps the "Runs on Atlassian" trust signal and removes the Postgres layer
  ([ADR-006](ADR-006-single-postgres-rls.md)), but depends on Forge limits (S2) and on Forge LLM economics (S1).
- The remote branch is the hybrid in [ADR-007](ADR-007-forge-ui-remote-batch-hybrid.md) (superseded pending this ADR). It
  adds a remote runtime, a data store, and an egress question for pilot customers' security reviews.

TODO: expand from source (`docs/source/conflict-radar-v3-addendum.md`, pending).

## Inputs

1. **S1:** LLM verdict cost ([`../spikes/01-forge-llm-cost-model.md`](../spikes/01-forge-llm-cost-model.md)).
2. **S2 / GATE-S2:** Forge compute feasibility ([`../spikes/02-forge-only-compute-feasibility.md`](../spikes/02-forge-only-compute-feasibility.md)).
3. **Pilot security requirements from Phase V.** Not available before Phase V; no code is needed to collect them
   ([`../phase-v/interview-script.md`](../phase-v/interview-script.md)).

## Decision Rule

> **PENDING SOURCE.** The decision rule is stated in `docs/source/conflict-radar-v3-addendum.md`, which is not in the repo.
> It is **not reproduced, paraphrased or improvised here.** Copy it verbatim when the file arrives, then apply it to the
> evidence table below.

## Evidence so far

TODO: fill from the S1 and S2 verdicts (written when those spikes land; see the end-state summary in
[`../PHASE-MINUS-1-SUMMARY.md`](../PHASE-MINUS-1-SUMMARY.md)).

## Decision Outcome

**Status: Open.** It cannot close on current evidence for two independent reasons:

1. the decision rule text is missing from this repo, so it cannot be applied; and
2. one of its three inputs, the pilot security requirements from Phase V, does not exist yet.

Exact inputs still needed to close it:

- the decision rule (copy verbatim from the addendum);
- Phase V: whether pilot admins' security reviews accept data leaving Atlassian (remote compute), and how much weight
  "Runs on Atlassian" carries in their approval.

### Consequences

- [ADR-006](ADR-006-single-postgres-rls.md) is contingent on this ADR.
- [ADR-007](ADR-007-forge-ui-remote-batch-hybrid.md) is superseded pending this ADR.
- If a remote backend survives: [A07](amendments/A07.md) applies (chunked, checkpointed worker; provisional number).

## Provenance

- Decision framing and status: the project owner's ADR-history follow-up, 2026-10-01 ("open fork"; inputs S1, S2 and pilot
  security requirements from Phase V; decision rule lives in the v3 addendum).
- The decision rule is **not** reproduced anywhere in this repo.
