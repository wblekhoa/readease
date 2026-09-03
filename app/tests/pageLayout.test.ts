import test from "node:test";
import assert from "node:assert/strict";
import { columnAt, layoutPages, viewCount, viewStart } from "../src/ui/pageLayout.ts";

test("a default window reads one page at the measure", () => {
  const layout = layoutPages(1012, 16);
  assert.equal(layout.cols, 1);
  assert.equal(layout.pageWidth, 640);
});

test("a wide window opens to a spread of two pages", () => {
  const layout = layoutPages(1252, 16);
  assert.equal(layout.cols, 2);
  assert.equal(layout.pageWidth, 602);
});

test("large type folds the spread back to one page", () => {
  assert.equal(layoutPages(1252, 21).cols, 1);
  assert.equal(layoutPages(1252, 19).cols, 2);
});

test("columns and views count the way pages are turned", () => {
  const layout = layoutPages(1252, 16);
  assert.equal(columnAt(0, layout), 0);
  assert.equal(columnAt(layout.step * 3 + 10, layout), 3);
  assert.equal(viewStart(3, 2), 2);
  assert.equal(viewStart(3, 1), 3);
  assert.equal(viewCount(5, 2), 3);
  assert.equal(viewCount(0, 2), 1);
});
