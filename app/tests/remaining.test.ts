import { test } from "node:test";
import assert from "node:assert/strict";
import { remainingParts, scopeKey } from "../src/ui/remaining.ts";

test("a forecast is rounded to the minute, never finer, never zero", () => {
  assert.deepEqual(remainingParts(0), { key: "remaining.under_minute", params: {} });
  assert.deepEqual(remainingParts(29), { key: "remaining.under_minute", params: {} });
  assert.deepEqual(remainingParts(30), { key: "remaining.minutes", params: { minutes: 1 } });
  assert.deepEqual(remainingParts(89), { key: "remaining.minutes", params: { minutes: 1 } });
  assert.deepEqual(remainingParts(90), { key: "remaining.minutes", params: { minutes: 2 } });
  assert.deepEqual(remainingParts(52 * 60 + 20), { key: "remaining.minutes", params: { minutes: 52 } });
});

test("from an hour up, hours and minutes - and no dangling zero minutes", () => {
  assert.deepEqual(remainingParts(60 * 60), { key: "remaining.hours_even", params: { hours: 1 } });
  assert.deepEqual(remainingParts(65 * 60), { key: "remaining.hours", params: { hours: 1, minutes: 5 } });
  assert.deepEqual(remainingParts(3 * 3600 + 10 * 60 + 40), { key: "remaining.hours", params: { hours: 3, minutes: 11 } });
  assert.deepEqual(remainingParts(119.6 * 60), { key: "remaining.hours_even", params: { hours: 2 } });
});

test("nonsense reads as under a minute rather than as a number", () => {
  assert.deepEqual(remainingParts(Number.NaN), { key: "remaining.under_minute", params: {} });
  assert.deepEqual(remainingParts(-5), { key: "remaining.under_minute", params: {} });
});

test("the scope phrase mirrors the cost panel's own words", () => {
  assert.equal(scopeKey(null), null);
  assert.equal(scopeKey(1), "cost.scope_one");
  assert.equal(scopeKey(2), "cost.scope_chapters");
  assert.equal(scopeKey(5), "cost.scope_chapters");
});
