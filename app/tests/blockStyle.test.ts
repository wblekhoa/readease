import assert from "node:assert/strict";
import { test } from "node:test";
import { continues, listLead, quoteRole } from "../src/ui/blockStyle.ts";

test("a list item gives up the marker the book typed in front of it", () => {
  assert.deepEqual(listLead("• Thiết kế và phát triển Web."), { marker: { kind: "dot" }, rest: "Thiết kế và phát triển Web." });
  assert.deepEqual(listLead("- Gạch đầu dòng kiểu Việt."), { marker: { kind: "dot" }, rest: "Gạch đầu dòng kiểu Việt." });
  assert.deepEqual(listLead("1. Hãy bắt đầu từ đầu nguồn."), { marker: { kind: "number", label: "1." }, rest: "Hãy bắt đầu từ đầu nguồn." });
  assert.deepEqual(listLead("a) Một mục chữ."), { marker: { kind: "number", label: "a)" }, rest: "Một mục chữ." });
  assert.deepEqual(listLead("(12) Mục trong ngoặc."), { marker: { kind: "number", label: "(12)" }, rest: "Mục trong ngoặc." });
  // Clean text: a dot is drawn, nothing is taken away.
  assert.deepEqual(listLead("Khó đăng ký đi bầu: lỗi UX"), { marker: { kind: "dot" }, rest: "Khó đăng ký đi bầu: lỗi UX" });
  // A number inside the sentence is not a marker; neither is "1998 là năm".
  assert.deepEqual(listLead("Năm 1998. Rồi sao?"), { marker: { kind: "dot" }, rest: "Năm 1998. Rồi sao?" });
  assert.deepEqual(listLead("1998 là năm khởi đầu."), { marker: { kind: "dot" }, rest: "1998 là năm khởi đầu." });
});

test("a blockquote of one to three unpunctuated words is a label, anything longer a quotation", () => {
  assert.equal(quoteRole("Trải nghiệm"), "label");
  assert.equal(quoteRole("Phần cứng"), "label");
  assert.equal(quoteRole("Jeremy Keith"), "label");
  assert.equal(quoteRole("Tuy nhiên, trong những gì đã trải qua, tôi chưa bao giờ gặp phải tai nạn."), "quotation");
  assert.equal(quoteRole("Hết giờ rồi!"), "quotation");

  // The demo chapter's three samples, by their exact text: the sampler is
  // what a person LOOKS at to see this rule, so if the thresholds move the
  // samples must stop matching here rather than quietly render as something
  // else on screen. "Ngắn thôi." is the pair to the two above it - the same
  // length, and a quotation only because it closes.
  assert.equal(quoteRole("Nhãn ngắn"), "label");
  assert.equal(quoteRole("Không chấm câu"), "label");
  assert.equal(quoteRole("Ngắn thôi."), "quotation");
});

test("only a split tail continues the block before it", () => {
  assert.equal(continues("split"), true);
  assert.equal(continues("block"), false);
  assert.equal(continues("line"), false);
  assert.equal(continues(undefined), false);
});
