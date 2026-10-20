import assert from "node:assert/strict";
import { test } from "node:test";
import { drainBookImports } from "../src/ui/bookImport.ts";

// RE-HOME-001: a Finder request can arrive while another import refreshes.
test("files arriving during a shelf refresh are imported and the latest book opens", async () => {
  const queue = ["first.epub"];
  const imported: string[] = [];
  let refreshes = 0;
  const result = await drainBookImports(queue, async path => { imported.push(path); return path; }, async () => {
    if (++refreshes === 1) queue.push("second.pdf");
    return imported.map(id => ({ id }));
  });
  assert.deepEqual(imported, ["first.epub", "second.pdf"]);
  assert.equal(refreshes, 2);
  assert.equal(result.book?.id, "second.pdf");
  assert.equal(queue.length, 0);
});
test("a failed file does not discard the other files or hide its error", async () => {
  const failure = new Error("Unreadable PDF");
  const result = await drainBookImports(["bad.pdf", "good.epub"], async path => {
    if (path === "bad.pdf") throw failure;
    return "good";
  }, async () => [{ id: "good" }]);
  assert.equal(result.book?.id, "good");
  assert.equal(result.error, failure);
});
test("a missing shelf or damaged book never opens a guessed document", async () => {
  const missing = await drainBookImports(["a.epub"], async () => "a", async () => null);
  const damaged = await drainBookImports(["a.epub"], async () => "a", async () => [{ id: "a", damaged: true }]);
  assert.equal(missing.book, undefined);
  assert.equal(damaged.book, undefined);
});
