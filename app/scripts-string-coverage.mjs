/* Which interface strings has no render-audit cell ever shown?
 *
 *   node scripts-audit-render.mjs --dump-text /tmp/cells.json
 *   node --experimental-strip-types scripts-string-coverage.mjs /tmp/cells.json
 *
 * Reads the words every reached cell showed (page text plus the names,
 * tooltips and placeholders on it) and the shell's i18n table, and lists the
 * keys whose words appear in no cell of their language. A placeholder matches
 * anything; a {n|one|many} form matches either word.
 *
 * Report-only, and a floor rather than a verdict: a string can be reached only
 * by a keys check (whose pages are not dumped), or only in the real app. It is
 * a map of where no cell has looked - on 27/09 three defects in a day (the
 * cost panel's English, two dimmed rows under AA, a success drawn as an error)
 * sat in screens no cell had opened.
 */
import { readFileSync } from "node:fs";
import { TEXT } from "./src/i18n.ts";

const dump = process.argv[2];
if (!dump) {
  console.error("usage: node --experimental-strip-types scripts-string-coverage.mjs <dump.json>");
  process.exit(2);
}
const cells = JSON.parse(readFileSync(dump, "utf8"));
// Lines kept: a blank matches within one line of the page, so "Trang
// {page}/{total}" is not found in a "Trang" and a "/" a paragraph apart.
const flat = (text) => text.replace(/[^\S\n]+/g, " ");
const pages = { vi: [], en: [] };
for (const { cell, text } of cells) {
  const language = cell.split("/")[2];
  if (language in pages) pages[language].push(flat(text));
}

/** The words of one string as a pattern: what it says, with its blanks open.
 * Case counts - a label "Lưu" is not the syllable in "Sao lưu" - so a label
 * that CSS sets in capitals ("ĐANG ĐỌC" from innerText) is looked for as a
 * second, capitalised pattern. */
function pattern(words, capitals = false) {
  const escape = (literal) => literal.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const cased = (literal) => (capitals ? literal.toUpperCase() : literal);
  const said = flat(words);
  let source = "";
  let last = 0;
  for (const blank of said.matchAll(/\{(\w+)(?:\|([^|}]*)\|([^}]*))?\}/g)) {
    source += escape(cased(said.slice(last, blank.index)));
    source += blank[2] !== undefined ? `(?:${escape(cased(blank[2]))}|${escape(cased(blank[3]))})` : "[^\\n]{0,80}?";
    last = blank.index + blank[0].length;
  }
  return new RegExp(source + escape(cased(said.slice(last))), "u");
}

/* Words the Mac draws, not the page: the menu bar (appMenu.ts builds it as
   a native menu) and the Now Playing panel. No cell can show them. */
const OUTSIDE_THE_PAGE = ["menu.", "now_playing."];

const never = [];
const oneSide = [];
const strings = Object.entries(TEXT).filter(([key]) => !OUTSIDE_THE_PAGE.some((prefix) => key.startsWith(prefix)));
for (const [key, [vi, en]] of strings) {
  const shown = {
    vi: [pattern(vi), pattern(vi, true)].some((re) => pages.vi.some((page) => re.test(page))),
    en: [pattern(en), pattern(en, true)].some((re) => pages.en.some((page) => re.test(page))),
  };
  if (!shown.vi && !shown.en) never.push(key);
  else if (!shown.vi || !shown.en) oneSide.push(`${key} (${shown.vi ? "en" : "vi"} never)`);
}

const total = strings.length;
const byArea = new Map();
for (const key of never) {
  const area = key.split(".")[0];
  byArea.set(area, [...(byArea.get(area) ?? []), key]);
}
console.log(`cells ${cells.length} (vi ${pages.vi.length} · en ${pages.en.length})`);
console.log(`strings shown ${total - never.length}/${total} · never shown ${never.length} · one language only ${oneSide.length}` +
  ` (${Object.keys(TEXT).length - total} drawn by the Mac, not counted)`);
for (const [area, keys] of [...byArea].sort((a, b) => b[1].length - a[1].length)) {
  console.log(`  ${area} (${keys.length}): ${keys.join(" ")}`);
}
if (oneSide.length) console.log(`  one language only: ${oneSide.join(" · ")}`);
console.log("STRING_COVERAGE REPORT (report-only)");
