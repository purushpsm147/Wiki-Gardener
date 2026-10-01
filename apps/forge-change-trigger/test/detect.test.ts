import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { alignSentences, analyzeEdit, detectConflicts, splitSentences, storageToText } from "../src/core";
import type { Conflict, PageText } from "../src/core";
import { approvedPages, dataset, pageDef, pageText } from "./helpers";

const approved = approvedPages();
const edit = (key: string, from: string, to: string, options = {}) =>
  analyzeEdit({ previous: pageText(key, from), current: pageText(key, to), approved, options });

const page = (id: string, title: string, text: string): PageText => ({ id, title, text });

describe("GATE-S3: an editor changes '90 days' to '30 days' on a procedure page", () => {
  const { conflicts, spans } = edit("runbook-log-rotation", "v1", "v2");
  const changedText = pageText("runbook-log-rotation", "v2").text;
  const policyText = pageText("policy-data-retention", "v1").text;

  it("only the number was edited, so only that span is checked", () => {
    assert.deepEqual(spans, [{ start: 103, end: 105 }]);
    assert.equal(changedText.slice(103, 105), "30");
  });

  it("reports exactly one conflict, against the approved policy page", () => {
    assert.equal(conflicts.length, 1);
    const c = conflicts[0]!;
    assert.equal(c.kind, "numeric");
    assert.equal(c.slot, "duration");
    assert.equal(c.approved.pageId, pageDef("policy-data-retention").id);
    assert.equal(c.changed.pageId, pageDef("runbook-log-rotation").id);
  });

  it("quotes both sentences exactly", () => {
    const c = conflicts[0]!;
    assert.equal(c.changed.quote, "Application logs are retained for 30 days.");
    assert.equal(c.approved.quote, "Application logs must be retained for 90 days.");
    assert.equal(c.changed.value, "30 days");
    assert.equal(c.approved.value, "90 days");
  });

  it("gives character offsets, hard-coded here so that a bug on both sides cannot pass", () => {
    const c = conflicts[0]!;
    assert.deepEqual([c.changed.start, c.changed.end, c.changed.valueStart, c.changed.valueEnd], [69, 111, 103, 110]);
    assert.deepEqual([c.approved.start, c.approved.end, c.approved.valueStart, c.approved.valueEnd], [123, 169, 161, 168]);
  });

  it("and the offsets really index into each page's normalized text", () => {
    const c = conflicts[0]!;
    assert.equal(changedText.slice(c.changed.start, c.changed.end), c.changed.quote);
    assert.equal(changedText.slice(c.changed.valueStart, c.changed.valueEnd), "30 days");
    assert.equal(policyText.slice(c.approved.start, c.approved.end), c.approved.quote);
    assert.equal(policyText.slice(c.approved.valueStart, c.approved.valueEnd), "90 days");
  });

  it("is near-identical to the approved sentence, and that is exactly why it is reported first", () => {
    assert.ok(conflicts[0]!.alignment >= 0.99, `alignment ${conflicts[0]!.alignment}`);
    assert.equal(conflicts[0]!.severity, 0.7);
  });
});

describe("the three planted contradictions", () => {
  for (const p of dataset.planted) {
    it(`detects ${p.name} with the right quotes, values and kind`, () => {
      const { conflicts } = edit(p.page, p.from, p.to);
      assert.equal(conflicts.length, 1, JSON.stringify(conflicts.map((c) => c.explanation)));
      const c = conflicts[0]!;
      assert.equal(c.kind, p.kind);
      assert.equal(c.changed.quote, p.changedQuote);
      assert.equal(c.approved.quote, p.approvedQuote);
      assert.equal(c.changed.value, p.changedValue);
      assert.equal(c.approved.value, p.approvedValue);
      assert.equal(c.approved.pageId, pageDef(p.approved).id);
      const changedText = pageText(p.page, p.to).text;
      const approvedText = pageText(p.approved, "v1").text;
      assert.equal(changedText.slice(c.changed.start, c.changed.end), p.changedQuote);
      assert.equal(approvedText.slice(c.approved.start, c.approved.end), p.approvedQuote);
      assert.equal(changedText.slice(c.changed.valueStart, c.changed.valueEnd), p.changedValue);
      assert.equal(approvedText.slice(c.approved.valueStart, c.approved.valueEnd), p.approvedValue);
    });
  }

  it("polarity: the negation word is located in the edited sentence and the non-negated side has a zero-length anchor", () => {
    const c = edit("runbook-prod-access", "v1", "v2").conflicts[0]!;
    assert.deepEqual([c.changed.start, c.changed.end, c.changed.valueStart, c.changed.valueEnd], [159, 224, 179, 182]);
    assert.deepEqual([c.approved.start, c.approved.end, c.approved.valueStart, c.approved.valueEnd], [73, 128, 92, 92]);
  });

  it("the paraphrased case (different subject wording) is found at a lower alignment, close to the threshold", () => {
    const c = edit("runbook-sev1-oncall", "v1", "v2").conflicts[0]!;
    assert.deepEqual([c.changed.start, c.changed.end, c.changed.valueStart, c.changed.valueEnd], [99, 167, 156, 166]);
    assert.deepEqual([c.approved.start, c.approved.end, c.approved.valueStart, c.approved.valueEnd], [25, 80, 69, 79]);
    assert.ok(c.alignment >= 0.5 && c.alignment < 0.7, `alignment ${c.alignment}`);
  });
});

