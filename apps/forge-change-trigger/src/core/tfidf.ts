// Function words, auxiliaries, modals and negations are dropped from the *template* a sentence is aligned on. Negations are
// dropped on purpose: "X must be retained" and "X must not be retained" must align (cosine 1.0) so that the polarity difference
// is found by the slot check instead of hiding the pair.
const STOP = new Set(
  (
    "a an the of to in on for and or but if is are was were be been being am by with at as it its this that these those from into " +
    "over under than then there their they them he she we you our your i do does did has have had will would shall should must may " +
    "might can could not no never cannot nor without neither also any all each every other such so very per via within up out"
  ).split(" "),
);

/** A deliberately crude stemmer. It only has to map both sides of a comparison to the same token. */
export function stem(word: string): string {
  let w = word;
  if (w.length > 4 && w.endsWith("ies")) w = w.slice(0, -3) + "y";
  else if (w.length > 5 && w.endsWith("ing")) w = w.slice(0, -3);
  else if (w.length > 4 && w.endsWith("ed")) w = w.slice(0, -2);
  else if (w.length > 4 && w.endsWith("es")) w = w.slice(0, -2);
  else if (w.length > 3 && w.endsWith("s") && !w.endsWith("ss")) w = w.slice(0, -1);
  if (w.length > 3 && w.endsWith("e")) w = w.slice(0, -1);
  return w;
}

/** Tokens a sentence is aligned on: lower-cased, stemmed words; every number becomes `<num>`; stop words and negations are dropped. */
export function templateTokens(sentence: string): string[] {
  const out: string[] = [];
  for (const raw of sentence.toLowerCase().split(/[^a-z0-9]+/)) {
    if (raw.length === 0) continue;
    if (/^\d+$/.test(raw)) {
      out.push("<num>");
      continue;
    }
    if (raw.length < 2 || STOP.has(raw)) continue;
    out.push(stem(raw));
  }
  return out;
}

/** Smoothed inverse document frequency over a corpus of token lists. */
export function idfFor(docs: string[][]): Map<string, number> {
  const df = new Map<string, number>();
  for (const d of docs) for (const t of new Set(d)) df.set(t, (df.get(t) ?? 0) + 1);
  const idf = new Map<string, number>();
  for (const [t, c] of df) idf.set(t, Math.log((docs.length + 1) / (c + 1)) + 1);
  return idf;
}

export type Vector = Map<string, number>;

export function vectorize(tokens: string[], idf: Map<string, number>): Vector {
  const tf = new Map<string, number>();
  for (const t of tokens) tf.set(t, (tf.get(t) ?? 0) + 1);
  const v: Vector = new Map();
  for (const [t, c] of tf) v.set(t, c * (idf.get(t) ?? 1));
  return v;
}

export function norm(v: Vector): number {
  let s = 0;
  for (const x of v.values()) s += x * x;
  return Math.sqrt(s);
}

export function cosine(a: Vector, b: Vector, normA = norm(a), normB = norm(b)): number {
  if (normA === 0 || normB === 0) return 0;
  const [small, large] = a.size <= b.size ? [a, b] : [b, a];
  let dot = 0;
  for (const [t, x] of small) {
    const y = large.get(t);
    if (y !== undefined) dot += x * y;
  }
  return dot / (normA * normB);
}
