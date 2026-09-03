import test from "node:test";
import assert from "node:assert/strict";
import { fold, matchesQuery, orderShelfItems } from "../src/ui/shelfFilter.ts";

const item = (title: string, status: "linked" | "importable" | "encrypted" | "too_large" | "missing", highlights = 0) =>
  ({ title, status, highlights });

test("accents do not matter when searching", () => {
  assert.equal(fold("Thiên Nga Đen"), "thien nga den");
  assert.ok(matchesQuery(item("Thiên Nga Đen", "importable"), "thien nga"));
  assert.ok(matchesQuery(item("Đừng bắt tôi phải suy nghĩ!", "linked"), "dung bat"));
  assert.ok(!matchesQuery(item("Thiên Nga Đen", "importable"), "trắng"));
});

test("status words narrow the shelf without a separate control", () => {
  assert.ok(matchesQuery(item("The Daily Stoic", "encrypted"), "drm"));
  assert.ok(matchesQuery(item("101 Essays", "importable", 1), "ghi chú"));
  assert.ok(!matchesQuery(item("101 Essays", "importable", 0), "ghi chú"));
  assert.ok(matchesQuery(item("Anything", "linked"), ""));
});

test("the most useful books come first", () => {
  const ordered = orderShelfItems([
    item("z linked quiet", "linked"),
    item("y blocked", "too_large", 3),
    item("x linked with notes", "linked", 2),
    item("w importable quiet", "importable"),
    item("v importable with notes", "importable", 5),
  ]);
  assert.deepEqual(ordered.map((b) => b.title[0]), ["v", "w", "x", "z", "y"]);
});