describe("edits that must NOT be reported", () => {
  for (const c of dataset.controls) {
    it(`${c.name}: ${c.why}`, () => {
      assert.deepEqual(edit(c.page, c.from, c.to).conflicts, []);
    });
  }
});

describe("audit mode: the whole page counts as changed", () => {
  const finals: Record<string, string> = {
    "runbook-log-rotation": "v2",
    "runbook-prod-access": "v2",
    "runbook-sev1-oncall": "v2",
    "faq-onboarding": "v1",
    "arch-overview": "v1",
    "kb-log-retention-summary": "v1",
    "environment-matrix": "v1",
  };
  it("finds exactly the three planted conflicts across the other seven pages, and no false positives", () => {
    const found: Conflict[] = [];
    for (const [key, version] of Object.entries(finals)) {
      found.push(...detectConflicts({ changed: pageText(key, version), changedSpans: "all", approved }));
    }
    assert.equal(found.length, 3, JSON.stringify(found.map((c) => `${c.changed.pageId}: ${c.explanation}`)));
    assert.deepEqual(found.map((c) => c.kind).sort(), ["numeric", "numeric", "polarity"]);
    assert.deepEqual(new Set(found.map((c) => c.approved.pageId)), new Set(dataset.pages.filter((p) => p.role === "approved").map((p) => p.id)));
  });

  it("a page with no previous version is treated as entirely changed", () => {
    const viaEdit = analyzeEdit({ previous: null, current: pageText("runbook-prod-access", "v2"), approved });
    assert.equal(viaEdit.spans, "all");
    assert.equal(viaEdit.conflicts.length, 1);
  });
});

describe("near-identical pairs are never dropped (amendment A3)", () => {
  it("an exact copy of an approved sentence aligns at cosine 1.0: there is no upper cut-off, and it is not a false positive", () => {
    const kb = pageText("kb-log-retention-summary", "v1");
    const pool = approved.flatMap((p) => splitSentences(p.text).map((sentence) => ({ page: p, sentence })));
    const alignments = alignSentences(splitSentences(kb.text), pool);
    const exact = alignments.filter((a) => a.cosine >= 0.999);
    assert.ok(exact.length >= 2, `${exact.length} exact alignments`);
    assert.deepEqual(detectConflicts({ changed: kb, changedSpans: "all", approved }), []);
  });

  it("a copy with exactly one number changed (cosine 1.0) is the single most dangerous case and is reported", () => {
    const policy = page("p", "Policy", "Application logs must be retained for 90 days.");
    const copy = page("c", "Copy", "Application logs must be retained for 60 days.");
    const [c, ...rest] = detectConflicts({ changed: copy, changedSpans: "all", approved: [policy] });
    assert.equal(rest.length, 0);
    assert.ok(c);
    assert.ok(Math.abs(c.alignment - 1) < 1e-9);
    assert.equal(c.changed.value, "60 days");
    assert.equal(c.approved.value, "90 days");
  });

  const policy = page(
    "p",
    "Policy",
    [
      "Application logs must be retained for 90 days.",
      "A VPN connection is required for all production access.",
      "A Sev1 incident must be acknowledged within 15 minutes.",
      "Backups must be encrypted at rest.",
    ].join("\n"),
  );
  const changed = page(
    "c",
    "Changed",
    [
      "Application logs must be retained for 60 days.",
      "A VPN connection is not required for read-only production access.",
      "The on-call engineer must acknowledge a Sev1 page within 30 minutes.",
      "Backups must be unencrypted at rest.",
    ].join("\n"),
  );

  it("truncation keeps the top of the ranking: maxResults = k is always the first k of the full ranking", () => {
    const full = detectConflicts({ changed, changedSpans: "all", approved: [policy] });
    assert.ok(full.length >= 4, `${full.length} conflicts`);
    for (let k = 0; k <= full.length + 1; k++) {
      const cut = detectConflicts({ changed, changedSpans: "all", approved: [policy] }, { maxResults: k });
      assert.deepEqual(cut.map((c) => c.id), full.slice(0, k).map((c) => c.id), `k=${k}`);
    }
  });

  it("the ranking is by severity, and the near-identical pair is among the reported conflicts", () => {
    const full = detectConflicts({ changed, changedSpans: "all", approved: [policy] });
    const severities = full.map((c) => c.severity);
    assert.deepEqual(severities, [...severities].sort((a, b) => b - a));
    assert.ok(full.some((c) => c.alignment >= 0.999 && c.kind === "numeric"));
  });
});

