import assert from "node:assert/strict";
import { readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, it } from "node:test";
import { changedSpans } from "../src/core";
import { dataset, FIXTURES, pageDef, pageText } from "./helpers";

describe("the synthetic dataset (ten pages, three planted contradictions)", () => {
  it("has ten pages: three approved sources, three procedure pages, four distractors, with unique ids and keys", () => {
    assert.equal(dataset.pages.length, 10);
    assert.deepEqual(["approved", "procedure", "distractor"].map((r) => dataset.pages.filter((p) => p.role === r).length), [3, 3, 4]);
    assert.equal(new Set(dataset.pages.map((p) => p.id)).size, 10);
    assert.equal(new Set(dataset.pages.map((p) => p.key)).size, 10);
  });

  it("references every HTML file once, and has no orphan files", () => {
    const referenced = dataset.pages.flatMap((p) => Object.values(p.versions)).sort();
    const onDisk = readdirSync(join(FIXTURES, "pages")).sort();
    assert.deepEqual(referenced, onDisk);
  });

  it("plants exactly three contradictions, each with real pages and versions", () => {
    assert.equal(dataset.planted.length, 3);
    assert.equal(new Set(dataset.planted.map((p) => p.name)).size, 3);
    for (const p of dataset.planted) {
      assert.ok(pageDef(p.page).versions[p.from] && pageDef(p.page).versions[p.to], p.name);
      assert.equal(pageDef(p.approved).role, "approved", p.name);
      assert.equal(pageDef(p.page).role, "procedure", p.name);
    }
    assert.equal(dataset.planted.filter((p) => p.gate === "GATE-S3").length, 1);
  });

  it("the GATE-S3 scenario is exactly '90 days' becoming '30 days' on a procedure page, and nothing else changes", () => {
    const g = dataset.planted.find((p) => p.gate === "GATE-S3")!;
    const before = pageText(g.page, g.from).text;
    const after = pageText(g.page, g.to).text;
    assert.ok(before.includes("Application logs are retained for 90 days."));
    assert.ok(after.includes("Application logs are retained for 30 days."));
    assert.equal(after.replace("30 days", "90 days"), before);
    assert.equal(changedSpans(before, after).length, 1);
  });

  it("every control references real pages and versions, and includes the near-identical, equivalent-unit and scope decoys", () => {
    for (const c of dataset.controls) assert.ok(pageDef(c.page).versions[c.from] && pageDef(c.page).versions[c.to], c.name);
    const names = dataset.controls.map((c) => c.name);
    for (const needle of ["retention-repair-30-to-90", "retention-90-days-to-3-months", "kb-intro-only", "environment-wording-only", "faq-unrelated-number"]) {
      assert.ok(names.includes(needle), needle);
    }
  });

  it("the approved sources are never edited in the scenarios", () => {
    const approvedKeys = new Set(dataset.pages.filter((p) => p.role === "approved").map((p) => p.key));
    for (const s of [...dataset.planted, ...dataset.controls]) assert.ok(!approvedKeys.has(s.page), s.name);
  });
});
