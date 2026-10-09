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

/* A word that agrees with its number (27/09). The English interface said
   "1 highlights", "1 results", "Added 1 documents", "The other 1 are not
   copied" wherever a count could be one. `{count|one|many}` picks the word;
   the number itself stays a plain `{count}`. */
test("a count of one takes the singular in English", () => {
  const en = (key: TextKey, values: Record<string, string | number>) => textIn("en", key, values);
  assert.equal(en("notes.count", { count: 1 }), "1 highlight");
  assert.equal(en("notes.count", { count: 2 }), "2 highlights");
  // A count may arrive already written for the screen.
  assert.equal(en("library.chapter_count", { count: "1" }), "1 chapter");
  assert.equal(en("reader.search_count", { n: 1 }), "1 result");
  assert.equal(en("library.chapter_count", { count: 1 }), "1 chapter");
  assert.equal(en("voices.marked", { count: 1 }), "1 voice marked for quick switching.");
  assert.equal(en("library.imported_many", { added: 1, existing: 2 }), "Added 1 document; 2 already in the library.");
  assert.equal(en("apple.summary", { imported: 1, matched: 3, unmatched: 0 }),
    "1 document imported · 3 highlights matched · 0 not found in the text");
  assert.equal(en("transfer.left_out", { count: 1 }), "The other 1 is not copied.");
  assert.equal(en("outcome.all_already_there", { count: 1 }), "The 1 item is already in the other copy; there is nothing to copy.");
  assert.equal(en("cost.detail", { chars: "11,800", chapters: 1, date: "10 September 2026" }),
    "At most 11,800 characters · 1 chapter · price quoted 10 September 2026");
  // Vietnamese words do not change with a number.
  assert.equal(textIn("vi", "notes.count", { count: 1 }), TEXT["notes.count"][0].replace("{count}", "1"));
});

test("a word chosen by a number names a number its string shows, and never reaches the screen", () => {
  for (const key of KEYS) {
    const [vi, en] = TEXT[key];
    assert.doesNotMatch(vi, /\{\w+\|/, `${key}: Vietnamese words do not change with a number`);
    const chosen = [...en.matchAll(/\{(\w+)\|[^|}]*\|[^}]*\}/g)].map((match) => match[1]);
    for (const name of chosen) assert.ok(en.includes(`{${name}}`), `${key}: {${name}|…} without the number {${name}}`);
    if (!chosen.length) continue;
    for (const n of [1, 2]) {
      const values = Object.fromEntries([...en.matchAll(/\{(\w+)[}|]/g)].map((match) => [match[1], n]));
      const said = textIn("en", key, values);
      assert.doesNotMatch(said, /[{}|]/, `${key} with ${n}: ${said}`);
    }
  }
});

test("before a choice, the interface speaks the Mac's first language if it is Vietnamese, English otherwise", async () => {
  const { systemLanguage } = await import("../src/i18n.ts");
  assert.equal(systemLanguage(["vi-VN", "en-US"]), "vi");
  assert.equal(systemLanguage(["vi"]), "vi");
  assert.equal(systemLanguage(["en-US", "vi-VN"]), "en");
  assert.equal(systemLanguage(["fr-FR"]), "en");
  assert.equal(systemLanguage([]), "en");
});
