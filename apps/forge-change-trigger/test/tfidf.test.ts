import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { cosine, idfFor, stem, templateTokens, vectorize } from "../src/core";

describe("stem", () => {
  it("maps inflections to the same token", () => {
    assert.equal(stem("acknowledge"), stem("acknowledged"));
    assert.equal(stem("retain"), stem("retained"));
    assert.equal(stem("log"), stem("logs"));
    assert.equal(stem("minute"), stem("minutes"));
    assert.equal(stem("day"), stem("days"));
    assert.equal(stem("require"), stem("required"));
  });
});

describe("templateTokens", () => {
  it("masks numbers, so sentences that differ only in a number have identical templates", () => {
    assert.deepEqual(templateTokens("Application logs must be retained for 90 days."), templateTokens("Application logs must be retained for 30 days."));
  });
  it("drops negations, so a polarity flip does not hide a pair", () => {
    assert.deepEqual(templateTokens("A VPN connection is required."), templateTokens("A VPN connection is not required."));
  });
  it("drops function words, modals and one-letter tokens", () => {
    assert.deepEqual(templateTokens("The user must be able to log in."), ["user", stem("able"), "log"]);
  });
});

describe("cosine", () => {
  const corpus = [["alpha", "beta"], ["alpha", "gamma"], ["delta"]];
  const idf = idfFor(corpus);
  it("is 1 for identical vectors and 0 for disjoint ones", () => {
    const a = vectorize(["alpha", "beta"], idf);
    assert.ok(Math.abs(cosine(a, a) - 1) < 1e-12);
    assert.equal(cosine(a, vectorize(["delta"], idf)), 0);
  });
  it("is symmetric", () => {
    const a = vectorize(["alpha", "beta"], idf);
    const b = vectorize(["alpha", "gamma"], idf);
    assert.ok(Math.abs(cosine(a, b) - cosine(b, a)) < 1e-12);
    assert.ok(cosine(a, b) > 0 && cosine(a, b) < 1);
  });
  it("is 0 for an empty vector", () => {
    assert.equal(cosine(vectorize([], idf), vectorize(["alpha"], idf)), 0);
  });
  it("weights rare terms more than common ones", () => {
    const rare = idf.get("beta")!;
    const common = idf.get("alpha")!;
    assert.ok(rare > common);
  });
});
