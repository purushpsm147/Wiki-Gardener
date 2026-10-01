/**
 * How noisy is the detector on real prose that nobody wrote for it? Run: `npm run probe` (after `npm ci`), `-- --show=10` for samples.
 *
 * Two corpora, both from the installed npm packages, so nothing here was written for the detector:
 *   readme     the README files of ~180 packages: ordinary technical prose, few numbers with units;
 *   types-node the JSDoc comments of @types/node (71 files): dense with defaults, limits, timeouts and sizes, in repetitive phrasing,
 *              which is the worst case for false alarms on numbers.
 * Documents inside a corpus are unrelated to each other, so any "conflict" between an edited document and the approved pool is a false
 * alarm by construction. The edited page is treated as entirely new text (audit mode: every sentence counts as changed).
 *
 * Every third document is the approved pool. The rest are edited pages, split alternately into "dev" (the half rules were tuned on) and
 * "held-out". Be honest about what "held-out" means here: an earlier run over all documents was read by the author before the
 * polarity rules were tightened, so held-out was seen once, not never.
 *
 * Then a positive control: take pool sentences with exactly one number-and-unit, change the number, put the result on a page by itself
 * and check that the original is reported as the conflicting approved sentence. That is the near-identical, one-number-changed case.
 *
 * It does NOT measure recall on real contradictions, which are paraphrased; nothing here is one. Output depends on the installed
 * package versions; the selection is deterministic for a given `node_modules`.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { detectConflicts, extractQuantities, splitSentences } from "../src/core";
import type { Conflict, DetectOptions, PageText } from "../src/core";

const ROOT = join(process.cwd(), "node_modules");

function readmes(limit: number): string[] {
  const found: string[] = [];
  const packages: string[] = [];
  for (const name of readdirSync(ROOT).sort()) {
    if (name.startsWith(".")) continue;
    if (name.startsWith("@")) for (const sub of readdirSync(join(ROOT, name)).sort()) packages.push(join(ROOT, name, sub));
    else packages.push(join(ROOT, name));
  }
  for (const dir of packages) {
    for (const f of ["README.md", "readme.md", "Readme.md"]) {
      const p = join(dir, f);
      try {
        if (statSync(p).isFile()) {
          found.push(p);
          break;
        }
      } catch {
        // no readme here
      }
    }
    if (found.length >= limit) break;
  }
  return found;
}

/** Join wrapped lines into one line per paragraph, heading or list item, as Confluence storage has them. */
function paragraphs(lines: string[]): string {
  const out: string[] = [];
  let buffer = "";
  const flush = () => {
    const line = buffer.replace(/\s+/g, " ").trim();
    if (line.length > 0 && !/^[|:\- ]+$/.test(line) && !line.startsWith("|")) out.push(line);
    buffer = "";
  };
  for (const raw of lines) {
    if (raw.trim() === "") {
      flush();
      continue;
    }
    const marker = /^\s*(?:#{1,6}\s|[-*+]\s|\d+\.\s|>\s?)/.exec(raw);
    if (marker || /^\s*(?:=+|-+)\s*$/.test(raw)) flush();
    buffer += (buffer ? " " : "") + (marker ? raw.slice(marker[0].length) : raw);
  }
  flush();
  return out.join("\n");
}

/** Fenced code and link targets are dropped, inline code keeps its text, heading and list markers are stripped. */
export function markdownToText(md: string): string {
  const cleaned = md
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/~~~[\s\S]*?~~~/g, " ")
    .replace(/<!--[\s\S]*?-->/g, " ")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/`([^`]*)`/g, "$1")
    .replace(/<[^>]+>/g, " ");
  return paragraphs(cleaned.split(/\r?\n/));
}

/** The prose of every JSDoc block: example code and tag names are dropped, the text after a tag is kept. */
export function jsdocToText(source: string): string {
  const lines: string[] = [];
  for (const block of source.match(/\/\*\*[\s\S]*?\*\//g) ?? []) {
    const body = block
      .replace(/^\/\*\*|\*\/$/g, "")
      .split(/\r?\n/)
      .map((l) => l.replace(/^\s*\*\s?/, ""))
      .join("\n")
      .replace(/```[\s\S]*?```/g, " ")
      .replace(/@example[\s\S]*?(?=\n@|$)/g, " ")
      .replace(/\{@link\s+([^}|\s]+)[^}]*\}/g, "$1")
      .replace(/\{@[a-z]+\s+([^}]*)\}/g, "$1")
      .replace(/`([^`]*)`/g, "$1")
      .replace(/@(?:param|returns?|since|default|deprecated|see|throws|template|version)\b(?:\s+\{[^}]*\})?(?:\s+[\w.$[\]]+(?=\s))?/g, " ");
    lines.push(...body.split("\n"), "");
  }
  return paragraphs(lines);
}

function typesNode(): string[] {
  const out: string[] = [];
  const walk = (dir: string) => {
    for (const name of readdirSync(dir).sort()) {
      const p = join(dir, name);
      if (statSync(p).isDirectory()) walk(p);
      else if (name.endsWith(".d.ts")) out.push(p);
    }
  };
  walk(join(ROOT, "@types", "node"));
  return out;
}

function corpus(name: string): PageText[] {
  const pages: PageText[] = [];
  const files = name === "readme" ? readmes(600) : typesNode();
  for (const f of files) {
    const raw = readFileSync(f, "utf8");
    const text = name === "readme" ? markdownToText(raw) : jsdocToText(raw);
    const id = f.slice(ROOT.length + 1);
    if (text.length > 200 && text.length < 400_000) pages.push({ id, title: id, text });
  }
  return pages;
}

