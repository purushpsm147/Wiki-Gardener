import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { sentencesTouching, splitSentences } from "../src/core";
import { dataset, pageText } from "./helpers";

describe("splitSentences", () => {
  it("returns exact offsets for every sentence of every fixture page, at every version", () => {
    let checked = 0;
    let versions = 0;
    for (const def of dataset.pages) {
      for (const version of Object.keys(def.versions)) {
        versions++;
        const { text } = pageText(def.key, version);
        for (const s of splitSentences(text)) {
          assert.equal(text.slice(s.start, s.end), s.text, `${def.key} ${version}`);
          assert.equal(s.text, s.text.trim());
          checked++;
        }
      }
    }
    assert.ok(checked >= versions * 2, `${checked} sentences over ${versions} page versions`);
  });

  it("splits on newlines and on sentence punctuation followed by a capital or digit", () => {
    const text = "First one. Second one! Third? 4 is a number.\nSecond line.";
    assert.deepEqual(splitSentences(text).map((s) => s.text), ["First one.", "Second one!", "Third?", "4 is a number.", "Second line."]);
  });

  it("does not split inside decimals, abbreviations or lower-case continuations", () => {
    assert.deepEqual(splitSentences("Keep 3.5 days of data, e.g. daily exports. Done.").map((s) => s.text), ["Keep 3.5 days of data, e.g. daily exports.", "Done."]);
    assert.equal(splitSentences("Use v1.2 for now, then switch.").length, 1);
  });

  it("returns nothing for empty text", () => {
    assert.deepEqual(splitSentences(""), []);
  });
});

describe("sentencesTouching", () => {
  const text = "Alpha one. Beta two.\nGamma three.";
  const sentences = splitSentences(text);

  it("selects the sentences a span overlaps", () => {
    const i = text.indexOf("two");
    assert.deepEqual(sentencesTouching(sentences, [{ start: i, end: i + 3 }]).map((s) => s.text), ["Beta two."]);
  });

  it("selects every sentence for audit mode", () => {
    assert.equal(sentencesTouching(sentences, "all").length, 3);
  });

  it("selects both neighbours for a deletion gap that straddles a sentence boundary", () => {
    const a = text.indexOf("one.") + 4; // end of "Alpha one."
    const b = text.indexOf("Beta");
    assert.deepEqual(sentencesTouching(sentences, [{ start: a, end: b }]).map((s) => s.text), ["Alpha one.", "Beta two."]);
  });

  it("selects nothing for no spans", () => {
    assert.deepEqual(sentencesTouching(sentences, []), []);
  });
});
