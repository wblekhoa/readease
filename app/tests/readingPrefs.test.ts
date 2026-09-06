import test from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_PREFS, LINE_HEIGHT, MARGIN, isDefaultPrefs, lineHeightBand, marginBand, measureEm,
  normalizePrefs,
} from "../src/ui/readingPrefs.ts";

test("a stored record is clamped to its scales and unknown values fall back", () => {
  assert.deepEqual(normalizePrefs(undefined), DEFAULT_PREFS);
  assert.deepEqual(normalizePrefs("garbage"), DEFAULT_PREFS);
  assert.deepEqual(
    normalizePrefs({ lineHeight: 9, margin: -20, columns: 3, justify: "yes", bold: true }),
    { lineHeight: 2.1, margin: 0, columns: "auto", justify: false, bold: true },
  );
  // Snapped to the slider's step, so a hand-edited 1.731 is a value the
  // slider can show.
  assert.equal(normalizePrefs({ lineHeight: 1.731 }).lineHeight, 1.75);
  assert.equal(normalizePrefs({ columns: 2 }).columns, 2);
});

test("margins narrow the measure from 40em to 30em", () => {
  assert.equal(measureEm(0), 40);
  assert.equal(measureEm(50), 35);
  assert.equal(measureEm(100), 30);
  assert.equal(measureEm(500), 30);
});

test("only the untouched record counts as default", () => {
  assert.equal(isDefaultPrefs(DEFAULT_PREFS), true);
  assert.equal(isDefaultPrefs({ ...DEFAULT_PREFS, bold: true }), false);
});

test("the word under a slider covers the whole scale and never splits on the default", () => {
  // Every value the slider can produce has a word - a gap would show as an
  // empty half of the read-out.
  for (const scale of [LINE_HEIGHT, MARGIN] as const) {
    const band = scale === LINE_HEIGHT ? lineHeightBand : marginBand;
    for (let v = scale.min; v <= scale.max + 1e-9; v += scale.step) {
      assert.ok(["tight", "normal", "loose"].includes(band(Number(v.toFixed(4)))));
    }
  }

  assert.equal(lineHeightBand(LINE_HEIGHT.min), "tight");
  assert.equal(lineHeightBand(LINE_HEIGHT.max), "loose");
  assert.equal(marginBand(MARGIN.min), "tight");
  assert.equal(marginBand(MARGIN.max), "loose");

  // The default must sit INSIDE the middle band, not on its edge: a default
  // on a boundary would flip the word on one step of the knob, which reads
  // as the control being unsure what it is.
  assert.equal(lineHeightBand(DEFAULT_PREFS.lineHeight), "normal");
  assert.equal(lineHeightBand(DEFAULT_PREFS.lineHeight - LINE_HEIGHT.step), "normal");
  assert.equal(lineHeightBand(DEFAULT_PREFS.lineHeight + LINE_HEIGHT.step), "normal");
});
