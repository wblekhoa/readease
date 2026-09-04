import test from "node:test";
import assert from "node:assert/strict";
import { FAULT_CODES, readingFault, faultKey } from "../src/ui/voiceFault.ts";
import { TEXT } from "../src/i18n.ts";

/* Eight sentences were written for the engine's eight failure names and none
 * of them had ever reached a screen: the footer printed the raw engine string
 * under `truncate`, so a reader out of credit saw `voice_failed: quota: You
 * exceeded...` with the end cut off. These pin the mapping that connects the
 * two, and the guard that keeps them connected. */

test("every named failure has a sentence written for it", () => {
  for (const code of FAULT_CODES) {
    assert.ok(
      `voiceerr.${code}` in TEXT,
      `no sentence for ${code} - a fault with no words is a blank line in front of a reader`,
    );
  }
});

test("every voiceerr sentence is reachable from some fault", () => {
  // The other direction, which is the one that rots: a code renamed in the
  // engine leaves its sentence stranded, and nothing notices.
  const written = Object.keys(TEXT).filter((key) => key.startsWith("voiceerr."));
  const reachable = FAULT_CODES.map((code) => `voiceerr.${code}`);
  assert.deepEqual(new Set(written), new Set(reachable));
});

test("a provider refusal is named", () => {
  const fault = readingFault("voice_failed: quota: You exceeded your quota");
  assert.equal(fault.code, "quota");
  assert.equal(faultKey(fault), "voiceerr.quota");
});

test("a reading blocked BEFORE anything was sent is named too", () => {
  // Two prefixes, because there are two moments: the provider said no, or it
  // was never asked - no key, or our own ceiling. Only handling the first
  // left the two cases where NOTHING was charged as raw strings.
  for (const reason of ["no_key", "budget"]) {
    const fault = readingFault(`voice_unavailable: ${reason}`);
    assert.equal(fault.code, reason);
  }
});

test("it finds the code inside whatever the error channel wrapped it in", () => {
  const wrapped = 'Error: engine request failed: "voice_failed: bad_key: refused"';
  assert.equal(readingFault(wrapped).code, "bad_key");
});

test("a failure that is not a voice failure keeps its own words", () => {
  // A local engine fault dressed up as a provider one would send somebody to
  // check an API key they do not have.
  const fault = readingFault("model not ready: onnxruntime missing");
  assert.equal(fault.code, null);
  assert.equal(faultKey(fault), null);
  assert.equal(fault.raw, "model not ready: onnxruntime missing");
});

test("a code that only LOOKS like one of ours is not one of ours", () => {
  assert.equal(readingFault("voice_failed: quotasaurus: ...").code, null);
});
