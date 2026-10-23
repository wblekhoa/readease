import { strict as assert } from "node:assert";
import { test } from "node:test";
import { PAPER_HUES, hashText, paperHues, wantsPaper } from "../src/ui/paperTint.ts";

test("bìa giấy: cùng tài liệu luôn cùng màu", () => {
  const ids = ["a1", "b2", "c3", "d4"];
  assert.deepEqual([...paperHues(ids)], [...paperHues(ids)]);
  assert.equal(hashText("Ghi chép"), hashText("Ghi chép"));
});

test("bìa giấy: hai tài liệu đứng cạnh nhau không trùng màu", () => {
  const ids = Array.from({ length: 200 }, (_, index) => `doc-${index}`);
  const hues = paperHues(ids);
  for (let index = 1; index < ids.length; index += 1) {
    assert.notEqual(hues.get(ids[index]), hues.get(ids[index - 1]), `${ids[index - 1]} / ${ids[index]}`);
  }
});

test("bìa giấy: màu trải đều trên bảng màu", () => {
  const ids = Array.from({ length: 800 }, (_, index) => `doc-${index}`);
  const counts = new Map<string, number>();
  for (const hue of paperHues(ids).values()) counts.set(hue, (counts.get(hue) ?? 0) + 1);
  assert.equal(counts.size, PAPER_HUES.length);
  for (const count of counts.values()) assert.ok(count > 50 && count < 150, `${count}`);
});

test("bìa giấy: chỉ cho tài liệu, không cho EPUB/PDF", () => {
  assert.equal(wantsPaper("md"), true);
  assert.equal(wantsPaper("DOCX"), true);
  assert.equal(wantsPaper("epub"), false);
  assert.equal(wantsPaper("PDF"), false);
});
