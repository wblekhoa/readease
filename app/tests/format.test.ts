/** Row metadata formatting - what tells two same-named books apart. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { setLanguage } from "../src/i18n.ts";
import { formatDate, formatDay, formatSize, hoverText } from "../src/ui/format.ts";

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

/* A price is quoted on a day ("2026-09-10"); the panel said it raw (27/09).
   And a day is one unit on its line: at the panel's width the Vietnamese one
   broke as "giá tham khảo 10 / tháng 9, 2026" - at a glance, a price of 10.
   So its spaces do not break. */
test("a quoted day reads in the reader's language, the month in words, on one line", () => {
  assert.equal(formatDay("2026-09-10"), "10\u00a0tháng\u00a09,\u00a02026");
  setLanguage("en");
  try {
    assert.equal(formatDay("2026-09-10"), "10\u00a0September\u00a02026");
  } finally {
    setLanguage("vi");
  }
  assert.equal(formatDay(null), null);
});

/* A bare day is midnight UTC to `Date`: written in the local zone, it was the
   day before anywhere west of Greenwich. CI runs in UTC, where the two agree,
   so the test moves itself west. */
test("a bare day is the same day in every time zone", () => {
  const zone = process.env.TZ;
  process.env.TZ = "America/Los_Angeles";
  try {
    assert.equal(formatDay("2026-09-10"), "10 tháng 9, 2026");
  } finally {
    if (zone === undefined) delete process.env.TZ;
    else process.env.TZ = zone;
  }
});
