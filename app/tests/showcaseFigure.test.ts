import { test } from "node:test";
import assert from "node:assert/strict";
import { showcaseChapterCopy, showcaseFigureSvg } from "../src/dev/showcaseFigure.ts";

for (const locale of ["vi", "en"] as const) {
  test(`public figure is self-contained, accessible and localized: ${locale}`, () => {
    const svg = showcaseFigureSvg(locale);
    assert.match(svg, /viewBox="0 0 1200 680"/);
    assert.match(svg, /aria-labelledby="title desc"/);
    assert.match(svg, locale === "vi" ? /Kỹ thuật/ : /Engineering/);
    assert.match(svg, locale === "vi" ? /Nghiên cứu/ : /Research/);
    assert.doesNotMatch(svg, /True Search|Thrive|Synthesis|<script|<image|href=|url\(/);
    for (const marker of ["01", "02", "03"]) assert.ok(svg.includes(`>${marker}</text>`));
  });
  test(`public chapter copy is coherent and complete: ${locale}`, () => {
    const chapter = showcaseChapterCopy(locale);
    assert.equal(chapter.length, 22);
    assert.match(chapter[0], locale === "vi" ? /Ba con đường/ : /Three paths/);
    assert.match(chapter[17], locale === "vi" ? /Hình 3\.1/ : /Figure 3\.1/);
    assert.doesNotMatch(chapter.join(" "), /duplicate|bản trùng|def read|True Search|Synthesis/);
  });
}
