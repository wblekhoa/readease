import test from "node:test";
import assert from "node:assert/strict";
import { buttonCost, formatCount, formatUsd, isPaidVoice, SCOPES, type Estimate } from "../src/ui/readingCost.ts";

const paid = (usd: number): Estimate => ({
  paid: true, provider: "openai", model: "tts-1", chars: 1000, utterances: 3,
  chapters: 1, usd, units: 1000, unit: "characters", price_dated: "2026-09-04",
});

test("a paid voice is the one with a provider and a model in its name", () => {
  assert.equal(isPaidVoice("openai:tts-1:alloy"), true);
  assert.equal(isPaidVoice("Minh Đức"), false);
  // A local voice could have a colon in its name; only three parts means paid.
  assert.equal(isPaidVoice("someone:else"), false);
});

test("under a cent says so instead of rounding to nothing", () => {
  // Being told $0.00 and then charged is being misled, however small the sum.
  assert.equal(formatUsd(0.004), "<$0,01");
  assert.equal(formatUsd(0.18), "$0,18");
  assert.equal(formatUsd(1.2), "$1,20");
  assert.equal(formatUsd(0), "$0");
});

test("the button carries the money and nothing else", () => {
  assert.equal(buttonCost(paid(0.18)), "$0,18");
  // Still measuring: nothing to say yet, and the button is disabled anyway.
  assert.equal(buttonCost(null), "");
  // The local model is free, so the button reads exactly as it always did.
  assert.equal(buttonCost({ paid: false, chars: 900, utterances: 2, chapters: 1 }), "");
});

test("counts read the way Vietnamese writes them", () => {
  assert.equal(formatCount(12400), "12.400");
});

test("the scopes offered start narrow and end at the whole book", () => {
  assert.deepEqual([...SCOPES], [1, 2, 5, null]);
});
