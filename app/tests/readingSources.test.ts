import assert from "node:assert/strict";
import { test } from "node:test";

import {
  anythingReadable,
  firstRunNeeded,
  initialReadingLanguage,
  languageHint,
  languageOfVoice,
  offeredFor,
  readable,
  voiceForTab,
  voicesFor,
  type ModelStatus,
} from "../src/ui/readingSources.ts";
import type { Voice } from "../src/ui/voiceShortlist.ts";

const ADAM: Voice = { id: "Adam", label: "Adam — Nam · Nam · Giọng đọc tự nhiên", languages: ["vi"] };
const LY: Voice = { id: "Trúc Ly", label: "Trúc Ly — Nữ · Bắc · Phong cách tự nhiên", languages: ["vi"] };
const HEART: Voice = { id: "af_heart", label: "Heart — Nữ · Mỹ", languages: ["en"] };
const MICHAEL: Voice = { id: "am_michael", label: "Michael — Nam · Mỹ", languages: ["en"] };
const ALLOY: Voice = { id: "openai:gpt-4o-mini-tts:alloy", label: "Alloy", languages: [] };
const NHU: Voice = { id: "elevenlabs:eleven_v3:nhu", label: "Nhu · ElevenLabs", languages: ["vi"] };
const ALL = [ADAM, LY, HEART, MICHAEL, ALLOY, NHU];

const BOTH: ModelStatus = {
  ready: true, precision: "fp32", installed: { fp32: 1 },
  english: { ready: true, installed: 1, download_bytes: 1 },
};

test("a language's voices are its own model's and the paid ones that fit", () => {
  assert.deepEqual(voicesFor(ALL, "vi").map((v) => v.id), ["Adam", "Trúc Ly", ALLOY.id, NHU.id]);
  assert.deepEqual(voicesFor(ALL, "en").map((v) => v.id), ["af_heart", "am_michael", ALLOY.id]);
});

test("a tab offers the marked voices that fit, the one in use included", () => {
  assert.deepEqual(
    offeredFor(ALL, ["Trúc Ly", "af_heart"], "Adam", "vi").map((v) => v.id),
    ["Adam", "Trúc Ly"],
  );
});

test("a tab with no marked voice that fits offers every voice that fits", () => {
  // The starting five are Vietnamese: a fresh English download must not
  // open on an empty select.
  assert.deepEqual(
    offeredFor(ALL, ["Adam", "Trúc Ly"], "Adam", "en").map((v) => v.id),
    ["af_heart", "am_michael", ALLOY.id],
  );
});

test("switching to a language brings back its last voice, else a local one, else any", () => {
  const english = offeredFor(ALL, [], "Adam", "en");
  assert.equal(voiceForTab("am_michael", english), "am_michael");
  assert.equal(voiceForTab("Trúc Ly", english), "af_heart");
  assert.equal(voiceForTab(null, english), "af_heart");
  assert.equal(voiceForTab(null, [ALLOY]), ALLOY.id);
  assert.equal(voiceForTab("af_heart", []), null);
});

test("a voice's language is the one it names, and only when it names one", () => {
  assert.equal(languageOfVoice(ADAM), "vi");
  assert.equal(languageOfVoice(HEART), "en");
  assert.equal(languageOfVoice(ALLOY), null);
  assert.equal(languageOfVoice({ languages: ["vi", "en"] }), null);
  assert.equal(languageOfVoice(undefined), null);
});

test("the tab opens on what was stored, else the voice's language, else the interface's", () => {
  assert.equal(initialReadingLanguage("en", ADAM, "vi"), "en");
  assert.equal(initialReadingLanguage("nonsense", HEART, "vi"), "en");
  assert.equal(initialReadingLanguage(null, ALLOY, "en"), "en");
  assert.equal(initialReadingLanguage(undefined, undefined, "vi"), "vi");
});

test("what can read a language: its model, or a paid voice that fits", () => {
  assert.deepEqual(readable("vi", BOTH, [ADAM], {}), { local: true, api: 0, keyed: false });
  const englishOnly: ModelStatus = { ...BOTH, ready: false, installed: {} };
  assert.deepEqual(readable("vi", englishOnly, [HEART], { openai: true }), { local: false, api: 0, keyed: true });
  assert.deepEqual(readable("vi", englishOnly, [HEART, ALLOY], { openai: true }), { local: false, api: 1, keyed: true });
  assert.equal(anythingReadable(englishOnly, [HEART], {}), true);
  assert.equal(anythingReadable({ ready: false, precision: null, installed: {} }, [], {}), false);
  assert.equal(anythingReadable(null, [ALLOY], { openai: true }), true);
});

test("the first-run screen is due only while nothing at all can read", () => {
  const nothing: ModelStatus = { ready: false, precision: null, installed: {} };
  assert.equal(firstRunNeeded(nothing, {}), true);
  assert.equal(firstRunNeeded(nothing, { openai: false }), true);
  // A key counts before its voices are listed.
  assert.equal(firstRunNeeded(nothing, { openai: true }), false);
  assert.equal(firstRunNeeded({ ...nothing, english: { ready: true, installed: 1, download_bytes: 1 } }, {}), false);
  assert.equal(firstRunNeeded(BOTH, {}), false);
  // No answer from the engine at all: not a reason to hold the door.
  assert.equal(firstRunNeeded(null, {}), true);
});

test("the hint: a voice on text it was not made for, and what to do about it", () => {
  // The voice fits: nothing to say.
  assert.equal(languageHint("vi", ADAM, [HEART]), null);
  // A paid voice that names nothing reads both: nothing to say.
  assert.equal(languageHint("en", ALLOY, []), null);
  // The Vietnamese voice on an English chapter, with an English voice to hand.
  assert.deepEqual(languageHint("en", ADAM, [HEART]), { content: "en", kind: "switch" });
  // ... and with none: the download is the way.
  assert.deepEqual(languageHint("en", ADAM, []), { content: "en", kind: "get" });
  // The other way round.
  assert.deepEqual(languageHint("vi", HEART, [ADAM]), { content: "vi", kind: "switch" });
  // No voice at all, on a known language.
  assert.deepEqual(languageHint("vi", undefined, []), { content: "vi", kind: "get" });
  // No language known: nothing to hint from.
  assert.equal(languageHint(null, ADAM, [HEART]), null);
});
