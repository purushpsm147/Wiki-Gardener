import { stem } from "./tfidf";

/**
 * Slots are the things two aligned sentences can disagree about. This is intentionally crude: numbers with units, negation, a
 * short list of antonym pairs, and an environment-scope guard. It will miss paraphrased and multi-sentence contradictions.
 */

export interface Quantity {
  /** "duration", "business-days", "size", "percent" or "count:<unit stem>". */
  slot: string;
  /** Canonical value: seconds for durations, bytes for sizes, the number itself otherwise. */
  value: number;
  /** The matched text, for example "30 days". */
  text: string;
  /** Offsets relative to the sentence. */
  start: number;
  end: number;
  /** True for months and years, which are not fixed lengths ("12 months" and "1 year"): comparisons allow a small difference. */
  approx?: boolean;
}

export interface Hit {
  word: string;
  start: number;
  end: number;
}

const SECONDS: Record<string, number> = {
  second: 1, seconds: 1, sec: 1, secs: 1,
  minute: 60, minutes: 60, min: 60, mins: 60,
  hour: 3600, hours: 3600, hr: 3600, hrs: 3600,
  day: 86_400, days: 86_400,
  week: 604_800, weeks: 604_800,
  month: 2_592_000, months: 2_592_000, // 30 days
  year: 31_536_000, years: 31_536_000, // 365 days
};
const BYTES: Record<string, number> = {
  kb: 1024, kib: 1024, mb: 1024 ** 2, mib: 1024 ** 2, gb: 1024 ** 3, gib: 1024 ** 3, tb: 1024 ** 4, tib: 1024 ** 4,
};
// Only these nouns count as a unit on their own ("3 attempts"). Any other word after a number ("Version 2 shipped") is not a quantity.
const COUNT_NOUNS = new Set(
  "attempt retry retries user reviewer approver character request item copy copies replica node server instance file member admin person people word".split(" ").map((w) => stem(w)),
);

function parseNumber(s: string): number {
  const thousands = /^\d{1,3}(,\d{3})+$/.test(s);
  return parseFloat(thousands ? s.replace(/,/g, "") : s.replace(",", "."));
}

/** Numbers followed by a unit word. Bare numbers (list numbers, versions, years) are ignored. */
export function extractQuantities(sentence: string): Quantity[] {
  const out: Quantity[] = [];
  const re = /(\d+(?:[.,]\d+)*)\s*(?:(business|working)\s+)?(%|[A-Za-z]+)?/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(sentence)) !== null) {
    const n = parseNumber(m[1]!);
    const qualifier = (m[2] ?? "").toLowerCase();
    const unit = (m[3] ?? "").toLowerCase();
    if (!Number.isFinite(n) || unit === "") continue;
    const text = m[0].trimEnd();
    let slot: string;
    let value: number;
    if (unit === "%" || unit === "percent") {
      slot = "percent";
      value = n;
    } else if (unit in SECONDS) {
      if (qualifier !== "" && (unit === "day" || unit === "days")) {
        slot = "business-days";
        value = n;
      } else {
        slot = "duration";
        value = n * SECONDS[unit]!;
      }
    } else if (unit in BYTES) {
      slot = "size";
      value = n * BYTES[unit]!;
    } else if (COUNT_NOUNS.has(stem(unit))) {
      slot = `count:${stem(unit)}`;
      value = n;
    } else {
      continue;
    }
    const q: Quantity = { slot, value, text, start: m.index, end: m.index + text.length };
    if (slot === "duration" && /^(?:month|months|year|years)$/.test(unit)) q.approx = true;
    out.push(q);
  }
  return out;
}

export interface NumericMismatch {
  slot: string;
  changed: Quantity;
  approved: Quantity;
}

/** Months and years differ in length ("12 months" is 360 days and "1 year" is 365), so when either side uses one, 2 % is the same value. */
export const CALENDAR_TOLERANCE = 0.02;

function sameValue(x: Quantity, y: Quantity): boolean {
  const diff = Math.abs(x.value - y.value);
  return x.approx || y.approx ? diff <= CALENDAR_TOLERANCE * Math.max(x.value, y.value) : diff < 1e-9;
}

/**
 * For every slot both sentences state, a mismatch exists only when *each* side has a value the other lacks ("30 days" against
 * "90 days"). A sentence that merely mentions an extra figure is not a contradiction.
 */
export function numericMismatches(changed: Quantity[], approved: Quantity[]): NumericMismatch[] {
  const out: NumericMismatch[] = [];
  const slots = new Set(changed.map((q) => q.slot));
  for (const slot of slots) {
    const a = changed.filter((q) => q.slot === slot);
    const b = approved.filter((q) => q.slot === slot);
    if (b.length === 0) continue;
    const x = a.find((q) => !b.some((r) => sameValue(r, q)));
    const y = b.find((r) => !a.some((q) => sameValue(r, q)));
    if (x && y) out.push({ slot, changed: x, approved: y });
  }
  return out;
}