const show = Number(process.argv.find((a) => a.startsWith("--show="))?.slice(7) ?? 0);
const only = process.argv.find((a) => a.startsWith("--corpus="))?.slice(9);
const per1000 = (n: number, d: number) => (d === 0 ? 0 : (1000 * n) / d);
// `--polarity-min-alignment=0.5` and `--polarity-min-tokens=0` re-run the probe with another setting, to sweep a rule's threshold.
const flag = (name: string): number | undefined => {
  const v = process.argv.find((a) => a.startsWith(`--${name}=`))?.slice(name.length + 3);
  return v === undefined ? undefined : Number(v);
};
const options: DetectOptions = {};
const pma = flag("polarity-min-alignment");
if (pma !== undefined) options.polarityMinAlignment = pma;
const pmt = flag("polarity-min-tokens");
if (pmt !== undefined) options.polarityMinTokens = pmt;

for (const name of ["readme", "types-node"]) {
  if (only && only !== name) continue;
  const pages = corpus(name);
  const pool = pages.filter((_, i) => i % 3 === 0);
  const edited = pages.filter((_, i) => i % 3 !== 0);
  const halves = { dev: edited.filter((_, i) => i % 2 === 0), "held-out": edited.filter((_, i) => i % 2 === 1) };
  const poolSentences = pool.reduce((n, p) => n + splitSentences(p.text).length, 0);
  const poolQuantities = pool.reduce((n, p) => n + splitSentences(p.text).filter((s) => extractQuantities(s.text).length > 0).length, 0);
  console.log(`\n=== ${name}: ${pages.length} documents; approved pool ${pool.length} documents = ${poolSentences} sentences (${poolQuantities} with a number and unit)`);

  for (const [half, docs] of Object.entries(halves)) {
    let sentences = 0;
    let withQuantity = 0;
    const hits: Conflict[] = [];
    const byKind: Record<string, number> = {};
    const pagesHit = new Set<string>();
    for (const page of docs) {
      const s = splitSentences(page.text);
      sentences += s.length;
      withQuantity += s.filter((x) => extractQuantities(x.text).length > 0).length;
      for (const c of detectConflicts({ changed: page, changedSpans: "all", approved: pool }, options)) {
        hits.push(c);
        pagesHit.add(page.id);
        byKind[c.kind] = (byKind[c.kind] ?? 0) + 1;
      }
    }
    console.log(`\n${half}: ${docs.length} edited documents, ${sentences} sentences (${withQuantity} with a number and unit)`);
    console.log(`  false alarms: ${hits.length}  (numeric ${byKind.numeric ?? 0}, polarity ${byKind.polarity ?? 0}, antonym ${byKind.antonym ?? 0})`);
    console.log(`  per 1,000 sentences: ${per1000(hits.length, sentences).toFixed(2)};  numeric per 1,000 sentences with a number and unit: ${per1000(byKind.numeric ?? 0, withQuantity).toFixed(1)}`);
    console.log(`  documents with at least one: ${pagesHit.size} of ${docs.length}`);
    if (show > 0 && half === "dev") {
      for (const c of [...hits].sort((a, b) => b.severity - a.severity).slice(0, show)) {
        console.log(`\n  [${c.kind}/${c.slot} severity ${c.severity} alignment ${c.alignment}]`);
        console.log(`    EDITED   (${c.changed.title}): ${c.changed.quote.slice(0, 220)}`);
        console.log(`    APPROVED (${c.approved.title}): ${c.approved.quote.slice(0, 220)}`);
      }
    }
  }

  // Positive control on real sentences.
  interface Mutation {
    sentence: string;
    mutated: string;
    from: string;
    to: string;
  }
  const mutations: Mutation[] = [];
  for (const page of pool) {
    for (const sentence of splitSentences(page.text)) {
      const q = extractQuantities(sentence.text);
      if (q.length !== 1) continue;
      const only1 = q[0]!;
      const lead = /^\d+/.exec(only1.text);
      if (!lead) continue;
      const n = Number(lead[0]);
      if (n === 0) continue; // 0 times anything is 0: nothing to mutate
      const changed = String(n * 2 + 1) + only1.text.slice(lead[0].length);
      mutations.push({ sentence: sentence.text, mutated: sentence.text.slice(0, only1.start) + changed + sentence.text.slice(only1.end), from: only1.text, to: changed });
    }
  }
  let found = 0;
  let spurious = 0;
  const missed: Mutation[] = [];
  for (const m of mutations) {
    const conflicts = detectConflicts({ changed: { id: "mutated", title: "mutated", text: m.mutated }, changedSpans: "all", approved: pool }, options);
    if (conflicts.some((c) => c.kind === "numeric" && c.approved.quote === m.sentence)) found++;
    else missed.push(m);
    if (detectConflicts({ changed: { id: "copy", title: "copy", text: m.sentence }, changedSpans: "all", approved: pool }, options).some((c) => c.changed.quote === m.sentence)) spurious++;
  }
  console.log(`\nmutation test (${name} pool): ${mutations.length} sentences with exactly one number and unit, the number changed`);
  console.log(`  original reported as the conflicting approved sentence: ${found} of ${mutations.length}`);
  console.log(`  unchanged copy reported as a conflict: ${spurious} of ${mutations.length}`);
  if (show > 0) for (const m of missed.slice(0, show)) console.log(`  MISSED: "${m.from}" -> "${m.to}"   ${m.sentence.slice(0, 180)}`);
}
