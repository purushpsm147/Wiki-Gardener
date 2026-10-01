/**
 * A half-open range [start, end) of UTF-16 code units in a page's normalized text. An edit that only deletes text is reported as
 * the gap between the tokens on either side of the deletion, so it touches both neighbouring sentences.
 */
export interface Span {
  start: number;
  end: number;
}

export interface Sentence {
  text: string;
  start: number;
  end: number;
}

/** A page reduced to normalized plain text. Every offset in this package refers to `text` (see `storageToText`). */
export interface PageText {
  id: string;
  title: string;
  version?: number;
  text: string;
}

export type ConflictKind = "numeric" | "polarity" | "antonym";

/** One side of a conflict: the whole sentence and the exact differing value, both with offsets into that page's text. */
export interface Quote {
  pageId: string;
  title: string;
  /** The sentence containing the claim. `page.text.slice(start, end) === quote`. */
  quote: string;
  start: number;
  end: number;
  /** The differing value, for example "30 days" or "not". Empty with a zero-length span when the claim has no token (polarity on the non-negated side). */
  value: string;
  valueStart: number;
  valueEnd: number;
}

export interface Conflict {
  /** Stable across runs for the same pair of sentences and slot. */
  id: string;
  kind: ConflictKind;
  /** What differs, for example "duration" or "negation". */
  slot: string;
  /** 0 to 1. Near-identical sentences that differ in exactly one slot score highest. */
  severity: number;
  /** TF-IDF cosine of the two sentences with slot values masked out. */
  alignment: number;
  changed: Quote;
  approved: Quote;
  explanation: string;
  note?: string;
}

export interface DetectOptions {
  /** Minimum alignment for two sentences to be compared. There is deliberately no maximum. Default 0.5. */
  alignThreshold?: number;
  /**
   * An edited sentence is compared only with approved sentences whose alignment is within this margin of its best match. Weaker
   * neighbours are different claims that merely share a template ("Audit logs ... 365 days" next to "Application logs ... 90 days").
   * Default 0.1.
   */
  alignMargin?: number;
  /**
   * Best-match gating (default true): compare an edited sentence only with approved sentences within `alignMargin` of its best
   * match, and report nothing if any of them agrees on every slot. Turn it off to compare every aligned pair independently, which
   * is what the first version did and which produced false positives between sibling sentences. Exists for ablation tests.
   */
  gating?: boolean;
  /** Skip comparisons across different environments ("Staging ..." against "Production ..."). Default true. Exists for ablation tests. */
  scopeGuard?: boolean;
  /** Keep at most this many conflicts, highest severity first. Default: all. */
  maxResults?: number;
}
