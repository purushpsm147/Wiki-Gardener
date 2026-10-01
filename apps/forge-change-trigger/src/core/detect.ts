import { changedSpans } from "./diff";
import { sentencesTouching, splitSentences } from "./sentences";
import {
  antonymMismatches,
  extractQuantities,
  isNegated,
  negations,
  numericMismatches,
  polarityAnchor,
  scopeRelation,
} from "./slots";
import { cosine, idfFor, norm, templateTokens, vectorize } from "./tfidf";
import type { Conflict, ConflictKind, DetectOptions, PageText, Quote, Sentence, Span } from "./types";

/**
 * A3-shaped divergence detector.
 *
 * It compares the *changed spans* of an edited page against an *approved sources* set. Two sentences are compared when their
 * TF-IDF cosine, computed with slot values masked out, reaches a threshold. There is deliberately **no upper bound**: a pair that
 * is nearly identical and differs in exactly one number is the most dangerous case, and it is ranked first, never filtered.
 * It is LLM-free.
 */

export const DEFAULT_ALIGN_THRESHOLD = 0.5;

const BASE_SEVERITY: Record<ConflictKind, number> = { polarity: 0.9, antonym: 0.8, numeric: 0.7 };

interface PoolEntry {
  page: PageText;
  sentence: Sentence;
}

export interface Alignment {
  changed: Sentence;
  approvedPage: PageText;
  approved: Sentence;
  cosine: number;
}

/** Every (edited sentence, approved sentence) pair whose alignment is at least `threshold`. No upper bound, no top-k. */
export function alignSentences(changed: Sentence[], pool: PoolEntry[], threshold = DEFAULT_ALIGN_THRESHOLD): Alignment[] {
  const changedTokens = changed.map((s) => templateTokens(s.text));
  const poolTokens = pool.map((p) => templateTokens(p.sentence.text));
  const idf = idfFor([...changedTokens, ...poolTokens]);
  const poolVectors = poolTokens.map((t) => vectorize(t, idf));
  const poolNorms = poolVectors.map((v) => norm(v));
  const out: Alignment[] = [];
  changed.forEach((cs, i) => {
    const tokens = changedTokens[i]!;
    if (tokens.filter((t) => t !== "<num>").length < 2) return; // too little text to align on
    const v = vectorize(tokens, idf);
    const vn = norm(v);
    pool.forEach((p, j) => {
      const shared = poolTokens[j]!.filter((t) => t !== "<num>" && tokens.includes(t));
      if (shared.length < 2) return;
      const c = cosine(v, poolVectors[j]!, vn, poolNorms[j]!);
      if (c >= threshold) out.push({ changed: cs, approvedPage: p.page, approved: p.sentence, cosine: c });
    });
  });
  return out;
}

function quote(page: PageText, s: Sentence, value: string, valueStart: number, valueEnd: number): Quote {
  return { pageId: page.id, title: page.title, quote: s.text, start: s.start, end: s.end, value, valueStart: s.start + valueStart, valueEnd: s.start + valueEnd };
}

function fnv1a(s: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16).padStart(8, "0");
}

function round3(x: number): number {
  return Math.round(x * 1000) / 1000;
}

export interface DetectInput {
  /** The page after the edit. */
  changed: PageText;
  /** Spans of `changed.text` that were edited, or `"all"` to treat the whole page as changed (audit mode, or a new page). */
  changedSpans: Span[] | "all";
  /** Pages whose statements the edit must not contradict. The edited page itself is ignored if present. */
  approved: PageText[];
}

export const DEFAULT_ALIGN_MARGIN = 0.1;

interface Finding {
  kind: ConflictKind;
  slot: string;
  changed: Quote;
  approved: Quote;
  explanation: string;
}

/** What differs between an edited sentence and one approved sentence it is aligned with. Empty means they agree. */
function findingsFor(changedPage: PageText, al: Alignment): Finding[] {
  const out: Finding[] = [];
  for (const mm of numericMismatches(extractQuantities(al.changed.text), extractQuantities(al.approved.text))) {
    out.push({
      kind: "numeric",
      slot: mm.slot,
      changed: quote(changedPage, al.changed, mm.changed.text, mm.changed.start, mm.changed.end),
      approved: quote(al.approvedPage, al.approved, mm.approved.text, mm.approved.start, mm.approved.end),
      explanation: `${mm.slot}: "${mm.approved.text}" in "${al.approvedPage.title}", "${mm.changed.text}" after this edit`,
    });
  }

  const cNeg = isNegated(al.changed.text);
  const aNeg = isNegated(al.approved.text);
  if (cNeg !== aNeg) {
    const hit = negations((cNeg ? al.changed : al.approved).text)[0]!;
    const anchor = (s: Sentence): number => polarityAnchor(s.text);
    out.push({
      kind: "polarity",
      slot: "negation",
      changed: cNeg
        ? quote(changedPage, al.changed, hit.word, hit.start, hit.end)
        : quote(changedPage, al.changed, "", anchor(al.changed), anchor(al.changed)),
      approved: aNeg
        ? quote(al.approvedPage, al.approved, hit.word, hit.start, hit.end)
        : quote(al.approvedPage, al.approved, "", anchor(al.approved), anchor(al.approved)),
      explanation: cNeg
        ? `negation: the edited sentence says "${hit.word}"; the approved sentence in "${al.approvedPage.title}" does not`
        : `negation: the approved sentence in "${al.approvedPage.title}" says "${hit.word}"; the edited sentence does not`,
    });
  }

  for (const am of antonymMismatches(al.changed.text, al.approved.text)) {
    out.push({
      kind: "antonym",
      slot: am.group,
      changed: quote(changedPage, al.changed, am.changed.word, am.changed.start, am.changed.end),
      approved: quote(al.approvedPage, al.approved, am.approved.word, am.approved.start, am.approved.end),
      explanation: `${am.group}: "${am.approved.word}" in "${al.approvedPage.title}", "${am.changed.word}" after this edit`,
    });
  }
  return out;
}

