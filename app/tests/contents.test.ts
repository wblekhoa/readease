import test from "node:test";
import assert from "node:assert/strict";
import { contentsRows, currentRow, marker, roman } from "../src/ui/contents.ts";

// An invented book, shaped like the real 4-level trees measured on 23/09:
// front matter, parts holding chapters, sections, subsections, back matter.
const entry = (level: number, title: string, n = title) => ({ level, title, segment_id: n });
const tree = [
  entry(1, "Lời bạt"),
  entry(1, "Phần mở đầu"),
  entry(2, "NHỮNG CÂU HỎI ĐẦU TIÊN"),
  entry(1, "Phần Một: NHỮNG CON ĐƯỜNG"),
  entry(2, "Chương 1 BẾN SÔNG"),
  entry(3, "CON THUYỀN"),
  entry(4, "Mái chèo"),
  entry(4, "Cánh buồm"),
  entry(3, "BỜ CÁT"),
  entry(2, "Chương 2 BỜ BÊN KIA"),
  entry(1, "Phần Hai BẦU TRỜI"),
  entry(2, "Chương 3 MÂY"),
  entry(3, "Phần Bốn KẾT THÚC"),
  entry(3, "MƯA"),
  entry(1, "Phần kết"),
  entry(1, "Lời cảm ơn"),
];

test("chapters keep the book's own numbers, parts get Roman numerals, sections count under them", () => {
  const rows = contentsRows(tree);
  assert.deepEqual(rows.map((r) => [r.number, r.label]), [
    [null, "Lời bạt"],
    [null, "Phần mở đầu"],
    [null, "NHỮNG CÂU HỎI ĐẦU TIÊN"],
    ["I", "NHỮNG CON ĐƯỜNG"],
    ["1", "BẾN SÔNG"],
    ["1.1", "CON THUYỀN"],
    ["1.1.1", "Mái chèo"],
    ["1.1.2", "Cánh buồm"],
    ["1.2", "BỜ CÁT"],
    ["2", "BỜ BÊN KIA"],
    ["II", "BẦU TRỜI"],
    ["3", "MÂY"],
    // "Phần" below the chapter level is an ordinary section, not a part.
    ["3.1", "Phần Bốn KẾT THÚC"],
    ["3.2", "MƯA"],
    [null, "Phần kết"],
    [null, "Lời cảm ơn"],
  ]);
});

test("each row knows its role and how far below the chapter level it sits", () => {
  const rows = contentsRows(tree);
  const pick = (label: string) => rows.find((r) => r.label === label)!;
  assert.deepEqual([pick("NHỮNG CON ĐƯỜNG").role, pick("NHỮNG CON ĐƯỜNG").sub], ["part", -1]);
  assert.deepEqual([pick("BẾN SÔNG").role, pick("BẾN SÔNG").sub], ["chapter", 0]);
  assert.deepEqual([pick("Mái chèo").role, pick("Mái chèo").sub], ["section", 2]);
  // Above the chapters, a group needs lines under it; a lone one is a stop.
  assert.equal(pick("Phần mở đầu").role, "part");
  assert.equal(pick("Lời bạt").role, "chapter");
  assert.equal(pick("Lời cảm ơn").role, "chapter");
});

test("a chapter numbered in words or Roman numerals keeps that number", () => {
  assert.deepEqual(marker("Chương Mười Hai: Gió"), { kind: "chapter", n: 12, rest: "Gió" });
  assert.deepEqual(marker("Chương hai mươi mốt Sóng"), { kind: "chapter", n: 21, rest: "Sóng" });
  assert.deepEqual(marker("Chapter IV — The Tide"), { kind: "chapter", n: 4, rest: "The Tide" });
  assert.deepEqual(marker("Part Two: Harbours"), { kind: "part", n: 2, rest: "Harbours" });
  assert.equal(marker("Phần mở đầu"), null);
  assert.equal(marker("Chương cuối"), null);
  assert.equal(roman(14), "XIV");
});

test("a title that is only its label keeps the label", () => {
  const rows = contentsRows([entry(1, "Chương 7"), entry(1, "Chương 8 Đêm")]);
  assert.deepEqual(rows.map((r) => [r.number, r.label]), [["7", "Chương 7"], ["8", "Đêm"]]);
});

test("a book without chapter labels is numbered 1..N at its top, less the matter its titles name", () => {
  const rows = contentsRows([
    entry(1, "Lời nói đầu"),
    entry(1, "Những ngày đầu"),
    entry(2, "Buổi sáng"),
    entry(1, "Mùa mưa"),
    entry(1, "Acknowledgements"),
  ]);
  assert.deepEqual(rows.map((r) => r.number), [null, "1", "1.1", "2", null]);
});

test("the row the reader is at is the deepest one at or before the place", () => {
  const rows = contentsRows(tree);
  const order = new Map(tree.map((e, i) => [e.segment_id, i * 10]));
  const orderOf = (id: string) => order.get(id) ?? -1;
  assert.equal(rows[currentRow(rows, orderOf, 65)].label, "Mái chèo");
  assert.equal(rows[currentRow(rows, orderOf, 69)].label, "Mái chèo");
  assert.equal(rows[currentRow(rows, orderOf, 70)].label, "Cánh buồm");
  assert.equal(currentRow(rows, orderOf, -1), -1);
});

test("an empty tree gives no rows", () => {
  assert.deepEqual(contentsRows([]), []);
});
