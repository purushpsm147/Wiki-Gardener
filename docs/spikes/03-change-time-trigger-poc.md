# Spike S3 — Change-time trigger proof of concept (GATE-S3)

> **One sentence:** the detection logic and the Forge handler work end to end against a faithful fake, 160 tests pass, and the
> manifest passes the platform's own validator, but **nothing has run on a real Confluence site**, so "within minutes" is an
> unmeasured claim and the live demo is a 30-minute TODO ([`DEPLOY.md`](../../apps/forge-change-trigger/DEPLOY.md)).

Links to `../source/`, `../phase-v/` and `01-forge-llm-cost-model.md` point at files in other pull requests of this session and
resolve once those merge.

## Question

Can an edit to a Confluence page be checked against approved source pages **at the moment of the edit**, using only what Forge gives
an app, and produce a conflict that a human can verify (both quotes, exact positions)? This is the claim the whole "prevent, not
just detect later" differentiation rests on, so this spike tries to break it cheaply.

**GATE-S3** (the owner's wording): *an editor changes "90 days" to "30 days" on a procedure page, and within minutes there is a
logged conflict against the approved policy page, with both quotes and offsets.* The fixture contains exactly this case, and the
test asserts the quotes **and** the character offsets, with the numbers hard-coded so a bug on both sides cannot pass.

## Evidence rules

- **VERIFIED** — read or run here: package contents on npm (`@forge/manifest@13.6.0`, `@forge/cli@14.1.0`, `@forge/api@8.2.0`,
  `@forge/kvs@2.0.7`, `@forge/resolver@2.0.0`, `@forge/bridge@7.1.0`, `@forge/react@12.3.0`, `confluence.js@3.2.0`; all fetched
  2026-10-01), and code executed in this sandbox. Type-checking the app against those packages under `strict` is also evidence: the
  calls exist with those shapes.
- **ASSUMED** — everything about how Atlassian's platform *behaves*. `*.atlassian.com` is blocked in this sandbox, so documentation
  claims are `ASSUMED (search-reported: <url>, 2026-10-01)`, a lead and not a fact.
- **MEASURED** numbers are sandbox CPU (Intel Xeon 2.1 GHz, Node 22.22), never Forge. **ESTIMATED** numbers show their arithmetic.
- **The A3 text did not arrive.** The source documents are still missing ([`docs/source/README.md`](../source/README.md)), so
  "A3-shaped" below means the owner's one-line description: *compare the changed spans of the updated page with an approved-sources
  set, and never drop near-identical pairs.* It is not a reading of amendment A3 itself.

## What was built

`apps/forge-change-trigger/` ([README](../../apps/forge-change-trigger/README.md)). A Forge app, UI Kit only, no remotes:

```
page created / updated  ->  trigger function  ->  fetch page, an earlier version, each approved source  (REST v2, app context)
  -> diff into changed spans  -> align changed sentences with approved sentences  -> compare numbers / negation / antonyms
  -> log lines (quotes + offsets) and a KVS record  -> byline panel "Conflict Radar", gated by the viewer's own read permission
```

The detector is LLM-free: a word-level diff, TF-IDF cosine on sentence templates with numbers masked and negations dropped (so
"retained for 30 days" and "must be retained for 90 days" look alike), unit-normalized quantity comparison, negation and a short
antonym list, and a guard that keeps "Staging ... 14 days" from contradicting "Production ... 90 days". **There is no upper
similarity cutoff**: a copy of an approved sentence with one number changed has cosine 1.0 and is ranked *first*.

## What ran, and how much it proves

| Step of GATE-S3 | What was exercised | Evidence |
|---|---|---|
| Editor changes 90 to 30 on a procedure page | Fixture `runbook-log-rotation` v1 to v2; only the number differs (`changedSpans` returns one span) | test, deterministic |
| An event reaches the app | `parseEvent` on a payload shaped like the documented one; **the real shape is unverified** | fake; ASSUMED (search-reported) |
| App reads the page, its earlier version and the approved pages | `getPage` through an injected requester; response shape from `confluence.js@3.2.0` types | **VERIFIED shape**, fake transport |
| Conflict found against the approved policy page | one `numeric/duration` conflict against page 1001 | test |
| Both quotes, with offsets | changed `[69,111]`, value `[103,110]`; approved `[123,169]`, value `[161,168]`; hard-coded; slices equal the quotes | test |
| Logged | structured `conflict-radar.conflict` line with both quotes and offsets; `forge logs` shows it | test of the line; **`forge logs` unrun** |
| Within minutes | the handler computes `versionToDetectedMs` and `eventToDetectedMs` itself; fake clock gives 2,620 ms and 1,620 ms, which is arithmetic, not a measurement | **not measured** |
| Viewer sees it only if allowed | `getPanelData` re-checks the viewer's read permission at read time and fails closed (amendment A06) | test; **`api.asUser()` unrun** |
| Manifest is deployable | `@forge/manifest` `validate()` passes; event exists in the platform's event-to-scope mapping; scopes cover it; no remotes, providers, Connect modules or external permissions | **VERIFIED** (offline); `forge lint` and `forge deploy` need a login |

## The fixture, and why it proves little

Ten synthetic pages in `test/fixtures/` (3 approved policies, 3 procedure pages, 4 distractors), three planted contradictions and
five controls that must stay quiet. **Written by the same author as the detector.** Passing it shows the plumbing and the rules do
what the author meant; it says nothing about recall or precision on real content.

| Planted | Edit | Found as |
|---|---|---|
| `retention-90-to-30` (**GATE-S3**) | "retained for 90 days" to "30 days" | numeric, duration; alignment 1.0, severity 0.7 |
| `vpn-required-to-not-required` | adds "A VPN connection is not required for read-only production access." | polarity, negation; alignment 0.779 (paraphrased) |
| `sev1-ack-15-to-30-minutes` | "within 15 minutes" to "within 30 minutes" | numeric, duration |

| Control (must not be reported) | Why it is a trap |
|---|---|
| `retention-repair-30-to-90` | the edit *removes* the disagreement (a naive pairwise detector flags it against a sibling sentence) |
| `retention-90-days-to-3-months` | equal after unit normalization |
| `kb-intro-only` | a near-identical copy of approved sentences, with only the intro changed (the A3 trap: it must align at 1.0 and *not* be a false positive) |
| `environment-wording-only` | another environment states 14 days; the scope guard must suppress 90 against 14 |
| `faq-unrelated-number` | same unit (business days) as an approved sentence, unrelated topic |

Audit mode (every sentence counts as changed, no previous version) over the other seven pages finds exactly the three planted
conflicts and nothing else. This is the mode the concierge audit in [`docs/phase-v/concierge-scanner-spec.md`](../phase-v/concierge-scanner-spec.md)
would use; `npm run scan -- <dir> --approved a.html,b.html` runs it offline on an exported folder.

### What was tuned after seeing results (a confession, not a footnote)

The rules below were added **after** running earlier versions on these same fixtures, so a clean pass on them is weaker than it
looks:

1. The first version compared every aligned pair on its own and flagged a correct repair against a sibling sentence ("Audit logs
   ... 365 days" next to "Application logs ... 90 days"). Added **best-match gating**: compare only the near-best approved
   sentences, and report nothing if any of them agrees on every slot. An ablation test shows what breaks without it.
2. A business-days regex bug and a too-permissive generic count slot (anything after a number counted as a unit, so "Version 2
   shipped" parsed) led to a **whitelist of count nouns**.
3. The alignment threshold (0.5 base) is a recall/precision dial; one test shows a stricter value misses the paraphrased planted case.

## Beyond the fixtures: probes that found real defects

After the fixtures passed, the detector was probed with inputs written to break it, and then run on **real prose nobody wrote for
it**. Each row changed the code and has a regression test.

| Probe | Found | Change |
|---|---|---|
| "12 months" against "1 year" | false conflict (a 30-day month is not 365/12 days) | calendar units (months, years) compare with 2 % tolerance; fixed units stay exact |
| "at least 12 characters" against "at most 12 characters" | missed (no word-level signal) | `at least / at most` antonym pair |
| Retention in a **table** (`Application logs | 90 days`) | **missed in both directions**: each cell was its own line | a table row is one line, cells joined by ` | ` |
| Two versions published before the first event is handled | the earlier edit was never checked (the diff was always latest-1 to latest) | diff from the oldest of: latest-1, the event's version-1, the last checked version |
| An approved source moved to the trash | still compared against | a source that is not `current` counts as unavailable and is listed in `approvedMissing` |
| The same event delivered twice, or an update that makes no version | full re-check, 2+N reads | skip when the version was already checked (one read) |
| Real prose: README files of ~180 npm packages and the JSDoc of `@types/node` (12,014 sentences, unrelated to each other, so every alarm is false) | **polarity was the noise**: 37 false alarms in the 5,240 README sentences (7.1 per 1,000), all negation differences ("not", "no", "without") between sentences that merely share a topic, many on headings and fragments | polarity needs both sentences to be statements (an auxiliary or modal, 3 content tokens) and alignment of at least 0.7; one alarm per approved page and slot |

Still **missed by design**, and shown by the probes: a paraphrase ("kept for a quarter" against "retained for 90 days"), a claim
spread over two sentences ("The retention period is 90 days."), and any contradiction with no number, negation or listed antonym.

### The polarity threshold is a recall/precision dial, measured

False alarms on the two real-prose corpora, alignment threshold for polarity swept (the statement rule on throughout). "dev" is the
half the rules were tuned on, "held-out" the other half; honestly, an earlier run over every document was read before the rules
were tightened, so held-out was seen once, not never.

| `polarityMinAlignment` | README corpus (5,240 sentences) | `@types/node` (6,774 sentences) | per 1,000 sentences, both |
|---|---|---|---|
| 0.5 | 8 | 53 | 5.08 |
| 0.6 | 2 | 22 | 2.00 |
| **0.7 (default)** | 1 | 5 | **0.50** |

The price of 0.7 is recall: *"Backups are encrypted and stored in a separate region."* against *"Backups are not encrypted when
they are stored in the same region."* aligns at 0.58 and is a real contradiction that the default does **not** report (a test shows it
is found with the rule off). *"Customer data must be encrypted at rest and in transit."* against *"... is not always encrypted at
rest."* aligns at 0.67 and is also missed. The default prefers precision, because a false alarm spends the credibility the product
lives on; whether that is the right trade is a Phase V question, not an engineering one.

**Numeric false alarms on real text are not measured.** Technical prose has few quantities with units: 27 sentences across the edited README
documents and 21 across the edited `@types/node` ones, so 0 false alarms in 48 opportunities says only that the rate is probably below about 6 % (rule of
three), and nothing about a space full of retention periods and SLAs. A **positive control** on real sentences (change the number in
a real sentence that has exactly one number-and-unit, and check the original is reported) found 17 of 18; the miss was a fragment
`(1KB = 1,024 Bytes)` with too little text to align. All 18 unchanged copies stayed quiet. `npm run probe` reproduces all of this.

## Cost and scale

**CPU is not the constraint.** `npm run bench` (MEASURED, sandbox CPU, synthetic text, one edited sentence checked against N approved
pages of 40 sentences each, which re-tokenizes the whole approved set on every edit): 3 pages 1 to 4 ms, 30 pages 11 to 21 ms, 100
pages 40 to 61 ms, 1,000 pages (40,000 sentences) 0.42 to 0.46 s. Roughly linear, about 0.4 ms per approved page. Both a sparse and
a dense vocabulary were run (the dense one sends more candidate pairs to the cosine step); they came out within about 25 % of each other,
which is run-to-run noise on this machine.

**REST reads are.** The app reads the current page, one earlier version and every approved page on every edit: **2 + N calls, each 1
base point plus 1 per page returned, so 4 + 2N points** (ESTIMATED; the point rule is `ASSUMED (search-reported)` from Spike S2, as
is whether Forge's own `requestConfluence` calls count).

| Approved pages N | Points per edit | Edits per hour the whole app's 65,000-point pool allows | With approved text cached (4 points) |
|---|---|---|---|
| 3 | 10 | 6,500 | 16,250 |
| 10 | 24 | 2,708 | 16,250 |
| 50 | 104 | 625 | 16,250 |
| 200 | 404 | 160 | 16,250 |
| 1,000 | 2,004 | 32 | 16,250 |

So the PoC's read pattern is fine for the demo (N = 3) and **cannot be the product**: the approved text must be cached (it
changes only when an approved page is edited, and the app already receives that event) and candidate sentences found through the
index Spike S2 sizes. This is the same wall S2 found, seen from the trigger side: the Confluence REST quota binds, not compute. A
second lever, storing each page's last normalized text so the earlier version need not be fetched, would cut a further 2 points.

## Design decisions (all reversible)

- **Store in KVS and show a byline panel, not a page comment.** A comment needs a write scope and would trigger the app's own events
  (`selfGenerated`); the KVS record needs only `storage:app`, is idempotent, and the panel can enforce amendment A06. "Cheaper"
  here means scope and trust, not lines of code. The gate asks for a *logged* conflict, which the log lines satisfy.
- **Read approved pages as the app, release them as the viewer.** Detection must see every approved page (`api.asApp()`), but what
  is *shown* is gated by `api.asUser()` at read time; a stored result is never an authorization layer, and an error means hidden.
  Quoting a page to someone who cannot open it is a leak whatever the architecture, so this is a design constraint, not an optimization.
- **Subscribe to created as well as updated.** A pasted copy of a stale policy is the classic contradiction; a new page is audit
  mode (its whole text counts as changed). One more event name, validated against the platform's mapping.
- **Skip edits to an approved source.** The reverse direction needs the S2 index (below).
- **Fail loudly.** A Confluence error throws and stores nothing, instead of recording a wrong "no conflicts".

## What this spike found

1. **The cheap detector reaches a narrow, sure class.** Numbers with units, negations and a few antonyms in near-restatements:
   exactly the "90 days became 30" edit. Real contradictions are mostly paraphrased, spread over sentences, or semantic; those need
   a language model, which [Spike S1](01-forge-llm-cost-model.md) found affordable on Forge. Whether the *narrow class* is where administrators' pain lives is the
   Phase V question ([`interview-script.md`](../phase-v/interview-script.md), [`concierge-scanner-spec.md`](../phase-v/concierge-scanner-spec.md)).
2. **The per-edit read pattern is the real cost** (above), and it is a Confluence quota problem rather than a Forge one.
3. **The reverse direction is not covered.** When an *approved* page changes ("retention is now 365 days"), the pages that now
   disagree with it must be found, and that needs the index, not this trigger. In a real space it may be the commoner source of
   contradictions, and it is the case a staleness tool can approximate.
4. **Live behaviour of the event is unknown**: whether it fires per published version or per autosave, what `updateTrigger` can be
   (it is search-reported to be "the reason that caused the update event to trigger"), whether delivery repeats, and the delay.

## What this spike does not prove

- **Any live behaviour.** No event was received, no function ran on Forge, no `forge lint`, `deploy` or `install` ran (all need a
  login), `forge logs` was not read, `api.asUser()` was not exercised, and the webpack bundling inside `forge deploy` has never seen this code.
- **Latency.** "Within minutes" is unmeasured. The 2.6 s in the tests comes from a fake clock.
- **Recall or precision on real contradictions.** The fixtures are circular; the real-prose probes measure false alarms between
  unrelated documents only, and numeric false alarms not at all (48 opportunities).
- **Live-edit mode.** Whether the event fires when an editor never clicks Update.
- **Tables beyond the simple case** (nested tables, merged cells), Markdown or other macros, and any page larger than the fixtures.
- **Two approved sources that disagree with each other**, and approved sources in other spaces.
- **A product.** There is no conflict lifecycle: the panel shows the result of the most recent check, so a later unrelated edit
  clears the display (the log keeps every detection).
- **That `confluence:contentBylineItem` with UI Kit renders the panel as written.** It type-checks against `@forge/react@12.3.0`;
  nothing has rendered it.

## Live demo results (TODO)

Not run: no Atlassian account, and `*.atlassian.com` is blocked in this sandbox. **Do not fill this in from the tests.**

TODO, local, about 30 minutes: follow [`DEPLOY.md`](../../apps/forge-change-trigger/DEPLOY.md) and paste its result sheet here
(`forge lint`/`deploy` outcome, the raw `event-probe` line, the logged conflict with offsets, 20 latency samples as min/median/max,
the A06 check with a second user, and `forge eligibility`, which also settles Spike S2's criterion G6).

## Confirm locally

| # | URL or action | What it must say |
|---|---|---|
| 1 | https://developer.atlassian.com/platform/forge/events-reference/confluence/ † | the payload of `avi:confluence:updated:page` and `created:page`: `content` shape (does it carry the id and version number?), `updateTrigger` values, `selfGenerated`; **when it fires** (publish, autosave, live edit) |
| 2 | https://developer.atlassian.com/platform/forge/manifest-reference/modules/trigger/ † | `events` and `filter` syntax; whether duplicate delivery can happen |
| 3 | https://community.developer.atlassian.com/t/event-when-confluence-page-is-updated/83692 † | what the community reports about when and how often the page-updated event fires |
| 4 | https://developer.atlassian.com/cloud/confluence/rate-limiting/ | the point rule, and whether Forge `requestConfluence` calls count against the 65,000 per hour |
| 5 | The Confluence v2 `GET /wiki/api/v2/pages/{id}` reference | the `version` query parameter, the `status` values (does a trashed page return, and as what?) |
| 6 | Forge docs, Key-Value Store | value size limit (240 KiB is assumed) and any per-installation cap |
| 7 | Forge docs, `confluence:contentBylineItem` and UI Kit resolvers | the module renders as written; `context.extension` carries the page id |
| 8 | Forge docs, "Product fetch API" and permissions | `asUser()` from a resolver needs consent for these scopes? |
| 9 | **Run** [`DEPLOY.md`](../../apps/forge-change-trigger/DEPLOY.md) | the live demo, the latency samples, A06 with two users, `forge eligibility` |

† came from a web-search result on 2026-10-01; the page itself was unreadable here. The other URLs are from memory and may have
moved; navigate from https://developer.atlassian.com/platform/forge/.

## Verdict

Decision: PROCEED-WITH-CONSTRAINT

Constraint: run the live demo in `DEPLOY.md` and record the latency before anyone says "change-time" in front of a customer; until Phase V shows what contradictions administrators actually have, describe the detector as finding changed numbers, negations and listed antonyms in near-restatements, and nothing wider.

GATE-S3: demonstrated end to end against a faithful fake of Confluence and Forge, where changing "90 days" to "30 days" on the runbook yields one logged conflict against the approved policy page with both quotes and character offsets 69 to 111 and 123 to 169, but NOT on a live site: event delivery, payload shape and "within minutes" are unmeasured and the exact procedure is `apps/forge-change-trigger/DEPLOY.md`.

Criteria evaluated:
- The GATE-S3 scenario produces a logged conflict with both quotes and offsets through the real handler against a fake Confluence — PASS — quotes and offsets `[69,111]` and `[123,169]` hard-coded in `detect.test.ts`, `app.test.ts` and the offline scanner test; fixture holds exactly this case
- A3 shape: changed spans compared with approved sources, no upper similarity cutoff, near-identical pairs ranked first, never dropped — PASS — an exact copy aligns at 1.0 and is quiet, a copy with one number changed is reported first (tests); implemented from the owner's description because the A3 text is missing
- Three planted contradictions found and five controls (repair, 90 days = 3 months, near-identical copy, other environment, unrelated number) quiet — PASS — circular: same author as the detector, and best-match gating and the count-noun whitelist were added after seeing results on these fixtures
- Manifest is deployable and Runs-on-Atlassian eligible by construction — PASS — `@forge/manifest@13.6.0` validates it offline, event and scopes match the platform mapping, no remotes, providers, Connect modules or external permissions; `forge lint` and `forge eligibility` need a login
- Results are released only to viewers who can read the approved page, at read time, failing closed (A06) — PASS — seven tests with fakes; `api.asUser()` itself unrun
- Behaviour survives bursts, duplicates, trashed sources, tables and calendar units — PASS — each found by a probe and pinned by a regression test
- Polarity and antonym false alarms on real unrelated prose are measured and brought below 1 per 1,000 sentences — PASS — 0.5 per 1,000 over 12,014 README and `@types/node` sentences (6 alarms, all polarity), down from 7.1 per 1,000 on the READMEs before the tightening; the threshold of 1 was a judgement made afterwards, not set in advance, and the 0.7 default trades recall for it
- Numeric false-alarm rate on real, quantity-dense text is known — FAIL — only 48 quantity-bearing sentences exist in the corpora, 0 alarms, which bounds the rate at about 6 % and says nothing about a policy space
- Recall on real, paraphrased contradictions is known — FAIL — not measured; two realistic paraphrased contradictions (alignment 0.58 and 0.67) are missed by the default, and paraphrase and multi-sentence claims are missed by design
- The event fires, carries the page id, and the conflict is logged within minutes on a real site — FAIL — not run (no Atlassian access); nothing live was observed and no latency was measured
- Per-edit cost is bounded independently of the approved-set size — FAIL — 4 + 2N Confluence REST points per edit (ESTIMATED), 2,004 at N = 1,000; CPU is not the problem (0.4 s at 40,000 approved sentences); the approved text must be cached and indexed (Spike S2)

Unverified assumptions carried forward: everything about live platform behaviour: that the page-updated event fires on the editor's normal save and on live-edit autosave, its payload (`content.id`, `content.version.number`, `updateTrigger` values) and its delay; duplicate delivery; the REST point rule and whether Forge requests count; that `forge deploy` bundles this code and `forge lint` accepts the manifest; that a UI Kit byline item renders the panel and that `api.asUser()` works from its resolver; the `status` the v2 API gives a trashed page; the KVS value limit; recall on real contradictions; numeric precision on real policy text; the same-author fixtures.

What would flip this verdict: (1) a live run in which the event does not fire for a normal published edit, lacks the page id, or arrives much later than a few minutes turns "change-time" into "scheduled-poll-time" and the differentiation thesis has to be re-argued around the polling interval; (2) a Phase V concierge audit in which fewer than a handful of the contradictions administrators care about are changed numbers, negations or listed antonyms, which makes a language-model stage the product and this detector a pre-filter; (3) Evergreen shipping change-time prevention first (Spike S4's kill clause).
