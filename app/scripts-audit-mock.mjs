// The gate that keeps the preview harness honest: every engine call the app
// makes must have an answer in dev/mockTauri.ts.
//
// Grown from a real measurement (2026-09-04). The app made 28 distinct calls
// and the harness answered 17; the other 11 fell through to `{}`. That is not
// a small gap - it is whole screens nobody could look at. The setup screen,
// the FIRST thing a new person sees, needs `prepare_model` and
// `model.set_precision`, so in the preview it hung forever. "Chuyển ghi chú"
// needed `notes.plan`; without it the screen had two empty pickers and no way
// forward. And `pause_audio` went unanswered while the fake reading kept
// walking, so the harness taught the OPPOSITE of what the app does.
//
// An unanswered call is worse than an obviously missing feature, because the
// screen still renders - it just renders a lie. So this is a build gate and
// not a report: the moment a new call goes in, the harness gains an answer
// with it, or the build says so.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const CALL_PATTERNS = [
  /method:\s*"([a-z_.]+)"/g,          // invoke("engine_request", { method: "…" })
  /\brequest<[^>]*>\(\s*"([a-z_.]+)"/g, // the per-screen request<T>("…") helper
  /\brequest\(\s*"([a-z_.]+)"/g,
  /invoke<[^>]*>\(\s*"([a-z_]+)"/g,   // a Tauri command, typed
  /invoke\(\s*"([a-z_]+)"/g,          // …and untyped
];

const mockPath = new URL("./src/dev/mockTauri.ts", import.meta.url).pathname;
const mock = readFileSync(mockPath, "utf-8");
const answered = new Set([
  ...[...mock.matchAll(/case\s*"([a-z_.]+)"/g)].map((m) => m[1]),
  ...[...mock.matchAll(/command === "([a-z_]+)"/g)].map((m) => m[1]),
]);

const callers = new Map();
function walk(directory) {
  for (const entry of readdirSync(directory)) {
    const path = join(directory, entry);
    if (statSync(path).isDirectory()) walk(path);
    else if (/\.tsx?$/.test(path) && path !== mockPath) {
      const source = readFileSync(path, "utf-8");
      for (const pattern of CALL_PATTERNS) {
        for (const match of source.matchAll(pattern)) {
          // `engine_request` is the envelope every method rides in, not a
          // call the harness answers by name.
          if (match[1] === "engine_request") continue;
          if (!callers.has(match[1])) callers.set(match[1], new Set());
          callers.get(match[1]).add(path.split("/src/")[1]);
        }
      }
    }
  }
}
walk(new URL("./src", import.meta.url).pathname);

const missing = [...callers.keys()].filter((name) => !answered.has(name)).sort();
if (missing.length) {
  console.error(
    `MOCK_AUDIT FAIL — ${missing.length}/${callers.size} lời gọi engine không có câu trả lời trong dev/mockTauri.ts:`,
  );
  for (const name of missing) {
    console.error(`  ${name}  ←  ${[...callers.get(name)].sort().join(", ")}`);
  }
  console.error("  (một màn hình vẫn vẽ ra, chỉ là vẽ sai - thêm handler vào mock)");
  process.exit(1);
}
console.log(`MOCK_AUDIT PASS — harness trả lời đủ ${callers.size} lời gọi engine`);
