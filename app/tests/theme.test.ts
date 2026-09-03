import test from "node:test";
import assert from "node:assert/strict";
import { nextTheme, resolveTheme } from "../src/ui/theme.ts";

test("without a choice the OS appearance shows", () => {
  assert.equal(resolveTheme("system", true), "dark");
  assert.equal(resolveTheme("system", false), "light");
});

test("a choice wins over the OS", () => {
  assert.equal(resolveTheme("light", true), "light");
  assert.equal(resolveTheme("dark", false), "dark");
});

test("the switch always goes to the other side of what shows", () => {
  assert.equal(nextTheme("dark"), "light");
  assert.equal(nextTheme("light"), "dark");
});
