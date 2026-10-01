# Phase V — concierge conflict audit (manual, one-off, paid)

A paid, human-in-the-loop audit that delivers the *value* of Conflict Radar once, so Phase V does not depend on product code.
It is scoped to **what the Spike 3 logic plus a human can produce**, and it deliberately promises less than the product would.

> Status: **spec only.** Nothing here has been run on a customer. Pricing is out of scope for Phase −1: **do not quote from this
> file.** Contract, data-processing terms and retention period are `TODO: owner to decide before the first audit`; none is
> drafted here.

## 1. What the customer gets

A **Conflict Audit Report** with:

1. **Summary:** pages scanned, approved sources used, conflicts flagged, conflicts confirmed by the human reviewer. Precision is
   reported as *confirmed ÷ flagged*.
2. **Conflict table.** One row per confirmed conflict:

   | Field | Content |
   |---|---|
   | ID, severity | severity is assigned by the human reviewer |
   | Page A (target) | title, space, URL, **quote**, **character offsets** into the extracted text |
   | Page B (approved source) | title, space, URL, **quote**, **character offsets** |
   | Divergence | what differs, e.g. `90 days ≠ 30 days`, or a polarity flip |
   | Rule that fired | which detector rule produced it |
   | Reviewer verdict and note | confirmed / not a conflict / unclear, and why |
   | Suggested owner | page owner as shown in Confluence metadata |

3. **Method and limits** (see §5): what the audit can and cannot find. **We claim precision, not recall** (amendment
   [A05](../adr/amendments/A05.md), provisional number).
4. **Appendix:** the approved-source list, scanned scope, excluded pages, and the false positives the reviewer rejected.
5. A **readout call** (about 45 minutes) to walk through the confirmed conflicts.

The audit is **read-only**. It proposes nothing to be written to Confluence ([ADR-004](../adr/ADR-004-suggest-only-writes.md)).

## 2. What the customer provides

- **Approved sources:** the policy / standard pages other content must agree with, chosen together. Expect a handful to a few
  dozen. *(The audit is only as good as this list.)*
- **Scope:** space keys or a label filter for the pages to check.
- **Access:** the lowest-privilege route the customer's security team accepts, in this order of preference:
  1. an **export** (HTML or XML) of the scoped spaces, produced by the customer's admin;
  2. a **read-only API token** limited to the scoped spaces.

  Which route is realistic is exactly the "access reality" question in the
  [interview script](interview-script.md) §5.
- A named **contact** to confirm findings and name page owners.

## 3. Method

1. **Extract** page text from the export, read-only, normalising to the same plain text the Spike 3 core uses, so character
   offsets mean the same thing in the report and in the code.
2. **Run the Spike 3 core in audit mode.** There is no edit, so *every sentence of each target page counts as a changed span*, and
   each is aligned against the approved sources exactly as in the change-time demo (no similarity ceiling; near-identical
   pairs are kept). The core is LLM-free.
3. **Human triage of every flagged pair**, two quotes side by side, confirm or reject. The human replaces the verdict stage, so
   **no customer content goes to any third-party LLM** unless the customer agrees in writing.
4. **Compose** the report and **read it out.**

### What this depends on in Spike 3 (commitments, checked when Spike 3 landed)

- the detector exists as **pure functions with no Forge imports**, runnable in plain Node;
- an **audit mode** that treats every sentence of a page as a changed span;
- an **offline runner** that scans a directory of exported pages and writes the conflict list as JSON with quotes and offsets.

The runner is a throwaway analysis aid, not a product component.

## 4. Operator checklist

- [ ] Agree approved sources, scope and access route in writing. Record the customer's retention expectation.
- [ ] Take the export. Hash it and log the file list, so the scan is reproducible.
- [ ] Run the scan. Keep the raw output.
- [ ] Review **every** flagged pair. Re-review a random 20 % of the rejected ones the next day *(suggestion; adjust after the first
      audit)*.
- [ ] Record per flagged pair how long review took, so the effort model is calibrated from data, not guessed.
- [ ] Deliver the report, run the readout, then **delete** the customer data per the agreed retention.

## 5. Limits the report must state

- **Precision, not recall.** A clean result does *not* mean the site has no contradictions.
- The detector finds only what it can express as a **slot mismatch** between aligned sentences: numbers with units, polarity
  flips, and a short list of antonym pairs. It will **systematically miss** paraphrased, multi-sentence and implicit
  contradictions. *(ASSUMED from the design; the audit's own false-negative checks are not possible without ground truth.)*
- Audit mode has no edit signal, so it faces many more candidate pairs than the change-time case. **Precision is expected to be
  lower than in the demo.** *(ASSUMED; the first audits are how it gets measured.)*
- Findings depend on the approved-source list. Wrong or stale sources yield wrong conflicts.
- Content visible only to some users was scanned with the export's permissions. The report is for the people the customer names,
  not for general distribution (see [A06](../adr/amendments/A06.md)).

## 6. What the audit is not

Not staleness or archiving, not canonicality, not continuous monitoring, not an automated fix, and not a product demo of the
Marketplace app.

## 7. Evidence the audit produces for Phase V

Flagged vs confirmed counts, review minutes per pair, the customer's reaction to the readout, and whether they ask for it to run
continuously. These feed [`kill-proceed-criteria.md`](kill-proceed-criteria.md) (PV.3, pending source). This file does not interpret
them.
