# Spike S2 — Forge-only compute feasibility (GATE-S2)

> **Status: pre-registration.** The architecture, parameters, criteria and decision rules below were committed *before* any
> number was computed (`git log -- docs/spikes/02-forge-only-compute-feasibility.md`). Measurements, arithmetic, the decision
> matrix and the verdict are added in later commits.

## Question

Can the classical pipeline (MinHash/LSH over 50k pages, incremental on change) run entirely inside Forge, keeping the **Runs on
Atlassian** trust signal? The brief's kill criterion: *if no Forge-only path handles 50k pages within limits, the product loses the
Runs-on-Atlassian signal, and that consequence is documented honestly instead of hand-waving Fargate.*

**GATE-S2** requires a verdict in one of two forms: *"Forge-only supports up to N pages with architecture X"* or *"Forge-only
impossible beyond N because Y (measured)"*. Where "measured" is impossible from this environment the verdict says **estimated** and
shows the arithmetic.

## Evidence rules (same as S1)

- `*.atlassian.com` cannot be fetched from the sandbox, so Forge limits and prices are `ASSUMED (search-reported: <url>, 2026-10-01)`.
- `VERIFIED` is reserved for what was read here: the `@forge/manifest@13.6.0` JSON schema from the npm registry (2026-10-01), and
  code I ran in this sandbox.
- CPU costs are **MEASURED on the sandbox's CPU, not on Forge hardware.** Everything derived from them is **ESTIMATED**.

## Architecture X (the hypothesis under test)

All compute and storage stay in Forge; the manifest contains **no `remotes`, no external `fetch` permission, no Connect modules, no
providers, no dynamic web triggers**, so it is eligible for Runs on Atlassian by the program's published criteria (search-reported).

| Concern | Choice |
|---|---|
| Incremental trigger | Confluence product events for page created / updated (event names are verified in Spike S3) |
| Backfill | A scheduled or long-running enqueuer lists page ids by cursor and pushes **≤ 50 page ids per async event**; consumers run with `timeoutSeconds: 900`, **1,024 MB**, capped concurrency |
| Per page | Fetch the body, compute a **MinHash signature (k = 128, uint32)** over **5-word shingles** and **16 LSH bands × 8 rows**, write rows, **discard the text** |
| State | **Forge SQL**: signature blob, band rows, metadata (page id, version, content hash per ADR-001) |
| Candidate pairs | SQL self-join per band; bodies for the A3 divergence check are **re-fetched on demand**, never stored |
| Verdicts | Forge LLMs API (Spike S1) |

## Parameters fixed in advance (all ASSUMED unless stated)

| Parameter | Value |
|---|---|
| Page-size mix (words) | 60 % × 300, 30 % × 1,500, 9 % × 6,000, 1 % × 20,000, so a mean of **1,370 words** |
| Storage-format bytes per word | 28 (the XHTML-ish storage format is several times the visible text) |
| SQL bytes per page | signature **512 B**, **16 band rows × 70 B** (row plus index), metadata **150 B** |
| Function | **1,024 MB**; CPU share = memory ÷ 1,769 MB (an AWS Lambda scaling rule); one sandbox core ≈ one Lambda vCPU |
| REST fetch | **250 pages per request**, **1 base point + 1 point per page** (search-reported rule), **5 s** per request, **10** concurrent consumers |
| REST quota | Tier 1 global pool **65,000 points/hour for the whole app**; a single onboarding tenant gets **100 %** (best case) or **20 %** (planning case) of it. Tier 2 (Standard edition): 100,000 + 10 per user per hour, 1,000 users |
| Steady state | 5 % of pages edited per month; per edit 1 s of function time at 0.5 GB, 20 SQL requests, 1 s of SQL compute |
| Forge prices | $0.000025 per GB-second; SQL $0.0007685 per GB-hour, $0.143 per compute hour, $1.929 per million requests; **no free allowance counted** (conservative) |

## Criteria

| ID | Criterion |
|---|---|
| **G1** | Storage: signatures + LSH index + metadata for **250k pages** fit in at most **50 %** of the Forge SQL 1 GiB per-installation limit |
| **G2** | A batch of 50 pages completes in at most **one fifth of the 900 s timeout** (≥ 5× headroom) at 1,024 MB |
| **G3** | A first full scan of **50k pages** finishes within **24 h** at both the 100 % and the 20 % share of the Tier 1 pool, and under a Tier 2 Standard pool |
| **G4** | Steady-state Forge platform cost (functions + SQL, no free allowance) is at most **5 %** of $830 net revenue per tenant per month at 50k pages |
| **G5** | The incremental path (one product event) fits inside the **55 s default** timeout, so it needs no long-running configuration |
| **G6** | The manifest of Architecture X is Runs-on-Atlassian eligible by construction |

### Decision rules (fixed before computing)

1. **G1, G2, G5 or G6 fails ⇒ GATE-S2 is "Forge-only impossible beyond N because Y"**, with N from the failing criterion. If
   N < 50k that is a **KILL** of the Runs-on-Atlassian signal, as the brief states.
2. G3 passes at 100 % but fails at 20 % ⇒ **PROCEED-WITH-CONSTRAINT** (staged or rate-limited backfill; ask for a Tier 2 pool).
3. G4 fails ⇒ PROCEED-WITH-CONSTRAINT (cost).
4. **All pass ⇒ "Forge-only supports up to N pages with architecture X"**, where N is the largest per-tenant page count satisfying
   G1. While any limit is not `VERIFIED` the decision is capped at PROCEED-WITH-CONSTRAINT.
5. Limits that bind **every** architecture (such as the Confluence REST quota) are reported as architecture-neutral risks, not as
   Forge-only failures.
