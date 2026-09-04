import test from "node:test";
import assert from "node:assert/strict";
import { markParagraph, type HighlightPiece } from "../src/ui/highlight.ts";

/** The pieces that came from a highlight, with the highlight that made them. */
const marks = (pieces: HighlightPiece[]) =>
  pieces.filter((piece) => piece.index !== null).map((piece) => [piece.index, piece.text]);

/** The one property every call must have: the paragraph is cut up, never
 * rewritten - so the pieces put back together are the paragraph again. */
function whole(pieces: HighlightPiece[], text: string) {
  assert.equal(pieces.map((piece) => piece.text).join(""), text);
}

test("curly quotes, non-breaking spaces and doubled spaces still find the words", () => {
  const text = "“Đừng hiểu lầm ý tôi.” Trước hết,  sản phẩm phải hoạt động.";
  const pieces = markParagraph(text, ['"Đừng hiểu lầm ý tôi." Trước hết, sản phẩm']);
  whole(pieces, text);
  assert.deepEqual(pieces, [
    { text: "“Đừng hiểu lầm ý tôi.” Trước hết,  sản phẩm", index: 0 },
    { text: " phải hoạt động.", index: null },
  ]);
});

test("a highlight that runs into the next paragraph marks to the end", () => {
  const text = "Câu cuối của đoạn này được bôi đen dở.";
  const pieces = markParagraph(text, ["được bôi đen dở. Và đoạn sau nữa."]);
  whole(pieces, text);
  assert.deepEqual(marks(pieces), [[0, "được bôi đen dở."]]);
});

test("words that are not here leave the paragraph plain", () => {
  const text = "Một đoạn văn.";
  assert.deepEqual(markParagraph(text, ["không có ở đây"]), [{ text, index: null }]);
  assert.deepEqual(markParagraph(text, ["   "]), [{ text, index: null }]);
  assert.deepEqual(markParagraph(text, []), [{ text, index: null }]);
});

test("the mark covers the displayed characters exactly", () => {
  assert.deepEqual(markParagraph("A B C D", ["b c"]), [
    { text: "A ", index: null },
    { text: "B C", index: 0 },
    { text: " D", index: null },
  ]);
});

test("every highlight in the paragraph is marked, in reading order", () => {
  const text = "Câu đầu tiên. Câu ở giữa. Câu cuối cùng.";
  // Handed over in the order the notes arrived, which is not reading order.
  const pieces = markParagraph(text, ["Câu cuối cùng", "Câu đầu tiên"]);
  whole(pieces, text);
  assert.deepEqual(marks(pieces), [
    [1, "Câu đầu tiên"],
    [0, "Câu cuối cùng"],
  ]);
});

test("the same words highlighted twice take the two places they are said", () => {
  const text = "Đọc chậm rồi đọc lại. Đọc chậm là cách duy nhất.";
  const pieces = markParagraph(text, ["Đọc chậm", "đọc chậm"]);
  whole(pieces, text);
  assert.deepEqual(marks(pieces), [
    [0, "Đọc chậm"],
    [1, "Đọc chậm"],
  ]);
});

test("a duplicate with nowhere else to go is dropped, not doubled", () => {
  const text = "Chỉ nói một lần thôi.";
  const pieces = markParagraph(text, ["một lần", "một lần"]);
  whole(pieces, text);
  assert.deepEqual(marks(pieces), [[0, "một lần"]]);
});

test("a phrase marked inside a sentence marked whole never marks it twice", () => {
  const text = "Thiết kế tốt là thiết kế vô hình, người dùng không nhận ra.";
  const pieces = markParagraph(text, ["thiết kế vô hình", "Thiết kế tốt là thiết kế vô hình"]);
  whole(pieces, text);
  // The longer highlight keeps its start; the phrase inside it has no free
  // occurrence left, so it makes no second mark.
  assert.deepEqual(marks(pieces), [[1, "Thiết kế tốt là thiết kế vô hình"]]);
});

test("two highlights that overlap are both shown, each on its own characters", () => {
  const text = "A B C D E";
  const pieces = markParagraph(text, ["A B C", "B C D"]);
  whole(pieces, text);
  assert.deepEqual(marks(pieces), [
    [0, "A B C"],
    [1, "D"],
  ]);
});
