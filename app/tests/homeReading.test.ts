import assert from "node:assert/strict";
import { test } from "node:test";
import { homeRecents, relativeDay } from "../src/ui/homeReading.ts";
const book = (id: string, at: string | null, extra = {}) => ({ id, title: id, imported_at: at, listened_at: null, damaged: false, ...extra });
// RE-HOME-001: recent content is derived, never persisted or synthesized as history.
test("empty sources produce a true empty state", () => {
  assert.deepEqual(homeRecents([], { text: " \n ", at: 3 }, []), []);
});
test("books, current paste and captures share chronological order and a five-item limit", () => {
  const books = [book("older", "2026-10-17"), book("heard", "2026-10-16", { listened_at: "2026-10-19" })];
  const at = Date.parse("2026-10-19T01:00:00Z");
  const recent = homeRecents(books, { text: "A draft", at }, Array.from({ length: 4 }, (_, i) => ({ at: at + i + 1, text: `capture ${i}` })));
  assert.deepEqual(recent.map(item => item.kind), ["external", "external", "external", "external", "paste"]);
  assert.equal(recent[0].at, at + 4);
});
test("book listening time wins over import time and damaged books cannot be opened", () => {
  const a = book("heard", "2026-10-16", { listened_at: "2026-10-19" });
  const b = book("imported", "2026-10-18");
  const input = [b, book("damaged", "2026-10-20", { damaged: true }), a];
  const result = homeRecents(input, null, []);
  assert.deepEqual(result.map(item => item.id), ["book:heard", "book:imported"]);
  assert.deepEqual(input.map(b => b.id), ["imported", "damaged", "heard"]);
});
test("capture references preserve translation, voice and original for the existing reader", () => {
  const capture = { at: 50, text: "Hello", original: "Xin chào", target: "en", voiceId: "voice" };
  const result = homeRecents([], null, [capture]);
  assert.equal(result[0].kind, "external");
  assert.equal(result[0].source, capture);
  assert.equal(capture.original, "Xin chào");
});
test("blank captures and invalid dates do not pollute or break recent content", () => {
  const result = homeRecents([book("undated", "bad")], null, [{ at: 2, text: "   " }, { at: 3, text: "Hello" }]);
  assert.deepEqual(result.map(item => item.id), ["external:3", "book:undated"]);
});

// RE-HOME-002: one line per recent item, its day said plainly.
test("recent dates read as today, yesterday, days ago, then the date", () => {
  const labels = { today: "Hôm nay", yesterday: "Hôm qua", daysAgo: (n: number) => `${n} ngày trước` };
  const now = new Date(2026, 9, 20, 15, 0).getTime();
  assert.match(relativeDay(new Date(2026, 9, 20, 9, 57).getTime(), now, "vi-VN", labels), /^Hôm nay 09:57$/);
  assert.equal(relativeDay(new Date(2026, 9, 19, 23, 0).getTime(), now, "vi-VN", labels), "Hôm qua");
  assert.equal(relativeDay(new Date(2026, 9, 17, 8, 0).getTime(), now, "vi-VN", labels), "3 ngày trước");
  assert.match(relativeDay(new Date(2026, 8, 23).getTime(), now, "vi-VN", labels), /23/);
});