describe("other conflict kinds and directions", () => {
  it("polarity in the other direction: removing a 'not' is found through the deletion gap", () => {
    const policy = page("p", "Policy", "Guest access is not allowed.");
    const r = analyzeEdit({ previous: page("c", "C", "Guest access is not allowed."), current: page("c", "C", "Guest access is allowed."), approved: [policy] });
    assert.equal(r.conflicts.length, 1);
    const c = r.conflicts[0]!;
    assert.equal(c.kind, "polarity");
    assert.equal(c.approved.value, "not");
    assert.equal(c.changed.value, "");
    assert.equal(c.changed.valueStart, c.changed.valueEnd);
  });

  it("antonyms: required against optional", () => {
    const policy = page("p", "Policy", "Multi-factor authentication is required for staff.");
    const c = detectConflicts({ changed: page("c", "C", "Multi-factor authentication is optional for staff."), changedSpans: "all", approved: [policy] });
    assert.equal(c.length, 1);
    assert.equal(c[0]!.kind, "antonym");
    assert.equal(c[0]!.changed.value, "optional");
    assert.equal(c[0]!.approved.value, "required");
  });

  it("tables: a changed row is compared with an approved sentence, and with an approved row", () => {
    const table = (days: number) =>
      `<table><tbody><tr><th><p>Log type</p></th><th><p>Retention</p></th></tr><tr><td><p>Application logs</p></td><td><p>${days} days</p></td></tr>` +
      `<tr><td><p>Audit logs</p></td><td><p>365 days</p></td></tr></tbody></table>`;
    const text = (html: string, id: string): PageText => page(id, id, storageToText(html));
    const sentence = text("<p>Application logs must be retained for 90 days.</p>", "policy");
    const rows = text(table(90), "policy-table");
    for (const approved of [sentence, rows]) {
      const r = analyzeEdit({ previous: text(table(90), "c"), current: text(table(30), "c"), approved: [approved] });
      assert.equal(r.conflicts.length, 1, approved.id);
      const c = r.conflicts[0]!;
      assert.equal(c.changed.quote, "Application logs | 30 days");
      assert.equal(c.changed.value, "30 days");
      assert.equal(storageToText(table(30)).slice(c.changed.start, c.changed.end), c.changed.quote);
    }
  });

  it("antonyms: a lower bound turned into an upper bound", () => {
    const policy = page("p", "Policy", "Passwords must be at least 12 characters long.");
    const c = detectConflicts({ changed: page("c", "C", "Passwords can be at most 12 characters long."), changedSpans: "all", approved: [policy] });
    assert.equal(c.length, 1);
    assert.equal(c[0]!.kind, "antonym");
    assert.equal(c[0]!.slot, "at least / at most");
  });

  it("calendar units: '12 months' agrees with '1 year', but '11 months' does not", () => {
    const policy = page("p", "Policy", "Logs must be retained for 1 year.");
    const run = (text: string) => detectConflicts({ changed: page("c", "C", text), changedSpans: "all", approved: [policy] });
    assert.deepEqual(run("Logs are retained for 12 months."), []);
    assert.equal(run("Logs are retained for 11 months.").length, 1);
  });

  it("an edited sentence that names an environment the approved one does not is flagged at lower severity, with a note", () => {
    const policy = page("p", "Policy", "Logs must be retained for 90 days.");
    const c = detectConflicts({ changed: page("c", "C", "Staging logs are retained for 30 days."), changedSpans: "all", approved: [policy] });
    assert.equal(c.length, 1);
    assert.ok(c[0]!.note?.includes("exception"));
    assert.ok(c[0]!.severity < 0.7 * c[0]!.alignment);
  });

  it("an approved sentence that names an environment the edited one does not is not a conflict", () => {
    const policy = page("p", "Policy", "Staging logs must be retained for 14 days.");
    assert.deepEqual(detectConflicts({ changed: page("c", "C", "Logs are retained for 90 days."), changedSpans: "all", approved: [policy] }), []);
  });
});

