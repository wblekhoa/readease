// The gate that keeps controls.tsx the single source: raw control signatures
// outside src/ui fail the build. Grown from two real regressions where a
// class string in the middle of a screen drifted past a sweep.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const FORBIDDEN = [
  /className="[^"]*h-\[30px\][^"]*"/,
  /className="[^"]*bg-brand-600[^"]*"/,
  /<select(?![^>]*data-raw)/,
  /<textarea(?![^>]*data-raw)/,
  /className="[^"]*rounded-2xl (border border-edge(-strong|-field)? )?bg-(paper|panel)[^"]*"/,
  /text-\[1[0-9]px\]/,
  // edge-strong is the control stroke, and controls live in src/ui. Added
  // after the External "Đổi phím tắt" button turned out to be BUTTON_SIZE.sm
  // + secondary retyped by hand, straight past the h-[30px] rule.
  /border-edge-strong/,
  // Off the radius scale (surface 2xl, content lg): rounded-md is 6px.
  /rounded-md/,
  // A control's corner comes from the cluster (`--ctl-radius`), never typed
  // into a screen - a hardcoded control radius is how the Kbd and the button
  // beside it ended up 4px apart.
  /rounded-xl/,
  // Brand red is identity, never a failure state - the rule the delete confirm
  // and the transfer verdict each broke once.
  // Bare, not className-scoped: both real violations were written as a
  // conditional expression, which a className="..." pattern cannot see.
  /text-brand-600/,
];

const violations = [];
function walk(directory) {
  for (const entry of readdirSync(directory)) {
    const path = join(directory, entry);
    if (statSync(path).isDirectory()) walk(path);
    else if (path.endsWith(".tsx") && !path.includes("/ui/")) {
      const source = readFileSync(path, "utf-8");
      for (const pattern of FORBIDDEN) {
        const match = source.match(pattern);
        if (match) violations.push(`${path}: ${match[0].slice(0, 70)}`);
      }
    }
  }
}
walk(new URL("./src", import.meta.url).pathname);

// An icon-only button says nothing out loud. controls.tsx has asked for an
// aria-label in a comment since it was written ("Pass aria-label always"),
// and a comment is not a gate: an unlabelled one went in on 09/09 and only a
// rendered audit found it. This walks EVERY .tsx, src/ui included - the
// pattern layer builds icon buttons too.
function iconButtonsWithoutALabel(directory) {
  for (const entry of readdirSync(directory)) {
    const path = join(directory, entry);
    if (statSync(path).isDirectory()) { iconButtonsWithoutALabel(path); continue; }
    if (!path.endsWith(".tsx")) continue;
    const source = readFileSync(path, "utf-8");
    for (const match of source.matchAll(/<IconButton\b/g)) {
      // To the '>' that closes the opening tag, ignoring any inside a prop.
      let index = match.index + match[0].length;
      let depth = 0;
      while (index < source.length) {
        const character = source[index];
        if (character === "{") depth += 1;
        else if (character === "}") depth -= 1;
        else if (character === ">" && depth === 0) break;
        index += 1;
      }
      if (!source.slice(match.index, index).includes("aria-label")) {
        const line = source.slice(0, match.index).split("\n").length;
        violations.push(`${path}:${line}: <IconButton> không có aria-label`);
      }
    }
  }
}
iconButtonsWithoutALabel(new URL("./src", import.meta.url).pathname);

if (violations.length) {
  console.error("UI_AUDIT FAIL:");
  for (const violation of violations) console.error("  " + violation);
  process.exit(1);
}
console.log("UI_AUDIT PASS — mọi control đi qua src/ui/controls.tsx");
