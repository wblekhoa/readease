import test from "node:test";
import assert from "node:assert/strict";
import { DEFAULT_PREFS, isDefaultPrefs, measureEm, normalizePrefs } from "../src/ui/readingPrefs.ts";

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
