import test from "node:test";
import assert from "node:assert/strict";
import { buttonCost, costPhrase, formatCount, formatUsd, isPaidVoice, providerOf, PROVIDERS, SCOPES, type Estimate } from "../src/ui/readingCost.ts";

const paid = (usd: number, over: Partial<Estimate & { paid: true }> = {}): Estimate => ({
  paid: true, provider: "elevenlabs", model: "eleven_flash_v2_5", chars: 1000,
  utterances: 3, chapters: 1, usd, units: 1000, unit: "credits",
  billing: "counted", price_dated: "2026-09-04", ...over,
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

test("a counted voice with a scope may promise a ceiling", () => {
  // The figure covers every way of starting a reading inside the scope, so
  // "tối đa" is true of it (owner, 04/09).
  assert.equal(costPhrase(paid(0.18)), "at_most");
});

test("pasted text on a counted voice is neither a ceiling nor a guess", () => {
  // No chapters and no click-to-read: the whole of it gets read, so the
  // figure is the figure and hedging it would overstate the doubt.
  assert.equal(costPhrase(paid(0.18, { chapters: 0 })), "exact");
});

test("a voice billed on something the text cannot be counted into only ever approximates", () => {
  // OpenAI bills tokens of generated audio. No ceiling can be promised over
  // that, and the scope does not change it: an estimate over one pasted
  // paragraph is still an estimate.
  const openai = { billing: "estimated" as const, unit: "tokens" as const, units: 0 };
  assert.equal(costPhrase(paid(0.24, openai)), "about");
  assert.equal(costPhrase(paid(0.24, { ...openai, chapters: 0 })), "about");
});

test("nothing is promised about a voice that costs nothing, or about no figure at all", () => {
  assert.equal(costPhrase(null), null);
  assert.equal(costPhrase({ paid: false, chars: 900, utterances: 2, chapters: 1 }), null);
});

test("counts read the way Vietnamese writes them", () => {
  assert.equal(formatCount(12400), "12.400");
});

test("the scopes offered start narrow and end at the whole book", () => {
  assert.deepEqual([...SCOPES], [1, 2, 5, null]);
});

test("a voice says which provider it belongs to, or that it belongs to none", () => {
  assert.equal(providerOf("openai:tts-1:alloy"), "openai");
  assert.equal(providerOf("elevenlabs:eleven_v3:rachel"), "elevenlabs");
  assert.equal(providerOf("Minh Đức"), null);
  // A three-part id from somewhere we do not know is not ours to route.
  assert.equal(providerOf("someone:some:thing"), null);
});

test("each provider names the settings key its credential lives under", () => {
  assert.deepEqual(
    PROVIDERS.map((provider) => provider.settingsKey),
    ["openai_api_key", "elevenlabs_api_key"],
  );
});
