import assert from "node:assert/strict";
import { test } from "node:test";
import { IDLE, playback, type Playback } from "../src/ui/playback.ts";

function run(events: Parameters<typeof playback>[1][], from: Playback = IDLE) {
  return events.reduce(playback, from);
}

test("stop lands on idle immediately, without waiting for anything", () => {
  const reading = run([{ type: "start" }]);
  assert.equal(reading.reading, "reading");
  assert.equal(reading.warming, true);
  const stopped = playback(reading, { type: "stop" });
  assert.equal(stopped.reading, "idle");
  assert.equal(stopped.warming, false);
});

test("a failure anywhere returns to idle and clears the warming notice", () => {
  const failed = run([{ type: "start" }, { type: "failed", error: "no voice" }]);
  assert.equal(failed.reading, "idle");
  assert.equal(failed.warming, false);
  assert.equal(failed.error, "no voice");
});

test("starting again clears the previous reading's warming and error", () => {
  const after = run([
    { type: "start" },
    { type: "done", error: "engine died" },
    { type: "start" },
  ]);
  assert.equal(after.reading, "reading");
  assert.equal(after.error, null);
  assert.equal(after.warming, true);
});

test("pressing stop five times fast stays idle, it does not toggle", () => {
  const after = run([
    { type: "start" },
    { type: "stop" },
    { type: "stop" },
    { type: "stop" },
    { type: "stop" },
    { type: "stop" },
  ]);
  assert.equal(after.reading, "idle");
});

test("pause toggles both ways and does nothing at all when idle", () => {
  const paused = run([{ type: "start" }, { type: "toggle" }]);
  assert.equal(paused.reading, "paused");
  assert.equal(playback(paused, { type: "toggle" }).reading, "reading");
  assert.deepEqual(playback(IDLE, { type: "toggle" }), IDLE);
});

test("late audio from a stopped reading cannot revive the transport", () => {
  const after = run([{ type: "start" }, { type: "stop" }, { type: "voice" }]);
  assert.equal(after.reading, "idle");
  assert.equal(after.warming, false);
});

test("first audio only clears warming, it never changes the reading", () => {
  const speaking = run([{ type: "start" }, { type: "voice" }]);
  assert.equal(speaking.reading, "reading");
  assert.equal(speaking.warming, false);
});

test("a reading that ends badly reports the error and stops", () => {
  const after = run([{ type: "start" }, { type: "done", error: "boom" }]);
  assert.deepEqual(after, { reading: "idle", warming: false, error: "boom" });
});
