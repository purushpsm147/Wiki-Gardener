import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { changedSpans, sentencesTouching, splitSentences } from "../src/core";
import { pageText } from "./helpers";

const slice = (text: string, spans: { start: number; end: number }[]): string[] => spans.map((s) => text.slice(s.start, s.end));

describe("changedSpans", () => {
  it("finds nothing when the text is identical or only whitespace differs", () => {
    assert.deepEqual(changedSpans("a b c", "a b c"), []);
    assert.deepEqual(changedSpans("a b\nc", "a  b c"), []);
  });

  it("marks a replaced token", () => {
    const next = "Application logs are retained for 30 days.";
    assert.deepEqual(slice(next, changedSpans("Application logs are retained for 90 days.", next)), ["30"]);
  });

  it("marks inserted tokens, merged into one span", () => {
    const next = "A VPN connection is required for all production access.";
    assert.deepEqual(slice(next, changedSpans("A VPN is required.", next)).length > 0, true);
    const spans = changedSpans("one two six", "one two three four five six");
    assert.deepEqual(slice("one two three four five six", spans), ["three four five"]);
  });

  it("reports a pure deletion as the gap around it, which still selects the sentence", () => {
    const next = "A VPN connection is required.";
    const spans = changedSpans("A VPN connection is not required.", next);
    assert.equal(spans.length, 1);
    const sentences = splitSentences(next);
    assert.deepEqual(sentencesTouching(sentences, spans).map((s) => s.text), [next]);
  });

  it("a deletion at the end of one sentence selects that sentence, not only the next", () => {
    const next = "Keep logs. Rotate nightly.";
    const spans = changedSpans("Keep logs for ever. Rotate nightly.", next);
    const picked = sentencesTouching(splitSentences(next), spans).map((s) => s.text);
    assert.ok(picked.includes("Keep logs."), JSON.stringify(picked));
  });

  it("reports separate edits as separate spans and merges ones separated only by whitespace", () => {
    const next = "alpha BETA gamma delta EPSILON zeta";
    const spans = changedSpans("alpha beta gamma delta epsilon zeta", next);
    assert.deepEqual(slice(next, spans), ["BETA", "EPSILON"]);
    const adjacent = changedSpans("a b c d", "a X Y d");
    assert.equal(adjacent.length, 1);
  });

  it("falls back to the whole changed middle when the table would be too large, never to less", () => {
    const old = Array.from({ length: 60 }, (_, i) => `old${i}`).join(" ");
    const next = "head " + Array.from({ length: 60 }, (_, i) => `new${i}`).join(" ") + " tail";
    const spans = changedSpans(`head ${old} tail`, next, 100);
    assert.equal(spans.length, 1);
    assert.ok(next.slice(spans[0]!.start, spans[0]!.end).startsWith("new0"));
    assert.ok(next.slice(spans[0]!.start, spans[0]!.end).endsWith("new59"));
  });

  it("matches the planted edit exactly: only the number changed", () => {
    const before = pageText("runbook-log-rotation", "v1").text;
    const after = pageText("runbook-log-rotation", "v2").text;
    assert.deepEqual(slice(after, changedSpans(before, after)), ["30"]);
    assert.deepEqual(changedSpans(before, after), [{ start: 103, end: 105 }]);
  });

  it("every span lies inside the new text and is ordered", () => {
    const before = pageText("runbook-prod-access", "v1").text;
    const after = pageText("runbook-prod-access", "v2").text;
    const spans = changedSpans(before, after);
    assert.ok(spans.length > 0);
    let last = -1;
    for (const s of spans) {
      assert.ok(s.start >= 0 && s.end <= after.length && s.start <= s.end);
      assert.ok(s.start > last);
      last = s.end;
    }
  });
});
