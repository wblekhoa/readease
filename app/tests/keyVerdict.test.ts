import test from "node:test";
import assert from "node:assert/strict";
import { keyVerdict } from "../src/ui/keyVerdict.ts";

/* The shipped build told the reader a key was fine whatever the provider
 * said, because it read the envelope's `ok` - which only means the engine
 * answered - instead of the verdict inside it. These pin which `ok` counts. */

test("the verdict comes from inside result, not from the envelope", () => {
  assert.deepEqual(
    keyVerdict({ ok: true, result: { saved: false, ok: false, code: "bad_key" } } as never),
    { ok: false, code: "bad_key" },
    "a rejected key must not be reported as working just because the engine replied",
  );
});

test("an accepted key is accepted", () => {
  assert.deepEqual(keyVerdict({ result: { saved: true, ok: true } } as never), {
    ok: true,
    code: null,
  });
});

test("no reply at all is not a working key", () => {
  assert.deepEqual(keyVerdict(null), { ok: false, code: "network" });
  assert.deepEqual(keyVerdict({}), { ok: false, code: "network" });
});
