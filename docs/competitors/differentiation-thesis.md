# Differentiation thesis: status

**As of 2026-10-01: not confirmed, not refuted.** Written from web-search summaries only. No competitor page could be read: the
sandbox's egress proxy refuses `marketplace.atlassian.com`, `*.atlassian.com`, `k-ai.ai` and `evergreen.team` (VERIFIED, 2026-10-01).
No baseline snapshot exists ([`snapshots/`](snapshots/README.md)). Last human review: 2026-10-01, by the author of this file, from
those summaries. **Read the snapshot's *Differentiation thesis status* table and this file together once a baseline exists.**

## The thesis

From the [README](../../README.md): Conflict Radar is a tightly scoped, **read-only contradiction-detection** app for Confluence on
Forge. It finds content that disagrees with itself and, at edit time, a page that was just changed to disagree with an approved
source. It is **not** a wiki-hygiene suite: that space is reported to be occupied (staleness, archiving, freshness scores) and
Atlassian's Rovo Documentation Agent is reported to cover staleness natively.

The differentiation therefore rests on three claims, each of which a competitor could undercut:

1. **Contradiction, not staleness.** Two pages that disagree, with both quotes, as opposed to a page that is old.
2. **At change time.** A conflict is raised when the edit is made, not at the next scan.
3. **Inside Atlassian's trust boundary and permissions** (Forge, read-only, results shown only to viewers who may read the quoted page).

## Kill clause (GATE-S4)

> *If Evergreen ships change-time prevention before our decision point, the differentiation thesis is re-argued from scratch in writing.*

| Question | Answer today |
|---|---|
| Who is "Evergreen"? | **Not located.** Three web searches (2026-10-01) found no Marketplace listing called *Evergreen AI for Confluence*. Unrelated products with that name came back (a financial adviser, a student-wellbeing tool, a storage subscription). The nearest Confluence matches use "evergreen" as a feature word: FreshPage tags pages as *evergreen* content that never goes stale, and Better Content Archiving can exempt *evergreen* pages. The owner needs to supply the exact name or URL. `evergreen.team` appeared in results; what it is, is unknown. |
| What is "change-time prevention"? | Not defined in any document in the repository (the source documents are missing: [`docs/source/README.md`](../source/README.md)). **Working definition, to be confirmed by the owner:** a competitor's own page says it checks a page against other content *when the page is created, edited or published* (in the editor, on save, before publishing), and flags a disagreement or a problem, rather than finding it in a later scan. |
| What is the decision point? | **Not recorded.** The date lives in the missing v3 addendum. TODO for the owner: put it here. Until it is known the clause cannot be evaluated against a date. |
| Has the clause fired? | No evidence that it has, and none that it has not: Evergreen cannot be evaluated, and no competitor page was readable. |

The watcher counts words, it does not judge. Each competitor gets a row in the generated table with the number of `contradiction`
words and of `change_time` words found on its pages. **REVIEW NOW** means both kinds are present, and a person must read the snippets
and decide. A competitor that cannot be read or located is **UNKNOWN**, never "not seen".

### A suggested widening (the owner decides)

The clause names one competitor that cannot be found. A vendor outside the brief already says it detects contradictions and has a
Confluence integration (below). I would widen the clause to *any competitor, or Atlassian*; the watcher already watches more than
Evergreen, so the table can support either wording.

## What bears on the thesis today (all ASSUMED, search-reported 2026-10-01)

| Who | What the searches reported | Bears on |
|---|---|---|
| **K-AI** ([k-ai.ai](https://www.k-ai.ai/en/)), not in the brief | Its pages are reported to say it *"continuously detects contradictions, duplicates, obsolescence"*, *"detecting conflicts in real-time"*, and to integrate with Confluence; a post titled *"Your tools catch contradictions inside a package. Nobody counts the ones that cross packages"*. A general document-quality platform, not a Marketplace app, as far as the summaries say. | Claim 1 directly. Claim 2 if "real-time" means at edit time inside Confluence, which nothing read says. **The material finding of this spike.** |
| **AI Hygiene Inspector** (Lumito lab) | Scores pages for freshness, clarity and context; finds stubs, outdated and orphaned pages; labels `rovo-ignore` or notifies owners; v4.2.0, 2026-03-16. One search summary said it addresses "contradictions, duplicates and outdated content"; the listing text quoted alongside did not use the word. | Claim 1 if the listing says "contradiction". **Unverified; the first snapshot answers it in one keyword count.** |
| **Better Content Archiving and Analytics** (Midori) | Content lifecycle management: statuses, owner notifications, automatic archiving, dashboards. No contradiction claim in any summary. | Not claim 1 or 2. |
| **FreshPage** (lead, off by default) | Trust banners, verification, review policies, an *evergreen* tag; reported $13.97 a month for 11 or more users, free up to 10. | Staleness only, as far as the summaries say. |
| **Atlassian Rovo, Documentation Agent** | Reported to review pages for staleness, propose updates and rewrite outdated content with approval. A review (Slite) could not establish that Rovo prefers a recently updated page when it conflicts with an older one. | Staleness is covered. Conflict resolution reportedly is not. Atlassian could change that in any release. |

## If the clause fires: the written re-argument

Not an essay for its own sake: five things, each short, each with a source.

1. **What shipped.** Quote, URL, fetch date, and how it was verified (the snapshot commit).
2. **Which claims survive.** For each of the three claims above: still true, narrowed, or gone, and why.
3. **What the evidence from real administrators says.** The Phase V interviews and audit ([`docs/phase-v/`](../phase-v/)): do they
   still want a contradiction tool from us, and is it urgent or would staleness do? Without that, this section is empty and says so.
4. **What the product would have to become, or why it should stop.** Name the narrowest remaining wedge, or recommend a kill.
5. **Decision, date, and the ADRs it touches** ([ADR-000](../adr/ADR-000-phase-minus-1-fact-finding-precedes-invariants.md) onward).
