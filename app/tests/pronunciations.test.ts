import { strict as assert } from "node:assert";
import { test } from "node:test";
import { readPronunciations, withPronunciation, withoutPronunciation } from "../src/ui/pronunciations.ts";

test("đọc giá trị đã lưu, bỏ qua dòng hỏng", () => {
  assert.deepEqual(
    readPronunciations([{ written: " ReadEase ", spoken: "rít  ít" }, { written: "", spoken: "x" }, 3]),
    [{ written: "ReadEase", spoken: "rít ít" }],
  );
  assert.deepEqual(readPronunciations("không phải json"), []);
});

test("thêm mới, hoặc sửa cách đọc của từ đã có mà giữ vị trí", () => {
  const one = withPronunciation([], "AI", "ây ai")!;
  const two = withPronunciation(one, "ReadEase", "rít ít")!;
  assert.deepEqual(withPronunciation(two, "ai", "a i")!, [
    { written: "ai", spoken: "a i" },
    { written: "ReadEase", spoken: "rít ít" },
  ]);
  assert.equal(withPronunciation(two, " ", "x"), null);
  assert.deepEqual(withoutPronunciation(two, "AI"), [{ written: "ReadEase", spoken: "rít ít" }]);
});
