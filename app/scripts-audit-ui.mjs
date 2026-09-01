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
if (violations.length) {
  console.error("UI_AUDIT FAIL — control thô ngoài src/ui:");
  for (const violation of violations) console.error("  " + violation);
  process.exit(1);
}
console.log("UI_AUDIT PASS — mọi control đi qua src/ui/controls.tsx");
