import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { TEXT } from "../src/i18n.ts";

/* The engine names the reason a selection could not be read; the shell looks
 * that name up as `status.<name>` and prints the sentence. Nothing held the
 * two lists together. And the shell does not fail softly here: `text()` is
 * `TEXT[key][...]`, so a name with no key throws inside render, and there is
 * no error boundary in this app - a renamed arm in Rust would take the whole
 * window white, not print a raw key. These pin both directions. */

const ENGINE_RS = readFileSync(new URL("../src-tauri/src/engine.rs", import.meta.url), "utf8");
const LIB_RS = readFileSync(new URL("../src-tauri/src/lib.rs", import.meta.url), "utf8");

/** Every name `selection_status_name` can return, the `_ =>` fallback included. */
function namesFromMatchArms(): string[] {
  const fn = /pub fn selection_status_name\(code: i32\) -> &'static str \{([\s\S]*?)\n\}/.exec(ENGINE_RS);
  assert.ok(fn, "selection_status_name is gone from engine.rs - this gate reads its match arms");
  const names = [...fn[1].matchAll(/=>\s*"([a-z_]+)"/g)].map((m) => m[1]);
  assert.ok(names.length > 1, "read no names out of selection_status_name - the shape of the function changed");
  return names;
}

/** Reasons Rust emits directly, without going through the table above. */
function reasonsEmittedInline(): string[] {
  return [...LIB_RS.matchAll(/"reason":\s*"([a-z_]+)"/g)].map((m) => m[1]);
}

const SPOKEN_ELSEWHERE = new Set(["reading"]); // External.tsx has its own sentence for it

test("every reason the engine can emit has a sentence in the shell", () => {
  for (const name of [...namesFromMatchArms(), ...reasonsEmittedInline()]) {
    if (SPOKEN_ELSEWHERE.has(name)) continue;
    assert.ok(
      `status.${name}` in TEXT,
      `the engine can say ${name} and the shell has no words for it - text() would throw mid-render, and this app has no error boundary`,
    );
  }
});

test("the reason External.tsx special-cases is still the one Rust sends", () => {
  // `reading` never reaches the table: it is emitted as a literal and read by
  // a branch of its own. Rename it in Rust and that branch quietly stops
  // matching, which drops it into the same lookup that throws.
  const inline = reasonsEmittedInline();
  for (const name of SPOKEN_ELSEWHERE) {
    assert.ok(
      inline.includes(name),
      `External.tsx still special-cases ${name} but no Rust site emits it any more`,
    );
  }
});

test("no status sentence is stranded", () => {
  // The direction that rots silently: an arm renamed in Rust leaves its
  // sentence behind, and the reader gets a throw instead of the new one.
  const written = Object.keys(TEXT).filter((key) => key.startsWith("status."));
  const reachable = namesFromMatchArms().map((name) => `status.${name}`);
  assert.deepEqual(
    new Set(written),
    new Set(reachable),
    "status.* sentences and the engine's reason names have drifted apart",
  );
});
