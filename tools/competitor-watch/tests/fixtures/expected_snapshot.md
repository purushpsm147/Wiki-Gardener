# Competitor snapshot

Taken 2026-10-08T06:00:00Z by competitor-watch 0.1.0. Generated: do not edit; run `python tools/competitor-watch/watch.py render --write`.
A value found in structured data (`json:`, `meta:`) is more reliable than one found by a text pattern (`text:`), which is a heuristic.

## Health

| Source | Status | Notes |
|---|---|---|
| `hygiene` | ok |  |
| `evergreen` | ok |  |
| `kai` | ok |  |
| `flaky` | failed | showing last good data from 2026-10-01T06:00:00Z; this run: https://example.test/flaky: HTTP 503 |
| `atlassian` | ok |  |

## Differentiation thesis status (generated)

GATE-S4 kill clause: *If Evergreen ships change-time prevention before our decision point, the differentiation thesis is re-argued from scratch in writing.*

This table is mechanical: it counts words on the pages that were fetched. It cannot tell a claim from a mention; a person reads the snippets below.
The thesis, the decision point and the written re-argument live in [`docs/competitors/differentiation-thesis.md`](../differentiation-thesis.md) (this file is generated into `docs/competitors/snapshots/`).

| Competitor | Kill-clause subject | Listing located | Contradiction words | Change-time words | Indicator |
|---|---|---|---|---|---|
| Example Hygiene |  | yes | 1 | 0 | contradiction words present: read the snippets |
| Evergreen AI for Confluence | yes | NO | 0 | 0 | UNKNOWN: not located, so the kill clause cannot be evaluated |
| Synthetic Knowledge Platform |  | yes | 3 | 1 | REVIEW NOW: contradiction words and change-time words both present |
| Flaky Source |  | unknown (source failed) | 0 | 0 | UNKNOWN: source failed (last good data shown) |

## Example Hygiene

`hygiene` · marketplace-listing · competitor · status **ok**

Why it is watched: Named in the brief. SYNTHETIC.

- https://example.test/hygiene: HTTP 200

| Fact | Value | How found |
|---|---|---|
| installs | 1234 | `text:installs` |
| last_updated | 2026-03-16 | `json:$.dateModified` |
| name | Example Page Hygiene for Confluence | `json:$.name` |
| price_currency | USD | `json:$.offers.priceCurrency` |
| price_samples | [{"key":"price","value":13.97}] | `json:$.offers.*` |
| rating | 4.5 | `json:$.aggregateRating.ratingValue` |
| review_count | 23 | `json:$.aggregateRating.ratingCount` |
| summary | Scores every page for freshness and flags stale pages for their owners. | `json:$.description` |
| vendor | Example Vendor | `json:$.author` |
| version | 4.2.0 | `json:$.softwareVersion` |

Features (3):
- Scores every page for freshness, clarity and context
- Finds stubs, outdated pages and orphaned pages
- Bulk remediation: label pages or notify their owners

**`contradiction`**: 1 match(es)
- "contradictions": …onfluence \| Atlassian Marketplace Keeps Confluence pages clean and current. Example Page Hygiene for Confluence Detects contradictions in your knowledge base and ready for AI. It scans every space on a schedule and tells page owners which pages need atte…

## Evergreen AI for Confluence

`evergreen` · search · competitor · status **ok**

NOT LOCATED (synthetic note).

- https://example.test/evergreen: HTTP 200

Search: found=False, readable=True

## Synthetic Knowledge Platform

`kai` · page · competitor · status **ok**

- https://example.test/kai: HTTP 200

Features (1):
- Finds duplicates, contradictions and obsolete documents

**`contradiction`**: 3 match(es)
- "contradictions": …Synthetic Knowledge Platform A platform that detects contradictions between documents and detects conflicts in real time, so that teams can trust what their AI tools read. It connects to…
- "contradictions": …t teams can trust what their AI tools read. It connects to Confluence and several other repositories. Finds duplicates, contradictions and obsolete documents…

**`change_time`**: 1 match(es)
- "real time": …Synthetic Knowledge Platform A platform that detects contradictions between documents and detects conflicts in real time, so that teams can trust what their AI tools read. It connects to Confluence and several other repositories. Finds dupl…

## Flaky Source

`flaky` · page · competitor · status **failed** · **stale**

- https://example.test/flaky: HTTP 200

**Failed this run; everything below is from 2026-10-01T06:00:00Z.** https://example.test/flaky: HTTP 503

## Atlassian Release Notes

`atlassian` · page · atlassian · status **ok**

- https://example.test/atlassian: HTTP 200

**`contradiction`**: 1 match(es)
- "conflict": …The Jira timeline view has a new zoom control and keyboard shortcuts for moving between sprints. Bitbucket shows merge conflict markers inline in the pull request diff, which is unrelated to documentation. Confluence tables can now be sorted by se…

**Mentions `documentation-agent`** (1):
- The Rovo Documentation Agent now reviews existing pages for staleness and proposes updates for owners to approve.
