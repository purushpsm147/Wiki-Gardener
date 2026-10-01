import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { before, describe, it } from "node:test";
import { fileURLToPath } from "node:url";

const APP = join(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(join(APP, "package.json"));

interface Mapping {
  mapping: { productEvent: string; oAuthScopes: { beta: string[]; current: string[] } }[];
}
const eventScopes: Mapping = JSON.parse(readFileSync(join(APP, "node_modules/@forge/manifest/out/mapping/product-event-to-scope-mapping.json"), "utf8"));

function unknownEvents(events: string[]): string[] {
  const known = new Set(eventScopes.mapping.map((m) => m.productEvent));
  return events.filter((e) => !known.has(e));
}
function missingScopes(events: string[], scopes: string[]): string[] {
  const need = new Set<string>();
  for (const e of events) for (const m of eventScopes.mapping.filter((x) => x.productEvent === e)) for (const s of m.oAuthScopes.beta) need.add(s);
  return [...need].filter((s) => !scopes.includes(s));
}

describe("manifest.yml", () => {
  let content: any;
  let result: { success: boolean; errors: unknown[]; manifestObject?: { typedContent?: unknown } };

  before(async () => {
    process.chdir(APP);
    const { validate } = require("@forge/manifest") as { validate: (basic?: boolean) => Promise<any> };
    result = await validate(false);
    content = result.manifestObject?.typedContent;
  });

  it("passes the validator that ships in @forge/manifest (offline; `forge lint` itself needs a login)", () => {
    assert.deepEqual(result.errors, []);
    assert.equal(result.success, true);
  });

  it("subscribes to an event that exists in the platform's own event list", () => {
    const events: string[] = content.modules.trigger.flatMap((t: { events: string[] }) => t.events);
    assert.deepEqual(events, ["avi:confluence:created:page", "avi:confluence:updated:page"]);
    assert.deepEqual(unknownEvents(events), []);
  });

  it("declares every scope the platform requires for that event", () => {
    const events: string[] = content.modules.trigger.flatMap((t: { events: string[] }) => t.events);
    assert.deepEqual(missingScopes(events, content.permissions.scopes), []);
  });

  it("the validator does NOT catch a mistyped event or a missing scope, so these two checks are the safety net", () => {
    assert.deepEqual(unknownEvents(["avi:confluence:updated:pages"]), ["avi:confluence:updated:pages"]);
    assert.deepEqual(missingScopes(["avi:confluence:updated:page"], ["storage:app"]).sort(), [
      "read:content.metadata:confluence",
      "read:page:confluence",
      "read:space:confluence",
      "read:user:confluence",
    ]);
  });

  it("is read-only against Confluence content: no write or delete scope is requested", () => {
    assert.deepEqual(content.permissions.scopes.filter((s: string) => /^(write|delete|manage):/.test(s)), []);
  });

  it("is eligible for Runs on Atlassian by construction (Spike S2, criterion G6)", () => {
    assert.equal(content.remotes, undefined);
    assert.equal(content.providers, undefined);
    assert.equal(content.connectModules, undefined);
    assert.equal(content.permissions.external, undefined);
    assert.equal(content.modules.webtrigger, undefined);
  });

  it("points at handlers that exist", () => {
    const fns: { key: string; handler: string }[] = content.modules.function;
    const byKey = Object.fromEntries(fns.map((f) => [f.key, f.handler]));
    assert.equal(byKey["on-page-updated"], "handler.onPageUpdated");
    assert.match(readFileSync(join(APP, "src/handler.ts"), "utf8"), /export async function onPageUpdated\(/);
    assert.equal(byKey["resolver"], "resolver.handler");
    assert.match(readFileSync(join(APP, "src/resolver.ts"), "utf8"), /export const handler = resolver\.getDefinitions\(\)/);
  });

  it("points at a UI resource that exists and a resolver function that is declared", () => {
    for (const r of content.resources) assert.ok(existsSync(join(APP, r.path)), r.path);
    const byline = content.modules["confluence:contentBylineItem"][0];
    assert.equal(byline.resolver.function, "resolver");
    assert.equal(byline.render, "native");
  });

  it("uses a supported Node runtime and never commits a real app id", () => {
    assert.ok(["nodejs20.x", "nodejs22.x", "nodejs24.x"].includes(content.app.runtime.name));
    assert.match(content.app.id, /00000000-0000-0000-0000-000000000000$/);
  });
});
