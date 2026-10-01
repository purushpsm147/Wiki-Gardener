# Reconciliation — repo state at the start of the ADR-history follow-up

Read on **2026-10-01 ~11:55 UTC**. Repo `purushpsm147/Wiki-Gardener`; session branch
`claude/inspiring-ritchie-ck3uk6` at `1aecfe6`, identical to `origin/main` at `1aecfe6`.
Evidence: `git ls-tree -r origin/main`, `git branch -a -vv`, and the GitHub PR list (0 PRs, open or closed).

This is a snapshot of the starting state. It is not updated as work lands; the end state is in
[`PHASE-MINUS-1-SUMMARY.md`](PHASE-MINUS-1-SUMMARY.md).

## 1. What exists

`LICENSE` (AGPL-3.0). That is the only tracked file. VERIFIED (tree listing above).

The first Phase −1 session was interrupted during reconnaissance, before any file was written. There is
nothing built, committed, or pushed from it.

## 2. Spike status

| Spike | Gate | Status | Verdict |
|---|---|---|---|
| S1 — Forge LLM cost model | — | **Not started** | none |
| S2 — Forge-only compute feasibility | GATE-S2 | **Not started** | none |
| S3 — Change-time trigger PoC | GATE-S3 | **Not started** | none |
| S4 — Competitor watch | GATE-S4 | **Not started** | none |

"Complete: 0 · Partial: 0 · Not started: 4." Because nothing was completed, no spike needs to be redone.
The spikes are built once, directly against the follow-up's gate definitions.

Recon findings from the interrupted session. Neither was committed, and they are re-stated here only so
they are not lost:

- **Egress block (new, affects the "verify live" rule).** The sandbox egress policy returns HTTP 403 to
  `CONNECT` for `developer.atlassian.com`, `marketplace.atlassian.com`, `confluence.atlassian.com`,
  `support.atlassian.com`, `community.atlassian.com`, `www.atlassian.com` and `dac-static.atlassian.com`
  (VERIFIED: `curl -v` output and the proxy's `recentRelayFailures`, 2026-10-01). `WebFetch` is blocked
  by the same policy. `registry.npmjs.org`, `pypi.org` and `api.github.com` are reachable. Consequence:
  no Atlassian page can be fetched directly from this environment. See §5.
- **One `WebSearch` pass on Forge LLM pricing** returned per-token prices and a billing-party statement.
  This is `SEARCH-REPORTED`: a search provider's summary of a page, not the page itself. It is graded as
  such in the S1 write-up and is not treated as VERIFIED.

## 3. ADR files

None exist. There is no `docs/adr/` directory, so no ADR-000 and none of the ADR-010/011/012 stubs the
original bootstrap prompt called for. Nothing carries a status.

## 4. Things I built or planned that the new material contradicts

Nothing in the repo is contradicted, because nothing was built. These are *plan-level* items that the
follow-up supersedes (listed per the instruction to list, not fix):

1. **ADR-012's identity.** I had planned to title the original brief's unspecified ADR-012 as "compute
   placement (Forge-only vs Containers vs Fargate)", flagged as an assumption. The follow-up says ADR-012 is
   the **connector expansion contract**; compute placement is **ADR-013** (Open). My guess was wrong. Not
   written anywhere.
2. **"Seed ADR-000 plus three stubs."** Superseded by seeding ADR-000 through ADR-013 (Step 2).
3. **Forge-first framing.** The original brief says "Fargate only if Forge-only compute proves
   infeasible", which treats Forge-only as the default. The ADR record treats it as an **open fork**
   (ADR-007 "originally expected: remote", now superseded pending ADR-013; ADR-006's Postgres layer is
   contingent on the outcome). S2 and S1 are therefore written as *inputs to ADR-013*, not as a
   confirmation of a Forge-first design.
4. **S2's verdict form.** I had planned the generic PROCEED/KILL block only. The follow-up requires the
   GATE-S2 sentence form ("Forge-only supports up to N pages with architecture X" / "impossible beyond N
   because Y").
5. **S3's detector shape.** I had planned a symmetric TF-IDF page-pair comparison against a fixed set.
   The follow-up requires an A3-shaped detector: compare the *changed spans* of the updated page against an
   *approved sources* set, report quotes and character offsets, never drop near-identical pairs. Built that
   way from the start.
6. **PR structure.** The first brief asked for one PR per spike. The follow-up asks for one PR for the
   ADR/amendment/ADR-013 work. Both are honoured: four spike PRs plus this one. See the PR descriptions.

## 5. Source documents: absent

`docs/source/wiki-gardener-prompt-set.md` and `docs/source/conflict-radar-v3-addendum.md` are **not
present** in this repo, on `origin/main`, on the session branch, or anywhere on the sandbox filesystem
(searched 2026-10-01). Per the instructions, `docs/source/README.md` records them as pending and nothing
has been paraphrased from memory.

Everything that the follow-up says to take *from the files* is therefore blocked, and is marked
`TODO: expand from source` rather than reconstructed:

| Needs the source file | State here |
|---|---|
| Full text and rationale of ADR-001 … ADR-013 | Decision one-liners only (from the follow-up table). Bodies `TODO`. |
| **ADR-013 decision rule** | **Not applied, not improvised.** ADR-013 stays Open. |
| Amendments A1–A11: numbering, titles, text | Only the 7 topics listed in the follow-up. Only **A3** is numbered there. Other numbers are provisional and flagged. A8–A11 (or however many remain) are unknown. |
| GATE-S2 / GATE-S3 / GATE-S4 exact wording | Taken from the follow-up's one-line definitions. |
| **PV.3 kill/proceed criteria** | **Not written.** `docs/phase-v/kill-proceed-criteria.md` is a marked placeholder. |
| Decision-point date (for GATE-S4's "before our decision point") | Unknown. GATE-S4 status is therefore not fully evaluable. |
| "Where the source contradicts my brief" | Cannot be done. Contradictions *between the two briefs* are listed in the summary instead. |

When the two files are added, re-run the pass: replace each `TODO: expand from source`, apply the ADR-013 rule,
renumber the amendments, and finish PV.3.
