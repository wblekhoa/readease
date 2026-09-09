/** Row metadata formatting - what tells two same-named books apart. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { setLanguage } from "../src/i18n.ts";
import { formatDate, formatSize, hoverText } from "../src/ui/format.ts";

test("kích thước ra MB một chữ số lẻ, đúng dấu phẩy VI", () => {
  setLanguage("vi");
  assert.equal(formatSize(9_100_000), "9,1 MB");
  setLanguage("en");
  assert.equal(formatSize(9_100_000), "9.1 MB");
  setLanguage("vi");
});

test("thiếu dữ liệu trả null, không bao giờ ra chữ undefined", () => {
  assert.equal(formatSize(null), null);
  assert.equal(formatSize(0), null);
  assert.equal(formatDate(null), null);
  assert.equal(formatDate("not a date"), null);
});

test("ngày SQLite (UTC) ra dd/mm/yyyy", () => {
  setLanguage("vi");
  assert.equal(formatDate("2026-08-31 10:15:00"), "31/08/2026");
});

test("một dòng bị cắt phải nói lại CHÍNH nó khi rê chuột", () => {
  // Thẻ sách từng treo tooltip về chương lên đúng dòng dữ kiện đang bị cắt:
  // rê vào phần chữ mất đi thì được trả lời một câu hỏi khác.
  assert.equal(
    hoverText("Đã đọc 42% · 26 chương · 9,5 MB · EPUB", "Chương 3"),
    "Đã đọc 42% · 26 chương · 9,5 MB · EPUB · Chương 3",
  );
  assert.equal(hoverText("Chỉ mình nó"), "Chỉ mình nó");
});

test("không có gì để nói thì không dựng tooltip rỗng", () => {
  assert.equal(hoverText(null, undefined, "   "), undefined);
  assert.equal(hoverText(), undefined);
});

test("nhãn không phải chuỗi thì bỏ qua, không in [object Object]", () => {
  assert.equal(hoverText({ jsx: true }, "Tên sách"), "Tên sách");
});
