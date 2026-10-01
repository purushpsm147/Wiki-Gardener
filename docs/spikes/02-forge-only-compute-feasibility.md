# Spike S2 — Forge-only compute feasibility (GATE-S2)

> **Status: results added.** The sections *Question* through *Decision rules* are unchanged since commit `744c541`, which was pushed
> **before** any measurement or arithmetic existed (`git log -- docs/spikes/02-forge-only-compute-feasibility.md`). Everything after
> them is result.

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

## Result in one paragraph

**All six pre-registered criteria pass on estimate.** Per tenant, the index takes about 1.8 KB a page (446 MB at 250k pages, 41.5 % of
Forge SQL's 1 GiB); a 50-page batch takes about 5.5 s against a 900 s timeout; a first scan of 50k pages takes 0.8 h of an exclusive
Tier 1 pool, 3.9 h at a 20 % share, or 27 min under a Tier 2 pool; and the pipeline's platform cost is about **$0.27 per tenant per
month**. The brief's kill criterion is **not triggered**: a Forge-only path handles 50k pages, so Runs on Atlassian survives S2.
**Compute and storage are not what binds.** The Confluence REST quota (65,000 points per hour for the *whole app*) is, and it binds
a remote backend equally.

## What was established

Fetch date for every row: **2026-10-01**. `ASSUMED (search-reported)` means a web-search summary of the page, not the page.

### Forge functions and async events

| Claim | Value | Grade | Source |
|---|---|---|---|
| Timeouts | UI modules **25 s**; events invoked by Forge Remote **5 s**; async events and scheduled triggers **up to 900 s**, default **55 s** | ASSUMED (search-reported) | [Invocation limits](https://developer.atlassian.com/platform/forge/limits-invocation/) |
| `timeoutSeconds` | **1 to 900** | **VERIFIED**, `@forge/manifest@13.6.0` schema | npm |
| Memory | Documented **512 MB default, 1,024 MB maximum**. **The schema disagrees with itself:** `maximum: 4096` on the function, "between 128 MB and 1024 MB" in the description | search-reported; schema VERIFIED | same page, schema |
| CPU | "Increasing the function memory also increases its CPU allocation"; the runtime is described as "**Lambda** architecture", `x86_64` or `arm64` | **VERIFIED**, schema | npm |
| Runtimes | `nodejs20.x`, `nodejs22.x`, `nodejs24.x` | **VERIFIED**, schema | npm |
| Scheduled trigger intervals | `fiveMinute`, `hour`, `day`, `week` | **VERIFIED**, schema | npm |
| Payloads | 5 MB per invocation; 500 KB request and 5 MB response for front-end invocations; one outbound request in an async event up to 180 s | ASSUMED (search-reported) | Invocation limits |
| Async events | **≤ 50 events and ≤ 200 KB per push; ≤ 500 events pushed per minute**; concurrency control per key; retries with backoff up to ~15 min | ASSUMED (search-reported) | [Async events limits](https://developer.atlassian.com/platform/forge/limits-async-events/) |
| Consumers and triggers can target a container endpoint | `consumer` and `scheduledTrigger` accept an `endpoint` instead of a `function` | **VERIFIED**, schema | npm |

### Storage

| Claim | Value | Grade | Source |
|---|---|---|---|
| Forge SQL | **1 GiB per production installation** (256 MiB staging, 128 MiB development); 200 tables; **150 DML/s**; 25 DDL/min; 6 MiB per row; **62.5 s of query time per minute** | ASSUMED (search-reported) | [Forge SQL](https://developer.atlassian.com/platform/forge/storage-reference/sql/) |
| KVS | key ≤ 500 chars; **value ≤ 240 KiB**; query returns ≤ 100; 1,000 requests/s per installation | ASSUMED (search-reported) | [KVS limits](https://developer.atlassian.com/platform/forge/limits-kvs-ce/) |
| Prices | SQL storage $0.0007685/GB-h (730 GB-h free); compute $0.143/h (1 h free); requests $1.929/M (100k free); KVS reads $0.055/GB, writes $1.09/GB (0.1 GB free each); function $0.000025/GB-s | ASSUMED (search-reported) | [Forge platform pricing](https://developer.atlassian.com/platform/forge/forge-platform-pricing/) |

### Forge Containers

| Claim | Value | Grade | Source |
|---|---|---|---|
| Status | **Preview**, not GA; some doc pages still titled "(EAP)". Preview allows production and Marketplace distribution | ASSUMED (search-reported) | [Containers overview](https://developer.atlassian.com/platform/forge/containers-reference/) |
| Size | up to **1000m CPU and 2048 MiB** per service | ASSUMED (search-reported) | same |
| Price | **reservation-based**: **$0.07177 per vCPU-hour + $0.00786 per GiB-hour**, billed whether or not requests arrive (about $64 a month for 1 vCPU / 2 GiB) | ASSUMED (search-reported) | [Containers pricing](https://developer.atlassian.com/platform/forge/containers-reference/pricing/) |
| Scaling | **Sources disagree.** The EAP page says one instance and no scaling; the Preview post says the scaling profile can be set per environment and region, and non-production scales to zero; the **manifest schema has `scaling {min, max}`** (VERIFIED) | conflicting | pages above, npm |
| Runs on Atlassian | Atlassian describes container services as keeping data residency and "eligibility for Runs on Atlassian" | ASSUMED (search-reported) | [Preview post](https://www.atlassian.com/blog/development/forge-container-services-preview) |

### Runs on Atlassian

`ASSUMED (search-reported)`, [Runs on Atlassian](https://developer.atlassian.com/platform/forge/runs-on-atlassian/): an app qualifies if it
(1) uses **exclusively Atlassian-hosted compute and storage**, (2) supports data residency matching the host app, and (3) lets
customers control external data egress. The manifest must not list external fetch domains (analytics excepted), **remotes**, Connect
modules, providers or dynamic web triggers. **Customer-managed egress and customer-managed remotes are not eligible.** The badge is
applied automatically.

### Confluence REST quota (architecture-neutral)

`ASSUMED (search-reported)`, [Rate limiting, Confluence Cloud](https://developer.atlassian.com/cloud/confluence/rate-limiting/) and the
[2026 point-based rate limits thread](https://community.developer.atlassian.com/t/2026-point-based-rate-limits/97828):

- Enforced from **2026-03-02** on **Forge, Connect and OAuth 3LO apps**.
- A request costs **1 base point + 1 per core object** (pages, spaces, attachments), **2 per identity object** (users, groups,
  permissions). Writes cost the base only.
- **Tier 1, the default: one pool of 65,000 points per hour for the app, shared across all tenants.**
- **Tier 2, per-tenant pools**: Standard 100,000 + 10 per user per hour; Premium 130,000 + 20; Enterprise 150,000 + 30. Assigned **only
  after review** for apps with exceptionally high or concentrated usage. "No increases can be requested on demand." About 95 % of apps
  never cross the Global Pool; Atlassian moved some that did to Tier 2.

### Forge Remote tokens (amendment A07)

`ASSUMED (search-reported)`, [Calling Atlassian app APIs from a remote](https://developer.atlassian.com/platform/forge/remote/calling-product-apis/):
the app system token is valid for at least ~2 h and at most **4 h**; there is **no endpoint to refresh a token proactively**; use a
scheduled trigger (hourly) to deliver fresh ones. A "Forge Remote access to tokens anytime" Preview exists and may relax this. This
**corroborates A07's "~2 to 4 hours, no proactive refresh"** (still unverified) and matters only if a remote backend is ever used.

### Package types that confirm the REST shape (VERIFIED)

`confluence.js@3.2.0` (npm, modified 2026-08-10; generated from Atlassian's OpenAPI): `getPages` takes `id[]`, `spaceId[]`,
`sort` (including `-modified-date`), `status[]`, `bodyFormat` (`storage`, `atlas_doc_format`), `cursor`, `limit`; `getPageById` takes
`version` and `bodyFormat`; a page carries `version { number, createdAt, authorId }` and `body.storage.value`. **The package states
no maximum for `limit`**, so the 250-per-request figure stays ASSUMED.

## Results (arithmetic shown in `tools/compute-budget/BUDGET.md`, generated)

| ID | Criterion | Result | Verdict |
|---|---|---|---|
| G1 | Index for 250k pages at most 50 % of the SQL limit | **41.5 %** (446 MB) | PASS |
| G2 | 50-page batch at most 1/5 of 900 s | **5.5 s** (162× headroom) | PASS |
| G3 | First scan of 50k pages within 24 h | **0.77 h** (Tier 1, 100 %) / **3.86 h** (20 %) / **0.46 h** (Tier 2 Standard) | PASS |
| G4 | Steady-state cost at most 5 % of $830 | **$0.27 / month** (0.033 %) | PASS |
| G5 | One incremental event within 55 s | **15.5 s** | PASS |
| G6 | RoA eligible by construction | no remotes, no egress | PASS |

### The arithmetic

- **Storage.** 512 B signature + 16 rows × 70 B + 150 B = **1,782 B per page**. 50k pages are 89 MB (8.3 %), 250k are 446 MB (41.5 %).
  N at 50 % headroom is **301,274** pages; at the hard limit 602,548.
- **CPU.** MEASURED on a 4-vCPU Xeon at 2.1 GHz, Node 22.22: the weighted median is **479 µs per page** (heavy-markup pages, 1,370
  words on average). At 1,024 MB the assumed CPU share is 0.579, so the estimate is **828 µs per page**: 41 s of CPU for a whole
  50k-page tenant. The sandbox is shared and noisy (p10 to p90 spreads reach about 80 % in the noisiest row), and the pages are synthetic.
- **Memory.** A naive `Map` LSH index costs **83 MB at 50k pages and 386 MB at 250k** (MEASURED); compact typed arrays 12 B per entry,
  **46 MB** at 250k. Neither is needed: state lives in SQL.
- **Batch.** 5.0 s REST fetch + 0.04 s CPU + 0.5 s SQL = 5.5 s per 50 pages; fetch dominates and CPU is 0.7 % of the batch.
- **Fan-out.** One event per page would take **1.7 h to enqueue at 50k pages** (500 events per minute); cursor chaining, one event per
  batch, removes it.
- **Cost.** Functions $0.031 + SQL storage $0.047 + SQL compute $0.099 + SQL requests $0.096 = **$0.274 a month** at 50k pages with no
  free allowance; $1.37 at 250k. A one-time backfill costs about $0.06.

### Sensitivity: where the estimate is weak

- **G1 is fragile.** It holds at 70 B per band row and **fails at 100 B or more** for 250k pages (52.7 %). The row overhead of Forge SQL
  cannot be measured from here. N ranges from **367k (50 B rows) to 175k (150 B rows)** at 50 % headroom. Levers if it is large: 8 bands
  instead of 16 (N → 439k), no stored signature (N → 423k), both with 150 B rows (N → 398k).
- **The 50k conclusion is not fragile.** To exceed the hard limit at 50k pages a page would need more than **21 KB** of SQL, about
  **12×** the estimate.
- **CPU is not the risk.** G2 has 162× headroom; the Forge CPU would have to be two orders of magnitude slower than the sandbox.

## The dangerous fact: the REST quota binds every architecture

The first scan of **one** 50k-page tenant costs **50,200 points: 77 % of an hour of the entire app's Tier 1 pool.** The numbers that
follow are `ESTIMATED` from the search-reported rule:

| Question | Answer |
|---|---|
| Full first scans the whole pool can do in a day, if it does nothing else | **31** tenants of 50k pages (6 at 250k pages); **6** at a 20 % share |
| When does steady-state edit traffic alone fill the pool? | **~1,000 tenants use 42 %, ~2,000 use 84 %** (50k pages each, 5 % edited a month, 8 points an edit) |
| Who can raise it? | Only Atlassian, **after review, not on demand** |
| Does a remote backend escape it? | **No.** The data source is Confluence, and the quota applies to Forge, Connect and OAuth 3LO apps |

It is not a Forge-only failure, so by decision rule 5 it does not change GATE-S2. It does mean the business is **rate-limited by
Atlassian's goodwill**, not by compute. Mitigations that fit the design: sync incrementally (`sort=-modified-date`, stop at the last
seen timestamp: a listing costs a point per object whatever the body size, so metadata-only diffing saves nothing); cache the
approved sources; queue backfills per tenant and throttle them; apply for a Tier 2 review before onboarding the first large tenant; for
very large tenants offer an export-based onboarding (the concierge path in [`../phase-v/`](../phase-v/concierge-scanner-spec.md)).

## Decision matrix

Estimates at 50k pages unless stated. Option C is not priced: AWS pricing was not researched.

| | **A. Forge functions + Forge SQL** (Architecture X) | **B. Forge Containers** (Preview) | **C. Fargate or other remote, via Forge Remote** |
|---|---|---|---|
| Feasible at 50k / 250k | **Yes / yes**, by estimate; 250k hinges on SQL row overhead | Yes. More headroom (1 vCPU, 2 GiB, long-running), **not needed** | Yes. No Forge limits |
| Runs on Atlassian | **Eligible** by the published criteria | **Eligible**, per Atlassian (search-reported; confirm) | **Not eligible** (remotes, egress) |
| Revenue-share consequence (S1, search-reported) | Keeps the 0 % window, worth up to ~$170k | Same, if eligible | Window likely forfeited; not established for remote-backed apps |
| Cost | **~$0.27 / tenant / month** (platform) | **$16 to $64 per instance per month, per region**, fixed and reservation-based, plus the above | infra + Postgres + egress: not priced |
| REST quota | Applies | Applies | **Applies** |
| Ops burden | **Lowest**: no infra | Medium: images, health checks, Preview-status risk | **Highest**: runtime, database (ADR-006), token handling (A07: 2 to 4 h tokens, no proactive refresh, so chunked and checkpointed workers), data residency, customer security review |
| Main risk | G1 at 250k; limits unverified | Preview; docs disagree on scaling | Loses the trust signal; most of the build |

### The consequence, stated plainly

The brief's kill criterion is **not triggered**: option A handles 50k pages within every limit found. If it had been, the product would
have lost the Runs-on-Atlassian signal and with it the "your data never leaves Atlassian" claim to security reviewers. Option C
would also add a database to run, token chunking (A07), a per-tenant data-residency problem, and a security review at every customer,
while leaving the REST quota exactly where it is.

## What this spike does not prove

- **Nothing ran on Forge.** CPU is from the sandbox, SQL row overhead and query behaviour are assumptions, REST latency (5 s) is a guess.
- **Every Forge and Confluence limit is search-reported**; the only VERIFIED limits are in the manifest schema.
- **Forge SQL join performance** for LSH candidate generation (62.5 s of query time per minute) is untested.
- **Event delivery semantics** (concurrency, ordering, duplicates) are untested; Spike S3 covers only the trigger.
- The **page-size mix and markup density** are assumptions; the pages were synthetic.
- The **REST point model** (1 per page, 250 pages per request with bodies) is search-reported.

## Confirm locally

| # | URL or action | What it must say |
|---|---|---|
| 1 | https://developer.atlassian.com/platform/forge/limits-invocation/ | 25 s / 55 s default / 900 s; **memory 512 default and 1,024 max** (the schema says 4,096); 5 MB payload; 180 s outbound |
| 2 | https://developer.atlassian.com/platform/forge/limits-async-events/ | ≤ 50 events and 200 KB per push; **500 events per minute (per installation or per app?)** |
| 3 | https://developer.atlassian.com/platform/forge/storage-reference/sql/ | **1 GiB per production installation**; 150 DML/s; 62.5 s query time per minute |
| 4 | **Measure:** a dev installation, 10k pages × 17 rows | **Bytes per band row** (`SELECT table_name, data_length + index_length FROM information_schema.tables WHERE table_schema = DATABASE()` if permitted, else the console's storage metric). G1 fails at ≥ ~95 B |
| 5 | **Measure:** paste `fingerprint()` into a throwaway Forge function | µs per page on Forge; set `core_ratio` |
| 6 | https://developer.atlassian.com/cloud/confluence/rate-limiting/ | **65,000 points/hour app-wide**; point rules; **do Forge `requestConfluence` calls count?**; Tier 2 numbers |
| 7 | https://community.developer.atlassian.com/t/2026-point-based-rate-limits/97828 | The Tier 2 review process and criteria |
| 8 | https://developer.atlassian.com/platform/forge/containers-reference/ and `/pricing/` | Preview vs GA; 1000m / 2048 Mi; scaling; **per app or per tenant**; Runs on Atlassian eligibility |
| 9 | https://developer.atlassian.com/platform/forge/runs-on-atlassian/ | The three criteria; whether SQL and containers qualify |
| 10 | https://developer.atlassian.com/platform/forge/remote/calling-product-apis/ | Token TTL 2 to 4 h; no proactive refresh (amendment A07) |
| 11 | The Confluence v2 `GET /wiki/api/v2/pages` reference | **Maximum `limit`**, and whether bodies are allowed at that size |

## Verdict

Decision: PROCEED-WITH-CONSTRAINT

Constraint: confirm the limits locally, measure Forge SQL bytes per band row and Forge CPU in a development installation, and request a Tier 2 per-tenant REST quota review before onboarding a large tenant.

GATE-S2: Forge-only supports up to about 300k pages per tenant (175k to 370k depending on the unmeasured SQL row overhead, at 50 % storage headroom) with Architecture X: Forge SQL for signatures and LSH bands, cursor-chained async-event workers of up to 250 pages each at 900 s and 1,024 MB, bodies re-fetched on demand, no remotes or egress. ESTIMATED; the 50k tier passes every criterion with wide margin, and the Confluence REST quota (65,000 points per hour app-wide) binds every architecture equally.

Criteria evaluated:
- G1 index for 250k pages within 50 % of the 1 GiB SQL limit — PASS — 41.5 % (446 MB); fragile: fails at 100 B or more per band row, which cannot be measured here
- G2 50-page batch within 1/5 of the 900 s timeout — PASS — 5.5 s, 162× headroom
- G3 first scan of 50k pages within 24 h at 100 % and 20 % of Tier 1 and under Tier 2 — PASS — 0.77 h, 3.86 h, 0.46 h
- G4 platform cost at most 5 % of net revenue at 50k pages — PASS — $0.27 a month (0.033 %)
- G5 one incremental event within the 55 s default — PASS — 15.5 s with three assumed 5 s REST calls
- G6 manifest Runs-on-Atlassian eligible by construction — PASS — no remotes, no egress (criteria search-reported)
- Forge limits and prices read from a primary source — FAIL — all search-reported except the manifest schema; the sandbox cannot fetch atlassian.com. Triggers decision rule 4
- CPU measured on Forge hardware — FAIL — sandbox CPU only; G2 has 162× headroom so this does not move the verdict
- The REST quota lets a multi-tenant business scale on the default Tier 1 pool — FAIL — one 50k-page first scan takes 77 % of an hour of the whole app's pool and edit traffic alone fills it at about 2,000 tenants; architecture-neutral, so it does not alter GATE-S2 (rule 5)

Unverified assumptions carried forward: every Forge and Confluence limit and price except the manifest schema facts (search-reported); the Forge SQL bytes per band row (70 B assumed); the Lambda CPU scaling rule (1,769 MB per vCPU) and sandbox-equals-Lambda-core; REST latency of 5 s and 250 pages per request with bodies; the 1-point-per-page rule and that Forge `requestConfluence` calls count against the quota; whether Tier 2 pools are obtainable; whether free allowances are per app or per installation; Forge Containers eligibility for Runs on Atlassian and their scaling behaviour; synthetic page sizes and markup; Forge SQL join performance; async event semantics.

What would flip this verdict: (1) a measured SQL footprint above about 2,100 bytes per page (band rows of roughly 95 B or more) turns G1 into FAIL: N at the pre-registered 50 % headroom would fall to about 237k pages (still about 474k at the hard 1 GiB limit), while the 50k tier would need more than 21 KB per page to fail; (2) Atlassian declining a Tier 2 pool while the app-wide limit stays at 65,000 points per hour would cap onboarding at about 31 large tenants a day and fill the pool at about 2,000 tenants, which is a business limit on every architecture rather than a Forge one.

Implication for ADR-013: Forge-only is feasible for the classical pipeline at 50k pages and, on estimate, up to about 300k, so the Runs-on-Atlassian path survives S2 and compute and storage give no reason to go remote; the binding limits (Confluence REST points and Forge LLM tokens per minute) apply to a remote backend as well, which would add a database, A07 token chunking and the loss of Runs on Atlassian, so S2 favours Forge-only pending the decision rule and Phase V pilot security input.
