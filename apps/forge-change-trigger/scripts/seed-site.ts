/**
 * Create the ten demo pages (version 1 of each) in a Confluence Cloud space, so the live GATE-S3 demo takes minutes to set up.
 *
 *   ATLASSIAN_API_TOKEN=... npx tsx scripts/seed-site.ts --site your-site.atlassian.net --email you@example.com --space-key DEMO
 *   add --dry-run to print the plan without any network call, and --prefix "S3 demo: " if page titles already exist in the space
 *
 * UNTESTED AGAINST A REAL SITE: it needs credentials, and `*.atlassian.com` is blocked in the sandbox where it was written. The
 * request construction is covered by unit tests with a fake `fetch`. The endpoints (`GET /wiki/api/v2/spaces?keys=`,
 * `POST /wiki/api/v2/pages`) and Basic auth with an API token are ASSUMED from memory of Atlassian's docs. It never edits a page: the
 * edit that triggers the check ("90 days" to "30 days") is made by hand in the editor, as the gate says.
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

interface DatasetPage {
  key: string;
  title: string;
  role: string;
  versions: Record<string, string>;
}

const FIXTURES = join(dirname(fileURLToPath(import.meta.url)), "..", "test", "fixtures");

export interface SeedOptions {
  site: string;
  email: string;
  token: string;
  spaceKey: string;
  prefix?: string;
  dryRun?: boolean;
  fetchImpl?: typeof fetch;
  log?: (line: string) => void;
}

export interface SeededPage {
  key: string;
  title: string;
  role: string;
  id: string | null;
}

export interface SeedResult {
  pages: SeededPage[];
  /** In dataset order, ready for `forge variables set APPROVED_SOURCE_PAGE_IDS`. Empty on a dry run. */
  approvedIds: string[];
}

function loadDataset(): DatasetPage[] {
  return (JSON.parse(readFileSync(join(FIXTURES, "dataset.json"), "utf8")) as { pages: DatasetPage[] }).pages;
}

export async function seedSite(opts: SeedOptions): Promise<SeedResult> {
  const log = opts.log ?? (() => undefined);
  const doFetch = opts.fetchImpl ?? fetch;
  const base = `https://${opts.site.replace(/^https?:\/\//, "").replace(/\/+$/, "")}`;
  const headers = {
    Authorization: `Basic ${Buffer.from(`${opts.email}:${opts.token}`).toString("base64")}`,
    Accept: "application/json",
  };
  const pages = loadDataset();
  const out: SeededPage[] = pages.map((p) => ({ key: p.key, title: (opts.prefix ?? "") + p.title, role: p.role, id: null }));

  if (opts.dryRun) {
    for (const p of out) log(`would create "${p.title}" (${p.role}) in space ${opts.spaceKey}`);
    return { pages: out, approvedIds: [] };
  }

  const spaces = await doFetch(`${base}/wiki/api/v2/spaces?keys=${encodeURIComponent(opts.spaceKey)}`, { headers });
  if (!spaces.ok) throw new Error(`looking up space ${opts.spaceKey} failed: HTTP ${spaces.status} ${(await spaces.text()).slice(0, 300)}`);
  const found = (await spaces.json()) as { results?: { id?: string | number }[] };
  const spaceId = found.results?.[0]?.id;
  if (spaceId === undefined) throw new Error(`space ${opts.spaceKey} not found, or not visible to ${opts.email}`);

  for (const [i, def] of pages.entries()) {
    const file = def.versions["v1"];
    if (!file) throw new Error(`fixture ${def.key} has no v1`);
    const value = readFileSync(join(FIXTURES, "pages", file), "utf8");
    const res = await doFetch(`${base}/wiki/api/v2/pages`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ spaceId: String(spaceId), status: "current", title: out[i]!.title, body: { representation: "storage", value } }),
    });
    if (!res.ok) throw new Error(`creating "${out[i]!.title}" failed: HTTP ${res.status} ${(await res.text()).slice(0, 300)}`);
    const created = (await res.json()) as { id?: string | number };
    if (created.id === undefined) throw new Error(`creating "${out[i]!.title}" returned no id`);
    out[i]!.id = String(created.id);
    log(`created ${out[i]!.id}  ${out[i]!.title} (${out[i]!.role})`);
  }
  return { pages: out, approvedIds: out.filter((p) => p.role === "approved").map((p) => p.id!) };
}

export function parseSeedArgs(argv: string[], env: Record<string, string | undefined>): SeedOptions {
  const value = (flag: string): string | undefined => {
    const i = argv.indexOf(flag);
    return i >= 0 ? argv[i + 1] : undefined;
  };
  const site = value("--site");
  const email = value("--email");
  const spaceKey = value("--space-key");
  const token = env.ATLASSIAN_API_TOKEN;
  if (!site || !email || !spaceKey) throw new Error("usage: seed-site --site <x.atlassian.net> --email <you> --space-key <KEY> [--prefix <text>] [--dry-run]  (token in ATLASSIAN_API_TOKEN)");
  if (!token && !argv.includes("--dry-run")) throw new Error("set ATLASSIAN_API_TOKEN (create one at https://id.atlassian.com/manage-profile/security/api-tokens)");
  const opts: SeedOptions = { site, email, spaceKey, token: token ?? "" };
  const prefix = value("--prefix");
  if (prefix !== undefined) opts.prefix = prefix;
  if (argv.includes("--dry-run")) opts.dryRun = true;
  return opts;
}

async function main(): Promise<void> {
  const opts = parseSeedArgs(process.argv.slice(2), process.env);
  const result = await seedSite({ ...opts, log: (l) => console.log(l) });
  if (!opts.dryRun) {
    console.log(`\nNext:\n  npx forge variables set -e development APPROVED_SOURCE_PAGE_IDS ${result.approvedIds.join(",")}`);
    const log = result.pages.find((p) => p.key === "runbook-log-rotation");
    console.log(`  then open "${log?.title}" (page id ${log?.id}), change "90 days" to "30 days", and click Update.`);
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((e: unknown) => {
    console.error(e instanceof Error ? e.message : String(e));
    process.exitCode = 2;
  });
}
