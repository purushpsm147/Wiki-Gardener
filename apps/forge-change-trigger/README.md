# forge-change-trigger

Spike S3's proof of concept: **a Confluence page edit triggers a check of the changed spans against approved source pages, and the
result is logged with both quotes and character offsets.** A demo to test one claim, not the product. The verdict, the evidence
labels and everything this does *not* prove are in [`docs/spikes/03-change-time-trigger-poc.md`](../../docs/spikes/03-change-time-trigger-poc.md).

```
Confluence page published
  -> Forge trigger (avi:confluence:created:page | avi:confluence:updated:page)
  -> src/handler.ts  -> src/app.ts: handlePageUpdated
       fetch the page, an earlier version, and each approved source          (REST v2, api.asApp(), read-only)
       diff the two versions into changed spans                              (src/core/diff.ts)
       align the changed sentences with approved sentences                   (src/core/tfidf.ts, detect.ts)
       compare numbers, units, negation, antonyms; no LLM                    (src/core/slots.ts)
  -> log lines  conflict-radar.result / conflict-radar.conflict              (forge logs)
  -> KVS key  conflicts:<pageId>
  -> byline item "Conflict Radar" on the page  -> src/resolver.ts -> src/panel.ts
       every quote from an approved page is released only after the *viewer's* live read permission is re-checked (A06)
```

## Run it

```
npm ci
npm test                  # the detector, the handler flow with a fake Confluence, A06, the manifest validator, the fixtures
npm run typecheck
npm run bench             # how long the analysis takes as the approved set grows (sandbox CPU)
npm run probe             # false alarms on real prose nobody wrote for it (the READMEs and @types/node in node_modules)
npm run scan -- <dir> --approved a.html,b.html     # offline audit of an exported folder of pages
```

Nothing here needs Atlassian. To run it on a real site, follow [`DEPLOY.md`](DEPLOY.md).

## Layout

| Path | What it is |
|---|---|
| `src/core/` | The detector. Pure functions on text, no Forge, no network. `analyzeEdit` is the entry point. |
| `src/confluence.ts` | A thin REST v2 client over an injected requester; response shape verified from `confluence.js@3.2.0` types. |
| `src/app.ts` | The change-time flow. Everything it needs from outside comes in through `Deps`, so tests use fakes. |
| `src/forge-deps.ts` | The only file that touches `@forge/api` and `@forge/kvs`. |
| `src/panel.ts`, `src/resolver.ts`, `src/frontend/index.tsx` | The byline panel and its viewer-permission check. |
| `manifest.yml` | Two product-event triggers, one resolver, four read-only scopes plus app storage, no remotes. |
| `test/fixtures/` | Ten synthetic pages, three planted contradictions, five controls. |
| `scripts/scan-files.ts` | Offline audit mode, the aid for the concierge audit in `docs/phase-v/concierge-scanner-spec.md`. |
| `scripts/seed-site.ts` | Creates the demo pages on a real site (untested against one). |
| `scripts/bench.ts` | The scale benchmark. |
| `scripts/corpus-probe.ts` | False alarms on unrelated real prose, with a dev/held-out split and a positive control. |

## How the detector decides

1. **What changed.** A word-level diff of the previous and current normalized text gives the changed spans. Only sentences touching a
   span are checked, so an old, unrelated disagreement on the page is not re-reported on every edit.
2. **What to compare with.** Sentences are compared by TF-IDF cosine with numbers masked and negations dropped, so "retained for 30
   days" and "must be retained for 90 days" look alike. **There is no upper similarity cutoff**: a near-identical pair that differs in
   exactly one number is the most dangerous case and is ranked first, never filtered (the "A3 shape").
3. **What counts as a disagreement.** Quantities are compared with unit normalization (`3 months` equals `90 days`; months and
   years allow 2 % so `12 months` equals `1 year`), polarity by negation (only between statements aligned at 0.7 or closer, because
   prose is full of unrelated "not"), and a short antonym list (`required`/`optional`, `allowed`/`prohibited`, `at least`/`at most`,
   ...). A table row is one line, cells joined by ` | `. If any near-best approved sentence agrees on every slot, nothing is reported.
   Different environments ("Staging ..." against "Production ...") are not compared as equals.
4. **What is reported.** Both whole sentences and the differing values, each with start and end offsets into that page's normalized
   plain text (`storageToText`), ranked by severity.

## Limits that matter before anyone relies on it

- The fixtures were written by the same author as the detector. Passing them shows the plumbing works; it says nothing about recall
  or precision on real content. Some rules (best-match gating, the count-noun whitelist) were added *after* seeing false positives on
  these same fixtures.
- It checks edits to ordinary pages against approved pages. It does **not** re-check the space when an approved page changes.
- It re-reads the whole approved set on every edit (4 + 2N REST points for N approved pages), which a real product cannot afford.
- It finds numbers, negations and a few antonyms in near-restatements. Paraphrases, claims spread over two sentences and anything
  without a number, negation or listed antonym are missed by design, and the 0.7 polarity threshold misses some real contradictions.
- The panel shows the result of the most recent check, not a lifecycle of open conflicts.
- No Forge deploy, no live event and no latency has been observed. See `DEPLOY.md`.
