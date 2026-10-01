/**
 * Offline audit: scan a directory of exported pages against a set of approved sources, with no Forge and no network.
 *
 *   npx tsx scripts/scan-files.ts <dir> --approved policy-a.html,policy-b.html
 *
 * Every other `.html` (Confluence storage format) and `.txt` file in <dir> is treated as entirely changed (audit mode) and checked
 * against the approved files. Prints a JSON array of `{ page, conflicts }`. This is the analysis aid the concierge audit in
 * docs/phase-v/concierge-scanner-spec.md relies on; it is not a product component.
 */
import { readdirSync, readFileSync } from "node:fs";
import { basename, extname, join } from "node:path";
import { pathToFileURL } from "node:url";
import { detectConflicts, storageToText } from "../src/core";
import type { Conflict, PageText } from "../src/core";

export interface ScanResult {
  page: string;
  conflicts: Conflict[];
}

export function loadPages(dir: string): { name: string; page: PageText }[] {
  const out: { name: string; page: PageText }[] = [];
  for (const name of readdirSync(dir).sort()) {
    const ext = extname(name).toLowerCase();
    if (![".html", ".htm", ".txt"].includes(ext)) continue;
    const raw = readFileSync(join(dir, name), "utf8");
    const text = ext === ".txt" ? raw.split(/\r?\n/).map((l) => l.trim()).filter(Boolean).join("\n") : storageToText(raw);
    out.push({ name, page: { id: name, title: basename(name, ext), text } });
  }
  return out;
}

export function scanDirectory(dir: string, approvedNames: string[]): ScanResult[] {
  const all = loadPages(dir);
  const missing = approvedNames.filter((n) => !all.some((p) => p.name === n));
  if (missing.length > 0) throw new Error(`approved file(s) not found in ${dir}: ${missing.join(", ")}`);
  const approved = all.filter((p) => approvedNames.includes(p.name)).map((p) => p.page);
  return all
    .filter((p) => !approvedNames.includes(p.name))
    .map((p) => ({ page: p.name, conflicts: detectConflicts({ changed: p.page, changedSpans: "all", approved }) }));
}

export function parseArgs(argv: string[]): { dir: string; approved: string[] } {
  const dir = argv.find((a) => !a.startsWith("--"));
  const i = argv.indexOf("--approved");
  const approved = i >= 0 && argv[i + 1] ? argv[i + 1]!.split(",").map((s) => s.trim()).filter(Boolean) : [];
  if (!dir || approved.length === 0) throw new Error("usage: scan-files <dir> --approved <file,file,...>");
  return { dir, approved };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const { dir, approved } = parseArgs(process.argv.slice(2));
    const results = scanDirectory(dir, approved);
    process.stdout.write(JSON.stringify(results, null, 2) + "\n");
    const total = results.reduce((n, r) => n + r.conflicts.length, 0);
    process.stderr.write(`${results.length} pages scanned against ${approved.length} approved, ${total} conflict(s)\n`);
  } catch (e) {
    process.stderr.write(`${e instanceof Error ? e.message : String(e)}\n`);
    process.exitCode = 2;
  }
}
