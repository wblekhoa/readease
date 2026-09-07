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
