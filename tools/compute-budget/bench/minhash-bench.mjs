#!/usr/bin/env node
// Spike S2 measurement harness. Dependency-free; Node >= 20.
//
//   node --expose-gc tools/compute-budget/bench/minhash-bench.mjs [--out results.json]
//
// MEASURES, on THIS machine (not Forge/Lambda hardware):
//   1. per-page CPU of the whole fingerprint pipeline: strip storage-format tags -> tokenize -> 5-word shingles
//      -> MinHash (k = 128, uint32) -> 16 LSH bands x 8 rows;
//   2. memory and build time of in-memory LSH indexes at 50k / 100k / 250k pages (naive Map vs compact typed arrays).
// Pages are synthetic (Zipf vocabulary, XHTML-ish markup), so absolute numbers are indicative, not representative of real
// Confluence content. docs/spikes/02-forge-only-compute-feasibility.md says how they are used.
import os from "node:os";
import { writeFileSync } from "node:fs";
import { performance } from "node:perf_hooks";

const K = 128;
const BANDS = 16;
const ROWS = K / BANDS;
const SHINGLE = 5;
const SIZES_WORDS = [300, 1500, 6000, 20000];
const PAGES_PER_SIZE = { 300: 400, 1500: 120, 6000: 40, 20000: 12 };
const ROUNDS = 7;

function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---- synthetic storage-format pages ---------------------------------------------------------------------------
const rnd = mulberry32(20261001);
const VOCAB = 20000;
const vocab = [];
for (let i = 0; i < VOCAB; i++) {
  const len = 2 + Math.floor(rnd() * 9);
  let w = "";
  for (let c = 0; c < len; c++) w += String.fromCharCode(97 + Math.floor(rnd() * 26));
  vocab.push(w);
}
const cdf = new Float64Array(VOCAB);
{
  let sum = 0;
  for (let i = 0; i < VOCAB; i++) sum += 1 / (i + 1);
  let acc = 0;
  for (let i = 0; i < VOCAB; i++) {
    acc += 1 / (i + 1) / sum;
    cdf[i] = acc;
  }
}
function zipfWord() {
  const u = rnd();
  let lo = 0;
  let hi = VOCAB - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (cdf[mid] < u) lo = mid + 1;
    else hi = mid;
  }
  return vocab[lo];
}

function makeStoragePage(words, markup) {
  const out = [];
  let made = 0;
  while (made < words) {
    const paraSentences = 3 + Math.floor(rnd() * 4);
    let para = "";
    for (let s = 0; s < paraSentences && made < words; s++) {
      const n = Math.min(words - made, 8 + Math.floor(rnd() * 15));
      const ws = [];
      for (let i = 0; i < n; i++) {
        let w = zipfWord();
        const r = rnd();
        if (markup === "heavy" && rnd() < 0.35) w = `<span style="color: rgb(23, 43, 77);" class="c${Math.floor(rnd() * 99)}">${w}</span>`;
        if (r < 0.03) w = `<strong>${w}</strong>`;
        else if (r < 0.05) w = `<a href="https://example.atlassian.net/wiki/spaces/ENG/pages/${Math.floor(rnd() * 1e9)}">${w}</a>`;
        else if (r < 0.06) w = `${w}&nbsp;`;
        ws.push(w);
      }
      made += n;
      const first = ws[0];
      ws[0] = first[0] === "<" ? first : first[0].toUpperCase() + first.slice(1);
      para += ws.join(" ") + ". ";
    }
    const block = `<p>${para.trim()}</p>`;
    out.push(rnd() < 0.03
      ? `<ac:structured-macro ac:name="info" ac:schema-version="1" ac:macro-id="${Math.floor(rnd() * 1e12)}"><ac:rich-text-body>${block}</ac:rich-text-body></ac:structured-macro>`
      : block);
  }
  return out.join("\n");
}

// ---- the pipeline under test ----------------------------------------------------------------------------------
const A = new Uint32Array(K);
const B = new Uint32Array(K);
{
  const r = mulberry32(7);
  for (let j = 0; j < K; j++) {
    A[j] = ((r() * 4294967296) | 1) >>> 0; // odd multiplier
    B[j] = (r() * 4294967296) >>> 0;
  }
}

