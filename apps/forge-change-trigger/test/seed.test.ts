import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { parseSeedArgs, seedSite } from "../scripts/seed-site";
import { dataset, storageOf } from "./helpers";

interface Call {
  url: string;
  method: string;
  headers: Record<string, string>;
  body?: any;
}

function fakeFetch(opts: { spaces?: unknown; failOnPost?: number } = {}) {
  const calls: Call[] = [];
  let posts = 0;
  const impl = (async (url: string, init: { method?: string; headers?: Record<string, string>; body?: string } = {}) => {
    calls.push({ url, method: init.method ?? "GET", headers: init.headers ?? {}, body: init.body ? JSON.parse(init.body) : undefined });
    const reply = (status: number, body: unknown) => ({ ok: status < 300, status, json: async () => body, text: async () => JSON.stringify(body) });
    if (url.includes("/wiki/api/v2/spaces")) return reply(200, opts.spaces ?? { results: [{ id: "9001", key: "DEMO" }] });
    posts++;
    if (opts.failOnPost === posts) return reply(400, { message: "A page with this title already exists" });
    return reply(200, { id: String(5000 + posts) });
  }) as unknown as typeof fetch;
  return { impl, calls };
}

describe("seed-site (the request construction; the real API is untested here)", () => {
  it("looks up the space, then creates the ten pages as storage-format bodies at version 1, in dataset order", async () => {
    const { impl, calls } = fakeFetch();
    const r = await seedSite({ site: "x.atlassian.net", email: "me@example.com", token: "tok", spaceKey: "DEMO", fetchImpl: impl });
    assert.equal(calls[0]!.url, "https://x.atlassian.net/wiki/api/v2/spaces?keys=DEMO");
    assert.equal(calls.length, 11);
    const posts = calls.slice(1);
    assert.ok(posts.every((c) => c.method === "POST" && c.url === "https://x.atlassian.net/wiki/api/v2/pages"));
    assert.deepEqual(posts.map((c) => c.body.title), dataset.pages.map((p) => p.title));
    assert.ok(posts.every((c) => c.body.spaceId === "9001" && c.body.status === "current" && c.body.body.representation === "storage"));
    assert.equal(posts[3]!.body.body.value, storageOf("runbook-log-rotation", "v1"));
    assert.equal(calls[1]!.headers.Authorization, `Basic ${Buffer.from("me@example.com:tok").toString("base64")}`);
    assert.equal(r.pages.length, 10);
  });

  it("returns the approved page ids in dataset order, ready for the environment variable", async () => {
    const { impl } = fakeFetch();
    const r = await seedSite({ site: "https://x.atlassian.net/", email: "e", token: "t", spaceKey: "DEMO", fetchImpl: impl });
    assert.deepEqual(r.approvedIds, ["5001", "5002", "5003"]);
  });

  it("applies a title prefix", async () => {
    const { impl, calls } = fakeFetch();
    await seedSite({ site: "x.atlassian.net", email: "e", token: "t", spaceKey: "DEMO", prefix: "S3 demo: ", fetchImpl: impl });
    assert.equal(calls[1]!.body.title, "S3 demo: Data Retention Policy (Approved)");
  });

  it("makes no request on a dry run", async () => {
    const { impl, calls } = fakeFetch();
    const lines: string[] = [];
    const r = await seedSite({ site: "x", email: "e", token: "", spaceKey: "DEMO", dryRun: true, fetchImpl: impl, log: (l) => lines.push(l) });
    assert.equal(calls.length, 0);
    assert.equal(lines.length, 10);
    assert.deepEqual(r.approvedIds, []);
  });

  it("stops at the first failure and says which page and why", async () => {
    const { impl, calls } = fakeFetch({ failOnPost: 3 });
    await assert.rejects(seedSite({ site: "x", email: "e", token: "t", spaceKey: "DEMO", fetchImpl: impl }), /creating "Incident Response Policy \(Approved\)" failed: HTTP 400.*already exists/);
    assert.equal(calls.length, 4, "the space lookup and three page creations, then nothing");
  });

  it("fails when the space is not found", async () => {
    const { impl } = fakeFetch({ spaces: { results: [] } });
    await assert.rejects(seedSite({ site: "x", email: "e", token: "t", spaceKey: "NOPE", fetchImpl: impl }), /space NOPE not found/);
  });

  it("parses its arguments and insists on a token unless it is a dry run", () => {
    const argv = ["--site", "x.atlassian.net", "--email", "me@example.com", "--space-key", "DEMO"];
    assert.deepEqual(parseSeedArgs(argv, { ATLASSIAN_API_TOKEN: "t" }), { site: "x.atlassian.net", email: "me@example.com", spaceKey: "DEMO", token: "t" });
    assert.throws(() => parseSeedArgs(argv, {}), /ATLASSIAN_API_TOKEN/);
    assert.equal(parseSeedArgs([...argv, "--dry-run"], {}).dryRun, true);
    assert.throws(() => parseSeedArgs(["--site", "x"], { ATLASSIAN_API_TOKEN: "t" }), /usage/);
  });
});
