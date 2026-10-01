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

Written 2026-10-01 from the four spike verdicts. **This is evidence, not a decision. The decision rule is missing (above), so it
has not been applied.** Every Atlassian number is `ASSUMED (search-reported)` unless marked otherwise: no Atlassian page could be
fetched from the environment that produced it, and each spike ends with a table of the exact URLs to confirm locally.

| Input | Source | What it found | Grade |
|---|---|---|---|
| **S1**: LLM verdict cost | [`S1`](../spikes/01-forge-llm-cost-model.md), [PR #1](https://github.com/purushpsm147/Wiki-Gardener/pull/1), PROCEED-WITH-CONSTRAINT | At the brief's funnel yields the verdict stage is about 0.08 % of net revenue at 50k pages ($0.68 against $830 a month). The deliberately hostile K3 corner fails (116 %), and Forge LLM costs are billed to the developer with no pass-through, so a hard per-tenant verdict budget is needed. Rovo may not be callable from a background backend. The Runs-on-Atlassian revenue-share window is worth up to about $170k. | model tested (23 tests); prices and limits search-reported |
| **S2** / GATE-S2: Forge-only compute | [`S2`](../spikes/02-forge-only-compute-feasibility.md), [PR #2](https://github.com/purushpsm147/Wiki-Gardener/pull/2), PROCEED-WITH-CONSTRAINT | Forge-only supports up to about 300k pages per tenant (175k to 370k, depending on an unmeasured SQL row overhead) with Architecture X: Forge SQL, cursor-chained async workers, no remotes. Platform cost about $0.27 per tenant per month. The Confluence REST quota (65,000 points an hour for the whole app) binds every architecture, a remote backend included. | ESTIMATED; limits search-reported; manifest schema facts VERIFIED |
| **S3**: change-time trigger PoC (supporting) | [`S3`](../spikes/03-change-time-trigger-poc.md), [PR #3](https://github.com/purushpsm147/Wiki-Gardener/pull/3), PROCEED-WITH-CONSTRAINT | The change-time check runs as a Forge app that is Runs-on-Atlassian eligible by construction (manifest validated offline) and needs no remote. Its per-edit read pattern costs 4 + 2N REST points for N approved pages, which shows that the approved text must be cached and indexed in any architecture. | validator VERIFIED; live behaviour and latency not measured |
| **S4**: competitors (supporting) | [`S4`](../spikes/04-competitor-watch.md), [PR #4](https://github.com/purushpsm147/Wiki-Gardener/pull/4), PROCEED-WITH-CONSTRAINT | Nothing about compute. Relevant only because a "Runs on Atlassian, your data never leaves Atlassian" claim is part of the differentiation, and it is the thing a remote backend would forfeit. | search-reported |
| **Pilot security requirements** (Phase V) | does not exist yet | whether pilot administrators' security reviews accept data leaving Atlassian, and how much weight "Runs on Atlassian" carries | none |
| **Decision rule** | v3 addendum | **missing** | none |

### The implication each spike drew, verbatim

> **S1:** LLM economics neither force nor favour remote compute: the verdict stage costs about 0.1 % of net revenue at the assumed
> yield, so S1 gives no economic reason to leave Forge, while the only customer-billed route (BYO key) needs external egress and
> would forfeit Runs on Atlassian, and with it the revenue-share window worth up to about $170k (search-reported).

> **S2:** Forge-only is feasible for the classical pipeline at 50k pages and, on estimate, up to about 300k, so the Runs-on-Atlassian
> path survives S2 and compute and storage give no reason to go remote; the binding limits (Confluence REST points and Forge LLM
> tokens per minute) apply to a remote backend as well, which would add a database, A07 token chunking and the loss of Runs on
> Atlassian, so S2 favours Forge-only pending the decision rule and Phase V pilot security input.

### What the evidence leans towards, and what could change it

It leans **Forge-only**: nothing found gives a technical or economic reason to leave Forge, the one quota that binds applies to a
remote backend equally, and a remote backend adds a database, token chunking ([A07](amendments/A07.md)), per-tenant data residency
and a security review at every customer while forfeiting Runs on Atlassian. **Leaning is not a decision rule**, and the rule is not
in this repository.

What could move it, each unmeasured today:

- the Forge limits and prices differ materially from the search-reported ones (for example function memory: the manifest schema
  allows 4,096 MB while the documentation is reported to cap it at 1,024), or Forge SQL and Containers turn out not to be
  Runs-on-Atlassian eligible;
- a measured Forge SQL footprint above about 2,100 bytes per page (G1 in S2), which lowers the ceiling from about 300k pages
  towards about 240k, and does not touch 50k;
- Atlassian declining a per-tenant quota (Tier 2) review, which caps onboarding on every architecture and is not an argument for a
  remote one;
- Phase V: pilot administrators who accept data leaving Atlassian and do not value the badge, which would remove the main reason to
  stay inside.

## Decision Outcome

**Status: Open.** It cannot close on current evidence for two independent reasons:

1. the decision rule text is missing from this repo, so it cannot be applied; and
2. one of its three inputs, the pilot security requirements from Phase V, does not exist yet.

The evidence in the table above leans Forge-only. That is a reading of the evidence, not an application of the rule.

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
- Evidence table: the four spike documents and their verdict blocks, written the same day; the implication lines are quoted
  verbatim from the S1 and S2 verdict blocks.
- The decision rule is **not** reproduced anywhere in this repo.