describe("rules that exist to prevent false positives (ablations)", () => {
  it("best-match gating: without it, a correct repair is flagged against a sibling sentence", () => {
    const repaired = edit("runbook-log-rotation", "v2", "v3");
    assert.deepEqual(repaired.conflicts, []);
    const noGating = edit("runbook-log-rotation", "v2", "v3", { gating: false });
    assert.ok(noGating.conflicts.length >= 1, "without gating the 365-day audit sentence is a false positive");
    assert.ok(noGating.conflicts.some((c) => c.approved.quote.startsWith("Audit logs")));
  });

  it("scope guard: without it, 'Production ... 90 days' contradicts 'Staging ... 14 days'", () => {
    const policy = page("p", "Policy", "Staging logs must be retained for 14 days.");
    const changed = page("c", "C", "Production logs are retained for 90 days.");
    assert.deepEqual(detectConflicts({ changed, changedSpans: "all", approved: [policy] }), []);
    assert.equal(detectConflicts({ changed, changedSpans: "all", approved: [policy] }, { scopeGuard: false }).length, 1);
  });

  it("the alignment threshold is a recall/precision dial: a stricter one misses the paraphrased planted case", () => {
    assert.equal(edit("runbook-sev1-oncall", "v1", "v2").conflicts.length, 1);
    assert.equal(edit("runbook-sev1-oncall", "v1", "v2", { alignThreshold: 0.7 }).conflicts.length, 0, "recall is lost at 0.7");
  });
});

describe("edge cases", () => {
  it("an edit that changes no words yields no spans and no conflicts", () => {
    const r = analyzeEdit({ previous: pageText("runbook-prod-access", "v2"), current: pageText("runbook-prod-access", "v2"), approved });
    assert.deepEqual(r.spans, []);
    assert.deepEqual(r.conflicts, []);
  });

  it("the edited page is ignored if it is also in the approved set", () => {
    const self = pageText("runbook-prod-access", "v2");
    assert.deepEqual(detectConflicts({ changed: self, changedSpans: "all", approved: [self] }), []);
  });

  it("no approved pages means no conflicts", () => {
    assert.deepEqual(detectConflicts({ changed: pageText("runbook-prod-access", "v2"), changedSpans: "all", approved: [] }), []);
  });

  it("is deterministic: same input, same ids, same order, and ids are unique", () => {
    const a = edit("runbook-log-rotation", "v1", "v2").conflicts.map((c) => c.id);
    const b = edit("runbook-log-rotation", "v1", "v2").conflicts.map((c) => c.id);
    assert.deepEqual(a, b);
    const all = detectConflicts({ changed: pageText("runbook-log-rotation", "v2"), changedSpans: "all", approved }, { gating: false }).map((c) => c.id);
    assert.equal(new Set(all).size, all.length);
  });

  it("very short or empty sentences never align", () => {
    const policy = page("p", "Policy", "Logs must be kept 90 days.");
    assert.deepEqual(detectConflicts({ changed: page("c", "C", "Yes."), changedSpans: "all", approved: [policy] }), []);
    assert.deepEqual(detectConflicts({ changed: page("c", "C", ""), changedSpans: "all", approved: [policy] }), []);
  });
});
