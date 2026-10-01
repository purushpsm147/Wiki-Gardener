import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { handlePageUpdated, resultKey } from "../src/app";
import type { Deps, StoredResult } from "../src/app";
import { canRead, getPage } from "../src/confluence";
import { getPanelData } from "../src/panel";
import { dataset, fixtureSite } from "./helpers";

const APPROVED = dataset.pages.filter((p) => p.role === "approved").map((p) => p.id);

async function storedFor(site = fixtureSite()) {
  const store = new Map<string, unknown>();
  const deps: Deps = {
    getPage: (id, opts) => getPage(site.requester(false), id, opts),
    kvs: { set: async (k, v) => void store.set(k, JSON.parse(JSON.stringify(v))), get: async <T,>(k: string) => store.get(k) as T | undefined },
    approvedIds: APPROVED,
    now: () => new Date("2026-10-01T10:00:04.000Z"),
    log: () => {},
  };
  await handlePageUpdated({ content: { id: "2001" } }, deps);
  return { store, site };
}

describe("panel: stored results are not an authorization layer (amendment A06)", () => {
  it("shows nothing when no check has run", async () => {
    const data = await getPanelData("2001", { kvs: { get: async () => undefined }, viewerCanRead: async () => true });
    assert.deepEqual(data, { state: "none" });
  });

  it("shows the conflict, with quotes, to a viewer who can read the approved page", async () => {
    const { store, site } = await storedFor();
    const data = await getPanelData("2001", { kvs: { get: async <T,>(k: string) => store.get(k) as T | undefined }, viewerCanRead: (id) => canRead(site.requester(true), id) });
    assert.equal(data.state, "ok");
    if (data.state !== "ok") return;
    assert.equal(data.conflicts.length, 1);
    assert.equal(data.hidden, 0);
    assert.equal(data.conflicts[0]!.approved.quote, "Application logs must be retained for 90 days.");
  });

  it("withholds the conflict, and every word of the quote, from a viewer who cannot read the approved page", async () => {
    const { store, site } = await storedFor();
    site.deny("1001");
    const data = await getPanelData("2001", { kvs: { get: async <T,>(k: string) => store.get(k) as T | undefined }, viewerCanRead: (id) => canRead(site.requester(true), id) });
    assert.equal(data.state, "ok");
    if (data.state !== "ok") return;
    assert.equal(data.conflicts.length, 0);
    assert.equal(data.hidden, 1);
    const wire = JSON.stringify(data);
    assert.ok(!wire.includes("must be retained"), "the approved quote must not leave the resolver");
    assert.ok(!wire.includes("Data Retention Policy"), "nor the approved page's title");
    assert.ok(!wire.includes("90 days"));
  });

  it("fails closed when the permission check errors", async () => {
    const { store } = await storedFor();
    const data = await getPanelData("2001", {
      kvs: { get: async <T,>(k: string) => store.get(k) as T | undefined },
      viewerCanRead: async () => {
        throw new Error("Confluence is down");
      },
    });
    assert.equal(data.state === "ok" && data.hidden, 1);
    assert.equal(data.state === "ok" && data.conflicts.length, 0);
  });

  it("re-checks at read time, not once at ingest: revoking access changes the next answer", async () => {
    const { store, site } = await storedFor();
    const deps = { kvs: { get: async <T,>(k: string) => store.get(k) as T | undefined }, viewerCanRead: (id: string) => canRead(site.requester(true), id) };
    const before = await getPanelData("2001", deps);
    site.deny("1001");
    const after = await getPanelData("2001", deps);
    assert.equal(before.state === "ok" && before.conflicts.length, 1);
    assert.equal(after.state === "ok" && after.conflicts.length, 0);
  });

  it("checks each approved page once per request, however many conflicts quote it", async () => {
    const { store } = await storedFor();
    const stored = store.get(resultKey("2001")) as StoredResult;
    stored.conflicts = [stored.conflicts[0]!, { ...stored.conflicts[0]!, id: "other" }, { ...stored.conflicts[0]!, id: "third" }];
    const asked: string[] = [];
    await getPanelData("2001", {
      kvs: { get: async <T,>(k: string) => store.get(k) as T | undefined },
      viewerCanRead: async (id) => {
        asked.push(id);
        return true;
      },
    });
    assert.deepEqual(asked, ["1001"]);
  });

  it("does not mutate the stored record", async () => {
    const { store, site } = await storedFor();
    site.deny("1001");
    const before = JSON.stringify(store.get(resultKey("2001")));
    await getPanelData("2001", { kvs: { get: async <T,>(k: string) => store.get(k) as T | undefined }, viewerCanRead: (id) => canRead(site.requester(true), id) });
    assert.equal(JSON.stringify(store.get(resultKey("2001"))), before);
  });
});
