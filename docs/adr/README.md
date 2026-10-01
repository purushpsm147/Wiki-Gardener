# Architecture decision records

MADR-format records for Wiki Gardener / Conflict Radar. ADR-001 … ADR-013 were seeded on 2026-10-01 from the project owner's
summary (decision one-liner and status only). **Bodies marked `TODO: expand from source` are waiting on two source documents
that are not yet in the repo** ([`../source/README.md`](../source/README.md)). Nothing was reconstructed from memory.

Numbers 001–009 were recorded before this repo existed. 010–012 were referenced by the Phase −1 brief. 013 is new.

| ADR | Decision | Status | Note from the owner's summary |
|---|---|---|---|
| [000](ADR-000-phase-minus-1-fact-finding-precedes-invariants.md) | Phase −1 hostile fact-finding precedes any invariant | Accepted | |
| [001](ADR-001-content-hash-and-timestamp-diffing.md) | Content-hash + timestamp diffing for incremental sync; Bloom filter banned | Accepted (pre-validation) | |
| [002](ADR-002-minhash-lsh-lexical-redundancy.md) | MinHash/LSH, lexical, not embeddings, for redundancy | Accepted (pre-validation) | |
| [003](ADR-003-composite-canonicality.md) | Composite canonicality over pure PageRank | Accepted (pre-validation) | Canonicality is out of Conflict Radar scope; retained for the proceed case |
| [004](ADR-004-suggest-only-writes.md) | Suggest-only by default; writes need dry-run, confirm, audit, undo | Accepted | Conflict Radar is read-only, so currently a non-issue; keep for the proceed case |
| [005](ADR-005-verdict-cache-key.md) | Verdict cache keyed by hashes + prompt + provider + model version | Accepted (pre-validation) | |
| [006](ADR-006-single-postgres-rls.md) | Single Postgres, RLS on `tenant_id`; revisit ~200 tenants | Accepted (pre-validation) | **Contingent on ADR-013**: Forge-only removes the Postgres layer |
| [007](ADR-007-forge-ui-remote-batch-hybrid.md) | Forge UI + remote batch backend (hybrid); originally "expected: remote" | **Superseded pending ADR-013** | |
| [008](ADR-008-same-topic-funnel.md) | Same-topic funnel: TF-IDF cosine first; MiniLM only if precision gate fails; LLM never funnels | Accepted (pre-validation) | Amended by A1–A11 where the addendum says so |
| [009](ADR-009-staleness-prior-and-hard-signals.md) | Staleness prior `S = I·(1 − e^(−λt))` modulated by hard signals | **Deferred** | Out of Conflict Radar scope |
| [010](ADR-010-per-tenant-lightgbm-feedback-ranker.md) | Per-tenant LightGBM feedback ranker | Post-validation reference, **do not implement** | "Log features from day one" applies only once there is a product |
| [011](ADR-011-verdictprovider-byo-llm-routing.md) | VerdictProvider abstraction + BYO-LLM routing | Post-validation reference | |
| [012](ADR-012-connector-expansion-contract.md) | Connector expansion contract (`SourceConnector` + capability matrix) | Post-validation reference | Build none until Confluence clears its gate |
| [013](ADR-013-forge-only-vs-remote-compute.md) | **Forge-only vs remote compute** | **Open** | Decision rule is in the v3 addendum (pending); apply, don't improvise |

## Amendments

[`amendments/`](amendments/README.md) holds amendments A1–A11 from the v3 addendum, which patch v2 for the proceed case.
**Only A3 is numbered in the owner's summary.** The other recalled topics carry provisional numbers (list order); A8–A11
are unknown. Renumber from the addendum when it arrives.

## Format

MADR 4 style: YAML front matter (`status`, `date`, `decision-makers`), then Context and Problem Statement, Decision Drivers,
Considered Options, Decision Outcome, Consequences, Confirmation. Sections with no source text say so explicitly rather than
being filled in.
