/** Paste and scan history as the screens see it (RE-HIST-001/002). */
import { test } from "node:test";
import assert from "node:assert/strict";
import { mergeCaptures, toCapture, withEntry, type HistoryEntry } from "../src/ui/readingHistory.ts";

const scan = (id: number, at: number, text: string, original: string | null = null): HistoryEntry =>
  ({ id, kind: "scan", text, original, target: original ? "vi" : null, at });

test("a stored scan becomes a Scan entry, translation and all", () => {
  assert.deepEqual(toCapture(scan(1, 5, "Bản dịch.", "Original.")), { at: 5, text: "Bản dịch.", original: "Original.", target: "vi" });
  assert.deepEqual(toCapture(scan(2, 6, "Đoạn.")), { at: 6, text: "Đoạn." });
});

test("stored scans fill in after this session's, newest first, without repeats", () => {
  const session = [{ at: 100, text: "Mới." }];
  const stored = [scan(1, 90, "Mới."), scan(2, 50, "Cũ."), { ...scan(3, 40, "Dán."), kind: "paste" as const }];
  assert.deepEqual(mergeCaptures(session, stored).map(entry => entry.text), ["Mới.", "Cũ."]);
});

test("the merged list is bounded", () => {
  const stored = Array.from({ length: 80 }, (_, index) => scan(index, index, `Đoạn ${index}.`));
  assert.equal(mergeCaptures([], stored).length, 50);
});

test("an entry read again moves to the top", () => {
  const list = [scan(1, 1, "A."), scan(2, 2, "B.")];
  assert.deepEqual(withEntry(list, { ...list[1], at: 9 }).map(entry => entry.id), [2, 1]);
});

test("a missing list merges as empty instead of throwing", () => {
  assert.deepEqual(mergeCaptures([{ at: 1, text: "A." }], undefined), [{ at: 1, text: "A." }]);
});
