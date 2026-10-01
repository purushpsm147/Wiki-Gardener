import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { HttpResponse, Requester } from "../src/confluence";
import { storageToText } from "../src/core";
import type { PageText } from "../src/core";

const HERE = dirname(fileURLToPath(import.meta.url));
export const FIXTURES = join(HERE, "fixtures");

export interface DatasetPage {
  key: string;
  id: string;
  title: string;
  role: "approved" | "procedure" | "distractor";
  versions: Record<string, string>;
}
export interface Planted {
  name: string;
  gate?: string;
  page: string;
  from: string;
  to: string;
  approved: string;
  changedQuote: string;
  changedValue: string;
  approvedQuote: string;
  approvedValue: string;
  kind: "numeric" | "polarity" | "antonym";
}
export interface Control {
  name: string;
  page: string;
  from: string;
  to: string;
  why: string;
}
export interface Dataset {
  pages: DatasetPage[];
  planted: Planted[];
  controls: Control[];
}

export const dataset: Dataset = JSON.parse(readFileSync(join(FIXTURES, "dataset.json"), "utf8")) as Dataset;

export function pageDef(key: string): DatasetPage {
  const p = dataset.pages.find((x) => x.key === key);
  if (!p) throw new Error(`no fixture page ${key}`);
  return p;
}

export function storageOf(key: string, version: string): string {
  const file = pageDef(key).versions[version];
  if (!file) throw new Error(`no version ${version} of ${key}`);
  return readFileSync(join(FIXTURES, "pages", file), "utf8");
}

export function pageText(key: string, version: string): PageText {
  const def = pageDef(key);
  return { id: def.id, title: def.title, text: storageToText(storageOf(key, version)) };
}

export function approvedPages(): PageText[] {
  return dataset.pages.filter((p) => p.role === "approved").map((p) => pageText(p.key, "v1"));
}

/** A fake Confluence site that serves the v2 page endpoint in the VERIFIED response shape and records every request. */
export class FakeSite {
  readonly requests: string[] = [];
  private readonly pages = new Map<string, { title: string; spaceId: string; versions: { storage: string; createdAt: string }[] }>();
  private readonly denied = new Set<string>();
  private readonly statuses = new Map<string, string>();
  /** Pages for which the *next* requests return HTTP 500, to test fail-closed behaviour. */
  private readonly broken = new Set<string>();

  addPage(id: string, title: string, versions: { storage: string; createdAt?: string }[]): this {
    this.pages.set(id, {
      title,
      spaceId: "9001",
      versions: versions.map((v, i) => ({ storage: v.storage, createdAt: v.createdAt ?? `2026-10-01T10:00:0${i}.000Z` })),
    });
    return this;
  }
  setStatus(id: string, status: string): this {
    this.statuses.set(id, status);
    return this;
  }
  deny(id: string): this {
    this.denied.add(id);
    return this;
  }
  break(id: string): this {
    this.broken.add(id);
    return this;
  }

  /** A requester behaving like `api.asApp()` (can read everything) or, with `asViewer`, like `api.asUser()`. */
  requester(asViewer = false): Requester {
    return async (path: string): Promise<HttpResponse> => {
      this.requests.push(path);
      const url = new URL(path, "https://example.atlassian.net");
      const m = /^\/wiki\/api\/v2\/pages\/([^/]+)$/.exec(url.pathname);
      const id = m?.[1] ? decodeURIComponent(m[1]) : undefined;
      const respond = (status: number, body: unknown): HttpResponse => ({
        ok: status >= 200 && status < 300,
        status,
        json: async () => body,
        text: async () => JSON.stringify(body),
      });
      if (!id) return respond(404, { message: "not a page path" });
      if (this.broken.has(id)) return respond(500, { message: "boom" });
      const page = this.pages.get(id);
      if (!page) return respond(404, { message: "not found" });
      if (asViewer && this.denied.has(id)) return respond(403, { message: "forbidden" });
      const wanted = url.searchParams.get("version");
      const number = wanted ? Number(wanted) : page.versions.length;
      const v = page.versions[number - 1];
      if (!v) return respond(404, { message: "no such version" });
      return respond(200, {
        id,
        status: this.statuses.get(id) ?? "current",
        title: page.title,
        spaceId: page.spaceId,
        version: { number, createdAt: v.createdAt, authorId: "u1", minorEdit: false },
        body: url.searchParams.get("body-format") === "storage" ? { storage: { representation: "storage", value: v.storage } } : undefined,
      });
    };
  }
}

/** A site holding the whole fixture dataset: every approved page at v1, every other page with all of its versions in order. */
export function fixtureSite(versionOrder: Record<string, string[]> = {}): FakeSite {
  const site = new FakeSite();
  for (const p of dataset.pages) {
    const order = versionOrder[p.key] ?? (p.role === "approved" ? ["v1"] : ["v1", "v2"].filter((v) => v in p.versions));
    site.addPage(p.id, p.title, order.map((v) => ({ storage: storageOf(p.key, v) })));
  }
  return site;
}
