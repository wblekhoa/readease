import { test } from "node:test";
import assert from "node:assert/strict";
import { excerpt } from "../src/ui/releaseNotes.ts";

test("the CHANGELOG's hard wraps are undone into paragraphs, bullets on their own", () => {
  const notes = [
    "The first release the app fetches by itself: a log file",
    "for bug reports,",
    "and the bundle's own category and copyright.",
    "",
    "- A log file: with the app opened from Finder, what the host and the",
    "  engine report goes to the Logs folder.",
    "- The bundle names its category.",
  ].join("\n");
  assert.deepEqual(excerpt(notes).split("\n"), [
    "The first release the app fetches by itself: a log file for bug reports, and the bundle's own category and copyright.",
    "• A log file: with the app opened from Finder, what the host and the engine report goes to the Logs folder.",
    "• The bundle names its category.",
  ]);
});

test("headings, emphasis and rules are stripped; at most eight paragraphs", () => {
  const notes = "## 0.1.12\n**Bold** start\n---\n" + Array.from({ length: 12 }, (_, i) => `- item ${i}`).join("\n");
  const lines = excerpt(notes).split("\n");
  assert.equal(lines[0], "Bold start");
  assert.equal(lines.length, 8);
  assert.equal(lines[1], "• item 0");
});
