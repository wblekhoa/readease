/** One breakpoint, declared twice, kept equal.
 *
 * A short window folds two different kinds of thing away: sentences, which
 * `index.css` hides with `short-hidden`, and a whole row of filter chips,
 * which `VoicesPanel` renders or does not render from `useShortWindow`. CSS
 * cannot read a React state and React cannot read a media query's own
 * threshold, so the number lives in both files - and a panel that drops its
 * captions at one height while offering the filter button at another is a
 * panel with two layouts nobody drew.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SHORT_WINDOW } from "../src/ui/useShortWindow.ts";

const CSS = readFileSync(new URL("../src/index.css", import.meta.url), "utf8");

test("ngưỡng màn thấp trong CSS và trong TS là một", () => {
  const inTs = /max-height:\s*(\d+)px/.exec(SHORT_WINDOW);
  assert.ok(inTs, `SHORT_WINDOW không có max-height: ${SHORT_WINDOW}`);

  const utility = /@utility short-hidden \{([\s\S]*?)\n\}/.exec(CSS);
  assert.ok(utility, "không tìm thấy @utility short-hidden trong index.css");
  const inCss = /max-height:\s*(\d+)px/.exec(utility[1]);
  assert.ok(inCss, "short-hidden không dùng max-height");

  assert.equal(
    inCss[1],
    inTs[1],
    `CSS gấp ở ${inCss[1]}px còn TS gấp ở ${inTs[1]}px`,
  );
});

test("short-hidden thực sự giấu đi, không chỉ làm mờ", () => {
  const utility = /@utility short-hidden \{([\s\S]*?)\n\}/.exec(CSS);
  assert.ok(utility);
  assert.match(utility[1], /display:\s*none/);
});