const NEGATION = /\b(?:not|no|never|cannot|without|neither|nor)\b|\b[a-z]+n['’]t\b/gi;

export function negations(sentence: string): Hit[] {
  const out: Hit[] = [];
  NEGATION.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = NEGATION.exec(sentence)) !== null) out.push({ word: m[0], start: m.index, end: m.index + m[0].length });
  return out;
}

/** An odd number of negations. Double negation is rare in policy text and is not modelled. */
export function isNegated(sentence: string): boolean {
  return negations(sentence).length % 2 === 1;
}

/** Where a polarity claim "sits" in a sentence that has no negation: just after its first auxiliary or modal, else the start. */
export function polarityAnchor(sentence: string): number {
  const m = /\b(?:is|are|was|were|be|must|should|shall|may|can|will|does|do|has|have)\b/i.exec(sentence);
  return m ? m.index + m[0].length : 0;
}

interface AntonymGroup {
  id: string;
  a: string[];
  b: string[];
}
const ANTONYMS: AntonymGroup[] = [
  { id: "required / optional", a: ["required", "mandatory", "compulsory"], b: ["optional", "voluntary"] },
  { id: "allowed / prohibited", a: ["allowed", "permitted", "authorized", "authorised"], b: ["prohibited", "forbidden", "disallowed", "banned", "unauthorized", "unauthorised"] },
  { id: "enabled / disabled", a: ["enabled"], b: ["disabled"] },
  { id: "public / private", a: ["public"], b: ["private"] },
  { id: "encrypted / unencrypted", a: ["encrypted"], b: ["unencrypted", "plaintext"] },
  { id: "at least / at most", a: ["at least"], b: ["at most"] },
];

function wordHits(sentence: string, words: string[]): Hit[] {
  const out: Hit[] = [];
  const re = new RegExp(`\\b(?:${words.join("|")})\\b`, "gi");
  let m: RegExpExecArray | null;
  while ((m = re.exec(sentence)) !== null) out.push({ word: m[0], start: m.index, end: m.index + m[0].length });
  return out;
}

export interface AntonymMismatch {
  group: string;
  changed: Hit;
  approved: Hit;
}

/** One side uses a word of one pole and the other a word of the opposite pole, with neither using both. */
export function antonymMismatches(changed: string, approved: string): AntonymMismatch[] {
  const out: AntonymMismatch[] = [];
  for (const g of ANTONYMS) {
    const cA = wordHits(changed, g.a);
    const cB = wordHits(changed, g.b);
    const pA = wordHits(approved, g.a);
    const pB = wordHits(approved, g.b);
    if (cA.length > 0 && cB.length === 0 && pB.length > 0 && pA.length === 0) out.push({ group: g.id, changed: cA[0]!, approved: pB[0]! });
    else if (cB.length > 0 && cA.length === 0 && pA.length > 0 && pB.length === 0) out.push({ group: g.id, changed: cB[0]!, approved: pA[0]! });
  }
  return out;
}

const SCOPE_CANON: Record<string, string> = {
  production: "production", prod: "production",
  staging: "staging", stage: "staging", preprod: "staging", uat: "staging",
  development: "development", dev: "development",
  test: "test", testing: "test", qa: "test",
  sandbox: "sandbox",
};

/** Environment words ("staging", "production"), canonicalised. Used to avoid reporting an environment-specific rule as a conflict. */
export function scopeWords(sentence: string): Set<string> {
  const out = new Set<string>();
  for (const w of sentence.toLowerCase().split(/[^a-z]+/)) {
    const c = SCOPE_CANON[w];
    if (c) out.add(c);
  }
  return out;
}

export type ScopeRelation = "same" | "different" | "approved-narrower" | "changed-narrower";

/**
 * - `same`: neither names an environment, or both name the same ones: compare.
 * - `different`: both name environments and they differ ("Staging ..." against "Production ..."): do not compare.
 * - `approved-narrower`: only the approved sentence names one (an exception to the edited, general sentence): do not compare.
 * - `changed-narrower`: only the edited sentence names one (it may be an exception, or an override): compare, with a note.
 */
export function scopeRelation(changed: string, approved: string): ScopeRelation {
  const a = scopeWords(changed);
  const b = scopeWords(approved);
  if (a.size === 0 && b.size === 0) return "same";
  if (a.size > 0 && b.size > 0) return [...a].every((x) => b.has(x)) && [...b].every((x) => a.has(x)) ? "same" : "different";
  return a.size === 0 ? "approved-narrower" : "changed-narrower";
}
