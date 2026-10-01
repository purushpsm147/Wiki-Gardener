# Phase −1 summary

Written 2026-10-01, at the end of the first Phase −1 session. Nothing here reproduces the two source documents, which never arrived
([`source/README.md`](source/README.md)). Evidence grades are in the [README](../README.md#evidence-grades): **VERIFIED** (read or
run here), **ASSUMED**, and **ASSUMED (search-reported: URL, date)** for a search provider's summary of a page this environment could
not open.

Links into `spikes/0N-*.md` and `competitors/` point at files in pull requests [#1](https://github.com/purushpsm147/Wiki-Gardener/pull/1)
to [#4](https://github.com/purushpsm147/Wiki-Gardener/pull/4) and resolve once those merge.

## Read this first

1. **Nothing Atlassian-specific is VERIFIED.** The environment's egress proxy refuses `*.atlassian.com` (and `k-ai.ai` and
   `evergreen.team`; VERIFIED by `curl`, by `WebFetch`, and by the competitor watcher's own run). Every Forge limit and price, the
   Confluence REST quota, the revenue-share rate and everything said about a competitor is search-reported. What *is* verified: the
   `@forge/manifest` schema and validator, the type definitions of the Forge and Confluence npm packages, the Forge CLI's commands,
   and all the code and arithmetic. Every spike ends with a table of the exact URLs to confirm locally.
2. **Material finding on the competition (Spike S4), flagged first as the brief asks.** **K-AI**, a vendor not in the brief, is
   reported to claim on its own pages that it "continuously detects contradictions" and "detects conflicts in real-time", with a
   Confluence integration. **AI Hygiene Inspector** may use the word too (unverified). **Evergreen AI for Confluence**, the competitor
   GATE-S4's kill clause names, **could not be located**. See [§5](#5-gate-s4-where-the-kill-clause-stands).
3. **Two things were not done, and are not simulated:** the live Forge demo of GATE-S3 and the competitor baseline snapshot. Each
   is a documented step for a machine that can reach Atlassian.
4. **The source documents are missing**, so the ADR-013 decision rule, the text of the amendments and the PV.3 criteria are not
   written, and "where the source contradicts the brief" cannot be answered ([§6](#6-reconciliation-and-the-source-documents)).

## 1. The four verdicts

All four are **PROCEED-WITH-CONSTRAINT**. None killed the idea, and none validated it; ADR-000 says no product code until real
administrators have.

| Spike | PR | Decision | What it found | What it could not establish |
|---|---|---|---|---|
| **S1** Forge LLM cost | [#1](https://github.com/purushpsm147/Wiki-Gardener/pull/1) | PROCEED-WITH-CONSTRAINT | The LLM verdict stage is about 0.08 % of net revenue at 50k pages ($0.68 against $830 a month); the funnel could pass about 369× more pairs first. Only the hostile stress corner K3 fails (116 %), and Forge LLM costs are developer-billed with no pass-through, so a hard per-tenant budget is the constraint. | Every price and limit is search-reported; the funnel yield is the brief's number, not a measurement. |
| **S2** Forge-only compute (**GATE-S2**) | [#2](https://github.com/purushpsm147/Wiki-Gardener/pull/2) | PROCEED-WITH-CONSTRAINT | *Forge-only supports up to about 300k pages per tenant (175k to 370k) with Architecture X* (Forge SQL for signatures and LSH bands, cursor-chained async workers, no remotes): ESTIMATED. 50k passes every criterion with wide margin; platform cost about $0.27 per tenant per month. | Nothing ran on Forge; SQL row overhead, CPU on Forge hardware and every limit are assumptions. |
| **S3** Change-time trigger PoC (**GATE-S3**) | [#3](https://github.com/purushpsm147/Wiki-Gardener/pull/3) | PROCEED-WITH-CONSTRAINT | Changing "90 days" to "30 days" on a runbook yields one logged conflict against the approved policy page with both quotes and character offsets (69 to 111 and 123 to 169), end to end through the real handler against a faithful fake; 160 tests; the manifest passes the platform's own validator and is Runs-on-Atlassian eligible by construction. | **No live run**: event delivery, payload, latency and "within minutes" are unmeasured. Recall on real contradictions and numeric precision on real policy text are unknown. |
| **S4** Competitor watch (**GATE-S4**) | [#4](https://github.com/purushpsm147/Wiki-Gardener/pull/4) | PROCEED-WITH-CONSTRAINT | A tested, polite, fail-loud weekly watcher with a generated thesis table; per-competitor paragraphs. **The kill clause cannot be evaluated** (Evergreen not located, "change-time prevention" undefined, decision point unrecorded), and a vendor outside the brief is reported to claim what we thought was ours. | **Baseline not taken** (egress blocked); the extractor has never seen a real page; every competitor statement is search-reported. |

Full verdict blocks, each ending in the form the spike template requires, are at the end of each spike document.

## 2. The three most dangerous facts

1. **The Confluence REST quota rate-limits the business whatever the architecture.** 65,000 points an hour for the *whole app*
   (Tier 1), per-tenant pools only after Atlassian's review (ESTIMATED from search-reported rules, S2). One first scan of a 50k-page
   tenant costs about 50,200 points: **77 % of an hour of the entire app's pool**; steady-state edit traffic alone fills it at about
   2,000 tenants; a remote backend does not escape it, because the data source is Confluence. S3 shows the same wall from the trigger
   side: re-reading every approved page on every edit costs 4 + 2N points, so the approved text has to be cached and indexed. The
   business is limited by Atlassian's goodwill, not by compute.
2. **The differentiation is already contested, and the named competitor cannot be found.** K-AI says it detects contradictions and
   has a Confluence integration; AI Hygiene Inspector may; Rovo's Documentation Agent is reported to cover staleness, and Atlassian
   could add conflict handling in one release. Evergreen AI for Confluence has no Marketplace listing that three searches could find,
   so the kill clause has no subject. (All search-reported; the baseline will settle most of it in one run.)
3. **The cheap, deterministic detector reaches a narrow class, and nobody has shown that class is where administrators' pain lives.**
   S3's LLM-free detector finds changed numbers, negations and listed antonyms in near-restatements, exactly the "90 days became 30"
   edit. Paraphrased and multi-sentence contradictions are missed by design, and tightening it for precision (false alarms on real
   prose fell from 7.1 to 0.2 per 1,000 README sentences, and is 0.5 across the two corpora tried) cost recall. Widening reach means an LLM stage, whose cost is billed to the
   developer (S1's stress corner is a 116 % loss on an uncapped tenant), and Rovo, the in-tenant default of ADR-011, is reported not
   to be callable from a background pipeline. So the product's reach, its cost and its differentiation all hinge on an empirical
   question, *what contradictions do administrators actually have, and how urgent are they*, that no spike can answer.

## 3. What the brief got wrong, or left unsaid (with sources)

"Trust the fetched docs" had little to trust, because no Atlassian page could be fetched. These are what the spikes found; the grade
is on each.

| The brief | What was found | Source and grade |
|---|---|---|
| Names **Evergreen AI for Confluence** as a competitor. | No Marketplace listing by that name could be found in three searches. Unrelated products named Evergreen came back; the nearest Confluence matches use "evergreen" as a feature word (FreshPage, Better Content Archiving). The name may be inexact, renamed, or not on the Marketplace. | Searches of 2026-10-01; [FreshPage listing](https://marketplace.atlassian.com/apps/1059183334/freshpage-trusted-knowledge-for-confluence); ASSUMED (search-reported). **Owner to supply the exact name or URL.** |
| Lists three competitors. | A fourth claims contradiction detection with a Confluence integration: **K-AI**. | [k-ai.ai](https://www.k-ai.ai/en/) and its news pages; ASSUMED (search-reported). |
| Frames the S1 kill criterion per **page** tier. | Revenue is per **user**, cost is per page; the axis that matters is pages per user (S1's K2 and K3 corners). | S1 pre-registered model; arithmetic, VERIFIED here; prices ASSUMED. |
| ADR-011 makes `RovoProvider`, in-tenant, the default verdict provider. | A Rovo agent reportedly **cannot be triggered from a Forge function** ("not part of the Forge roadmap"); the bridge API only opens the chat from the UI. Customer-billed Rovo credits then apply only to interactive use, not to a background funnel. The thread's date is unknown. | [community thread](https://community.developer.atlassian.com/t/trigger-a-rovo-agent-from-a-forge-function/87749), [bridge API](https://developer.atlassian.com/platform/forge/apis-reference/ui-api-bridge/rovo/); ASSUMED (search-reported). |
| Treats Forge-vs-remote as a cost and limits question. | The **Runs-on-Atlassian revenue-share window** (100 % until $1M lifetime Forge revenue; worth up to about $170k) is an unstated economic reason to stay Forge-only. | [Atlassian blog, 2026 revenue share](https://www.atlassian.com/blog/development/updates-to-marketplace-revenue-share-2026), [100 % post](https://www.atlassian.com/blog/development/runs-on-atlassian-apps-can-now-take-home-100-of-marketplace-revenue); ASSUMED (search-reported). |
| Does not mention the Confluence **REST quota**. | 65,000 points an hour app-wide; binds every architecture (see §2). | [rate limiting](https://developer.atlassian.com/cloud/confluence/rate-limiting/), [2026 thread](https://community.developer.atlassian.com/t/2026-point-based-rate-limits/97828); ASSUMED (search-reported). |
| "Fargate only if Forge-only compute proves infeasible", i.e. Forge-first by default. | The ADR record the follow-up describes treats compute placement as an **open fork** (ADR-013); ADR-007 "originally expected: remote". S1 and S2 are written as inputs to it. The evidence leans Forge-only, but that is not the same as a default. | Follow-up message vs original brief ([`RECONCILIATION.md`](RECONCILIATION.md) §4). |
| Forge function memory, as an example of docs conflicting. | The `@forge/manifest` schema allows 4,096 MB; the documentation is reported to cap it at 1,024. | Schema VERIFIED (`@forge/manifest@13.6.0`); documentation ASSUMED (search-reported: [limits](https://developer.atlassian.com/platform/forge/limits-invocation/)). |
| Points at Atlassian release notes and announcements for the Rovo Documentation Agent. | None could be found by search; the agent is described only by secondary sources (reviews, consultancies) as reviewing pages for staleness and proposing rewrites. | Searches of 2026-10-01; ASSUMED (search-reported). |

What the brief got **right**, as far as anything checks: Forge LLM calls are billed to the developer (the conceded mistake), and
"staleness" is a space Atlassian itself occupies.

## 4. ADR-013: status and evidence

**Status: Open.** It cannot close for two independent reasons: the decision rule is in the v3 addendum, which is not in the
repository, so it **cannot be applied** (and was not improvised); and one of its three inputs, the pilot security requirements from
Phase V, does not exist yet.

| Input | Result | Grade |
|---|---|---|
| S1: LLM cost | About 0.08 % of net revenue; no economic reason to leave Forge; BYO key would need egress and forfeit Runs on Atlassian | model tested; prices search-reported |
| S2 / GATE-S2: Forge-only compute | Up to about 300k pages (175k to 370k) with Architecture X; REST quota binds every architecture | ESTIMATED; limits search-reported |
| S3: trigger PoC | Forge-only check is eligible by construction; per-edit reads show the approved text must be cached | validator VERIFIED; live unmeasured |
| Pilot security requirements (Phase V) | does not exist yet | none |
| Decision rule | missing | none |

The evidence **leans Forge-only**; that is a reading, not an application of the rule. The evidence table, the verbatim implication
lines from S1 and S2, and what could change the reading are in [ADR-013](adr/ADR-013-forge-only-vs-remote-compute.md#evidence-so-far).

## 5. GATE-S4: where the kill clause stands

> *If Evergreen ships change-time prevention before our decision point, the differentiation thesis is re-argued from scratch in writing.*

**Has it fired? No evidence that it has; it cannot be evaluated.** Evergreen is not located; no competitor page could be fetched;
"change-time prevention" is not defined in any document in the repository; and the decision point is not recorded (it lives in the
missing addendum). The weekly watcher keeps the question open mechanically: its generated thesis table reads `UNKNOWN: not located`
for Evergreen, never "not seen", and `REVIEW NOW` for any competitor whose own pages use both contradiction words and change-time
words. The written side, with a working definition of "change-time prevention" for the owner to confirm, a suggestion to widen the
clause to *any competitor, or Atlassian*, and the template for the re-argument, is in
[`competitors/differentiation-thesis.md`](competitors/differentiation-thesis.md).

## 6. Reconciliation and the source documents

**State at the start** ([`RECONCILIATION.md`](RECONCILIATION.md)): the repository held only `LICENSE`; the first session was
interrupted before any file was written; nothing was complete, so nothing needed redoing.

**The two source documents never arrived** (`wiki-gardener-prompt-set.md`, the v2 plan; `conflict-radar-v3-addendum.md`, the active
plan). Per the instructions, [`source/README.md`](source/README.md) records them as pending and nothing was paraphrased from memory.
Consequently, and listed in [`source/README.md`](source/README.md): the bodies of ADR-001 to ADR-013 are `TODO: expand from source`;
the ADR-013 decision rule is not applied; the amendments A1 to A11 are numbered only where the owner's message numbered them (A03),
the others provisionally, and A08 to A11 are unknown; PV.3 ([`phase-v/kill-proceed-criteria.md`](phase-v/kill-proceed-criteria.md))
is a placeholder with **no thresholds**; the exact GATE wording is the owner's one-line definitions; the decision-point date is unknown.

**"Every place the source documents contradicted my brief": none can be listed**, because there are no source documents in the
repository to read. What can be listed is where the *follow-up message*, which describes them, contradicted the *original brief*
([`RECONCILIATION.md`](RECONCILIATION.md) §4):

1. **ADR-012's identity.** I had planned it as "compute placement". The follow-up says ADR-012 is the connector expansion contract
   and compute placement is ADR-013 (Open). My guess was wrong; nothing was written under it.
2. **"Seed ADR-000 plus three stubs"** became ADR-000 to ADR-013 with the owner's statuses.
3. **Forge-first framing** versus an open fork (see §3).
4. **S2's verdict form**: the generic block became the GATE-S2 sentence form (*"Forge-only supports up to N pages with architecture
   X"*), with "estimated, arithmetic shown" where it cannot be measured.
5. **S3's detector shape**: I had planned a symmetric TF-IDF page-pair comparison; the follow-up requires the A3 shape (changed
   spans against an approved-sources set, quotes and character offsets, never drop near-identical pairs). Built that way.
6. **PR structure**: one PR per spike *and* one PR for the ADR, amendment and ADR-013 work. Both honoured: four spike PRs plus the
   session PR.

When the two files are added, re-run the pass described at the end of `RECONCILIATION.md`: replace each `TODO: expand from source`,
apply the ADR-013 rule, renumber the amendments, write PV.3, and then list the real contradictions.

## 7. Recommended next gate: the admin mockup falsification test

**Not a kill recommendation.** No spike falsified the idea: the LLM stage is affordable with a budget cap, Forge-only fits at 50k pages
with margin, the change-time check works in principle, and the competitor evidence is search-reported and unread. But no spike
validated the wedge either, and the open questions that decide it are exactly the ones only administrators can answer:

- **Contradictions urgent, or would staleness do?** The thesis stands or falls on this, now that K-AI claims the word and Rovo
  covers staleness.
- **Do they have the contradictions the cheap detector can catch** (changed numbers, negations, near-restatements), or mostly
  paraphrases?
- **Would they give access?** Read-only app permissions on a 50k-page instance is a security review, and ADR-013's last input.
- **Evergreen-forcing:** which tool do they use or consider today, and what would it have to do before they stopped caring?

The draft is [`phase-v/interview-script.md`](phase-v/interview-script.md): for administrators of 50k-page-plus instances, with
Evergreen-forcing questions, access-reality questions, and the contradictions-urgent versus staleness-would-do question, plus a
record sheet. The audit that goes with it is [`phase-v/concierge-scanner-spec.md`](phase-v/concierge-scanner-spec.md) (it runs
`npm run scan` from Spike S3 on an exported space). **PV.3, the kill and proceed bar, must be written before the first interview**,
so that the result cannot move the goalposts; it is a placeholder here because its text is in the missing addendum.

**The next action, in one sentence: run the one-command competitor baseline (so the interviews can name K-AI, AI Hygiene Inspector
and whatever Evergreen turns out to be), supply the missing PV.3 criteria, and then show contradiction-report mockups to administrators
of 50k-plus-page Confluence instances using `docs/phase-v/interview-script.md`.**

## Appendix: pull requests and the files each created or changed

Generated from `git diff --name-status origin/main...<branch>` on 2026-10-01; later commits to a branch are not reflected. The five
branches touch no file in common, so they can merge in any order.

<details><summary><b>Session pull request: "ADR history, amendments, ADR-013 wiring"</b>, PR (this PR): 35 files, all created</summary>


- `.github/workflows/ci-docs.yml`
- `.gitignore`
- `README.md`
- `docs/PHASE-MINUS-1-SUMMARY.md`
- `docs/RECONCILIATION.md`
- `docs/adr/ADR-000-phase-minus-1-fact-finding-precedes-invariants.md`
- `docs/adr/ADR-001-content-hash-and-timestamp-diffing.md`
- `docs/adr/ADR-002-minhash-lsh-lexical-redundancy.md`
- `docs/adr/ADR-003-composite-canonicality.md`
- `docs/adr/ADR-004-suggest-only-writes.md`
- `docs/adr/ADR-005-verdict-cache-key.md`
- `docs/adr/ADR-006-single-postgres-rls.md`
- `docs/adr/ADR-007-forge-ui-remote-batch-hybrid.md`
- `docs/adr/ADR-008-same-topic-funnel.md`
- `docs/adr/ADR-009-staleness-prior-and-hard-signals.md`
- `docs/adr/ADR-010-per-tenant-lightgbm-feedback-ranker.md`
- `docs/adr/ADR-011-verdictprovider-byo-llm-routing.md`
- `docs/adr/ADR-012-connector-expansion-contract.md`
- `docs/adr/ADR-013-forge-only-vs-remote-compute.md`
- `docs/adr/README.md`
- `docs/adr/amendments/A01.md`
- `docs/adr/amendments/A02.md`
- `docs/adr/amendments/A03.md`
- `docs/adr/amendments/A04.md`
- `docs/adr/amendments/A05.md`
- `docs/adr/amendments/A06.md`
- `docs/adr/amendments/A07.md`
- `docs/adr/amendments/README.md`
- `docs/phase-v/concierge-scanner-spec.md`
- `docs/phase-v/interview-script.md`
- `docs/phase-v/kill-proceed-criteria.md`
- `docs/source/README.md`
- `docs/spikes/README.md`
- `tools/check-verdicts/check_verdicts.py`
- `tools/check-verdicts/tests/test_check_verdicts.py`

</details>

<details><summary><b>Spike S1: Forge LLM cost model</b>, PR #1: 12 files, all created</summary>


- `.github/workflows/ci-cost-model.yml`
- `docs/spikes/01-forge-llm-cost-model.md`
- `tools/cost-model/README.md`
- `tools/cost-model/SENSITIVITY.md`
- `tools/cost-model/__pycache__/cost_model.cpython-311.pyc`
- `tools/cost-model/__pycache__/report.cpython-311.pyc`
- `tools/cost-model/cost_model.py`
- `tools/cost-model/prices.json`
- `tools/cost-model/report.py`
- `tools/cost-model/run.py`
- `tools/cost-model/tests/__pycache__/test_cost_model.cpython-311.pyc`
- `tools/cost-model/tests/test_cost_model.py`

</details>

<details><summary><b>Spike S2: Forge-only compute feasibility</b>, PR #2: 14 files, all created</summary>


- `.github/workflows/ci-compute-budget.yml`
- `docs/spikes/02-forge-only-compute-feasibility.md`
- `tools/compute-budget/BUDGET.md`
- `tools/compute-budget/README.md`
- `tools/compute-budget/__pycache__/budget.cpython-311.pyc`
- `tools/compute-budget/__pycache__/report.cpython-311.pyc`
- `tools/compute-budget/bench/minhash-bench.mjs`
- `tools/compute-budget/bench/results.json`
- `tools/compute-budget/budget.py`
- `tools/compute-budget/limits.json`
- `tools/compute-budget/report.py`
- `tools/compute-budget/run.py`
- `tools/compute-budget/tests/__pycache__/test_budget.cpython-311.pyc`
- `tools/compute-budget/tests/test_budget.py`

</details>

<details><summary><b>Spike S3: change-time trigger PoC</b>, PR #3: 62 files, all created</summary>


- `.github/workflows/ci-forge-change-trigger.yml`
- `apps/forge-change-trigger/.gitignore`
- `apps/forge-change-trigger/DEPLOY.md`
- `apps/forge-change-trigger/README.md`
- `apps/forge-change-trigger/manifest.yml`
- `apps/forge-change-trigger/package-lock.json`
- `apps/forge-change-trigger/package.json`
- `apps/forge-change-trigger/scripts/bench.ts`
- `apps/forge-change-trigger/scripts/corpus-probe.ts`
- `apps/forge-change-trigger/scripts/scan-files.ts`
- `apps/forge-change-trigger/scripts/seed-site.ts`
- `apps/forge-change-trigger/src/app.ts`
- `apps/forge-change-trigger/src/confluence.ts`
- `apps/forge-change-trigger/src/core/detect.ts`
- `apps/forge-change-trigger/src/core/diff.ts`
- `apps/forge-change-trigger/src/core/index.ts`
- `apps/forge-change-trigger/src/core/sentences.ts`
- `apps/forge-change-trigger/src/core/slots.ts`
- `apps/forge-change-trigger/src/core/text.ts`
- `apps/forge-change-trigger/src/core/tfidf.ts`
- `apps/forge-change-trigger/src/core/types.ts`
- `apps/forge-change-trigger/src/forge-deps.ts`
- `apps/forge-change-trigger/src/frontend/index.tsx`
- `apps/forge-change-trigger/src/handler.ts`
- `apps/forge-change-trigger/src/panel.ts`
- `apps/forge-change-trigger/src/resolver.ts`
- `apps/forge-change-trigger/test/app.test.ts`
- `apps/forge-change-trigger/test/confluence.test.ts`
- `apps/forge-change-trigger/test/detect.test.ts`
- `apps/forge-change-trigger/test/diff.test.ts`
- `apps/forge-change-trigger/test/fixtures.test.ts`
- `apps/forge-change-trigger/test/fixtures/dataset.json`
- `apps/forge-change-trigger/test/fixtures/pages/arch-overview.v1.html`
- `apps/forge-change-trigger/test/fixtures/pages/environment-matrix.v1.html`
- `apps/forge-change-trigger/test/fixtures/pages/environment-matrix.v2.html`
- `apps/forge-change-trigger/test/fixtures/pages/faq-onboarding.v1.html`
- `apps/forge-change-trigger/test/fixtures/pages/faq-onboarding.v2.html`
- `apps/forge-change-trigger/test/fixtures/pages/kb-log-retention-summary.v1.html`
- `apps/forge-change-trigger/test/fixtures/pages/kb-log-retention-summary.v2.html`
- `apps/forge-change-trigger/test/fixtures/pages/policy-access-control.v1.html`
- `apps/forge-change-trigger/test/fixtures/pages/policy-data-retention.v1.html`
- `apps/forge-change-trigger/test/fixtures/pages/policy-incident-response.v1.html`
- `apps/forge-change-trigger/test/fixtures/pages/runbook-log-rotation.v1.html`
- `apps/forge-change-trigger/test/fixtures/pages/runbook-log-rotation.v2-months.html`
- `apps/forge-change-trigger/test/fixtures/pages/runbook-log-rotation.v2.html`
- `apps/forge-change-trigger/test/fixtures/pages/runbook-log-rotation.v3.html`
- `apps/forge-change-trigger/test/fixtures/pages/runbook-prod-access.v1.html`
- `apps/forge-change-trigger/test/fixtures/pages/runbook-prod-access.v2.html`
- `apps/forge-change-trigger/test/fixtures/pages/runbook-sev1-oncall.v1.html`
- `apps/forge-change-trigger/test/fixtures/pages/runbook-sev1-oncall.v2.html`
- `apps/forge-change-trigger/test/helpers.ts`
- `apps/forge-change-trigger/test/manifest.test.ts`
- `apps/forge-change-trigger/test/panel.test.ts`
- `apps/forge-change-trigger/test/scan.test.ts`
- `apps/forge-change-trigger/test/seed.test.ts`
- `apps/forge-change-trigger/test/sentences.test.ts`
- `apps/forge-change-trigger/test/slots.test.ts`
- `apps/forge-change-trigger/test/text.test.ts`
- `apps/forge-change-trigger/test/tfidf.test.ts`
- `apps/forge-change-trigger/tsconfig.json`
- `apps/forge-change-trigger/tsconfig.test.json`
- `docs/spikes/03-change-time-trigger-poc.md`

</details>

<details><summary><b>Spike S4: competitor watch</b>, PR #4: 38 files, all created</summary>


- `.github/workflows/ci-competitor-watch.yml`
- `.github/workflows/competitor-watch.yml`
- `docs/competitors/README.md`
- `docs/competitors/differentiation-thesis.md`
- `docs/competitors/snapshots/README.md`
- `docs/spikes/04-competitor-watch.md`
- `tools/competitor-watch/.gitignore`
- `tools/competitor-watch/README.md`
- `tools/competitor-watch/competitor_watch/__init__.py`
- `tools/competitor-watch/competitor_watch/cli.py`
- `tools/competitor-watch/competitor_watch/config.py`
- `tools/competitor-watch/competitor_watch/diffing.py`
- `tools/competitor-watch/competitor_watch/extract.py`
- `tools/competitor-watch/competitor_watch/fetch.py`
- `tools/competitor-watch/competitor_watch/render.py`
- `tools/competitor-watch/competitor_watch/snapshot.py`
- `tools/competitor-watch/sources.json`
- `tools/competitor-watch/tests/fixtures/bot_wall.html`
- `tools/competitor-watch/tests/fixtures/expected_snapshot.md`
- `tools/competitor-watch/tests/fixtures/js_shell.html`
- `tools/competitor-watch/tests/fixtures/listing_jsonld.html`
- `tools/competitor-watch/tests/fixtures/listing_nextdata.html`
- `tools/competitor-watch/tests/fixtures/listing_text.html`
- `tools/competitor-watch/tests/fixtures/release_notes.html`
- `tools/competitor-watch/tests/fixtures/robots_allow.txt`
- `tools/competitor-watch/tests/fixtures/robots_disallow.txt`
- `tools/competitor-watch/tests/fixtures/search_empty.html`
- `tools/competitor-watch/tests/fixtures/search_results.html`
- `tools/competitor-watch/tests/helpers.py`
- `tools/competitor-watch/tests/test_cli.py`
- `tools/competitor-watch/tests/test_config.py`
- `tools/competitor-watch/tests/test_diff.py`
- `tools/competitor-watch/tests/test_extract.py`
- `tools/competitor-watch/tests/test_fetch.py`
- `tools/competitor-watch/tests/test_render.py`
- `tools/competitor-watch/tests/test_snapshot.py`
- `tools/competitor-watch/tests/test_transport_local.py`
- `tools/competitor-watch/watch.py`

</details>

161 files in total across the five pull requests; every one is new (the repository held only `LICENSE`). Of the files in the session pull request, `docs/adr/ADR-013-forge-only-vs-remote-compute.md` and this document were written last, after the spike verdicts existed.

