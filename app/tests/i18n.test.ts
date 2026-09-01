/** The string table's contract - the same class of guards the Qt shell's
 * test_i18n carried, ported to the web shell where the strings now live. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { setLanguage, text, TEXT, type TextKey } from "../src/i18n.ts";

const KEYS = Object.keys(TEXT) as TextKey[];

test("mọi key có đủ VI và EN, không rỗng", () => {
  assert.ok(KEYS.length > 0, "không đọc được bảng chuỗi");
  for (const key of KEYS) {
    setLanguage("vi");
    const vi = text(key);
    setLanguage("en");
    const en = text(key);
    assert.ok(vi.trim().length > 0, `${key}: VI rỗng`);
    assert.ok(en.trim().length > 0, `${key}: EN rỗng`);
  }
  setLanguage("vi");
});

test("chuỗi hiển thị dùng gạch ngang, không em/en dash (luật DS)", () => {
  for (const key of KEYS) {
    setLanguage("vi");
    assert.ok(!/[—–]/.test(text(key)), `${key} (VI) chứa em/en dash`);
    setLanguage("en");
    assert.ok(!/[—–]/.test(text(key)), `${key} (EN) chứa em/en dash`);
  }
  setLanguage("vi");
});

test("placeholder {x} khớp nhau giữa hai ngôn ngữ", () => {
  const tokens = (value: string) =>
    new Set([...value.matchAll(/\{([a-z_]+)\}/g)].map((m) => m[1]));
  for (const key of KEYS) {
    setLanguage("vi");
    const vi = tokens(text(key));
    setLanguage("en");
    const en = tokens(text(key));
    assert.deepEqual(
      [...vi].sort(),
      [...en].sort(),
      `${key}: placeholder lệch giữa VI/EN`,
    );
  }
  setLanguage("vi");
});