let shingleBuf = new Uint32Array(4096);
const sig = new Uint32Array(K);
const bandKeys = new Float64Array(BANDS);

function fingerprint(storageHtml) {
  // 1. strip tags and entities, lowercase
  const text = storageHtml.replace(/<[^>]*>/g, " ").replace(/&nbsp;|&amp;|&lt;|&gt;/g, " ").toLowerCase();
  // 2. tokenize to word hashes (FNV-1a over [a-z0-9]+), no per-token string allocation
  const n = text.length;
  let words = 0;
  let wh = shingleBuf; // reuse as scratch for word hashes, grown on demand
  let h = 2166136261;
  let inWord = false;
  for (let i = 0; i <= n; i++) {
    const c = i < n ? text.charCodeAt(i) : 32;
    const isW = (c >= 97 && c <= 122) || (c >= 48 && c <= 57);
    if (isW) {
      h = Math.imul(h ^ c, 16777619);
      inWord = true;
    } else if (inWord) {
      if (words === wh.length) {
        const g = new Uint32Array(wh.length * 2);
        g.set(wh);
        wh = g;
      }
      wh[words++] = h >>> 0;
      h = 2166136261;
      inWord = false;
    }
  }
  shingleBuf = wh; // keep the grown scratch buffer for the next page
  // 3. shingle hashes: combine SHINGLE consecutive word hashes
  const m = words - SHINGLE + 1;
  if (m <= 0) return { words, shingles: 0 };
  const sh = new Uint32Array(m);
  for (let i = 0; i < m; i++) {
    let s = 0x9e3779b1;
    for (let k = 0; k < SHINGLE; k++) s = Math.imul(s ^ wh[i + k], 0x85ebca6b) ^ (s >>> 13);
    sh[i] = s >>> 0;
  }
  // 4. MinHash, k permutations as (a*s + b) mod 2^32
  sig.fill(0xffffffff);
  for (let i = 0; i < m; i++) {
    const s = sh[i];
    for (let j = 0; j < K; j++) {
      const v = (Math.imul(A[j], s) + B[j]) >>> 0;
      if (v < sig[j]) sig[j] = v;
    }
  }
  // 5. LSH band keys: two 32-bit mixes -> one 53-bit number per band
  for (let b = 0; b < BANDS; b++) {
    let h1 = 2166136261 ^ b;
    let h2 = 0x9747b28c ^ b;
    for (let r = 0; r < ROWS; r++) {
      const v = sig[b * ROWS + r];
      h1 = Math.imul(h1 ^ v, 16777619);
      h2 = Math.imul(h2 + v, 0x5bd1e995) ^ (h2 >>> 15);
    }
    bandKeys[b] = (h1 >>> 0) * 2097152 + ((h2 >>> 0) >>> 11);
  }
  return { words, shingles: m };
}

function quantile(sorted, q) {
  const i = Math.min(sorted.length - 1, Math.max(0, Math.round(q * (sorted.length - 1))));
  return sorted[i];
}

function benchSize(words, markup) {
  const count = PAGES_PER_SIZE[words];
  const pages = [];
  let bytes = 0;
  for (let i = 0; i < count; i++) {
    const p = makeStoragePage(words, markup);
    pages.push(p);
    bytes += p.length;
  }
  let shingles = 0;
  for (const p of pages) shingles = fingerprint(p).shingles; // warm-up, and capture shingles/page
  const perPageUs = [];
  for (let r = 0; r < ROUNDS; r++) {
    const t0 = performance.now();
    for (const p of pages) fingerprint(p);
    perPageUs.push(((performance.now() - t0) * 1000) / pages.length);
  }
  perPageUs.sort((a, b) => a - b);
  return {
    markup,
    words,
    pages: count,
    storage_bytes_per_page: Math.round(bytes / count),
    storage_bytes_per_word: +(bytes / count / words).toFixed(1),
    shingles_per_page: shingles,
    us_per_page_median: +quantile(perPageUs, 0.5).toFixed(1),
    us_per_page_p10: +quantile(perPageUs, 0.1).toFixed(1),
    us_per_page_p90: +quantile(perPageUs, 0.9).toFixed(1),
    us_per_word_median: +(quantile(perPageUs, 0.5) / words).toFixed(3),
  };
}

