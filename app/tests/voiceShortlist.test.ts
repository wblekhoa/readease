import { strict as assert } from "node:assert";
import { test } from "node:test";
import {
  initialShortlist, matchesVoice, matchesVoiceFilters, offeredVoices, parseShortlist, serializeShortlist,
  speaksVietnamese, STARTING_VOICES, tidyName, toggleShortlist, voiceDescription, voiceName,
  voiceGender,
} from "../src/ui/voiceShortlist.ts";

const CATALOGUE = [
  { id: "a", label: "Trúc Ly - Nữ · Bắc · Phong cách tự nhiên" },
  { id: "b", label: "Thái Sơn - Nam · Nam · Phong cách kể chuyện" },
  { id: "c", label: "Mai Anh - Nữ · Bắc · Phong cách tin tức" },
];

test("a label splits into the name and what the voice is like", () => {
  assert.equal(voiceName(CATALOGUE[0].label), "Trúc Ly");
  assert.equal(voiceDescription(CATALOGUE[0].label), "Nữ · Bắc · Phong cách tự nhiên");
  assert.equal(voiceDescription("Adam"), undefined);
  assert.equal(voiceName(undefined), "");
});

test("an unreadable stored list is an empty list, not a crash", () => {
  assert.deepEqual(parseShortlist(null), []);
  assert.deepEqual(parseShortlist("not json"), []);
  assert.deepEqual(parseShortlist('{"a":1}'), []);
  assert.deepEqual(parseShortlist('["a",2,"b"]'), ["a", "b"]);
  assert.deepEqual(parseShortlist(serializeShortlist(["a", "b"])), ["a", "b"]);
});

test("toggling adds and removes", () => {
  assert.deepEqual(toggleShortlist([], "a"), ["a"]);
  assert.deepEqual(toggleShortlist(["a", "b"], "a"), ["b"]);
});

test("what is offered keeps the catalogue's order", () => {
  assert.deepEqual(offeredVoices(CATALOGUE, ["c", "a"], "a").map((v) => v.id), ["a", "c"]);
});

test("the voice being used is offered even when it is not marked", () => {
  assert.deepEqual(offeredVoices(CATALOGUE, ["c"], "b").map((v) => v.id), ["b", "c"]);
});

test("nothing marked offers only the voice in use", () => {
  assert.deepEqual(offeredVoices(CATALOGUE, [], "b").map((v) => v.id), ["b"]);
});

const SHIPPED = STARTING_VOICES.map((id) => ({ id, label: `${id} - Nữ · Bắc` }))
  .concat([{ id: "Kim Thanh", label: "Kim Thanh - Nữ · Nam" }]);

test("chưa từng chọn thì bật sẵn năm giọng mở đầu", () => {
  assert.deepEqual(initialShortlist(null, SHIPPED), [...STARTING_VOICES]);
  assert.deepEqual(initialShortlist(undefined, SHIPPED), [...STARTING_VOICES]);
  assert.deepEqual(initialShortlist("", SHIPPED), [...STARTING_VOICES]);
});

test("giọng mở đầu mà bản dựng này không có thì bỏ, không mời", () => {
  assert.deepEqual(initialShortlist(null, [{ id: "Adam", label: "Adam" }]), ["Adam"]);
});

test("đã tự tắt hết thì tôn trọng, không mồi lại", () => {
  assert.deepEqual(initialShortlist("[]", SHIPPED), []);
  assert.deepEqual(initialShortlist('["Kim Thanh"]', SHIPPED), ["Kim Thanh"]);
});


/* A search that cannot find "Hùng" when you type "hung" is a search nobody
 * uses, and a name carrying the timestamp it was cloned at is filing, not a
 * name. Both showed up the moment an ElevenLabs account with forty-five
 * voices reached the panel (owner, 05/09). */

test("search ignores tone marks, in both directions", () => {
  const hung = { id: "elevenlabs:m:1", label: "Hùng - Giọng Nam, Miền Bắc · ElevenLabs" };
  assert.ok(matchesVoice(hung, "hung"));
  assert.ok(matchesVoice(hung, "Hùng"));
  assert.ok(matchesVoice(hung, "mien bac"));
  assert.ok(!matchesVoice(hung, "nữ"));
});

