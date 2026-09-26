import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
import { test } from "node:test";

/* The spring curves are points written into index.css (HIG 3.17, owner
   26/09). A list cut short that ends at 0.98 leaves the segmented pill
   visibly short of its option; a typo past the peak turns a settle into a
   lurch. These read the stylesheet the app ships. */
const css = readFileSync(new URL("../src/index.css", import.meta.url), "utf8");

function curve(name: string): number[] {
  const match = css.match(new RegExp(`${name}:\\s*linear\\(([^)]*)\\)`));
  assert.ok(match, `${name} is not a linear() curve in index.css`);
  return match[1].split(",").map((stop) => Number(stop.trim()));
}

test("the control spring starts at 0, ends exactly on 1, and overshoots by 1-3 %", () => {
  const stops = curve("--ease-spring");
  assert.ok(stops.length >= 20, `only ${stops.length} stops`);
  assert.equal(stops[0], 0);
  assert.equal(stops[stops.length - 1], 1);
  const peak = Math.max(...stops);
  assert.ok(peak > 1.01 && peak < 1.03, `peak ${peak}`);
});

test("the star's pop starts at 0, ends exactly on 1, and bounces by 8-16 %", () => {
  const stops = curve("--ease-pop");
  assert.equal(stops[0], 0);
  assert.equal(stops[stops.length - 1], 1);
  const peak = Math.max(...stops);
  assert.ok(peak > 1.08 && peak < 1.16, `peak ${peak}`);
});

test("each spring has its duration, and Reduce Motion stops both", () => {
  assert.match(css, /--dur-spring:\s*\d+ms/);
  assert.match(css, /--dur-pop:\s*\d+ms/);
  const reduced = [...css.matchAll(/@media \(prefers-reduced-motion: reduce\) \{([\s\S]*?)\n\}/g)].map((block) => block[1]).join("\n");
  assert.match(reduced, /--dur-spring:\s*0ms/);
  assert.match(reduced, /\.star-pop\s*\{\s*animation:\s*none/);
});