// ---- in-memory LSH index memory ---------------------------------------------------------------------------------
function memNow() {
  if (global.gc) global.gc();
  const m = process.memoryUsage();
  return { heapUsed: m.heapUsed, arrayBuffers: m.arrayBuffers, rss: m.rss };
}

function benchLshIndex(pages) {
  const r = mulberry32(99);
  // random band keys, with ~2 % of pages copying another page's key in a band so buckets are not all singletons
  const keys = new Float64Array(pages * BANDS);
  for (let i = 0; i < keys.length; i++) {
    keys[i] = r() < 0.02 && i >= BANDS ? keys[Math.floor(r() * i)] : Math.floor(r() * 9007199254740991);
  }
  const base = memNow();

  // (a) naive: one Map<number, number[]> per band
  let t0 = performance.now();
  const naive = [];
  for (let b = 0; b < BANDS; b++) {
    const mp = new Map();
    for (let p = 0; p < pages; p++) {
      const k = keys[p * BANDS + b];
      const e = mp.get(k);
      if (e) e.push(p);
      else mp.set(k, [p]);
    }
    naive.push(mp);
  }
  const naiveMs = performance.now() - t0;
  const afterNaive = memNow();
  const naiveKeepAlive = naive.length; // keep reachable: V8 otherwise frees the maps before the measurement

  // (b) compact: per band a sorted (key, id) pair of typed arrays
  t0 = performance.now();
  const compactKeys = [];
  const compactIds = [];
  for (let b = 0; b < BANDS; b++) {
    const order = new Int32Array(pages);
    for (let p = 0; p < pages; p++) order[p] = p;
    const bk = new Float64Array(pages);
    for (let p = 0; p < pages; p++) bk[p] = keys[p * BANDS + b];
    order.sort((x, y) => bk[x] - bk[y]);
    const sk = new Float64Array(pages);
    for (let p = 0; p < pages; p++) sk[p] = bk[order[p]];
    compactKeys.push(sk);
    compactIds.push(order);
  }
  const compactMs = performance.now() - t0;
  const afterCompact = memNow();
  const keepAlive = naiveKeepAlive + compactKeys.length + compactIds.length; // see above
  const mb = (x) => +(x / 1048576).toFixed(1);
  return {
    pages,
    entries: pages * BANDS,
    naive_map_heap_mb: mb(afterNaive.heapUsed - base.heapUsed),
    naive_build_ms: Math.round(naiveMs),
    compact_typed_array_mb: mb(afterCompact.arrayBuffers - afterNaive.arrayBuffers),
    compact_theoretical_mb: mb(pages * BANDS * 12),
    compact_build_ms: Math.round(compactMs),
    _kept_alive: keepAlive,
  };
}

// ---- run --------------------------------------------------------------------------------------------------------
const cpus = os.cpus();
const result = {
  meta: {
    note: "MEASURED on this machine only. Not Forge/Lambda hardware. Synthetic Zipf pages with XHTML-ish markup.",
    date: new Date().toISOString(),
    node: process.version,
    v8: process.versions.v8,
    platform: `${os.platform()} ${os.arch()}`,
    cpu_model: cpus[0]?.model ?? "unknown",
    cpu_count: cpus.length,
    total_mem_gb: +(os.totalmem() / 1073741824).toFixed(1),
    k: K,
    bands: BANDS,
    rows: ROWS,
    shingle_words: SHINGLE,
    rounds: ROUNDS,
    gc_exposed: typeof global.gc === "function",
  },
  fingerprint: ["light", "heavy"].flatMap((markup) => SIZES_WORDS.map((w) => benchSize(w, markup))),
  lsh_index_memory: [50000, 100000, 250000].map(benchLshIndex),
};

const out = process.argv.includes("--out") ? process.argv[process.argv.indexOf("--out") + 1] : null;
const json = JSON.stringify(result, null, 2) + "\n";
if (out) {
  writeFileSync(out, json);
  console.error(`wrote ${out}`);
}
process.stdout.write(json);
