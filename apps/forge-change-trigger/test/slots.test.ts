import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  antonymMismatches,
  extractQuantities,
  isNegated,
  negations,
  numericMismatches,
  scopeRelation,
  scopeWords,
} from "../src/core";

const q = (s: string) => extractQuantities(s);

describe("extractQuantities", () => {
  it("finds a number with a unit, with offsets into the sentence", () => {
    const s = "Application logs must be retained for 90 days.";
    const [x] = q(s);
    assert.ok(x);
    assert.equal(x.text, "90 days");
    assert.equal(s.slice(x.start, x.end), "90 days");
    assert.equal(x.slot, "duration");
    assert.equal(x.value, 90 * 86_400);
  });

  it("normalizes time units, so equal durations compare equal", () => {
    assert.equal(q("kept 90 days")[0]!.value, q("kept 3 months")[0]!.value);
    assert.equal(q("kept 24 hours")[0]!.value, q("kept 1 day")[0]!.value);
    assert.equal(q("kept 2 weeks")[0]!.value, q("kept 14 days")[0]!.value);
    assert.notEqual(q("kept 1 year")[0]!.value, q("kept 12 months")[0]!.value, "the canonical values differ: a 30-day month is not a 365-day year");
  });

  it("marks months and years as approximate and nothing else", () => {
    assert.equal(q("kept 3 months")[0]!.approx, true);
    assert.equal(q("kept 1 year")[0]!.approx, true);
    assert.equal(q("kept 90 days")[0]!.approx, undefined);
    assert.equal(q("kept 2 weeks")[0]!.approx, undefined);
  });

  it("keeps business days apart from calendar days", () => {
    assert.equal(q("within 5 business days")[0]!.slot, "business-days");
    assert.equal(q("within 5 working days")[0]!.slot, "business-days");
    assert.equal(q("within 5 days")[0]!.slot, "duration");
  });

  it("normalizes sizes and percentages, and counts other nouns by stem", () => {
    assert.equal(q("max 1 GB")[0]!.value, q("max 1024 MB")[0]!.value);
    assert.equal(q("99.9% uptime")[0]!.slot, "percent");
    assert.equal(q("at most 3 attempts")[0]!.slot, "count:attempt");
    assert.equal(q("at most 3 attempt")[0]!.slot, "count:attempt");
  });

  it("parses thousands separators and decimals", () => {
    assert.equal(q("up to 1,000 users")[0]!.value, 1000);
    assert.equal(q("every 1.5 hours")[0]!.value, 1.5 * 3600);
  });

  it("ignores bare numbers, years, and numbers followed by function words", () => {
    assert.deepEqual(q("Version 2 shipped in 2026."), []);
    assert.deepEqual(q("Step 3 and 4 or 5."), []);
    assert.deepEqual(q("a 5 th item"), []);
  });
});

describe("numericMismatches", () => {
  it("reports a slot when each side has a value the other lacks", () => {
    const m = numericMismatches(q("kept 30 days"), q("kept 90 days"));
    assert.equal(m.length, 1);
    assert.equal(m[0]!.changed.text, "30 days");
    assert.equal(m[0]!.approved.text, "90 days");
  });

  it("does not report agreement, equal values in other units, or a merely extra figure", () => {
    assert.deepEqual(numericMismatches(q("kept 90 days"), q("kept 90 days")), []);
    assert.deepEqual(numericMismatches(q("kept 3 months"), q("kept 90 days")), []);
    assert.deepEqual(numericMismatches(q("kept 90 days and 365 days"), q("kept 90 days")), []);
  });

  it("does not compare different slots", () => {
    assert.deepEqual(numericMismatches(q("kept 30 days"), q("limit 30 attempts")), []);
  });
});

describe("negation and polarity", () => {
  it("detects negation words and contractions, with offsets", () => {
    assert.deepEqual(negations("A VPN is not required.").map((h) => h.word), ["not"]);
    assert.deepEqual(negations("It doesn't help and can't be used.").map((h) => h.word), ["doesn't", "can't"]);
    assert.equal(isNegated("Access is never allowed."), true);
    assert.equal(isNegated("Access is allowed."), false);
  });

  it("treats two negations as positive, a documented simplification", () => {
    assert.equal(isNegated("It is not unusual and not rare."), false);
  });
});

describe("numericMismatches: calendar units", () => {
  const mismatch = (a: string, b: string) => numericMismatches(q(a), q(b)).length;

  it("treats 12 months as 1 year, 24 months as 2 years, 3 months as 90 days and 365 days as 12 months", () => {
    assert.equal(mismatch("kept 12 months", "kept 1 year"), 0);
    assert.equal(mismatch("kept 24 months", "kept 2 years"), 0);
    assert.equal(mismatch("kept 3 months", "kept 90 days"), 0);
    assert.equal(mismatch("kept 365 days", "kept 12 months"), 0);
  });

  it("still reports a real difference involving a calendar unit", () => {
    assert.equal(mismatch("kept 11 months", "kept 1 year"), 1, "8 % apart");
    assert.equal(mismatch("kept 6 months", "kept 90 days"), 1);
    assert.equal(mismatch("kept 1 month", "kept 28 days"), 1, "7 % apart");
  });

  it("keeps fixed units exact, however close", () => {
    assert.equal(mismatch("kept 7 days", "kept 1 week"), 0);
    assert.equal(mismatch("kept 6 days", "kept 1 week"), 1);
    assert.equal(mismatch("kept 364 days", "kept 365 days"), 1);
  });
});

describe("antonymMismatches", () => {
  it("catches a lower bound turned into an upper bound", () => {
    const m = antonymMismatches("Passwords can be at most 12 characters.", "Passwords must be at least 12 characters.");
    assert.equal(m.length, 1);
    assert.equal(m[0]!.group, "at least / at most");
    assert.equal(m[0]!.changed.word, "at most");
    assert.equal(m[0]!.approved.word, "at least");
  });

  it("finds opposite poles with neither side using both", () => {
    const m = antonymMismatches("MFA is optional for staff.", "MFA is required for staff.");
    assert.equal(m.length, 1);
    assert.equal(m[0]!.changed.word, "optional");
    assert.equal(m[0]!.approved.word, "required");
  });
  it("finds nothing when both sides agree or one side uses both poles", () => {
    assert.deepEqual(antonymMismatches("MFA is required.", "MFA is required."), []);
    assert.deepEqual(antonymMismatches("MFA is required or optional.", "MFA is required."), []);
    assert.deepEqual(antonymMismatches("Passwords must have at least 8 characters.", "Passwords must have at least 12 characters."), []);
  });
});

describe("scopeRelation", () => {
  it("canonicalizes environment words", () => {
    assert.deepEqual([...scopeWords("Prod and Staging and UAT and dev")].sort(), ["development", "production", "staging"]);
  });
  it("classifies the four cases", () => {
    assert.equal(scopeRelation("Logs are kept.", "Logs must be kept."), "same");
    assert.equal(scopeRelation("Staging logs are kept.", "Staging logs must be kept."), "same");
    assert.equal(scopeRelation("Staging logs are kept.", "Production logs must be kept."), "different");
    assert.equal(scopeRelation("Logs are kept.", "Staging logs must be kept."), "approved-narrower");
    assert.equal(scopeRelation("Staging logs are kept.", "Logs must be kept."), "changed-narrower");
  });
});
