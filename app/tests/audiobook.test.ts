import { strict as assert } from "node:assert";
import { test } from "node:test";
import { audiobookName, chapterRange, progressFor } from "../src/ui/audiobook.ts";

test("chapter ranges reject invalid or reversed bounds before asking the engine", () => {
  assert.deepEqual(chapterRange(2, 4, 9), { fromChapter: 1, chapters: 3 });
  assert.equal(chapterRange(4, 2, 9), null);
  assert.equal(chapterRange(0, 2, 9), null);
  assert.equal(chapterRange(1, 10, 9), null);
});
test("an audiobook filename cannot introduce a folder or lose its extension", () => {
  assert.equal(audiobookName("A/B: C"), "A B C.m4b");
  assert.equal(audiobookName("  "), "ReadEase.m4b");
});
test("late progress cannot revive a finished job; finalisation is indeterminate", () => {
  assert.deepEqual(progressFor({ kind: "done" }, { done: 9, total: 10 }), { kind: "done" });
  const job = { kind: "running" as const, done: 2, total: 10, title: "Book", startedAt: 42, phase: "synthesising" as const };
  assert.deepEqual(progressFor(job, { done: 10, total: 10, phase: "encoding" }), { ...job, done: 10, phase: "encoding" });
});
