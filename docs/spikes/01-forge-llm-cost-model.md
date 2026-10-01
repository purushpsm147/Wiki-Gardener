# Spike S1 — Forge LLM cost model

> **Status: results added.** The *Pre-registered model* section below is unchanged since commit `9f085c5`, which was pushed
> **before** `tools/cost-model` was first run (`git log -- docs/spikes/01-forge-llm-cost-model.md`). Everything after it is result.

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

## Result in one paragraph

At the brief's funnel yields the LLM verdict stage is **not** the cost problem. The base case spends **$0.68 a month** on tokens
(**0.08 %** of $830 net revenue); the funnel could pass about **92,000 candidate pairs, 369× the base case**, before the 30 % line.
K1, K2 and K4 pass. Only the deliberately hostile K3 corner fails (116 %). By the rules fixed in advance that gives
**PROCEED-WITH-CONSTRAINT**. The real risks are elsewhere: the funnel yield is an *unmeasured* input; nothing here is `VERIFIED`
against an Atlassian page; Rovo may not be callable from a backend at all; and the revenue-share window rewards staying
Runs-on-Atlassian.

## What was established about Forge LLMs

Fetch date for every row: **2026-10-01**. Grade `ASSUMED (search-reported)` means a web-search summary, not the page.

| Claim | Value | Grade | Source |
|---|---|---|---|
| Billing party | Forge LLM usage is charged to the **app developer** and counted toward the developer's monthly Forge bill. **No free monthly quota**; all tokens billed | ASSUMED (search-reported; the same statement came back from three differently-worded queries) | [Forge LLMs pricing](https://developer.atlassian.com/platform/forge/runtime-reference/forge-llms-api-pricing/) |
| Per-token price (in / out per 1M) | Haiku 4.5 **$1 / $5**; Sonnet 4.5 **$3 / $15**; Opus 4.6 **$5 / $25** | ASSUMED (search-reported) | same page |
| Credits | **$0.10 per 1M input credits, $0.50 per 1M output credits**; Haiku 10, Sonnet 30, Opus 50 credits per token. The summary wrote "per 1M tokens", which is arithmetically inconsistent; the per-token reading matches the dollar prices (`tests/` checks this) | ASSUMED (search-reported); internal consistency checked | same page |
| Price parity with Anthropic | The three Forge prices equal Anthropic's first-party list prices for the same models (Haiku 4.5 $1/$5, Sonnet 4.6 $3/$15, Opus 4.6 $5/$25) | Anthropic side: local skill file, 2026-09-25. **Inference:** Forge passes list price through | `claude-api` skill table |
| Models Forge supports | Haiku 4.5, Sonnet 4.5, Sonnet 4.6, **Sonnet 5**, Opus 4.6, **4.7**, **4.8**. **No Forge price found** for Sonnet 5, Opus 4.7 or 4.8; the model assumes parity (Sonnet 5 at $2 / $10) | ASSUMED (search-reported) for the list; parity ASSUMED | [Models](https://developer.atlassian.com/platform/forge/runtime-reference/forge-llms-models/) |
| Rate limits | **100 requests/min**; **50,000 tokens/min per installation, per model** | ASSUMED (search-reported) | [Forge LLM limits](https://developer.atlassian.com/platform/forge/limits-llm/) |
| Context window | 200,000 tokens | ASSUMED (search-reported) | same page |
| Compute inflation | An LLM call raises Forge function compute **15× to 27×** versus typical apps because the function waits on the model; GB-seconds are billed on top of tokens | ASSUMED (search-reported) | [RFC-117 clarification](https://community.developer.atlassian.com/t/rfc-117-clarification-on-forge-llms-compute-usage-and-pricing/98220) |
| Function compute | **$0.000025 per GB-second**; 200,000 GB-seconds free per month; billing from 2026-01-01 | ASSUMED (search-reported) | [Forge platform pricing](https://developer.atlassian.com/platform/forge/forge-platform-pricing/) |
| Availability | A "now GA" announcement exists; the pricing, models and reference pages are still titled "(Preview)". Date and scope of GA not captured | ASSUMED (search-reported); **sources disagree** | [GA post](https://www.atlassian.com/blog/development/forge-llms-api-is-now-ga-heres-how-you-can-build-ai-native-apps-on-atlassian) |
| Marketplace-partner programs | **None found** (no free credits or discount for Forge LLM tokens). Absence in search results is weak evidence | ASSUMED | searches 2026-10-01 |

### Read directly from npm packages (primary, `VERIFIED`)

Source: registry.npmjs.org, tarballs fetched **2026-10-01**.

- `@forge/llm@1.0.7` (modified 2026-09-29). Responses carry `usage: { input_tokens, output_tokens, total_tokens }` **per call**, so
  spend can be metered exactly. The model list is **dynamic**: `list()` returns `{ model, status: "active" | "deprecated" }`, so
  models can be retired under the app (hence `model_version` in the ADR-005 cache key). Client-side validation only requires a
  positive integer `max_completion_tokens`, `temperature` and `top_p` in [0, 1], and roles `system|user|assistant|tool`; no output
  cap is enforced client-side, so the server-side cap is unknown.
- `@forge/manifest@13.6.0` (modified 2026-10-01). The `llm` module takes `model: ["claude"]` (a family, not a model id) and the
  schema **forbids `unlicensedAccess`** on it.

## Rovo is not a background verdict provider (ADR-011)

ADR-011 makes `RovoProvider` the default, in-tenant provider. Searches returned, `ASSUMED (search-reported)`:

- A Rovo agent **cannot be triggered from a Forge function**; the thread states it is "not part of the Forge roadmap", and the
  `bridge.rovo` API only opens the Rovo chat sidebar **from the UI** ([thread](https://community.developer.atlassian.com/t/trigger-a-rovo-agent-from-a-forge-function/87749),
  [bridge API](https://developer.atlassian.com/platform/forge/apis-reference/ui-api-bridge/rovo/)). **The thread's date is unknown and it may be stale.**
- Rovo credits for an agent's AI interaction are paid by the **customer's** pooled allowance, while the developer pays Forge
  compute, storage and logs for the agent's actions.

If both hold, a customer-billed verdict exists **only when a human invokes an agent interactively**. A background funnel can only
use the Forge LLMs API, which the developer pays for. "Rovo-first, in-tenant" would then be the *UI* path, not the pipeline.

## Marketplace revenue share (and why it touches ADR-013)

`ASSUMED (search-reported)`, [Updates to Marketplace revenue share: 2026](https://www.atlassian.com/blog/development/updates-to-marketplace-revenue-share-2026), 2026-10-01:

- Forge apps: **84 %** from 2026-04-01, **83 % from 2026-10-01** (today). Connect: 80 % then 75 %.
- **100 % until $1M lifetime Forge revenue**, described as being for **qualifying Runs on Atlassian apps**. Lifetime revenue is counted per
  partner across all their Forge apps.
- A Forge app may use **Forge remotes** and still get the Forge rate. Whether a **remote-backed** app also gets the 100 % window was
  **not established.**
- Reading "revenue share rate" as the share the *partner keeps* (so Atlassian takes 17 %) is **ASSUMED**.

On that reading the Runs-on-Atlassian window is worth up to **17 % × $1,000,000 = $170,000**. That is an economic reason to stay
Forge-only that the architecture brief does not mention.

## Comparable prices

Marketplace price is per **user of the host product** in tiers (the 1–10 tier can be $0), billed on the host's cycle
([billing doc, search-reported](https://support.atlassian.com/subscriptions-and-billing/docs/understand-billing-for-cloud-apps/)).
**Revenue therefore scales with users while LLM cost scales with pages.**

Price points that came back, all `ASSUMED (search-reported)` and **none a content-quality competitor**:

| Listing | Reported price |
|---|---|
| [FreshPage](https://marketplace.atlassian.com/apps/1059183334/freshpage-trusted-knowledge-for-confluence) | free up to 10 users; "$13.97 per month for 11 or more users" (ambiguous: tier total or per user) |
| [Airtable for Confluence](https://marketplace.atlassian.com/apps/1222040/airtable-for-confluence?tab=pricing) | $2.10–$2.31 per user per month |
| [Analytics Bundle+](https://marketplace.atlassian.com/apps/1225803?tab=pricing&hosting=cloud) | $5–$19.03 per user per month |

**Not obtained:** prices for Better Content Archiving and Analytics, AI Hygiene Inspector, Content Retention Manager, Scroll Content
Manager. The summaries said pricing was not in the indexed page. The model therefore uses a **price grid ($0.25–$4 per user per
month, ASSUMED)** and reports break-even revenue instead of betting on one number. **Compare the break-even to the real listing
prices** (see *Confirm locally*).

## Results

Full tables: [`tools/cost-model/SENSITIVITY.md`](../../tools/cost-model/SENSITIVITY.md) (generated; a test fails if stale). Reproduce
with `python tools/cost-model/run.py`.

### Pre-registered criteria

| ID | Criterion | Result | Verdict |
|---|---|---|---|
| K1 | Base case: at most 30 % of net revenue | **0.08 %** ($0.675 of $830) | PASS |
| K2 | 250 users at $0.50; 2 % yield; T3 | **8.4 %** | PASS |
| K3 | Stress: 2 % yield, T4, Opus 4.6, 100 % churn | **116 %** ($120 of $103.75) | **FAIL** |
| K4 | 50k backfill within 24 h | **16 min** | PASS |

### Monthly LLM cost (base prompt and model, 20 % churn)

| Pages \ yield | 0.1 % | 0.5 % | 2 % |
|---|---|---|---|
| 10k | $0.027 | $0.135 | $0.540 |
| 50k | $0.135 | **$0.675** | $2.70 |
| 250k | $0.675 | $3.38 | $13.50 |

One-time backfill at 50k pages and 0.5 % is **$3.38**; at 250k pages and 2 % it is $67.50.

### Where it breaks

- **Break-even** (net monthly revenue for LLM to stay under 30 %): **$2.25** at 50k pages and 0.5 %; **$45** at 250k pages and 2 %.
- **Yield multiplier:** each flagged page would have to bring about **369 partners** at the base prompt size before K1 flips. The
  alternative reading of "yield" (×5, ×20, ×100) costs 0.4 %, 1.6 % and 8.1 % of net revenue.
- **Revenue floor:** under the stress cost ($120 a month), tenants below about **$400 net revenue a month** (about $482 gross; for
  example 100 users at $4) are over the line (table E3). Under section-level prompts (E2) only 100 users at $0.25 crosses 30 %.
- **Throughput:** 16 min for a 50k-page backfill, but **5.5 h** at 250k pages and 2 % yield under the 50,000 tokens/min limit.
  Backfills for the largest tenants are an overnight job and need a resumable queue.

## Gross-margin implication

On the LLM stage plus the Forge wait time, margin at 1,000 users and $1.00 is **99.9 %** for the base case and **99.99 %** with
Haiku-class prices and A3-shaped prompts (T1). Under the K3 stress cost it is **85.5 %** (17 % take) to **88.0 %** (0 % take).
**The LLM is not what decides gross margin.** Not modelled: Forge storage (KVS or SQL), the classical pipeline's compute (Spike
S2), payment fees and support. The LLM-free A3 detector costs nothing here.

## Redesign options (needed for the K3 stress corner, not for the base case)

Ranked by how much they preserve:

1. **Per-tenant monthly verdict budget** with a hard stop and an admin-visible counter. Costs are developer-billed with no
   pass-through, so an uncapped tenant is an uncapped liability.
2. **A3-shaped prompts (T1):** hand the verdict stage only the differing spans. It is about 2.6× cheaper (table C1: $0.263 vs $0.675 a month).
3. **Cheaper default model:** Haiku 4.5 is about 3× cheaper than Sonnet 4.5; Sonnet 5 about 1.5× if its Forge price follows list.
4. **Pair cap per page** at the funnel; the ADR-005 cache already removes repeats.
5. **LLM-free only:** the A3 detector alone, with a human verdict (the concierge audit in [`../phase-v/`](../phase-v/concierge-scanner-spec.md)).
6. **Customer BYO key:** moves cost to the customer but needs **external egress**, so the app can no longer be Runs on Atlassian
   (see S2 and ADR-013). It is the only customer-billed route if Rovo cannot be called from a backend.

## What the brief got wrong, or leaves unsaid

- **Confirmed, not wrong:** Forge LLMs are developer-billed (search-reported), which matches the conceded mistake in the brief.
- **ADR-011's default provider** (`RovoProvider`, in-tenant) may not be callable from a background pipeline. Treat as a risk to
  check, not a fact.
- **Revenue is per user, cost is per page.** The brief frames the kill criterion per page-tier; the relevant axis is pages *per
  user*.
- **The Runs-on-Atlassian revenue window** (up to ~$170k) is a missing input to the Forge-vs-remote decision.

## What this spike does not prove

- The **funnel yield** (0.1–2 % of pages) is the brief's number, not a measurement. Everything scales linearly with it.
- **Token profiles, churn, users and price** are assumptions; the break-even tables are the defence against being wrong about them.
- **Verdict quality** is untested: this says what an LLM stage would cost, not whether it earns that cost over the LLM-free A3
  detector.
- **No Atlassian number is `VERIFIED`.** The verdict is conditional on the confirmations below.

## Confirm locally

Open each URL, check the claim, and update the grade in `tools/cost-model/prices.json`, then re-run `python tools/cost-model/run.py --write`.

| # | URL | What it must say |
|---|---|---|
| 1 | https://developer.atlassian.com/platform/forge/runtime-reference/forge-llms-api-pricing/ | Per-token prices above; credits $0.10 / $0.50 per 1M; no free quota; **billed to the developer**; **prices for Sonnet 5 and Opus 4.7/4.8** (missing) |
| 2 | https://developer.atlassian.com/platform/forge/limits-llm/ | 100 requests/min; 50,000 tokens/min per installation per model; 200k context; **whether TPM counts input + output**; any output-token cap |
| 3 | https://developer.atlassian.com/platform/forge/runtime-reference/forge-llms-models/ | Supported models; Preview vs GA |
| 4 | https://developer.atlassian.com/platform/forge/forge-platform-pricing/ | $0.000025 per GB-second; 200,000 free; whether the free allowance is per app or per developer |
| 5 | https://community.developer.atlassian.com/t/rfc-117-clarification-on-forge-llms-compute-usage-and-pricing/98220 | 15–27× compute inflation |
| 6 | https://www.atlassian.com/blog/development/updates-to-marketplace-revenue-share-2026 | 83 % from 2026-10-01; **whether that is the partner's share**; 100 % window and its eligibility |
| 7 | https://www.atlassian.com/blog/development/runs-on-atlassian-apps-can-now-take-home-100-of-marketplace-revenue | **Does a Forge-remote app qualify for the 100 % window?** |
| 8 | https://community.developer.atlassian.com/t/trigger-a-rovo-agent-from-a-forge-function/87749 | Date of the thread; whether a backend can still not call Rovo |
| 9 | Pricing tabs of [Better Content Archiving](https://marketplace.atlassian.com/apps/123/better-content-archiving-and-analytics-for-confluence), [AI Hygiene Inspector](https://marketplace.atlassian.com/apps/512832479/ai-hygiene-inspector-manage-readiness-for-confluence), [FreshPage](https://marketplace.atlassian.com/apps/1059183334/freshpage-trusted-knowledge-for-confluence), [Content Retention Manager](https://marketplace.atlassian.com/apps/1233769/content-retention-manager-for-confluence), [Scroll Content Manager](https://marketplace.atlassian.com/apps/1217608/scroll-content-manager-for-confluence) | Price at 500 / 1,000 / 2,000 / 5,000 users. Compare with break-even in table F |

## Verdict

Decision: PROCEED-WITH-CONSTRAINT

Constraint: confirm every Atlassian price and limit locally before ADR-013 closes, and enforce a per-tenant monthly verdict budget (hard stop) so the stress corner (K3) cannot occur.

Criteria evaluated:
- K1 base case: LLM cost at most 30 % of net revenue — PASS — 0.08 % ($0.675 vs $830/month); the funnel could pass about 369× more pairs first
- K2 page-heavy, user-light tenant (250 users at $0.50, 2 % yield, T3) — PASS — 8.4 %
- K3 stress corner (2 % yield, T4 prompts, Opus 4.6, 100 % monthly churn, 250 users at $0.50) — FAIL — 116 % ($120 vs $103.75); costs are developer-billed with no pass-through, so an uncapped tenant is a real exposure
- K4 50k-page backfill within 24 h under the Forge LLM limits — PASS — 16 min (5.5 h at 250k pages and 2 % yield)
- Atlassian prices and limits read from a primary source — FAIL — all search-reported; the sandbox cannot fetch atlassian.com. Triggers decision rule 4
- Cost model is tested and reproducible — PASS — 23 unit tests, a golden-file check, base case and criteria pinned by a test

Unverified assumptions carried forward: all Forge LLM prices, credit rates, limits, and the Forge compute price (search-reported); price parity for Sonnet 5 and Opus 4.7/4.8; whether the token limit counts input plus output; the 83 % rate and its reading as the partner's share; whether a remote-backed Forge app gets the 100 % revenue window; that Rovo cannot be called from a Forge backend (thread date unknown); GA vs Preview status; the funnel yield and its reading as pages × yield; token profiles, churn, wait time, users and price per user; no verified comparable listing price.

What would flip this verdict: (1) a measured funnel yield above about 1.8 candidate pairs per page at 3,000/300-token prompts, or the Forge pricing page showing per-token prices roughly 100× the reported ones, turns K1 into FAIL and the decision into KILL-OR-REDESIGN; (2) pricing tabs showing that comparable apps charge so little that typical 50k-page tenants pay under about $2 net per month (table F) would make even the base case marginal.

Implication for ADR-013: LLM economics neither force nor favour remote compute: the verdict stage costs about 0.1 % of net revenue at the assumed yield, so S1 gives no economic reason to leave Forge, while the only customer-billed route (BYO key) needs external egress and would forfeit Runs on Atlassian, and with it the revenue-share window worth up to about $170k (search-reported).
