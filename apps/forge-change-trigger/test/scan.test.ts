import assert from "node:assert/strict";
import { copyFileSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, it } from "node:test";
import { parseArgs, scanDirectory } from "../scripts/scan-files";
import { dataset, FIXTURES, pageDef } from "./helpers";

function exportDir(): string {
  const dir = mkdtempSync(join(tmpdir(), "scan-"));
  const finals: Record<string, string> = {
    "policy-data-retention": "v1", "policy-access-control": "v1", "policy-incident-response": "v1",
    "runbook-log-rotation": "v2", "runbook-prod-access": "v2", "runbook-sev1-oncall": "v2",
    "faq-onboarding": "v1", "arch-overview": "v1", "kb-log-retention-summary": "v1", "environment-matrix": "v1",
  };
  for (const [key, version] of Object.entries(finals)) copyFileSync(join(FIXTURES, "pages", pageDef(key).versions[version]!), join(dir, `${key}.html`));
  writeFileSync(join(dir, "notes.md"), "ignored: not html or txt");
  return dir;
}

describe("scan-files (offline audit mode, used by the concierge audit)", () => {
  const approved = dataset.pages.filter((p) => p.role === "approved").map((p) => `${p.key}.html`);

  it("scans an exported directory and finds exactly the three planted conflicts", () => {
    const results = scanDirectory(exportDir(), approved);
    assert.equal(results.length, 7);
    const flagged = results.filter((r) => r.conflicts.length > 0).map((r) => r.page).sort();
    assert.deepEqual(flagged, ["runbook-log-rotation.html", "runbook-prod-access.html", "runbook-sev1-oncall.html"]);
    assert.equal(results.reduce((n, r) => n + r.conflicts.length, 0), 3);
  });

  it("reports quotes and offsets, so a human reviewer can check each one", () => {
    const c = scanDirectory(exportDir(), approved).find((r) => r.page === "runbook-log-rotation.html")!.conflicts[0]!;
    assert.equal(c.changed.quote, "Application logs are retained for 30 days.");
    assert.equal(c.approved.quote, "Application logs must be retained for 90 days.");
    assert.ok(c.approved.end > c.approved.start);
  });

  it("refuses to run when an approved file is missing, instead of silently checking against less", () => {
    assert.throws(() => scanDirectory(exportDir(), [...approved, "missing.html"]), /not found/);
  });

  it("parses its arguments and rejects a missing --approved", () => {
    assert.deepEqual(parseArgs(["dir", "--approved", "a.html, b.html"]), { dir: "dir", approved: ["a.html", "b.html"] });
    assert.throws(() => parseArgs(["dir"]), /usage/);
  });
});
