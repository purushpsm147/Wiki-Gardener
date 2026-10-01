# Source documents — PENDING

Two documents are the authoritative source for the decision record. **Neither is in this repo yet.**
Nothing under `docs/adr/`, `docs/phase-v/` or the spike docs may be treated as a reproduction of them.
They were not paraphrased from memory.

| File (to be added here) | Role | Status |
|---|---|---|
| `wiki-gardener-prompt-set.md` | **v2.** 16-prompt, 9-phase build plan for a Copilot-implements / Claude-reviews loop. **Post-validation reference only.** Demoted because it carried an unverified assumption as an invariant (Forge LLMs billing to the customer's Rovo credits). | **Pending: not in repo** |
| `conflict-radar-v3-addendum.md` | **The active plan.** Narrows the product to Conflict Radar; defines Phase −1 spikes S1–S4 and their gates; Phase V paid validation (PV.3 criteria); ADR-013 as an open fork with an explicit decision rule; amendments A1–A11; scope ledger; timeline. | **Pending: not in repo** |

Where the files and the project owner's chat summary differ, the files win. The summary text that
the ADRs were seeded from is the owner's message of 2026-10-01 (the "ADR history" follow-up).

## What is blocked until the files arrive

- ADR-013 **decision rule** (apply verbatim; never improvise).
- Full text, context and consequences for ADR-001 … ADR-013 (bodies are `TODO: expand from source`).
- Amendment numbering and text, A1–A11 (`docs/adr/amendments/`). Only A3 is numbered in the owner's summary.
- PV.3 kill/proceed criteria, including the competitive forcing amendment (`docs/phase-v/kill-proceed-criteria.md`).
- GATE-S2/S3/S4 exact wording and the **decision-point date** that GATE-S4's kill clause refers to.
- The list of places where the source contradicts the owner's brief.

## How to add them

```
cp <wherever>/wiki-gardener-prompt-set.md   docs/source/
cp <wherever>/conflict-radar-v3-addendum.md docs/source/
grep -rn "TODO: expand from source\|PENDING SOURCE" docs/   # the work list
```

Then replace this README's status column, and re-run the reconciliation pass described at the end of
[`../RECONCILIATION.md`](../RECONCILIATION.md).
