/** The string table's contract - the same class of guards the Qt shell's
 * test_i18n carried, ported to the web shell where the strings now live. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { setLanguage, text, textIn, TEXT, type TextKey } from "../src/i18n.ts";

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

/** The panel tells a reader a preview costs "chưa tới $0,01". That is
 * arithmetic over the sample sentence, not a hedge, so the sentence has a
 * length it may not exceed. The other half of the claim - that 90 characters
 * comes to under a cent on every price this app quotes - is pinned in
 * tests/speech/test_external_estimate.py, which cites this test by name. */
test("câu nghe thử đủ ngắn để lời hứa 'chưa tới $0,01' còn đúng", () => {
  const LIMIT = 90;
  for (const key of ["voices.sample", "voices.sample_en"] as TextKey[]) {
    for (const language of ["vi", "en"] as const) {
      setLanguage(language);
      assert.ok(
        text(key).length <= LIMIT,
        `${key} (${language}): ${text(key).length} ký tự, quá ${LIMIT}`,
      );
    }
  }
  setLanguage("vi");
});

test("chữ của tài liệu theo ngôn ngữ tài liệu, không theo giao diện (HIG 3.9)", () => {
  // An English document under a Vietnamese interface: the picture's label is
  // the document's word, as the voice says it.
  setLanguage("vi");
  assert.equal(textIn("en", "reader.figure_label", { n: 1 }), "Figure 1");
  assert.equal(textIn("vi", "reader.figure_label", { n: 2 }), "Hình 2");
  // No language, or one the table does not have: the interface's.
  assert.equal(textIn(undefined, "reader.figure_label", { n: 3 }), "Hình 3");
  assert.equal(textIn("fr", "reader.figure_label", { n: 4 }), "Hình 4");
  setLanguage("en");
  assert.equal(textIn("vi", "reader.figure_label", { n: 5 }), "Hình 5");
  assert.equal(text("reader.figure_label", { n: 6 }), "Figure 6");
  setLanguage("vi");
});
