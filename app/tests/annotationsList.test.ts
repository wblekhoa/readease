import { strict as assert } from "node:assert";
import { test } from "node:test";
import { groupAnnotations, noteCount } from "../src/ui/annotationsList.ts";

const CHAPTERS = [
  { id: "c1", title: "Chương một", segments: [{ id: "s1" }, { id: "s2" }] },
  { id: "c2", title: "Chương hai", segments: [{ id: "s3" }, { id: "s4" }] },
];
const at = (id: string, segment: string, note: string | null = null) =>
  ({ id, segment_id: segment, selected_text: "trích", note });

test("gom theo chương, theo đúng thứ tự đọc", () => {
  const groups = groupAnnotations(CHAPTERS, [at("a", "s4"), at("b", "s1"), at("c", "s3")]);
  assert.deepEqual(groups.map((g) => g.chapterId), ["c1", "c2"]);
  assert.deepEqual(groups[1].items.map((i) => i.id), ["c", "a"]);
  assert.equal(groups[0].chapterTitle, "Chương một");
});

test("hai highlight trong cùng một đoạn đều giữ lại", () => {
  const groups = groupAnnotations(CHAPTERS, [at("a", "s1"), at("b", "s1")]);
  assert.equal(groups.length, 1);
  assert.deepEqual(groups[0].items.map((i) => i.id), ["a", "b"]);
});

test("đoạn không thuộc sách này thì bỏ, không đoán chương", () => {
  const groups = groupAnnotations(CHAPTERS, [at("a", "lạ"), at("b", "s2")]);
  assert.deepEqual(groups.map((g) => g.chapterId), ["c1"]);
  assert.deepEqual(groups[0].items.map((i) => i.id), ["b"]);
});

test("không có gì thì không có nhóm nào", () => {
  assert.deepEqual(groupAnnotations(CHAPTERS, []), []);
});

test("đếm riêng những cái có ghi chú", () => {
  assert.equal(noteCount([at("a", "s1", "hay"), at("b", "s2"), at("c", "s3", "")]), 1);
});
