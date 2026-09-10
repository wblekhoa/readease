/** What a person actually reads when an engine call is rejected.
 *
 * The table is not the point - `TranslationCoverageTests` on the Python side
 * already guards that every Vietnamese sentence HAS an English one. The point
 * is that the shipping shell READS it: for a long time the table was complete
 * and nobody consulted it, so the guard was green while an English interface
 * printed Vietnamese. These pin the behaviour instead of the asset. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { engineMessage, runtime, setLanguage } from "../src/i18n.ts";
import { faultKey, readingFault } from "../src/ui/voiceFault.ts";

const WRAPPED =
  "engine refused library.import: PDF không có lớp văn bản; bản MVP chưa hỗ trợ OCR.";

test("EN: cởi lớp vỏ truyền tin RỒI dịch", () => {
  setLanguage("en");
  assert.equal(
    engineMessage(WRAPPED),
    "This PDF has no text layer; OCR is not supported yet.",
  );
  setLanguage("vi");
});

test("VI: chỉ cởi vỏ, giữ nguyên câu của engine", () => {
  setLanguage("vi");
  assert.equal(
    engineMessage(WRAPPED),
    "PDF không có lớp văn bản; bản MVP chưa hỗ trợ OCR.",
  );
});

test("vỏ truyền tin không được sót lại ở bất kỳ ngôn ngữ nào", () => {
  for (const language of ["vi", "en"] as const) {
    setLanguage(language);
    assert.ok(
      !engineMessage(WRAPPED).includes("engine refused"),
      `${language}: còn nguyên "engine refused"`,
    );
  }
  setLanguage("vi");
});

test("câu có số đi qua mẫu, giữ đúng các con số", () => {
  setLanguage("en");
  assert.equal(runtime("Chương 3/10 · Đoạn 2/5"), "Chapter 3/10 · Paragraph 2/5");
  assert.equal(
    runtime("Không có bước nâng cấp dữ liệu lên v7."),
    "No upgrade step to data v7.",
  );
  setLanguage("vi");
});

test("câu không ai dịch thì giữ nguyên, không bị nuốt", () => {
  setLanguage("en");
  assert.equal(runtime("Một câu chưa ai viết bản dịch."),
               "Một câu chưa ai viết bản dịch.");
  // This side's own transport words are already English and stay untouched.
  assert.equal(engineMessage("engine timeout on library.list"),
               "engine timeout on library.list");
  setLanguage("vi");
});

/** The shell asked for this and did not do it (10/09).
 *
 * `readingFault()` keeps `raw` untouched on purpose - it classifies on that
 * string, and a fault it has no code for must not be dressed up as one it
 * knows. But App.tsx then printed that same `raw` when there was no code,
 * so a reader whose PDF had no text layer met the Rust transport's English
 * wrapper standing in front of a sentence written for them in Vietnamese.
 * Classifying and displaying are two jobs; only the second one translates. */
test("một lỗi đọc không có mã vẫn phải rụng vỏ truyền tin", () => {
  const fault = readingFault(WRAPPED);
  assert.equal(fault.code, null, "câu này cố tình không có mã");
  assert.equal(faultKey(fault), null);

  setLanguage("vi");
  assert.equal(
    engineMessage(fault.raw),
    "PDF không có lớp văn bản; bản MVP chưa hỗ trợ OCR.",
  );
  setLanguage("en");
  assert.equal(
    engineMessage(fault.raw),
    "This PDF has no text layer; OCR is not supported yet.",
  );
  setLanguage("vi");
});
