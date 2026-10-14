/** The bug form opens with the build and the Mac filled in (RE-HELP-001). */
import { test } from "node:test";
import assert from "node:assert/strict";
import { feedbackUrl, NEW_ISSUE_URL } from "../src/ui/feedback.ts";

test("fills the template's version and macos fields", () => {
  const url = new URL(feedbackUrl({ build: "0.1.21+5c39011", macos: "27.0", arch: "aarch64" }));
  assert.equal(url.origin + url.pathname, NEW_ISSUE_URL);
  assert.equal(url.searchParams.get("template"), "bug.yml");
  assert.equal(url.searchParams.get("version"), "0.1.21+5c39011");
  assert.equal(url.searchParams.get("macos"), "macOS 27.0 · Apple silicon");
});

test("keeps the + in a build id (a raw + would read as a space)", () => {
  const raw = feedbackUrl({ build: "0.1.21+5c39011", macos: "27.0", arch: "aarch64" });
  assert.ok(raw.includes("version=0.1.21%2B5c39011"), raw);
});

test("still names the chip when the macOS version could not be read", () => {
  const url = new URL(feedbackUrl({ build: "0.1.21", macos: null, arch: "x86_64" }));
  assert.equal(url.searchParams.get("macos"), "Intel");
});

test("opens the plain form when the facts are missing", () => {
  assert.equal(feedbackUrl(null), NEW_ISSUE_URL);
});
