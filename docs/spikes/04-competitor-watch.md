# Spike S4 — Competitor watch protocol (GATE-S4)

> **Material finding, flagged first as the brief asks (ASSUMED, search-reported 2026-10-01; no competitor page could be read here):**
> **K-AI**, a vendor *not in the brief*, is reported to say on its own pages that it "continuously detects contradictions, duplicates,
> obsolescence" and "detects conflicts in real-time", with a Confluence integration. **AI Hygiene Inspector** may use the word too
> (one search summary did; the listing text quoted next to it did not). **Evergreen AI for Confluence**, the competitor GATE-S4's kill
> clause names, **could not be located** on the Marketplace by three searches. So the kill clause cannot be evaluated, and the
> thesis "nobody claims contradiction detection" is **already doubtful** before the first real snapshot. The baseline is one command
> away ([how](#baseline-not-taken-the-one-command)).

## Goal

An automated, repeatable baseline so nobody re-researches competitors by hand: snapshot the Marketplace listings of Evergreen AI for
Confluence, AI Hygiene Inspector and Better Content Archiving, plus Atlassian release notes and announcements that mention the Rovo
Documentation Agent or Rovo content-quality features, capturing feature list, pricing, install count, last updated, review count and
rating, and any mention of "contradiction", "conflict" or "inconsistent"; take the baseline; run it weekly, diff, and open an issue on
change; and say, per competitor, whether they now claim contradiction detection.

**GATE-S4** (the owner's wording): a competitor-watch verdict with a kill clause: *if Evergreen ships change-time prevention before our
decision point, the differentiation thesis is re-argued from scratch in writing.* The competitor snapshot carries a **Differentiation
thesis status** section: generated into `latest.md` from what the pages say, and written by a person in
[`docs/competitors/differentiation-thesis.md`](../competitors/differentiation-thesis.md).

## Evidence rules

- **VERIFIED** — run or read here: the tool's tests, its real HTTP transport against a local server, its real failure under the
  egress block, `actionlint`, the proxy's refusals.
- **ASSUMED (search-reported: URL, 2026-10-01)** — everything a competitor or Atlassian page is said to contain. A search provider's
  summary of a page this sandbox could not open: a lead, not a fact. `marketplace.atlassian.com`, `*.atlassian.com`, `k-ai.ai` and
  `evergreen.team` are all refused by the egress proxy (`WebFetch` returns `EGRESS_BLOCKED`; the tool's own run returns `Tunnel
  connection failed: 403`). The policy was left alone.
- Links to `../source/`, `../phase-v/` and the other spike documents resolve once the other pull requests of this session merge.

## What was built

[`tools/competitor-watch/`](../../tools/competitor-watch/README.md), Python standard library only:

```
sources.json ─► fetch (User-Agent, robots.txt, retries, size cap) ─► parse HTML ─► facts, features, keyword hits, mentions
                                                                       │
 docs/competitors/snapshots/latest.{json,md}  ◄── written only when something real changed
 issue body ◄── diff against the last snapshot (material / routine), plus health lines
```

- **Three extraction layers**, most to least reliable: the visible text (keywords and sentences survive any layout change),
  embedded structured data searched by key name (JSON-LD, `__NEXT_DATA__`), and regular expressions over the text. Every extracted
  value records which layer found it.
- **Two keyword classes.** `contradiction`: the owner's three words (`contradict*`, `conflict*`, `inconsisten*`) plus `discrepanc*`.
  `change_time`: words that suggest checking content as it is written or published (`before publish`, `as you edit`, `real-time`,
  `prevent*`, ...). A hit is a word with 120 characters of context on each side, not a claim; a person reads it.
- **Fails loudly.** Per source: `ok`, `partial` or `failed`, with the reason (HTTP status, `robots.txt`, empty JavaScript shell, bot
  wall, too little text, no structured fact). Exit code 2 if any source failed; the workflow then opens a `competitor-watch-broken`
  issue. A failed source **keeps its last good facts, marked stale**, so a bad week never reads as "the competitor dropped every
  feature"; a first run in which *every* source fails writes **no** snapshot.
- **Polite.** A User-Agent that says who is asking, `robots.txt` respected (unreachable or 5xx means do not fetch, as RFC 9309 says),
  two retries with backoff, 5 MB cap, text content only.
- **Weekly workflow** (`competitor-watch.yml`, Mondays 06:41 UTC and `workflow_dispatch`): run the tests, run the watcher, upload the
  raw pages as an artifact for 14 days, commit the snapshot if it changed, open an issue titled with the change count (and
  `MATERIAL` when a thesis keyword, feature, price, or Atlassian mention changed), open or update the broken-source issue, go red on a
  failure.
- **Offline mode.** `--raw-dir` saves every fetched page; `--from-dir` replays saved pages (or pages saved by hand from a browser)
  with no network. That is how the tool is used if a site shows the Action a bot wall, and how real pages become real test fixtures.
- **The thesis table.** After its Health table, `latest.md` has a generated one: for each competitor, whether its listing was
  located, how many `contradiction` words and how many `change_time` words its pages hold, and an indicator: `UNKNOWN` (not located,
  or the source failed), `REVIEW NOW` (both kinds of word present), words of one kind, or `not seen`. Evergreen, unlocated, reads
  `UNKNOWN: not located, so the kill clause cannot be evaluated`, never "not seen".

### Assumptions I made (stated, not asked)

- **"Open an issue if anything changed"** is read as: any change *past a noise threshold*. Install counts drift daily, so literally
  anything would open an issue every Monday. Installs, downloads and review counts must move 5 %, the rating 0.1; version, last
  updated, title and headings always count; features, prices, summaries, thesis keywords and Atlassian mentions are always material.
  `"issue_on": "material"` quiets it further. The snapshot is rewritten only when something other than timestamps and page hashes
  changed, so there is no commit a week of nothing.
- **Evergreen** is a `search` source: the watcher looks for a Marketplace listing with the name each week, and `UNKNOWN`s the kill
  clause until one exists. When the owner supplies the URL, the config change is five lines (see the tool README).
- **K-AI** is watched (home page, and its news index as an optional page) although it is not in the brief, because it is the only
  vendor found that claims contradiction detection. **FreshPage** and **evergreen.team** are in `sources.json` but off.
- **The Atlassian sources** are the "Atlassian Cloud changes" blog index and Atlassian's Rovo-for-Confluence guide. Atlassian pages
  are scanned for sentences with "Documentation Agent", or "Rovo" next to "outdated", "stale", "duplicate", "contradict" and similar.
  Their URLs are search-reported; the blog *index* URL is a guess.

## What was verified, and what was not

| Claim | Status |
|---|---|
| 170 unit tests pass on Python 3.10, 3.11 and 3.12 (config, fetch, extract, snapshot, diff, render, CLI) | **VERIFIED**, run here |
| The real `urllib` transport follows redirects, retries 5xx and 429, times out, reports a refused connection, honours `robots.txt` (a disallowed path is never requested), caps size, refuses non-text, decodes charsets | **VERIFIED** against a throwaway HTTP server on localhost (`test_transport_local.py`) |
| Run for real against the six enabled sources from this sandbox: every source fails loudly with the reason (`robots.txt unreachable (URLError: Tunnel connection failed: 403 Forbidden)`), exit code 2, no snapshot written | **VERIFIED**, run here |
| `actionlint` 1.7.12 finds nothing in `competitor-watch.yml` or `ci-competitor-watch.yml` | **VERIFIED** (`actionlint-py` from PyPI) |
| The extractor reads a real Marketplace listing, a real Atlassian page, a real K-AI page | **NOT VERIFIED**: never seen one. Fixtures are synthetic and labelled so; their structure is a guess |
| Marketplace pages are readable without JavaScript, and `robots.txt` allows them | **NOT VERIFIED** |
| The weekly workflow runs on GitHub (permissions, push to the default branch, issue creation) | **NOT VERIFIED**: workflow files that run on a schedule only run from the default branch, so it can run only after the merge. `actions/upload-artifact@v4` is pinned from memory |

## Baseline: not taken, the one command

Spike S4's second instruction was *take the baseline snapshot now and commit it*. It **cannot be done from this environment**, and no
fixture or search summary stands in for it. On any machine with ordinary internet access:

```
python tools/competitor-watch/watch.py run --raw-dir /tmp/competitor-raw
git add docs/competitors/snapshots && git commit -m "competitor-watch: baseline"
```

Or, after the merge, *Actions → competitor-watch → Run workflow*: the workflow commits the baseline itself. Nothing in this session
triggered it: making GitHub's runners fetch what this sandbox's policy refuses would be going around that policy, and the owner can do
it with one click.

### What to check on the first real run

1. **The Health table in `latest.md`.** `failed` or `partial` means the extractor's guesses about a layout were wrong, or the site
   refuses the tool. Open `/tmp/competitor-raw/<source>__0.html`: an empty page means a JavaScript shell (the tool cannot read it:
   save the rendered page from a browser as `<source>__0.html` and use `--from-dir`), a short page with "verify you are human" is a
   bot wall, and `robots.txt` blocks are reported by name.
2. **The three numbers that matter.** `contradiction` and `change_time` word counts for AI Hygiene Inspector, Better Content
   Archiving and K-AI, and whether the snippets are claims or noise ("merge conflict").
3. **Evergreen.** Does the Marketplace search show a listing? If the search page is a JavaScript shell the source is `failed` and
   the owner has to supply the name or URL.
4. **Facts.** Do installs, rating, reviews, price and version come out, and from which layer (`json:` is reliable, `text:` is a
   heuristic)? Fix the extractor against the saved pages and commit them as fixtures, replacing the synthetic ones.
5. **The URLs I guessed**: the Atlassian blog index, the pricing tab URLs, K-AI's `/en/news/`.

## One paragraph per competitor: do they now claim contradiction detection?

All of this is **ASSUMED (search-reported, 2026-10-01)**. None of these pages could be read.

**Evergreen AI for Confluence.** *Unknown, and the name could not be matched to a product.* Three searches
(`"Evergreen AI" Confluence`; `"Evergreen" for Confluence ... outdated`; `Evergreen Confluence app Marketplace stale`) found no
Marketplace listing. They found unrelated products named Evergreen (a consumer financial adviser, a university student-wellbeing
tool, a storage subscription) and two Confluence apps that use "evergreen" as a feature word: FreshPage, which tags pages as
*evergreen* content that is never flagged stale, and Better Content Archiving, which can exempt *evergreen* pages from lifecycle
rules. `evergreen.team` appeared in the results and nothing is known about it. The name in the brief may be inexact, a renamed or
removed listing, or a product that does not list on the Marketplace. **The owner should supply the exact name or URL.** Until then
GATE-S4's kill clause has no subject.

**AI Hygiene Inspector** (Lumito lab, [listing](https://marketplace.atlassian.com/apps/512832479/ai-hygiene-inspector-manage-readiness-for-confluence)).
*Possibly, unverified.* The listing is reported to describe a Forge app that scores pages 0 to 100 % for freshness, clarity and
context, finds stubs, outdated pages and orphaned pages, shows an admin dashboard of "AI readiness", and bulk-labels pages
`rovo-ignore` or notifies owners; version 4.2.0, 2026-03-16, scanning up to 50 spaces at once. One search summary said it addresses
"contradictions, duplicates, and outdated content"; the listing text that same summary quoted does not contain the word, so it may be
the summariser's gloss. It is also described as an audit-and-remediate tool, not a change-time one. The baseline's keyword count on
this listing settles it.

**Better Content Archiving and Analytics for Confluence** (Midori Global, [listing](https://marketplace.atlassian.com/apps/123/better-content-archiving-and-analytics-for-confluence)).
*No claim found.* Content lifecycle management: autonomous page statuses, owner notifications, automatic archiving, dashboards and
policy-driven retention across spaces. Its pages are reported to position it as the lifecycle and audit trail around AI-driven
cleanup, and a search aimed at "contradictions" returned nothing about them. Pages are expired after a period without updates (100
days is the example reported). Lifecycle, not content disagreement.

**Atlassian Rovo (Documentation Agent and content-quality features).** *Staleness yes, contradiction reportedly no.* Secondary
sources describe the Documentation Agent as reviewing existing Confluence pages for staleness, proposing updates, and rewriting
outdated content with approval; no Atlassian release note or page was readable, so even that is unconfirmed. A review (Slite) could
not establish that Rovo treats a recently updated page as more authoritative when it conflicts with an older one, and community
threads complain that Rovo answers from old pages. That is the opening, and it is exactly the kind of thing Atlassian can close in
one release: the weekly watcher scans Atlassian's changes blog and Rovo guide for it.

**K-AI** (outside the brief, [k-ai.ai](https://www.k-ai.ai/en/)). ***Claims it, in so many words.*** Its pages are reported to say it
"continuously detects contradictions, duplicates, obsolescence, and missing subjects", that it integrates with Confluence among other
repositories, "detecting conflicts in real-time", and to cite a client where it found 1,300+ anomalies; its news pages include *"Your
tools catch contradictions inside a package. Nobody counts the ones that cross packages"* and *"When One Document Contradiction
Becomes a Serial Defect"*. It presents itself as a Document Knowledge Platform that cleans a repository upstream of AI tools, not as a
Marketplace app, and nothing read says whether its Confluence integration checks a page *when it is edited*. Claim 1 of the
differentiation thesis (contradiction, not staleness) is already taken by it, at least in marketing; claim 2 (at change time) and claim
3 (inside Atlassian's trust boundary) are not established either way.

**FreshPage** (lead, off by default, [listing](https://marketplace.atlassian.com/apps/1059183334/freshpage-trusted-knowledge-for-confluence)).
*No claim found.* Trust banners, one-click verification, ownership, review policies and an *evergreen* tag; reported $13.97 a month for
11 or more users, free up to 10. Freshness and trust, not contradiction.

## GATE-S4: where the kill clause stands

See [`docs/competitors/differentiation-thesis.md`](../competitors/differentiation-thesis.md). In short: **not fired as far as anything
readable goes, and not evaluable**: Evergreen is not located, no competitor page could be fetched, "change-time prevention" is not
defined in any document in the repository, and the decision point is not recorded (the v3 addendum is missing). The suggested
widening (any competitor or Atlassian, not only Evergreen) is the owner's call.

## What this spike does not prove

- **Anything about what a competitor actually says.** Every competitor statement above is a search provider's summary of a page that
  could not be opened. The synthesis step can invent words, as the AI Hygiene Inspector summary may have.
- **That the extractor works on a real page.** It has run on synthetic fixtures and a local server only.
- **That the Action works on GitHub.** It cannot run before the merge.
- **That a keyword hit is a claim.** "Conflict" appears in "merge conflict"; "prevent" appears in every brochure.
- **Anything behind a login, in a screenshot, or in a video.** A competitor could demonstrate contradiction detection in a demo
  video and never write the word.
- **Completeness.** Three searches did not find Evergreen; a fourth might.

## Confirm locally

| # | URL or action | What it must say |
|---|---|---|
| 1 | **Run** the baseline command above | the Health table (which sources read), the thesis table, the snippets |
| 2 | https://marketplace.atlassian.com/apps/512832479/ai-hygiene-inspector-manage-readiness-for-confluence | does the listing itself say "contradiction"? installs, rating, price, last updated |
| 3 | https://marketplace.atlassian.com/apps/123/better-content-archiving-and-analytics-for-confluence | same; and whether anything has been added about AI or contradictions |
| 4 | https://marketplace.atlassian.com/search?hosting=cloud&product=confluence&query=Evergreen | is there a listing named Evergreen; if not, ask the owner for the exact name or URL |
| 5 | https://www.k-ai.ai/en/ and https://www.k-ai.ai/en/news/scope-of-document-contradiction-detection/ | the exact words; whether the Confluence integration works on edit, or only on a scan |
| 6 | https://confluence.atlassian.com/cloud/blog (the weekly "Atlassian Cloud changes") | does the index exist at that URL; any "Documentation Agent" or Rovo content-quality entry |
| 7 | https://marketplace.atlassian.com/robots.txt | does it allow `/apps/` and `/search` for a polite bot? If not, the tool reports it and `--from-dir` is the way |
| 8 | **Ask the owner** | the exact name or URL of "Evergreen AI for Confluence"; the decision point's date; a definition of "change-time prevention" |

## Verdict

Decision: PROCEED-WITH-CONSTRAINT

Constraint: take the baseline (one command) and identify Evergreen before the next decision, and read the AI Hygiene Inspector and K-AI snippets yourself; until then do not describe the product as the only contradiction-focused tool.

GATE-S4: the kill clause has not fired as far as anything readable goes, but it cannot be evaluated: Evergreen AI for Confluence could not be located by three searches, no competitor page could be fetched from this sandbox, "change-time prevention" is undefined and the decision point is unrecorded; the watcher is built, tested and linted and the baseline is one command away, and a vendor outside the brief (K-AI) is reported to claim contradiction detection with a Confluence integration, so the thesis needs re-checking against it first.

Criteria evaluated:
- The tool snapshots Marketplace listings and Atlassian pages to JSON and markdown, capturing features, price, installs, last updated, reviews and rating, and the three keywords — PASS — 170 tests on synthetic fixtures; the real transport against a local server; never run against a real page
- It fails loudly per source and never overwrites good data with a failure — PASS — every failure class is tested; the real run from this sandbox failed all six sources with reasons and exit code 2 and wrote nothing
- A weekly GitHub Action diffs against the last snapshot, commits it and opens an issue on change — PASS — written, `actionlint` clean, and the logic it calls (diff, thresholds, outputs, report) is tested end to end; it has not run on GitHub
- The weekly workflow has run once on GitHub — FAIL — scheduled and dispatchable workflows run only from the default branch, so only after the merge
- The baseline snapshot is taken and committed — FAIL — the egress proxy refuses every watched host (`EGRESS_BLOCKED`); one documented command, or one workflow dispatch after the merge
- The extractor works on real Marketplace, Atlassian and vendor pages — FAIL — it has never seen one; the first real run is the test
- Each competitor has a paragraph on whether it claims contradiction detection — PASS — six paragraphs; every statement in them is ASSUMED (search-reported)
- No competitor claims contradiction detection — FAIL — K-AI is reported to, in so many words, with a Confluence integration; AI Hygiene Inspector possibly
- The kill clause can be evaluated — FAIL — Evergreen is not located, "change-time prevention" is undefined and the decision point is unrecorded

Unverified assumptions carried forward: everything any competitor or Atlassian page is said to contain (all search-reported, and a summary can invent words); that Marketplace listings are readable without JavaScript and allowed by `robots.txt`; the extractor's layout guesses (JSON-LD, `__NEXT_DATA__`, the text patterns); the Atlassian blog index, pricing-tab and K-AI news URLs; that the workflow's permissions, push and issue creation work and that `actions/upload-artifact@v4` resolves; that a changed install count of 5 % is worth an issue; that "Evergreen" is a product with a listing at all.

What would flip this verdict: (1) a baseline in which any competitor's own page claims contradiction detection and also uses change-time words (the thesis table's `REVIEW NOW`), which fires the kill clause in spirit and re-opens the thesis in writing, and probably turns this to KILL unless the Phase V interviews show administrators still want ours; (2) Evergreen found and shown to be staleness-only, which strengthens the thesis and lets the clause be evaluated; (3) the Marketplace refusing a polite bot (`robots.txt`) or serving only JavaScript, which turns the weekly watch into a manual quarterly one with `--from-dir`.
