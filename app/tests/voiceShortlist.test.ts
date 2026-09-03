import { strict as assert } from "node:assert";
import { test } from "node:test";
import {
  initialShortlist, offeredVoices, parseShortlist, serializeShortlist,
  STARTING_VOICES, toggleShortlist, voiceDescription, voiceName,
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

