---
status: "accepted"
date: 2026-10-01
decision-makers: project owner
---

# ADR-000 — Phase −1 hostile fact-finding precedes any invariant

## Context and Problem Statement

The v2 plan (`docs/source/wiki-gardener-prompt-set.md`: 16 prompts, 9 phases, written for a
Copilot-implements / Claude-reviews loop) contained an **unverified assumption stated as an invariant**: that Forge LLM
usage bills to the customer's Rovo credits. The plan was demoted to *post-validation reference only* for that reason.

Adversarial review of the v3 direction conceded further flaws (project brief, 2026-10-01):

- assuming Forge LLMs bill to the customer's Rovo credits (they are developer-billed);
- treating Confluence ACLs as an authorization layer for the app's own outputs;
- near-duplicate detection that *drops* the most divergent pair, which is the most dangerous case;
- funnel anchors that anti-select contradictions.

A plan whose invariants include unchecked external facts yields verdicts nobody can trust. Which comes first, the
invariants or the checks?

## Decision Drivers

- The owner works falsification-first: unsupported claims get pushed back on, and recycled context is not evidence.
- Several load-bearing facts are external and move (billing party, compute limits, competitor claims).
- Killing the idea cheaply is a successful outcome, not a failure.

## Considered Options

1. Build the v2 pipeline and validate with admins later.
2. **Phase −1:** hostile fact-finding spikes first, with no product pipeline code until the wedge is validated with
   real admins.

## Decision Outcome

Chosen option: **2**.

- **No product pipeline code** until the wedge is validated with real admins.
- Phase −1 consists of four spikes (S1–S4) whose job is to try to kill the idea cheaply. Each ends in a written verdict
  block: `PROCEED | PROCEED-WITH-CONSTRAINT | KILL`, with criteria marked PASS/FAIL, the unverified assumptions carried
  forward, and what would flip the verdict (format in [`../spikes/README.md`](../spikes/README.md)).
- **Evidence grades.** Every non-trivial factual claim is `VERIFIED` (primary source read here; URL or package@version
  plus UTC fetch date) or `ASSUMED`. A claim resting on a web-search summary of a page that could not be fetched is
  written `ASSUMED (search-reported: <url>, <date>)`: a lead, not evidence. Nothing is simulated when it cannot be
  obtained; it is left as a marked TODO with the exact local step.
- **When docs conflict** with each other or with the brief, the fetched docs win, and the discrepancy is reported.
- **Out of scope for Phase −1:** Notion, SharePoint and any connector other than Confluence; the LightGBM ranker
  (ADR-010); the full similarity pipeline; marketing copy; pricing pages.

### Consequences

- Good: wrong invariants are found before they are built on.
- Good: every spike has a stop condition, so "interesting" cannot substitute for "viable".
- Bad: slower to first user-visible output; the spike PoC (S3) is explicitly a demo, not the product.
- Bad: while the sandbox cannot reach `*.atlassian.com`, most Atlassian facts can only be graded
  `ASSUMED (search-reported)`, and each spike must ship a "confirm locally" table (see
  [`../RECONCILIATION.md`](../RECONCILIATION.md)).

### Confirmation

- `tools/check-verdicts` runs in CI and fails any spike document that does not end in a well-formed verdict block.
- Reviewers can grep a spike for `VERIFIED` and check that each one cites a source and date.

## Provenance

Authored from the project owner's Phase −1 brief and ADR-history follow-up (2026-10-01). The v2 demotion rationale is
as stated in the follow-up; the source file is pending ([`../source/README.md`](../source/README.md)).
