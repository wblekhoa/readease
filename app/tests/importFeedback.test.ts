/** What the shelf says about a drop and about an import. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { setLanguage } from "../src/i18n.ts";
import { dropHeadline, importNotice } from "../src/ui/importFeedback.ts";

test("kéo qua cửa sổ: nói số tài liệu sẽ thêm, hoặc rằng không có tệp nào đọc được", () => {
  setLanguage("vi");
  assert.equal(dropHeadline(1).headline, "Thả tệp để nhập tài liệu");
  assert.equal(dropHeadline(3).headline, "Thả để thêm 3 tài liệu vào thư viện");
  assert.equal(dropHeadline(0).headline, "Chỉ nhận PDF hoặc EPUB");
  // A refusal is a refusal in colour too, not only in words.
  assert.equal(dropHeadline(0).tone, "error");
  assert.equal(dropHeadline(1).tone, "ok");
  assert.equal(dropHeadline(3).tone, "ok");
  setLanguage("en");
  assert.equal(dropHeadline(3).headline, "Drop to add 3 documents to the library");
  setLanguage("vi");
});

test("một tệp: hai câu quen thuộc; nhiều tệp: đếm; có lỗi: nói lỗi", () => {
  setLanguage("vi");
  assert.deepEqual(importNotice({ added: 1, existing: 0, failed: 0, lastError: null }),
    { tone: "ok", message: "Đã thêm tài liệu vào thư viện." });
  assert.deepEqual(importNotice({ added: 0, existing: 1, failed: 0, lastError: null }),
    { tone: "ok", message: "Tài liệu này đã có trong thư viện." });
  assert.deepEqual(importNotice({ added: 2, existing: 1, failed: 0, lastError: null }),
    { tone: "ok", message: "Đã thêm 2 tài liệu; 1 đã có sẵn trong thư viện." });
  assert.deepEqual(importNotice({ added: 0, existing: 0, failed: 1, lastError: "PDF không có lớp văn bản." }),
    { tone: "error", message: "PDF không có lớp văn bản." });
  assert.deepEqual(importNotice({ added: 2, existing: 0, failed: 1, lastError: "PDF không có lớp văn bản." }),
    { tone: "error", message: "Đã thêm 2 tài liệu; 1 tệp không nhập được. PDF không có lớp văn bản." });
});