/**
 * Conflicts introduced by an edit, most severe first.
 *
 * For each edited sentence only the approved sentences within `alignMargin` of its best match are compared. If any of them agrees
 * with it on every slot, the sentence is consistent with the approved sources and nothing is reported. Otherwise every mismatch among
 * those candidates is reported. `maxResults` truncates *after* ranking, so the most severe conflict always survives.
 */
export function detectConflicts(input: DetectInput, options: DetectOptions = {}): Conflict[] {
  const threshold = options.alignThreshold ?? DEFAULT_ALIGN_THRESHOLD;
  const margin = options.alignMargin ?? DEFAULT_ALIGN_MARGIN;
  const guard = options.scopeGuard ?? true;
  const gating = options.gating ?? true;
  const changedSentences = sentencesTouching(splitSentences(input.changed.text), input.changedSpans);
  if (changedSentences.length === 0) return [];

  const pool: PoolEntry[] = [];
  for (const page of input.approved) {
    if (page.id === input.changed.id) continue;
    for (const sentence of splitSentences(page.text)) pool.push({ page, sentence });
  }

  const groups = new Map<number, Alignment[]>();
  for (const al of alignSentences(changedSentences, pool, threshold)) {
    const g = groups.get(al.changed.start);
    if (g) g.push(al);
    else groups.set(al.changed.start, [al]);
  }

  const found = new Map<string, Conflict>();
  for (const group of groups.values()) {
    const best = Math.max(...group.map((a) => a.cosine));
    const evaluated = group
      .filter((a) => !gating || a.cosine >= best - margin - 1e-12)
      .map((al) => {
        const relation = guard ? scopeRelation(al.changed.text, al.approved.text) : "same";
        return { al, relation, comparable: relation === "same" || relation === "changed-narrower", findings: findingsFor(input.changed, al) };
      });
    if (gating && evaluated.some((e) => e.comparable && e.findings.length === 0)) continue; // a consistent counterpart exists

    for (const e of evaluated) {
      if (!e.comparable) continue;
      const narrower = e.relation === "changed-narrower";
      for (const f of e.findings) {
        const id = fnv1a([input.changed.id, e.al.approvedPage.id, e.al.changed.start, e.al.approved.start, f.kind, f.slot].join("|"));
        if (found.has(id)) continue;
        const c: Conflict = {
          id,
          kind: f.kind,
          slot: f.slot,
          severity: round3(BASE_SEVERITY[f.kind] * e.al.cosine * (narrower ? 0.6 : 1)),
          alignment: round3(e.al.cosine),
          changed: f.changed,
          approved: f.approved,
          explanation: f.explanation,
        };
        if (narrower) c.note = "The edited sentence names an environment the approved sentence does not; it may be a legitimate exception.";
        found.set(id, c);
      }
    }
  }

  const ranked = [...found.values()].sort(
    (x, y) => y.severity - x.severity || y.alignment - x.alignment || x.changed.start - y.changed.start || (x.id < y.id ? -1 : 1),
  );
  return options.maxResults === undefined ? ranked : ranked.slice(0, Math.max(0, options.maxResults));
}

export interface EditAnalysis {
  spans: Span[] | "all";
  changedSentences: Sentence[];
  conflicts: Conflict[];
}

/**
 * Diff the previous version against the current one, then check only what changed. With no previous version (a new page) the whole
 * page counts as changed. An edit that changes no words yields no spans and no conflicts.
 */
export function analyzeEdit(args: {
  previous: PageText | null;
  current: PageText;
  approved: PageText[];
  options?: DetectOptions;
}): EditAnalysis {
  const spans: Span[] | "all" = args.previous ? changedSpans(args.previous.text, args.current.text) : "all";
  if (spans !== "all" && spans.length === 0) return { spans, changedSentences: [], conflicts: [] };
  const changedSentences = sentencesTouching(splitSentences(args.current.text), spans);
  const conflicts = detectConflicts({ changed: args.current, changedSpans: spans, approved: args.approved }, args.options);
  return { spans, changedSentences, conflicts };
}
