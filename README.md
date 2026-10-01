# Wiki Gardener / Conflict Radar

**Thesis.** *Conflict Radar* is a tightly scoped, **read-only contradiction-detection** app for Confluence,
distributed on the Atlassian Marketplace and built on Forge. It finds places where Confluence content
disagrees with itself, and, at edit time, where a page was just changed to disagree with an approved source.
It uses a classical-first pipeline (lexical resemblance, containment joins, near-duplicate divergence
detection) and keeps any LLM as a narrow, high-precision verdict stage at the end of the funnel. It is *not* a
broad wiki-hygiene suite: per the project brief that space is occupied (Evergreen AI for Confluence,
AI Hygiene Inspector, Midori's Better Content Archiving) and Atlassian's Rovo Documentation Agent covers
staleness natively. Those competitor claims are **ASSUMED** until Spike 4 re-checks them.

## Current phase: Phase −1 — hostile fact-finding

**No product pipeline code is written until the wedge is validated with real admins** ([ADR-000](docs/adr/ADR-000-phase-minus-1-fact-finding-precedes-invariants.md)).
Phase −1 is four spikes whose job is to try to kill the idea cheaply. Each ends in a written
PROCEED / PROCEED-WITH-CONSTRAINT / KILL verdict ([`docs/spikes/`](docs/spikes/README.md)).

| Spike | Question | Output |
|---|---|---|
| S1 | What does the LLM verdict stage really cost per tenant? | cost model + verdict |
| S2 | Can the classical pipeline run entirely inside Forge? | GATE-S2 verdict (feeds ADR-013) |
| S3 | Does "page edited → conflict surfaced against an approved source, with quotes and offsets" work? | Forge PoC + GATE-S3 verdict |
| S4 | Has a competitor claimed contradiction / change-time detection? | automated competitor watch + GATE-S4 verdict |

**Status (2026-10-01):** all four spikes are written, each **PROCEED-WITH-CONSTRAINT**, in pull requests
[#1](https://github.com/purushpsm147/Wiki-Gardener/pull/1) (S1), [#2](https://github.com/purushpsm147/Wiki-Gardener/pull/2) (S2),
[#3](https://github.com/purushpsm147/Wiki-Gardener/pull/3) (S3) and [#4](https://github.com/purushpsm147/Wiki-Gardener/pull/4) (S4).
Nothing Atlassian-specific is VERIFIED, the live Forge demo and the competitor baseline are documented local steps, and one
competitor-claim finding needs reading first: start with [`docs/PHASE-MINUS-1-SUMMARY.md`](docs/PHASE-MINUS-1-SUMMARY.md).

Start here:

- Decision record: [`docs/adr/`](docs/adr/README.md) (ADR-000 … ADR-013, amendments in `docs/adr/amendments/`)
- Where the project stands: [`docs/PHASE-MINUS-1-SUMMARY.md`](docs/PHASE-MINUS-1-SUMMARY.md)
- What was found on the starting state: [`docs/RECONCILIATION.md`](docs/RECONCILIATION.md)
- Authoritative source documents (**pending, not yet in repo**): [`docs/source/`](docs/source/README.md)
- Phase V hand-off (interviews and a manual paid audit; no code needed): [`docs/phase-v/`](docs/phase-v/)

## Evidence grades

Every non-trivial factual claim in `docs/` carries one of two labels.

- **VERIFIED** — the primary source was read in the environment that produced the claim. The source is cited
  with a URL (or `package@version`) and the UTC date it was fetched.
- **ASSUMED** — everything else. When a web-search summary attributes a claim to a URL that could not be
  fetched, it is written `ASSUMED (search-reported: <url>, <date>)`. That is a lead to confirm, not evidence.

Numbers carry a second qualifier where it matters: **MEASURED** (run here, hardware stated) or **ESTIMATED**
(arithmetic shown).

> The build environment's egress policy blocks `*.atlassian.com`, so Atlassian documentation and Marketplace
> listings could not be fetched directly while writing the Phase −1 docs (see `docs/RECONCILIATION.md`).
> Atlassian facts are therefore `ASSUMED (search-reported)` unless they come from a primary source that *was*
> reachable (for example the contents of an npm package). Each spike lists the exact URLs to confirm locally.

## Layout

```
docs/adr/                 decision record (MADR) + amendments/
docs/spikes/              one document per spike, each ending in a verdict block
docs/competitors/         competitor snapshots (Spike 4)
docs/phase-v/             interview script, concierge audit spec, kill/proceed criteria
docs/source/              authoritative source documents (pending)
apps/forge-change-trigger/  Spike 3 proof of concept (a demo, not the product)
tools/cost-model/         Spike 1
tools/competitor-watch/   Spike 4
tools/check-verdicts/     CI check that every spike ends in a well-formed verdict block
.github/workflows/        CI and the weekly competitor diff
```

## License

AGPL-3.0, see [`LICENSE`](LICENSE).
