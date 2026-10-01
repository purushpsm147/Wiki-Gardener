/**
 * How long does `analyzeEdit` take as the approved set grows? Run: `npm run bench` (add `-- --json` for machine-readable output).
 *
 * Synthetic text (seeded, so the corpus is identical on every run; the timings are not). Each approved page has 40 sentences of 8 to
 * 20 words with a skewed word distribution, about a quarter of them carrying a number with a unit. The edited page has 40 sentences,
 * and one of them changes "90 days" to "30 days"; its approved counterpart is planted on the first approved page, so the full path
 * (alignment, slot comparison, ranking) runs and exactly one conflict is expected. Two vocabularies bracket real text: SPARSE (3,000
 * words, little lexical overlap, so few pairs reach the cosine step) and DENSE (120 words, heavy overlap, so most pairs do).
 * This measures the PoC's own cost: it re-tokenizes the whole approved set on every edit and keeps no index. It does not measure
 * Forge, REST latency or real Confluence markup.
 */
import { cpus } from "node:os";
import { analyzeEdit } from "../src/core";
import type { PageText } from "../src/core";

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const SYLLABLES = ["ba", "ke", "lo", "mi", "ra", "su", "ta", "ve", "no", "pi", "da", "fu", "ge", "hi", "jo", "ku"];
function makeVocab(size: number): string[] {
  const out: string[] = [];
  const r = mulberry32(7);
  const seen = new Set<string>();
  while (out.length < size) {
    const n = 2 + Math.floor(r() * 3);
    let w = "";
    for (let i = 0; i < n; i++) w += SYLLABLES[Math.floor(r() * SYLLABLES.length)];
    if (!seen.has(w)) {
      seen.add(w);
      out.push(w);
    }
  }
  return out;
}
const SPARSE = makeVocab(3000);
const DENSE = makeVocab(120);
const UNITS = ["days", "hours", "minutes", "weeks", "months"];

function sentence(vocab: string[], r: () => number, number?: number): string {
  const n = 8 + Math.floor(r() * 13);
  const words: string[] = [];
  for (let i = 0; i < n; i++) words.push(vocab[Math.floor(Math.pow(r(), 2) * vocab.length)]!); // skewed towards common words
  if (number !== undefined || r() < 0.25) {
    const at = 2 + Math.floor(r() * (words.length - 3));
    words.splice(at, 0, "for", String(number ?? 1 + Math.floor(r() * 90)), UNITS[Math.floor(r() * UNITS.length)]!);
  }
  const s = words.join(" ");
  return s[0]!.toUpperCase() + s.slice(1) + ".";
}

function makePage(vocab: string[], id: string, seed: number, extra?: string, sentences = 40): PageText {
  const r = mulberry32(seed);
  const list = Array.from({ length: sentences }, () => sentence(vocab, r));
  if (extra) list[10] = extra;
  return { id, title: `Page ${id}`, text: list.join(" ") };
}

/** The edited page before and after: sentence 20 is the same claim with the number changed. */
function makeEdit(vocab: string[]): { previous: PageText; current: PageText; counterpart: string } {
  const r = mulberry32(99);
  const body = Array.from({ length: 40 }, () => sentence(vocab, r));
  const before = [...body];
  const after = [...body];
  before[20] = sentence(vocab, mulberry32(5), 90);
  after[20] = sentence(vocab, mulberry32(5), 30);
  return {
    counterpart: sentence(vocab, mulberry32(5), 90),
    previous: { id: "edited", title: "Edited", text: before.join(" ") },
    current: { id: "edited", title: "Edited", text: after.join(" ") },
  };
}

function median(xs: number[]): number {
  const s = [...xs].sort((a, b) => a - b);
  return s[Math.floor(s.length / 2)]!;
}

interface Row {
  approvedPages: number;
  approvedSentences: number;
  medianMs: number;
  minMs: number;
  maxMs: number;
  conflicts: number;
}

function run(vocab: string[], approvedPages: number, repeats: number): Row {
  const { previous, current, counterpart } = makeEdit(vocab);
  const approved = Array.from({ length: approvedPages }, (_, i) => makePage(vocab, `a${i}`, 1000 + i, i === 0 ? counterpart : undefined));
  analyzeEdit({ previous, current, approved }); // warm-up
  const times: number[] = [];
  let conflicts = 0;
  for (let i = 0; i < repeats; i++) {
    const t0 = performance.now();
    conflicts = analyzeEdit({ previous, current, approved }).conflicts.length;
    times.push(performance.now() - t0);
  }
  return { approvedPages, approvedSentences: approvedPages * 40, medianMs: median(times), minMs: Math.min(...times), maxMs: Math.max(...times), conflicts };
}

const sizes = [3, 10, 30, 100, 300, 1000];
const corpora = [
  { name: "sparse", vocab: SPARSE },
  { name: "dense", vocab: DENSE },
].map((c) => ({ name: c.name, rows: sizes.map((n) => run(c.vocab, n, n >= 300 ? 3 : 7)) }));

if (process.argv.includes("--json")) {
  process.stdout.write(JSON.stringify({ node: process.version, cpu: cpus()[0]?.model, cores: cpus().length, corpora }, null, 2) + "\n");
} else {
  console.log(`node ${process.version}, ${cpus()[0]?.model ?? "unknown cpu"} x${cpus().length}`);
  for (const c of corpora) {
    console.log(`\n${c.name} vocabulary`);
    console.log("approved pages | approved sentences | median ms | min ms | max ms | conflicts");
    for (const r of c.rows) {
      console.log(
        `${String(r.approvedPages).padStart(14)} | ${String(r.approvedSentences).padStart(18)} | ${r.medianMs.toFixed(1).padStart(9)} | ${r.minMs.toFixed(1).padStart(6)} | ${r.maxMs.toFixed(1).padStart(6)} | ${r.conflicts}`,
      );
    }
  }
}
