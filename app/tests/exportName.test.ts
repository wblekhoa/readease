import { strict as assert } from "node:assert";
import { test } from "node:test";
import { asWavPath, defaultExportName } from "../src/ui/exportName.ts";

test("tên đề xuất là app và thời điểm, không lấy chữ của nội dung", () => {
  assert.equal(defaultExportName(new Date(2026, 9, 14, 9, 5)), "ReadEase 2026-10-14 09.05.wav");
});

test("đường dẫn đã chọn luôn kết thúc bằng .wav", () => {
  assert.equal(asWavPath("/Volumes/Phim/Giọng đọc"), "/Volumes/Phim/Giọng đọc.wav");
  assert.equal(asWavPath("/Volumes/Phim/a.WAV"), "/Volumes/Phim/a.WAV");
  assert.equal(asWavPath("/Volumes/Phim/a.wav"), "/Volumes/Phim/a.wav");
});
