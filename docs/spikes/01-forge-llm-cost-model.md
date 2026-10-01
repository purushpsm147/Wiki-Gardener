# Spike S1 — Forge LLM cost model

> **Status: pre-registration.** This section was committed *before* `tools/cost-model` was ever run, so the base case,
> thresholds and decision rules below cannot have been tuned to the output. Results and the verdict are added in later commits.
> Check `git log` on this file.

## Question

Is the LLM verdict stage affordable per tenant? The brief's kill criterion: *if LLM verdict cost at 50k pages exceeds ~30 % of
plausible revenue for that tier, flag KILL-OR-REDESIGN and propose the redesign.*

## Evidence rules for this spike

- `*.atlassian.com` could not be fetched from the sandbox (egress policy; see [`../RECONCILIATION.md`](../RECONCILIATION.md)), so
  **no Atlassian page was read directly.** Every Atlassian fact below is `ASSUMED (search-reported: <url>, 2026-10-01)`: a
  web-search provider's summary of that page. It is a lead, not a verification.
- Primary sources that *were* reachable are cited as `VERIFIED` with package and version: the `@forge/llm@1.0.7` and
  `@forge/manifest@13.6.0` tarballs from the npm registry, read 2026-10-01.
- Anthropic's list prices come from the `claude-api` skill's cached model table dated 2026-09-25, a local file and not a live
  fetch, and are used only as a cross-check.

## Pre-registered model

One scenario, fixed in advance. Everything is a parameter in `tools/cost-model/` and printed by `run.py`.

| Parameter | Base value | Why |
|---|---|---|
| Pages | 50,000 | the brief's kill-criterion tier |
| Funnel yield | 0.5 % of pages as candidate pairs, so **250 pairs** | brief's mid value. **Reading is ASSUMED:** pairs = pages × yield. `pair_multiplier` covers the reading where each flagged page brings several partners |
| Tokens per call | **3,000 in / 300 out** | ASSUMED: two ~500-token passages plus instructions and a JSON schema |
| Model and price | Claude Sonnet 4.5 at **$3 / $15 per 1M tokens** | the Sonnet-tier price the search summary reported for Forge |
| Calls per pair | 1 | ASSUMED |
| Monthly churn | **20 %** of pairs new or changed per month | ASSUMED. ADR-005's verdict cache means unchanged pairs never re-bill |
| Forge wait compute | 15 s at 0.5 GB per call, $0.000025 per GB-second | ASSUMED wait; price search-reported. Forge's free allowance is ignored (conservative) |
| Revenue | **1,000 users × $1.00 per user per month** = $1,000 gross | ASSUMED. Marketplace price is per *user* of the host product, not per page |
| Atlassian take | **17 %**, so $830 net | search-reported: Forge rate 83 % from 2026-10-01; reading as "partner keeps 83 %" is ASSUMED |

"Revenue" for the 30 % test is **net of the Atlassian take** (the stricter reading), not list price.

### Criteria

| ID | Criterion |
|---|---|
| **K1** | Base case: steady-state monthly LLM cost is at most 30 % of net revenue |
| **K2** | Page-heavy, user-light tenant (250 users at $0.50; 2 % yield; 12k/500-token prompts): at most 30 % |
| **K3** | Stress (250 users at $0.50; 2 % yield; 20k/800-token prompts; Claude Opus 4.6; every pair re-judged monthly): at most 30 % |
| **K4** | A 50k-page backfill completes within 24 h under the Forge LLM rate limits |

### Decision rules (fixed before running)

1. **K1 fails ⇒ KILL**, flagged KILL-OR-REDESIGN, with a redesign proposed (LLM-free only; narrower prompts; pair cap; BYO key).
2. K1 passes and **K2 or K3 fails ⇒ PROCEED-WITH-CONSTRAINT**, naming the constraint (per-tenant verdict budget, cheaper default
   model).
3. K4 failing is a constraint (time to first report), not a kill.
4. **All pass ⇒ PROCEED, but** while any input price is not `VERIFIED` the decision is capped at PROCEED-WITH-CONSTRAINT with the
   constraint "confirm prices locally". Every Atlassian price here is search-reported, so this cap applies.
