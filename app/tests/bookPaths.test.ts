/** A drop from Finder: which paths become imports. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { bookPaths } from "../src/ui/bookPaths.ts";

test("chỉ giữ PDF và EPUB, không phân biệt hoa thường, giữ thứ tự thả", () => {
  assert.deepEqual(
    bookPaths(["/x/a.PDF", "/x/ảnh.png", "/x/b.epub", "/x/c.Epub", "/x/thư mục", "/x/d.dmg"]),
    ["/x/a.PDF", "/x/b.epub", "/x/c.Epub"],
  );
});

test("cùng một tệp thả hai lần chỉ nhập một lần", () => {
  assert.deepEqual(bookPaths(["/x/a.pdf", "/x/a.pdf"]), ["/x/a.pdf"]);
});

test("không có sách thì không có gì để nhập", () => {
  assert.deepEqual(bookPaths([]), []);
  assert.deepEqual(bookPaths(["/x/notes.txt", "/x/README"]), []);
});
