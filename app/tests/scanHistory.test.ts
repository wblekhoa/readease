import { strict as assert } from "node:assert";
import { test } from "node:test";
import { currentPart, isOpen, summarise } from "../src/ui/scanHistory.ts";

test("the passage being read opens itself", () => {
  assert.equal(isOpen(10, 10, {}), true);
  assert.equal(isOpen(9, 10, {}), false);
});

test("a click wins over that, in both directions", () => {
  assert.equal(isOpen(10, 10, { 10: false }), false);
  assert.equal(isOpen(9, 10, { 9: true }), true);
});

test("nothing is being read: entries stay as they were left", () => {
  assert.equal(isOpen(9, null, {}), false);
  assert.equal(isOpen(9, null, { 9: true }), true);
});

test("the marker only lands in the passage the voice is in", () => {
  // Every passage has a part-2. Without this, one reading would paint a
  // marker in every open entry at once.
  assert.equal(currentPart(10, 10, "part-2"), "part-2");
  assert.equal(currentPart(9, 10, "part-2"), null);
});

test("no reading means no marker anywhere", () => {
  assert.equal(currentPart(10, null, "part-2"), null);
  assert.equal(currentPart(10, 10, null), null);
});

test("a summary is one line, and says when it stopped short", () => {
  assert.equal(summarise("  Câu một.\n\nCâu hai.  "), "Câu một. Câu hai.");
  const long = summarise("a".repeat(200));
  assert.equal(long.length, 91);
  assert.ok(long.endsWith("…"));
});
