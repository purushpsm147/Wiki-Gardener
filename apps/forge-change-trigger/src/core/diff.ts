import type { Span } from "./types";

interface Token {
  text: string;
  start: number;
  end: number;
}

export function tokenize(text: string): Token[] {
  const out: Token[] = [];
  const re = /\S+/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) out.push({ text: m[0], start: m.index, end: m.index + m[0].length });
  return out;
}

/**
 * The spans of `newText` that differ from `oldText`, as offsets into `newText`.
 *
 * Whitespace-delimited tokens are compared (common prefix and suffix first, then a longest-common-subsequence over the middle).
 * Inserted or replaced tokens become spans over the new tokens. Pure deletions become the gap between the surrounding tokens.
 * Adjacent spans separated only by whitespace are merged. If the middle region is too large for the O(n*m) table
 * (`maxCells`), the whole middle of the new text is reported as one span, which errs on the side of checking more, never less.
 */
export function changedSpans(oldText: string, newText: string, maxCells = 4_000_000): Span[] {
  if (oldText === newText) return [];
  const a = tokenize(oldText);
  const b = tokenize(newText);

  let prefix = 0;
  while (prefix < a.length && prefix < b.length && a[prefix]!.text === b[prefix]!.text) prefix++;
  let suffix = 0;
  while (
    suffix < a.length - prefix &&
    suffix < b.length - prefix &&
    a[a.length - 1 - suffix]!.text === b[b.length - 1 - suffix]!.text
  ) {
    suffix++;
  }
  const aMid = a.slice(prefix, a.length - suffix);
  const bMid = b.slice(prefix, b.length - suffix);

  // the gap between b[index - 1] and b[index]: where a pure deletion happened
  const gap = (index: number): Span => ({
    start: index > 0 ? b[index - 1]!.end : 0,
    end: index < b.length ? b[index]!.start : newText.length,
  });

  if (aMid.length === 0 && bMid.length === 0) return []; // only whitespace or line breaks differ
  if (bMid.length === 0) return [gap(prefix)];
  const wholeMiddle: Span = { start: bMid[0]!.start, end: bMid[bMid.length - 1]!.end };
  if (aMid.length === 0 || aMid.length * bMid.length > maxCells) return [wholeMiddle];

  // dp[i][j] = length of the longest common subsequence of aMid[i..] and bMid[j..]
  const n = aMid.length;
  const m = bMid.length;
  const width = m + 1;
  const dp = new Uint32Array((n + 1) * width);
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i * width + j] =
        aMid[i]!.text === bMid[j]!.text
          ? dp[(i + 1) * width + j + 1]! + 1
          : Math.max(dp[(i + 1) * width + j]!, dp[i * width + j + 1]!);
    }
  }

  const raw: Span[] = [];
  let i = 0;
  let j = 0;
  let runI = -1;
  let runJ = -1;
  const close = (): void => {
    if (runI < 0) return;
    const deleted = i - runI;
    const inserted = j - runJ;
    if (inserted > 0) raw.push({ start: bMid[runJ]!.start, end: bMid[j - 1]!.end });
    else if (deleted > 0) raw.push(gap(prefix + j));
    runI = -1;
    runJ = -1;
  };
  while (i < n || j < m) {
    if (i < n && j < m && aMid[i]!.text === bMid[j]!.text) {
      close();
      i++;
      j++;
      continue;
    }
    if (runI < 0) {
      runI = i;
      runJ = j;
    }
    if (i < n && (j >= m || dp[(i + 1) * width + j]! >= dp[i * width + j + 1]!)) i++;
    else j++;
  }
  close();

  // merge spans separated only by whitespace
  raw.sort((x, y) => x.start - y.start || x.end - y.end);
  const merged: Span[] = [];
  for (const sp of raw) {
    const last = merged[merged.length - 1];
    if (last && (sp.start <= last.end || newText.slice(last.end, sp.start).trim() === "")) last.end = Math.max(last.end, sp.end);
    else merged.push({ ...sp });
  }
  return merged;
}
