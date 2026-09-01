/** Row metadata formatting - what tells two same-named books apart. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { setLanguage } from "../src/i18n.ts";
import { formatDate, formatSize } from "../src/ui/format.ts";

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
