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

test("sàn chiều cao của cửa sổ nằm TRONG vùng gấp", () => {
  // Hai con số phải đứng đúng phía của nhau, và đây là chỗ duy nhất nói ra:
  //   - sàn CAO hơn ngưỡng ⇒ đường gấp thành mã chết, không ai chạy vào.
  //   - sàn thấp hơn nhiều ⇒ có những chiều cao hợp lệ mà không ai đã đo.
  // Cửa sổ nhỏ nhất mà macOS cho phép (đo 07/09: ép xuống 380px thì bị kẹp
  // lại đúng 600) là chiều cao mà bảng nổi PHẢI dùng được, nên nó nằm dưới
  // ngưỡng gấp - đo ở khung nhìn 572px (600 trừ thanh tiêu đề): danh sách
  // giọng được 234px, khoảng 3,7 giọng.
  const config = JSON.parse(
    readFileSync(new URL("../src-tauri/tauri.conf.json", import.meta.url), "utf8"),
  );
  const floor = config.app.windows[0].minHeight;
  assert.equal(typeof floor, "number", "cửa sổ không khai minHeight");
  const breakpoint = Number(/max-height:\s*(\d+)px/.exec(SHORT_WINDOW)![1]);
  assert.ok(
    floor <= breakpoint,
    `sàn cửa sổ ${floor}px cao hơn ngưỡng gấp ${breakpoint}px: đường gấp không bao giờ chạy`,
  );
  // Và sàn phải THỰC SỰ có: bỏ nó đi thì cửa sổ co được tới 0.
  assert.ok(floor >= 480, `sàn ${floor}px thấp tới mức không ai đo được`);
});

test("short-hidden thực sự giấu đi, không chỉ làm mờ", () => {
  const utility = /@utility short-hidden \{([\s\S]*?)\n\}/.exec(CSS);
  assert.ok(utility);
  assert.match(utility[1], /display:\s*none/);
});
