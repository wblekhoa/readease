import test from "node:test";
import assert from "node:assert/strict";
import { orderShelf } from "../src/ui/libraryOrder.ts";

const book = (id: string, reading: boolean, imported: string | null, listened: string | null = null) => ({
  id, segment_id: reading ? "seg" : null, imported_at: imported, listened_at: listened,
});

test("books being read come first, newest import next", () => {
  const ordered = orderShelf([
    book("old", false, "2026-08-01"),
    book("reading-old", true, "2026-07-01"),
    book("new", false, "2026-09-01"),
    book("reading-new", true, "2026-08-15"),
  ]);
  assert.deepEqual(ordered.map((b) => b.id), ["reading-new", "reading-old", "new", "old"]);
});

test("a missing import date sorts last within its group and never throws", () => {
  const ordered = orderShelf([book("undated", false, null), book("dated", false, "2026-01-01")]);
  assert.deepEqual(ordered.map((b) => b.id), ["dated", "undated"]);
});

test("the input is not mutated", () => {
  const input = [book("b", false, "2026-01-02"), book("a", false, "2026-01-03")];
  orderShelf(input);
  assert.deepEqual(input.map((b) => b.id), ["b", "a"]);
});

test("among the books being read, the one heard most recently leads, whatever its import date", () => {
  const ordered = orderShelf([
    book("heard-last-week", true, "2026-09-10", "2026-09-16 08:00:00"),
    book("imported-old-heard-now", true, "2026-07-01", "2026-09-23 09:30:00"),
    book("never-started", false, "2026-09-22"),
    book("heard-yesterday", true, "2026-09-20", "2026-09-22 21:10:00"),
  ]);
  assert.deepEqual(ordered.map((b) => b.id),
    ["imported-old-heard-now", "heard-yesterday", "heard-last-week", "never-started"]);
});

test("a book being read with no time heard falls behind the ones heard, by import", () => {
  const ordered = orderShelf([
    book("no-ear-new", true, "2026-09-20"),
    book("heard", true, "2026-01-01", "2026-09-01 10:00:00"),
    book("no-ear-old", true, "2026-08-01"),
  ]);
  assert.deepEqual(ordered.map((b) => b.id), ["heard", "no-ear-new", "no-ear-old"]);
});
