import { test } from "node:test";
import assert from "node:assert/strict";
import { excerpt, releaseDate } from "../src/ui/releaseNotes.ts";

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

/* A release's notes are written twice - Vietnamese, a rule, English - and
   the sheet showed the Vietnamese half in the English interface (27/09). */
const BILINGUAL = [
  "## ReadEase — Thư Âm 0.1.19",
  "",
  "**Nghe rõ đâu là chương.** Ký Developer ID; có `.dmg` và `.zip`.",
  "",
  "- **Chương dài, mục ngắn**: âm dài khi sang chương.",
  "",
  "---",
  "",
  "**Hear where a chapter starts.** Developer ID-signed; `.dmg` and `.zip`.",
  "",
  "- **Chapters long, sections short**: the long sound opens a chapter; \"Về chỗ đang đọc\" brings you back.",
].join("\n");

test("a bilingual note shows the reader's half, in the reader's language", () => {
  assert.deepEqual(excerpt(BILINGUAL, "vi").split("\n"), [
    "Nghe rõ đâu là chương. Ký Developer ID; có .dmg và .zip.",
    "• Chương dài, mục ngắn: âm dài khi sang chương.",
  ]);
  assert.deepEqual(excerpt(BILINGUAL, "en").split("\n"), [
    "Hear where a chapter starts. Developer ID-signed; .dmg and .zip.",
    "• Chapters long, sections short: the long sound opens a chapter; \"Về chỗ đang đọc\" brings you back.",
  ]);
});

test("code marks and links read as their words", () => {
  assert.equal(excerpt("Signed; `.dmg` and `.zip`. See [the licence](https://example.com/LICENSE).", "en"), "Signed; .dmg and .zip. See the licence.");
});

test("the release date is written in the reader's language", () => {
  assert.equal(releaseDate("2026-09-27T02:00:00Z", "en"), "27\u00a0September\u00a02026");
  assert.match(releaseDate("2026-09-27T02:00:00Z", "vi"), /tháng\u00a09/);
});
