import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { canRead, ConfluenceError, getPage, parsePage } from "../src/confluence";
import type { HttpResponse, Requester } from "../src/confluence";

const res = (status: number, body: unknown = {}): HttpResponse => ({ ok: status >= 200 && status < 300, status, json: async () => body, text: async () => JSON.stringify(body) });
const page = { id: "123", status: "current", title: "T", spaceId: "9", version: { number: 4, createdAt: "2026-10-01T10:00:00.000Z" }, body: { storage: { representation: "storage", value: "<p>x</p>" } } };

describe("getPage", () => {
  it("asks for the storage body of the current version", async () => {
    const seen: string[] = [];
    const r: Requester = async (p) => (seen.push(p), res(200, page));
    const doc = await getPage(r, "123");
    assert.deepEqual(seen, ["/wiki/api/v2/pages/123?body-format=storage"]);
    assert.deepEqual(doc, { id: "123", status: "current", title: "T", spaceId: "9", version: { number: 4, createdAt: "2026-10-01T10:00:00.000Z" }, storage: "<p>x</p>" });
  });

  it("asks for an earlier version with the version parameter", async () => {
    const seen: string[] = [];
    await getPage(async (p) => (seen.push(p), res(200, page)), "123", { version: 3 });
    assert.equal(seen[0], "/wiki/api/v2/pages/123?body-format=storage&version=3");
  });

  it("encodes the id, so it cannot change the path", async () => {
    const seen: string[] = [];
    await getPage(async (p) => (seen.push(p), res(200, page)), "1/../2?x=y");
    assert.ok(seen[0]!.startsWith("/wiki/api/v2/pages/1%2F..%2F2%3Fx%3Dy?"));
  });

  it("returns null for 404 and throws a ConfluenceError with the status for anything else", async () => {
    assert.equal(await getPage(async () => res(404), "1"), null);
    await assert.rejects(getPage(async () => res(500, { message: "boom" }), "1"), (e: unknown) => e instanceof ConfluenceError && e.status === 500 && /boom/.test(e.message));
    await assert.rejects(getPage(async () => res(403), "1"), (e: unknown) => e instanceof ConfluenceError && e.status === 403);
  });
});

describe("parsePage", () => {
  it("accepts a numeric id and a missing body", () => {
    const doc = parsePage({ id: 55, title: "T", version: { number: 1 } });
    assert.equal(doc.id, "55");
    assert.equal(doc.storage, "");
  });
  it("names the missing field", () => {
    assert.throws(() => parsePage(null), /not an object/);
    assert.throws(() => parsePage({ title: "T", version: { number: 1 } }), /no id/);
    assert.throws(() => parsePage({ id: "1", version: { number: 1 } }), /no title/);
    assert.throws(() => parsePage({ id: "1", title: "T" }), /version\.number/);
    assert.throws(() => parsePage({ id: "1", title: "T", version: { number: "2" } }), /version\.number/);
  });
});

describe("canRead", () => {
  it("is true for 200, false for 403 and 404, and throws otherwise so callers can fail closed", async () => {
    assert.equal(await canRead(async () => res(200, page), "1"), true);
    assert.equal(await canRead(async () => res(403), "1"), false);
    assert.equal(await canRead(async () => res(404), "1"), false);
    await assert.rejects(canRead(async () => res(500), "1"), ConfluenceError);
  });
  it("does not ask for the body, so the check costs only the base point plus one", async () => {
    const seen: string[] = [];
    await canRead(async (p) => (seen.push(p), res(200, page)), "7");
    assert.deepEqual(seen, ["/wiki/api/v2/pages/7"]);
  });
});