test("đ is folded too - it carries no combining mark", () => {
  const voice = { id: "v", label: "Đức Anh - kể chuyện" };
  assert.ok(matchesVoice(voice, "duc anh"));
  assert.ok(matchesVoice(voice, "ĐỨC"));
});

test("every word must match, so two words narrow the list", () => {
  const voice = { id: "v", label: "Minh Trung - Authentic Southern Vietnamese Male Voice" };
  assert.ok(matchesVoice(voice, "minh vietnamese"));
  assert.ok(!matchesVoice(voice, "minh northern"));
});

test("an empty query is not a filter", () => {
  assert.ok(matchesVoice({ id: "v", label: "Alloy · OpenAI" }, ""));
  assert.ok(matchesVoice({ id: "v", label: "Alloy · OpenAI" }, "   "));
});

test("a cloned voice loses the date it was saved with, and nothing else", () => {
  assert.equal(tidyName("JM – Husky & Engaging (2025-01-25_1100)"), "JM – Husky & Engaging");
  // Not a date: this is what the voice is.
  assert.equal(tidyName("Rob - Natural Authority (Real Time AI Voice)"), "Rob");
  assert.equal(tidyName("Hùng - Giọng Nam, Miền Bắc"), "Hùng");
});

/* A badge is a claim somebody made. Absence is "nobody checked", never "no". */

test("a voice the provider verified in Vietnamese says so, whatever the region tag", () => {
  assert.ok(speaksVietnamese({ languages: ["vi"] }));
  assert.ok(speaksVietnamese({ languages: ["en", "VI-VN"] }));
});

test("no verification, no claim - including the local model and OpenAI", () => {
  assert.ok(!speaksVietnamese({ languages: [] }));
  assert.ok(!speaksVietnamese({}));
  // The primary subtag decides, so an odd region tag is still Vietnamese.
  assert.ok(speaksVietnamese({ languages: ["en", "vi-fake"] }));
  assert.ok(!speaksVietnamese({ languages: ["en-us", "fr"] }));
});

test("gender uses explicit provider metadata and the structured local label only", () => {
  assert.equal(voiceGender({ id: "local-m", label: "Minh Đức - Nam · Bắc" }), "male");
  assert.equal(voiceGender({ id: "local-f", label: "Trúc Ly - Nữ · Bắc" }), "female");
  assert.equal(voiceGender({ id: "elevenlabs:model:id", label: "A", gender: "female" }, false), "female");
  assert.equal(voiceGender({ id: "openai:tts-1:nova", label: "Nova · OpenAI" }, false), null);
  assert.equal(voiceGender({ id: "elevenlabs:model:id", label: "Nam - Nam · provider description" }, false), null);
});

test("provider, gender and search filters combine instead of replacing each other", () => {
  const voices = [
    { id: "local-m", label: "Minh Đức - Nam · Bắc" },
    { id: "local-f", label: "Trúc Ly - Nữ · Bắc" },
    { id: "openai:tts-1:nova", label: "Nova · OpenAI" },
    { id: "elevenlabs:model:nhu", label: "Nhu · ElevenLabs", gender: "female" as const },
  ];
  const source = (id: string) => id.includes(":") ? id.split(":")[0] : "local";

  assert.deepEqual(
    voices.filter((voice) => matchesVoiceFilters(voice, "", source(voice.id), "local", "female")).map((voice) => voice.id),
    ["local-f"],
  );
  assert.deepEqual(
    voices.filter((voice) => matchesVoiceFilters(voice, "nhu", source(voice.id), "elevenlabs", "female")).map((voice) => voice.id),
    ["elevenlabs:model:nhu"],
  );
  assert.deepEqual(
    voices.filter((voice) => matchesVoiceFilters(voice, "", source(voice.id), "all", "male")).map((voice) => voice.id),
    ["local-m"],
  );
});
