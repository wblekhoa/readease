import test from "node:test";
import assert from "node:assert/strict";
import { splitHighlight } from "../src/ui/highlight.ts";

test("curly quotes, non-breaking spaces and doubled spaces still find the words", () => {
  const text = "“Đừng hiểu lầm ý tôi.” Trước hết,  sản phẩm phải hoạt động.";
  const split = splitHighlight(text, '"Đừng hiểu lầm ý tôi." Trước hết, sản phẩm');
  assert.ok(split);
  assert.equal(split.before, "");
  assert.equal(split.mark, "“Đừng hiểu lầm ý tôi.” Trước hết,  sản phẩm");
  assert.equal(split.after, " phải hoạt động.");
});

test("a highlight that runs into the next paragraph marks to the end", () => {
  const text = "Câu cuối của đoạn này được bôi đen dở.";
  const split = splitHighlight(text, "được bôi đen dở. Và đoạn sau nữa.");
  assert.ok(split);
  assert.equal(split.mark, "được bôi đen dở.");
  assert.equal(split.after, "");
});

test("words that are not here give null", () => {
  assert.equal(splitHighlight("Một đoạn văn.", "không có ở đây"), null);
  assert.equal(splitHighlight("Một đoạn văn.", "   "), null);
});

test("the mark covers the displayed characters exactly", () => {
  const text = "A B C D";
  const split = splitHighlight(text, "b c");
  assert.deepEqual(split, { before: "A ", mark: "B C", after: " D" });
});
