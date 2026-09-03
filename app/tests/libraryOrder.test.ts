import test from "node:test";
import assert from "node:assert/strict";
import { orderShelf } from "../src/ui/libraryOrder.ts";

const book = (id: string, reading: boolean, imported: string | null) => ({
  id, segment_id: reading ? "seg" : null, imported_at: imported,
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
