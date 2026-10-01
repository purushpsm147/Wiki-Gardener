import type { Sentence, Span } from "./types";

const ABBREVIATION_END = /\b(?:e\.g|i\.e|etc|vs|approx|incl|fig|dr|mr|ms|mrs|inc|ltd)\.$/i;

function pushTrimmed(line: string, from: number, to: number, base: number, out: Sentence[]): void {
  const raw = line.slice(from, to);
  const trimmed = raw.trim();
  if (trimmed.length === 0) return;
  const lead = raw.length - raw.trimStart().length;
  const start = base + from + lead;
  out.push({ text: trimmed, start, end: start + trimmed.length });
}

function splitLine(line: string, base: number, out: Sentence[]): void {
  // A boundary is sentence punctuation (plus closing quotes), whitespace, then something that can start a sentence.
  // "3.5 days" has no whitespace after the dot, so it is never split.
  const re = /([.!?]+["')\]]*)\s+(?=[A-Z0-9"'(\[])/g;
  let from = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(line)) !== null) {
    const end = m.index + (m[1] ?? "").length;
    if (ABBREVIATION_END.test(line.slice(from, end))) continue;
    pushTrimmed(line, from, end, base, out);
    from = m.index + m[0].length;
  }
  pushTrimmed(line, from, line.length, base, out);
}

/** Split normalized text (see `storageToText`) into sentences, each with exact offsets: `text.slice(start, end) === sentence.text`. */
export function splitSentences(text: string): Sentence[] {
  const out: Sentence[] = [];
  let base = 0;
  for (const line of text.split("\n")) {
    splitLine(line, base, out);
    base += line.length + 1;
  }
  return out;
}

/**
 * The sentences that overlap or touch any of the spans. A deletion is a span covering the gap around the removed text, so removing a
 * word such as "not" still marks its sentence as changed. `"all"` selects every sentence (audit mode).
 */
export function sentencesTouching(sentences: Sentence[], spans: Span[] | "all"): Sentence[] {
  if (spans === "all") return sentences;
  return sentences.filter((s) => spans.some((sp) => sp.start <= s.end && sp.end >= s.start));
}
