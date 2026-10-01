# competitor-watch

A weekly, repeatable baseline so nobody re-researches competitors by hand. It fetches a short list of public pages, records what they
say, diffs against the last snapshot, and says so loudly when it cannot read something. Python standard library only; no network is
needed to run the tests.

**Status:** built and tested against synthetic fixtures and a local HTTP server. **Never run against a real Marketplace page**: the
sandbox that wrote it cannot reach `*.atlassian.com`. There is no baseline snapshot yet. The first real run is the real test of the
extractor; [`docs/spikes/04-competitor-watch.md`](../../docs/spikes/04-competitor-watch.md) says what to look for.

## Take the baseline (one command, any machine with normal internet)

```
python tools/competitor-watch/watch.py run --raw-dir /tmp/competitor-raw
git add docs/competitors/snapshots && git commit -m "competitor-watch: baseline"
```

Or, once this is on the default branch: Actions, *competitor-watch*, *Run workflow*. The workflow commits the baseline itself.

Then read `docs/competitors/snapshots/latest.md`. Look first at the **Health** table (a source marked `failed` or `partial` needs a
look; that is the extractor telling you its guesses about a layout were wrong), then the **Differentiation thesis status** table.
`--raw-dir` keeps the pages it fetched; if a source failed, those files (or pages you save by hand) are what to turn into real test
fixtures.

## What it does

```
sources.json ──► fetch (UA, robots.txt, retries, size cap) ──► parse HTML ──► facts + keyword hits + mentions
                                                                   │
                       docs/competitors/snapshots/latest.json ◄────┤  (written only when something real changed)
                       docs/competitors/snapshots/latest.md        │
                       issue body (the diff)  ◄── diff vs last snapshot, with health lines
```

For each source it records, as JSON and as markdown:

- **facts**: installs, downloads, rating, review count, last updated, version, price samples and price text, vendor, name, summary,
  each with *how it was found* (`json:` and `meta:` are reliable, `text:` is a heuristic);
- **features** (list items) and **headings**;
- **keyword hits** with a snippet of context, in two classes: `contradiction` (the owner's three words, `contradict*`, `conflict*`,
  `inconsisten*`, plus `discrepanc*`) and `change_time` (words that suggest checking content as it is written or published);
- **mentions**: sentences on Atlassian pages that contain, for example, "Documentation Agent", or "Rovo" next to "outdated", "stale",
  "duplicate", "contradict" and similar;
- **discovery**: for a source of kind `search`, whether a listing with the expected name appears in the results.

Three layers do the extracting, from most to least reliable: the visible text (keywords and sentences survive any layout change),
structured data the page embeds (JSON-LD, `__NEXT_DATA__`, searched by key name, not position), and regular expressions over the text.
If the structured layers find nothing, the keyword scan and the diff still work.

## Health: it fails loudly

Per source: **ok**, **partial** (something is missing: an optional page failed, no structured fact was found, a search page showed
no readable results) or **failed** (nothing usable: HTTP error, `robots.txt` disallows or is unreachable, the page is an empty
JavaScript shell, looks like a bot wall, or has almost no text). The process exits **2** if any source failed, and the workflow then
opens (or comments on) a `competitor-watch-broken` issue and goes red.

A failed source **keeps its last good facts, marked stale**, so a bad week never reads as "the competitor removed every feature"; when
it recovers it is diffed against that last good data. A first run in which *every* source fails writes **no** snapshot (an empty one
would be mistaken for a baseline).

It respects `robots.txt` (a missing file allows everything, an unreachable or 5xx one means *do not fetch*, as RFC 9309 says),
identifies itself in the User-Agent, retries 429 and 5xx twice with backoff, caps responses at 5 MB, and refuses non-text content.
`--no-robots` exists for a decision you make on purpose.

## What counts as a change

| Severity | What | Rule |
|---|---|---|
| **material** | name, summary, vendor, price changed; features added or removed; a `contradiction` or `change_time` hit appeared or vanished; a mention sentence appeared or vanished; a listing was found for a search; a source was added or removed | always reported |
| **routine** | installs, downloads, reviews | reported past `numeric_change_pct` (default 5 %) |
| **routine** | rating | reported past `rating_change` (default 0.1) |
| **routine** | version, last updated, page title, headings | always reported |

The brief asked for an issue "if anything changed". Install counts drift daily, so literally *anything* would open an issue every
week; the thresholds above are my reading of the intent. `"issue_on": "material"` in `sources.json` quiets the routine ones further.
The snapshot is rewritten only when something other than timestamps and page hashes changed, so the repository does not get a commit a
week of nothing.

## `sources.json`

`kind`: `marketplace-listing` (facts, features, keywords), `page` (keywords and mentions: release notes, a vendor site), `search`
(is there a listing called `expect_text`?). `role`: `competitor` (appears in the thesis table), `atlassian`, `lead` (off by default).
`urls` must all be read; `optional_urls` only warn. `provenance` says why a source is watched and how its URL was found; every entry has
one. `kill_clause_subject: true` marks the competitor that GATE-S4's kill clause names.

To turn the **Evergreen** placeholder into a real listing once its URL is known: change its `kind` to `marketplace-listing`, replace
`urls` with the listing URL, add `require_any_field`, drop `expect_text` and `min_text_chars: 0`, and run `check-config`.

## Commands

```
watch.py run           [--snapshots DIR] [--raw-dir DIR] [--from-dir DIR] [--report FILE] [--github-output FILE]
                       [--only ID ...] [--dry-run] [--no-robots] [--timeout S] [--retries N]
watch.py render        [--snapshots DIR] [--write]     # markdown from an existing latest.json
watch.py check-config
```

`--from-dir DIR` reads pages saved earlier (by `--raw-dir`, or by hand from a browser) as `<source-id>__<n>.html` and touches no
network: the way to use the tool when a site shows the Action a bot wall.

## Tests

```
python -m unittest discover -s tools/competitor-watch/tests -v
```

170 tests, no network. The fixtures in `tests/fixtures/` are **synthetic**: each says so, none is a copy of a real page, and their
structure is a guess. `test_transport_local.py` runs the real `urllib` transport against a throwaway server on localhost (redirects,
retries, timeouts, `robots.txt`, size cap, charsets). `tests/fixtures/expected_snapshot.md` is a golden file for the markdown
(`UPDATE_GOLDEN=1` regenerates it; read the diff).

## Limits

- The extractor has never seen a real listing. Expect the first run to show which of its guesses were wrong.
- It does not run JavaScript. A page drawn client-side is reported as a failure, not guessed at.
- A keyword hit is a word, not a claim. "Conflict" appears in "merge conflict" and "conflict of interest". A person reads the snippets.
- It cannot read what is behind a login, and it should not try.
