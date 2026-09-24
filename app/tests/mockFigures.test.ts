import { test } from "node:test";
import assert from "node:assert/strict";
import { mockFigureSvgs } from "../src/dev/mockFigures.ts";

const figures = mockFigureSvgs();
// The Vietnamese sample book's pictures, and the English book's (`en-`).
const sets = {
  vi: Object.entries(figures).filter(([id]) => !id.startsWith("en-")),
  en: Object.entries(figures).filter(([id]) => id.startsWith("en-")),
};
const VIETNAMESE = /[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]/i;

function size(svg: string): { width: number; height: number } {
  const match = svg.match(/^<svg [^>]*width="(\d+)" height="(\d+)" viewBox="0 0 (\d+) (\d+)"/);
  assert.ok(match, "an svg with a width, a height and a viewBox");
  const [width, height, boxWidth, boxHeight] = match.slice(1).map(Number);
  assert.deepEqual([boxWidth, boxHeight], [width, height], "the viewBox is the picture's own size");
  return { width, height };
}

test("every harness picture is self-contained and named", () => {
  for (const [id, svg] of Object.entries(figures)) {
    size(svg);
    assert.match(svg, /role="img"/, id);
    assert.match(svg, /<title>[^<]+<\/title>/, id);
    assert.doesNotMatch(svg, /<script|<image|<foreignObject|href=|url\((?!#)/, id);
    for (const [, ref] of svg.matchAll(/url\(#([\w-]+)\)/g)) {
      assert.match(svg, new RegExp(`id="${ref}"`), `${id} defines #${ref}`);
    }
  }
});

for (const [language, set] of Object.entries(sets)) {
  test(`the ${language} pictures cover the shapes a page lays out differently`, () => {
    const shapes = set.map(([, svg]) => size(svg));
    const ratios = shapes.map(({ width, height }) => width / height);
    assert.ok(ratios.some((ratio) => ratio >= 3), "a panorama");
    assert.ok(ratios.some((ratio) => ratio > 1.6 && ratio < 2), "a wide chart");
    assert.ok(ratios.some((ratio) => ratio > 0.95 && ratio < 1.05), "a square");
    assert.ok(ratios.some((ratio) => ratio < 0.6), "a phone-tall picture");
    assert.ok(new Set(ratios.map((ratio) => ratio.toFixed(1))).size >= 7, "seven different shapes");
    assert.ok(shapes.some(({ width, height }) => width <= 600 && height <= 300), "one smaller than the column");
    // Line art as books ship it: its first drawing is not a full-bleed ground.
    const onNothing = set.filter(
      ([, svg]) => !/<\/title>\s*(<defs>[\s\S]*?<\/defs>\s*)?<rect width=/.test(svg),
    );
    assert.equal(onNothing.length, 1, "exactly one picture without a background");
  });
}

test("the English book's pictures say nothing in Vietnamese", () => {
  for (const [id, svg] of sets.en) assert.doesNotMatch(svg, VIETNAMESE, id);
});

test("the translated copy is the same picture in the other language", () => {
  assert.deepEqual(size(figures["fig-sample"]), size(figures["fig-sample-vi"]));
  assert.match(figures["fig-sample"], /Three paths into UX/);
  assert.match(figures["fig-sample-vi"], /Ba con đường vào UX/);
});
