import { test } from "node:test";
import assert from "node:assert/strict";
import { announcement } from "../src/ui/announce.ts";
import { IDLE, playback } from "../src/ui/playback.ts";

const after = (state: typeof IDLE, ...events: Parameters<typeof playback>[1][]) =>
  events.reduce((value, event) => playback(value, event), state);

test("the three things a listener has to hear, and nothing else", () => {
  const asking = playback(IDLE, { type: "start" });
  assert.equal(announcement(IDLE, asking), "a11y.preparing");
  const speaking = playback(asking, { type: "voice" });
  assert.equal(announcement(asking, speaking), "a11y.reading");
  const paused = playback(speaking, { type: "toggle" });
  assert.equal(announcement(speaking, paused), "a11y.paused");
  assert.equal(announcement(paused, playback(paused, { type: "toggle" })), "a11y.resumed");
  assert.equal(announcement(speaking, playback(speaking, { type: "stop" })), "a11y.stopped");
  assert.equal(announcement(speaking, playback(speaking, { type: "done" })), "a11y.stopped");
});

test("silence where a live region would only nag", () => {
  const speaking = after(IDLE, { type: "start" }, { type: "voice" });
  // The same state again: a position marker moved, nothing was said.
  assert.equal(announcement(speaking, speaking), null);
  // Idle to idle - a stop that arrived twice.
  assert.equal(announcement(IDLE, IDLE), null);
});

test("a failure says nothing here; the alert notice owns it", () => {
  const speaking = after(IDLE, { type: "start" }, { type: "voice" });
  const failed = playback(speaking, { type: "failed", error: "voice_unavailable: budget" });
  // The state went idle, so the region says it stopped - the sentence about
  // WHY is the alert's, not this one's.
  assert.equal(announcement(speaking, failed), "a11y.stopped");
});
