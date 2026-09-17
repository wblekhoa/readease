import test from "node:test";
import assert from "node:assert/strict";
import { MAX_HITS, foldMap, foldQuery, matchRanges, searchBook } from "../src/ui/textSearch.ts";

const BOOK = [
  { id: "c1", title: "Một", segments: [
    { id: "s1", text: "Trải nghiệm người dùng là cảm nhận tổng thể. Trải nghiệm tốt thì nhớ lâu." },
    { id: "s2", text: "Anh Hùng đến muộn." },
  ] },
  { id: "c2", title: "Hai", segments: [
    { id: "s3", text: "Không có gì ở đây." },
  ] },
];

test("typing without diacritics finds the book's own spelling, marked exactly", () => {
  const hits = searchBook(BOOK, "trai nghiem");
  assert.equal(hits.length, 2);
  assert.equal(hits[0].match, "Trải nghiệm");
  assert.equal(hits[0].segmentId, "s1");
  assert.equal(hits[0].chapterTitle, "Một");
  assert.equal(hits[0].before, "");
  assert.ok(hits[0].after.startsWith(" người dùng"));
  assert.equal(hits[1].match, "Trải nghiệm");
  assert.ok(hits[1].before.startsWith("…"));
});

test("the fold keeps every character's origin, đ included", () => {
  const { folded, map } = foldMap("Đến Hùng");
  assert.equal(folded, "den hung");
  assert.deepEqual(map, [0, 1, 2, 3, 4, 5, 6, 7]);
  assert.equal(searchBook(BOOK, "hung")[0].match, "Hùng");
});

test("short or empty queries find nothing, and spaces do not matter", () => {
  assert.equal(foldQuery("  Trải   nghiệm "), "trai nghiem");
  assert.deepEqual(searchBook(BOOK, "t"), []);
  assert.deepEqual(searchBook(BOOK, "   "), []);
});

test("hits stop at the cap", () => {
  const long = { id: "c", title: "Dài", segments: Array.from({ length: 300 }, (_, i) => ({ id: `s${i}`, text: "lặp lại" })) };
  assert.equal(searchBook([long], "lặp").length, MAX_HITS);
});

test("the page marks every match of the query, in order, on the printed text", () => {
  const text = "Tính năng này, và tinh nang kia; TÍNH NĂNG nữa.";
  const ranges = matchRanges(text, "tinh nang");
  assert.deepEqual(ranges.map(([start, end]) => text.slice(start, end)), ["Tính năng", "tinh nang", "TÍNH NĂNG"]);
  assert.deepEqual(matchRanges(text, "t"), []);
  assert.deepEqual(matchRanges("không có gì", "tính năng"), []);
});

test("a hit at the head of a list item drops the item's marker from its snippet", () => {
  const chapters = [{ id: "c", title: "C", segments: [
    { id: "s1", text: "• Thiết kế và phát triển Web." },
    { id: "s2", text: "1. Thiết kế đồ họa." },
    { id: "s3", text: "Không phải danh sách: thiết kế in ấn." },
  ] }];
  const hits = searchBook(chapters, "thiet ke");
  assert.deepEqual(hits.map((hit) => hit.before), ["", "", "Không phải danh sách: "]);
  assert.deepEqual(hits.map((hit) => hit.match), ["Thiết kế", "Thiết kế", "thiết kế"]);
});
