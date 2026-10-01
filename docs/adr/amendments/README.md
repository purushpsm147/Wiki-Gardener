# Amendments A1–A11 (v3 addendum)

The v3 addendum patches the v2 plan for the **proceed case** with amendments A1–A11, each correcting a flaw conceded during
adversarial review. The addendum (`docs/source/conflict-radar-v3-addendum.md`) is **not yet in the repo**
([`../../source/README.md`](../../source/README.md)), so these records are built only from the seven topics the project owner
recalled in the ADR-history follow-up (2026-10-01), who asked for them to be verified against the file.

> **PENDING SOURCE.** If any of these does not match the addendum, **the addendum wins.**

## Numbering

| File | Topic | Number status |
|---|---|---|
| [A01](A01.md) | Containment joins instead of symmetric Jaccard | **Provisional** (list order) |
| [A02](A02.md) | Cohesion-constrained clustering | **Provisional** (list order) |
| [A03](A03.md) | Near-duplicate divergence detector | **Confirmed.** The owner's summary calls it "A3" |
| [A04](A04.md) | Funnel anchor correction | **Provisional** (list order) |
| [A05](A05.md) | Canonicality demotion and recall honesty | **Provisional** (list order; may be two amendments in the source) |
| [A06](A06.md) | Stored ACLs are not an authorization layer | **Provisional** (list order) |
| [A07](A07.md) | Forge Remote token lifetime: chunked, checkpointed worker | **Provisional** (list order) |
| A08–A11 | Not recalled in the owner's summary | **Unknown. Do not guess.** |

A01 and A02 sit before A03 in the owner's list, which is *consistent* with A3 being third, but that is circumstantial. From
A04 onward, the order carries no confirmation at all. Every file says so in its header.

## Record shape

Each file has: what v2 said; the conceded flaw; what the amendment changes; the ADRs it touches. Where the owner's summary does
not state one of those, the file says `TODO: expand from source` instead of inferring. Anything inferred is labelled
*(inferred)*.

## Which ADRs are touched

Only inferences from the topics, pending source: ADR-002 and ADR-008 (A01–A04), ADR-003 (A05), ADR-004, ADR-006, ADR-007 and
ADR-013 (A06, A07).
