import { strict as assert } from "node:assert";
import { test } from "node:test";
import { groupAnnotations, noteCount, notesMarkdown } from "../src/ui/annotationsList.ts";

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

// RE-NOTE-008
test("ghi chú ra Markdown theo thứ tự đọc, đoạn tô thành trích dẫn, ghi chú ở dưới", () => {
  const markdown = notesMarkdown("Sách thử", CHAPTERS, [
    { id: "b", segment_id: "s3", selected_text: "dòng một\ndòng hai", note: null },
    { id: "a", segment_id: "s1", selected_text: " Câu tô ", note: " nhớ " },
    { id: "z", segment_id: "khong-co", selected_text: "lạc", note: null },
  ]);
  assert.equal(markdown, [
    "# Sách thử", "", "## Chương một", "", "> Câu tô", "", "nhớ",
    "", "## Chương hai", "", "> dòng một", "> dòng hai", "",
  ].join("\n"));
});
