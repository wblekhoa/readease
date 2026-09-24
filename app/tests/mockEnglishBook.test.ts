import { test } from "node:test";
import assert from "node:assert/strict";
import { ENGLISH_BOOK, ENGLISH_TOC } from "../src/dev/mockEnglishBook.ts";
import { mockFigureSvgs } from "../src/dev/mockFigures.ts";

const segments = ENGLISH_BOOK.chapters.flatMap((chapter) => chapter.segments);
const ids = new Set(segments.map((segment) => segment.id));
const VIETNAMESE = /[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]/i;

test("every passage of the English book has an id of its own", () => {
  assert.equal(ids.size, segments.length);
});

test("every picture hangs on, and is captioned by, a passage of its own chapter", () => {
  const pictures = mockFigureSvgs();
  for (const chapter of ENGLISH_BOOK.chapters) {
    const here = new Set(chapter.segments.map((segment) => segment.id));
    for (const figure of chapter.figures) {
      assert.ok(pictures[figure.id], `${figure.id} has a picture`);
      assert.ok(here.has(figure.anchor_segment_id), `${figure.id} hangs in ${chapter.id}`);
      if ("caption_segment_id" in figure) {
        assert.ok(here.has(String(figure.caption_segment_id)), `${figure.id}'s caption is in ${chapter.id}`);
      }
    }
  }
});

test("every line of the contents leads somewhere in the book", () => {
  for (const entry of ENGLISH_TOC) assert.ok(ids.has(entry.segment_id), entry.title);
});

test("the English book is English throughout", () => {
  const words = [
    ENGLISH_BOOK.title,
    ...ENGLISH_BOOK.chapters.map((chapter) => chapter.title),
    ...segments.map((segment) => segment.text),
    ...ENGLISH_BOOK.chapters.flatMap((chapter) => chapter.figures.map((figure) => figure.alt)),
    ...ENGLISH_TOC.map((entry) => entry.title),
  ];
  for (const text of words) assert.doesNotMatch(text, VIETNAMESE, text);
});
