import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { baselineVersion, handlePageUpdated, parseEvent, resultKey, STORED_CONFLICT_LIMIT } from "../src/app";
import type { Deps, StoredResult } from "../src/app";
import { getPage } from "../src/confluence";
import { dataset, FakeSite, fixtureSite, pageDef, storageOf } from "./helpers";

const APPROVED = dataset.pages.filter((p) => p.role === "approved").map((p) => p.id);
const T0 = Date.parse("2026-10-01T10:00:03.500Z");

function harness(site: FakeSite, over: Partial<Deps> = {}) {
  const store = new Map<string, unknown>();
  const logs: string[] = [];
  let calls = 0;
  const deps: Deps = {
    getPage: (id, opts) => getPage(site.requester(false), id, opts),
    kvs: {
      set: async (k, v) => void store.set(k, JSON.parse(JSON.stringify(v))),
      get: async <T,>(k: string) => store.get(k) as T | undefined,
    },
    approvedIds: APPROVED,
    // the first call is "started", the second is "detected", 120 ms later
    now: () => new Date(T0 + (calls++ === 0 ? 0 : 120)),
    log: (l) => logs.push(l),
    ...over,
  };
  return { deps, store, logs };
}

const event = (pageId: string, extra: Record<string, unknown> = {}) => ({
  eventType: "avi:confluence:updated:page",
  atlassianId: "u1",
  eventCreatedDate: "2026-10-01T10:00:02.000Z",
  updateTrigger: "edit",
  selfGenerated: false,
  content: { id: pageId, version: { number: 2 } },
  ...extra,
});

describe("GATE-S3 end to end: page updated -> fetched -> compared -> logged and stored", () => {
  const site = fixtureSite();
  const { deps, store, logs } = harness(site);
  let result: StoredResult | null = null;

  it("handles the event for the edited runbook", async () => {
    result = await handlePageUpdated(event(pageDef("runbook-log-rotation").id), deps);
    assert.ok(result);
    assert.equal(result.pageId, "2001");
    assert.equal(result.version, 2);
    assert.equal(result.previousVersion, 1);
  });

  it("stores one conflict with both quotes and character offsets under the page's key", () => {
    const stored = store.get(resultKey("2001")) as StoredResult;
    assert.equal(stored.conflicts.length, 1);
    const c = stored.conflicts[0]!;
    assert.equal(c.changed.quote, "Application logs are retained for 30 days.");
    assert.equal(c.approved.quote, "Application logs must be retained for 90 days.");
    assert.deepEqual([c.changed.start, c.changed.end], [69, 111]);
    assert.deepEqual([c.approved.start, c.approved.end], [123, 169]);
    assert.equal(c.approved.pageId, "1001");
  });

  it("logs the conflict as structured lines, with quotes and offsets", () => {
    const lines = logs.map((l) => JSON.parse(l) as Record<string, any>);
    const summary = lines.find((l) => l.msg === "conflict-radar.result")!;
    assert.equal(summary.conflicts, 1);
    const conflict = lines.find((l) => l.msg === "conflict-radar.conflict")!;
    assert.equal(conflict.edited.quote, "Application logs are retained for 30 days.");
    assert.deepEqual([conflict.approved.start, conflict.approved.end], [123, 169]);
  });

  it("measures its own latency from the edit, so 'within minutes' is a number and not a claim", () => {
    // version 2 was created at 10:00:01.000Z in the fake site; detection is at 10:00:03.620Z
    assert.equal(result!.latency.versionToDetectedMs, 2620);
    assert.equal(result!.latency.eventToDetectedMs, 1620);
    assert.equal(result!.elapsedMs, 120);
    assert.equal(result!.updateTrigger, "edit");
  });

  it("costs exactly 2 + N Confluence reads for N approved pages, all asking for the storage body", () => {
    assert.equal(site.requests.length, 2 + APPROVED.length, site.requests.join("\n"));
    assert.ok(site.requests.every((r) => r.includes("body-format=storage")));
    assert.ok(site.requests.some((r) => r.includes("/pages/2001?") && r.includes("version=1")));
  });
});

