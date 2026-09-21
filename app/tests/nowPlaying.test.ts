import { test } from "node:test";
import assert from "node:assert/strict";
import { artworkPayload } from "../src/ui/nowPlaying.ts";

const COVER = "data:image/jpeg;base64,/9j/4AAQSkZJRg==";

test("the bytes travel once: with the first payload for a key, never again", () => {
  assert.deepEqual(artworkPayload("book-1", COVER, null), { key: "book-1", data: "/9j/4AAQSkZJRg==" });
  assert.deepEqual(artworkPayload("book-1", COVER, "book-1"), { key: "book-1" });
  // Another document: its own bytes, once.
  assert.deepEqual(artworkPayload("book-2", COVER, "book-1"), { key: "book-2", data: "/9j/4AAQSkZJRg==" });
});

test("no cover, a cover still loading, or one that is not base64 sends nothing", () => {
  assert.equal(artworkPayload("book-1", null, null), null);
  assert.equal(artworkPayload("book-1", undefined, null), null);
  assert.equal(artworkPayload("book-1", "https://example.invalid/cover.jpg", null), null);
  assert.equal(artworkPayload("book-1", "data:image/png,rawbytes", null), null);
});