describe("handlePageUpdated: other outcomes", () => {
  it("overwrites an earlier result with an empty one when the edit repairs the conflict", async () => {
    const site = fixtureSite({ "runbook-log-rotation": ["v1", "v2", "v3"] });
    const { deps, store } = harness(site);
    store.set(resultKey("2001"), { stale: true });
    const r = await handlePageUpdated(event("2001", { content: { id: "2001", version: { number: 3 } } }), deps);
    assert.deepEqual(r!.conflicts, []);
    assert.deepEqual((store.get(resultKey("2001")) as StoredResult).conflicts, []);
  });

  it("treats a first version as entirely changed (audit semantics)", async () => {
    const site = new FakeSite();
    for (const p of dataset.pages.filter((x) => x.role === "approved")) site.addPage(p.id, p.title, [{ storage: storageOf(p.key, "v1") }]);
    site.addPage("2002", "Runbook: Production Access", [{ storage: storageOf("runbook-prod-access", "v2") }]);
    const { deps } = harness(site);
    const r = await handlePageUpdated(event("2002"), deps);
    assert.equal(r!.spans, "all");
    assert.equal(r!.previousVersion, null);
    assert.equal(r!.conflicts.length, 1);
  });

  it("skips events it cannot read, self-generated events and edits to an approved source, and says why", async () => {
    const site = fixtureSite();
    const a = harness(site);
    assert.equal(await handlePageUpdated({ eventType: "x" }, a.deps), null);
    assert.match(a.logs.join("\n"), /no page id in event/);
    const b = harness(site);
    assert.equal(await handlePageUpdated(event("2001", { selfGenerated: true }), b.deps), null);
    assert.match(b.logs.join("\n"), /self-generated/);
    const c = harness(site);
    assert.equal(await handlePageUpdated(event("1001"), c.deps), null);
    assert.match(c.logs.join("\n"), /approved source/);
    assert.equal(site.requests.length, 0, "no Confluence call is made for skipped events");
  });

  it("skips a page that is not current or does not exist", async () => {
    const site = fixtureSite().setStatus("2001", "trashed");
    const a = harness(site);
    assert.equal(await handlePageUpdated(event("2001"), a.deps), null);
    assert.match(a.logs.join("\n"), /status is trashed/);
    const b = harness(fixtureSite());
    assert.equal(await handlePageUpdated(event("999999"), b.deps), null);
    assert.match(b.logs.join("\n"), /page not found/);
  });

  it("records an approved page it could not read, and carries on with the rest", async () => {
    const site = fixtureSite();
    const { deps } = harness(site, { approvedIds: [...APPROVED, "424242"] });
    const r = await handlePageUpdated(event("2001"), deps);
    assert.deepEqual(r!.approvedMissing, ["424242"]);
    assert.equal(r!.conflicts.length, 1);
  });

  it("does not compare against an approved source that has been trashed, and records it as unavailable", async () => {
    const { deps } = harness(fixtureSite().setStatus("1001", "trashed"));
    const r = await handlePageUpdated(event("2001"), deps);
    assert.deepEqual(r!.approvedMissing, ["1001"]);
    assert.deepEqual(r!.conflicts, []);
  });

  it("fails loudly when Confluence errors, instead of storing a wrong 'no conflicts'", async () => {
    const site = fixtureSite().break("2001");
    const { deps, store } = harness(site);
    await assert.rejects(handlePageUpdated(event("2001"), deps), /HTTP 500/);
    assert.equal(store.size, 0);
  });

  it("logs the raw event in probe mode, so the real payload shape can be checked on first deploy", async () => {
    const { deps, logs } = harness(fixtureSite(), { probe: true });
    await handlePageUpdated(event("2001"), deps);
    assert.match(logs[0]!, /event-probe/);
    assert.match(logs[0]!, /"updateTrigger":"edit"/);
  });

  it("stores at most STORED_CONFLICT_LIMIT conflicts and says when it truncated", async () => {
    const letters = "bdfgklmnprtvz";
    const names: string[] = [];
    for (const a of letters) for (const b of letters) names.push(`${a}a${b}o`);
    const lines = (days: number) => names.slice(0, STORED_CONFLICT_LIMIT + 10).map((n) => `<p>${n} logs must be retained for ${days} days.</p>`).join("");
    const site = new FakeSite().addPage("1", "Policy", [{ storage: lines(90) }]).addPage("2", "Big", [{ storage: lines(90) }, { storage: lines(30) }]);
    const { deps } = harness(site, { approvedIds: ["1"] });
    const r = await handlePageUpdated(event("2"), deps);
    assert.equal(r!.conflicts.length, STORED_CONFLICT_LIMIT);
    assert.equal(r!.conflictsTruncated, true);
  });
});

describe("which earlier version an edit is compared with", () => {
  it("baselineVersion diffs from the oldest of: the version before the latest, before the event's, and the last one checked", () => {
    assert.equal(baselineVersion(1), null, "a first version has nothing before it");
    assert.equal(baselineVersion(2), 1);
    assert.equal(baselineVersion(2, 2), 1, "the ordinary case: one edit, one event");
    assert.equal(baselineVersion(2, 2, 1), 1);
    assert.equal(baselineVersion(4, 3, 2), 2, "versions 3 and 4 arrived before the event for 3 was handled");
    assert.equal(baselineVersion(4, 4), 3);
    assert.equal(baselineVersion(4, 3), 2, "an event handled late still covers its own edit");
    assert.equal(baselineVersion(4, undefined, 1), 1);
    assert.equal(baselineVersion(4, 4, 4), 3, "a last-checked version that is not older than the latest is ignored");
    assert.equal(baselineVersion(4, 9, 9), 3, "nonsense versions are ignored");
    assert.equal(baselineVersion(3, 1), null, "an event naming version 1 means the first version is in play: diff nothing, audit the page");
  });

  // version 2 introduces the conflict, version 3 changes something unrelated
  const burst = () =>
    new FakeSite()
      .addPage("1001", "Data Retention Policy (Approved)", [{ storage: storageOf("policy-data-retention", "v1") }])
      .addPage("2001", "Runbook: Log Rotation", [
        { storage: storageOf("runbook-log-rotation", "v1") },
        { storage: storageOf("runbook-log-rotation", "v2") },
        { storage: storageOf("runbook-log-rotation", "v2").replace("nightly", "weekly") },
      ]);

  it("catches the conflict from version 2 when the event for version 2 is handled after version 3 exists", async () => {
    const { deps } = harness(burst(), { approvedIds: ["1001"] });
    const r = await handlePageUpdated(event("2001", { content: { id: "2001", version: { number: 2 } } }), deps);
    assert.equal(r!.version, 3);
    assert.equal(r!.previousVersion, 1, "the diff spans versions 1 to 3");
    assert.equal(r!.conflicts.length, 1);
  });

  it("catches it from the last checked version too, when the event does not name a version", async () => {
    const { deps, store } = harness(burst(), { approvedIds: ["1001"] });
    store.set(resultKey("2001"), { version: 1, conflicts: [] });
    const r = await handlePageUpdated(event("2001", { content: { id: "2001" } }), deps);
    assert.equal(r!.previousVersion, 1);
    assert.equal(r!.conflicts.length, 1);
  });

  it("with no hint at all it compares only the last two versions, so the earlier edit is not re-checked (the residual gap)", async () => {
    const { deps } = harness(burst(), { approvedIds: ["1001"] });
    const r = await handlePageUpdated(event("2001", { content: { id: "2001" } }), deps);
    assert.equal(r!.previousVersion, 2);
    assert.equal(r!.conflicts.length, 0);
  });
});

describe("parseEvent", () => {
  it("accepts the documented fields and tolerates the unverified shape of `content`", () => {
    assert.deepEqual(parseEvent(event("2001")), {
      pageId: "2001",
      versionNumber: 2,
      eventCreatedDate: "2026-10-01T10:00:02.000Z",
      updateTrigger: "edit",
      selfGenerated: false,
    });
    assert.equal(parseEvent({ page: { id: 77 } }).pageId, "77");
    assert.equal(parseEvent({ pageId: "88" }).pageId, "88");
    assert.deepEqual(parseEvent(null), {});
    assert.deepEqual(parseEvent("nope"), {});
  });
});
