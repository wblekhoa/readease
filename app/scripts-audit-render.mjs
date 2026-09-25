#!/usr/bin/env node
/**
 * RENDER_AUDIT — does every screen of the shell actually render, in every
 * state the mock backend can put it in, without a console error?
 *
 * UI_AUDIT checks that every control goes through controls.tsx and
 * MOCK_AUDIT that the harness answers every engine call; neither opens a
 * browser. This one does: headless Chrome over the DevTools protocol against
 * the dev server, one cell per (screen × mock state × language × theme), and
 * for each cell it records exceptions, console errors, i18n keys that leaked
 * into the page as text, horizontal overflow at the window floor, and
 * whether the page declares the language the cell is named for.
 *
 *   node scripts-audit-render.mjs            # against http://localhost:1420
 *   node scripts-audit-render.mjs --port N   # elsewhere
 *   node scripts-audit-render.mjs --shots DIR  # also write a PNG per cell
 *   node scripts-audit-render.mjs --no-axe   # skip the accessibility pass
 *   node scripts-audit-render.mjs --keys     # only the keyboard pass (below)
 *
 * Accessibility (HIG 4.2) rides along: axe-core runs in every cell that was
 * reached, under wcag2a/wcag2aa. Serious and critical violations are RED;
 * moderate and minor are listed to watch. Findings are grouped by rule and
 * element and printed once with the first cell that showed them - 620 cells
 * would otherwise print the same sentence six hundred times.
 *
 * The keyboard's half of HIG 4.2 (point 3) rides along too, once per run
 * and not per cell, because no scanner can see it: axe reads the page as it
 * stands, never where the focus goes when a panel opens and closes. A full
 * run ends with it; `--keys` runs it alone; `--only` leaves it out.
 *
 * Chrome is given a bounded lifetime - it is spawned, driven, and killed by
 * this process; a hang ends with a report line, never a stuck process.
 */
import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const opt = (name, fallback) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : fallback; };
const PORT = Number(opt("--port", "1420"));
const SHOTS = opt("--shots", null);
const AXE = !args.includes("--no-axe");
const ONLY = opt("--only", null); // e.g. "voices/default" narrows a run to one screen/state
const KEYS_ONLY = args.includes("--keys");
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const CDP_PORT = 9333 + Math.floor(Math.random() * 500);
const W = 960, H = 600; // tauri.conf.json minWidth/minHeight - the floor a person can shrink to

// Every key the interface can print, so a leaked one is recognisable by name.
const I18N = readFileSync(join(HERE, "src/i18n.ts"), "utf8");
// axe-core is a dev dependency; its source is read once and injected per page.
const AXE_SOURCE = AXE ? readFileSync(join(HERE, "node_modules/axe-core/axe.min.js"), "utf8") : "";
const KEYS = new Set([...I18N.matchAll(/^  "([a-z_]+\.[a-z_0-9]+)"/gm)].map((m) => m[1]));

// The matrix. Screens are reached by clicking; states by query string.
//
// Navigation lives in the side column (HIG 3.16), which folds itself at
// this window's 960px - so every path starts by unfolding it, the way a
// person would: through the mode switch by the title, whose menu carries
// "Cột bên" while the column is folded. "click?" is a click that is allowed
// to find nothing (in the `sidebar` state the column is already open and
// the menu has no such row; the menu itself then closes on the next click).
const UNFOLD = [["click?", /^Đổi chế độ$|^Switch mode$/], ["click?", /^Cột bên|^Side column/]];
const OPEN_BOOK = [...UNFOLD, ["click", /^Thư viện$|^Library$/], ["click", /^(Mở|Open) (?!PDF)(?!a PDF)/], ["wait", /^Quay lại thư viện$|^Back to library$/]];
const SCREENS = {
  shelf:  [...UNFOLD, ["click", /^Thư viện$|^Library$/]],
  paste:  [...UNFOLD, ["click", /^Dán nội dung$|^Paste text$/]],
  scan:   [...UNFOLD, ["click", /^Quét đọc$|^Read a selection$/]],
  notes:  [...UNFOLD, ["click", /^Chuyển ghi chú$|^Move notes$/]],
  reader: OPEN_BOOK,
  voices: [...OPEN_BOOK,
           ["click", /^Cài đặt giọng đọc$|^Voice settings$/], ["click", /^Quản lý giọng|^Manage voices/], ["wait", /^Danh sách giọng đọc$|^Voices$/]],
  // The hub, from the gear in the column's foot (or the toolbar while the
  // column is folded): the sheet's title is what the wait looks for.
  hub: [...UNFOLD, ["click", /^Thư viện$|^Library$/], ["click", /^Giọng đọc & mô hình$|^Voices & models$/], ["wait", /^Giọng đọc & mô hình$|^Voices & models$/]],
  // A book's three lists, as tabs of the side column (HIG 3.16): each
  // toolbar switch opens the column on its tab, and the tab's own label is
  // the sign it is up.
  // A book opens on its contents when the column is up, so the switch may
  // already read "Ẩn mục lục": pressing it then would fold the column.
  contents: [...OPEN_BOOK, ["click?", /^Hiện mục lục$|^Show contents$/], ["wait", /^Mục lục$|^Contents$/]],
  // The notes tab is named by its count ("3 highlight") and the search tab
  // like the toolbar's search button, so each is proven by what only the
  // open tab has: the checked radio for notes, the search box for search.
  book_notes: [...OPEN_BOOK, ["click", /^Highlight và ghi chú$|^Highlights and notes$/], ["wait", /^\d+ highlights?$/]],
  search: [...OPEN_BOOK, ["click", /^Tìm trong tài liệu$|^Search in document$/], ["wait", /^Tìm trong tài liệu$|^Search in document$/, "[role=radio]"]],
  // The two floating settings panels over an open document (HIG 4.2): until
  // 23/09 no cell opened either, so axe had never seen a control in them -
  // and four of their selects had no name. The reading panel opens its finer
  // choices too, or the sliders and switches under "Tuỳ chỉnh" stay unseen.
  player_settings: [...OPEN_BOOK, ["click", /^Cài đặt giọng đọc$|^Voice settings$/], ["wait", /^Cài đặt giọng đọc$|^Voice settings$/, "[role=dialog]"]],
  reading_settings: [...OPEN_BOOK, ["click", /^Cài đặt đọc$|^Reading settings$/], ["wait", /^Cài đặt đọc$|^Reading settings$/, "[role=dialog]"],
    ["click", /^Tuỳ chỉnh$|^Customize$/], ["wait", /^Giãn dòng$|^Line spacing$/, "input"]],
  // A picture opened large (HIG 3.10). Its ground is black in both themes,
  // where line art on a transparent ground disappears - so the cell exists
  // to measure the sheet the picture sits on (25/09). The picture is opened
  // the way its click handler is reached, not by where it happens to be on
  // the page: every chapter's figures are in the DOM, most off-page.
  // Reached through the contents, like a reader would: the sample's sketch
  // on a transparent ground sits in "Chương 6 Bài tập 02".
  lightbox: [...OPEN_BOOK, ["click?", /^Hiện mục lục$|^Show contents$/], ["click", /Bài tập 02/],
    ["open-figure"], ["wait", /^Đóng ảnh$|^Close image$/]],
};
// A panel is opened only in the states that change what is in it. The two
// settings panels follow the models and the voice, not the library's
// states: opened in all sixteen they would add 120 cells (~6 min of a
// ~31 min run) saying the same thing, for these 28.
const ONLY_IN = {
  player_settings: ["default", "sidebar", "english_missing", "english_partial", "vietnamese_missing"],
  reading_settings: ["default", "sidebar"],
  lightbox: ["default"],
};
const STATES = {
  default: "",
  empty: "empty=all",
  fail: "fail=1",
  keyfail: "keyfail=bad_key",
  voicefail: "voicefail=quota",
  unreachable: "unreachable=openai",
  permission: "permission=missing",
  model_missing: "model=missing",
  scanned: "scanned=3",
  damaged: "damaged=1",
  dragging: "drag=3",
  dragnone: "drag=none",
  english_missing: "english=missing",
  english_partial: "english=partial",
  vietnamese_missing: "vietnamese=missing",
  // The side column unfolded at the 960px floor, where it folds itself:
  // the "không tràn ngang" that matters most (HIG 3.16, C9).
  sidebar: "sidebar=open",
};
const LANGS = ["vi", "en"];
const THEMES = ["light", "dark"];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${CDP_PORT}`,
    `--window-size=${W},${H}`, `--user-data-dir=/tmp/readease-render-audit-${process.pid}`, "about:blank",
  ], { stdio: "ignore" });
  // A bound on a hung Chrome, not a budget: the full matrix (412 cells)
  // took 14m34s+ on 15/09 once the mock's bridge answered a tick later, a
  // minute under the old 15, so the next state added would have turned a
  // green run red for taking too long.
  const killer = setTimeout(() => { console.error("RENDER_AUDIT RED chrome lifetime exceeded"); chrome.kill("SIGKILL"); process.exit(2); }, 60 * 60 * 1000); // 620 cells took 31 min run screen by screen (16/09); 35 was cut twice; 648 with the two settings panels took 31m38s (23/09)
  try {
    const wsUrl = await (async () => {
      for (let i = 0; i < 60; i++) {
        try { const l = await (await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`)).json(); const p = l.find((t) => t.type === "page"); if (p) return p.webSocketDebuggerUrl; } catch {}
        await sleep(250);
      }
      throw new Error("chrome did not come up");
    })();
    const ws = new WebSocket(wsUrl);
    await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
    let id = 0; const pending = new Map(); const events = [];
    ws.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
      else if (m.method) events.push(m);
    };
    const send = (method, params = {}) => new Promise((r) => { const n = ++id; pending.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
    const evalJs = async (expression) => { const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }); return r.result?.result?.value; };
    await send("Page.enable"); await send("Runtime.enable"); await send("Log.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });

    // A click lands only once its target exists: the shelf is still being
    // drawn when the tab switch returns, and a click fired into that gap
    // reached nothing - one cell in 216 read as unreachable on the second
    // full run, and three re-probes with a wait in front reached it every
    // time.
    // A picture of the document, opened large: its images arrive a
    // tick after the text, so wait for one before clicking it.
    const openFigure = async () => {
      // The sketch on a transparent ground - the picture the sheet exists
      // for - and only when it never arrives, the first picture there is.
      for (const selector of ['[data-figure="fig-lineart"] img', "[data-figure] img"]) {
        for (let i = 0; i < 40; i++) {
          const opened = await evalJs(`(() => { const img = document.querySelector(${JSON.stringify(selector)}); if (!img) return false; img.click(); return true; })()`);
          if (opened) { await sleep(350); return true; }
          await sleep(150);
        }
      }
      return false;
    };
    const findAndClick = async (re, patience = 4000) => {
      await waitFor(re, patience);
      // The first VISIBLE match, as a hand would find it: the folded column
      // keeps its tabs in the DOM at zero width behind \`inert\`, and a tab
      // named like the toolbar button ("Tìm trong tài liệu") used to be
      // found first and clicked at the fold (16/09, search unreachable).
      const box = await evalJs(`(() => {
        const re = ${re.toString()};
        const el = [...document.querySelectorAll("button,[role=button],[role=radio],[role=tab],a,summary")]
          .find((e) => re.test((e.getAttribute("aria-label") || e.textContent || "").trim())
            && !e.closest("[inert]") && e.getBoundingClientRect().width > 0);
        if (!el) return null; el.scrollIntoView({ block: "center" }); const r = el.getBoundingClientRect();
        return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()`);
      if (!box) return false;
      for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) await send("Input.dispatchMouseEvent", { type, x: box.x, y: box.y, button: "left", clickCount: 1 });
      await sleep(350); return true;
    };
    // A name is an aria-label, a placeholder (an input's name) or the text;
    // a radio counts only while CHECKED, so waiting on a tab's name proves
    // the tab is the one showing, not merely that the row of tabs exists.
    async function waitFor(re, ms = 6000, within = "button,[role=button],[role=radio],a,h1,h2,h3,input,textarea") {
      const until = Date.now() + ms;
      while (Date.now() < until) {
        if (await evalJs(`!![...document.querySelectorAll(${JSON.stringify(within)})]
          .find((e) => ${re.toString()}.test((e.getAttribute("aria-label") || e.getAttribute("placeholder") || e.textContent || "").trim())
            && (e.getAttribute("role") !== "radio" || e.getAttribute("aria-checked") === "true"))`)) return true;
        await sleep(150);
      }
      return false;
    }
    // Every cell states its language instead of inheriting one. The mock
    // keeps its settings in localStorage so they outlive a reload, as the
    // engine's do - so the English one cell switched to used to carry into
    // every cell after it, and "vi" cells past the first state were drawn in
    // English (measured 23/09: 6 of the 8 "vi" cells of a 16-cell run).
    // Written before the page loads, so the language is there from the
    // first frame; the page is on this origin from the first navigation on.
    const seedLanguage = (lang) => evalJs(`(() => { try {
      const key = "readease.mock-settings";
      const saved = JSON.parse(localStorage.getItem(key) || "{}");
      saved.ui_language = ${JSON.stringify(lang)};
      localStorage.setItem(key, JSON.stringify(saved));
      return true;
    } catch { return false; } })()`);
    await send("Page.navigate", { url: `http://localhost:${PORT}/?` });
    await sleep(900);

    if (SHOTS) mkdirSync(SHOTS, { recursive: true });
    const findings = []; let cells = 0;
    // (rule + element) -> where it was first seen. Deduplicated because the
    // same button is the same button in 620 cells.
    const axeSeen = new Map();
    for (const [stateName, query] of KEYS_ONLY ? [] : Object.entries(STATES)) {
      for (const lang of LANGS) {
        for (const theme of THEMES) {
          await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: theme }] });
          for (const screen of Object.keys(SCREENS)) {
            const cell = `${screen}/${stateName}/${lang}/${theme}`;
            if (ONLY && !cell.startsWith(ONLY)) continue;
            if (ONLY_IN[screen] && !ONLY_IN[screen].includes(stateName)) continue;
            cells++;
            // With no model on the machine the shell shows the setup screen
            // and nothing else - there are no tabs to reach. That screen is
            // the cell; walking to a tab would be walking into a wall.
            const steps = stateName === "model_missing" ? [["wait", /Chọn cách đọc để bắt đầu|Choose how to read/]] : SCREENS[screen];
            // An empty shelf has no book to open: the reader and the voice
            // panel do not exist in that state, so neither does the cell.
            if (stateName === "empty" && ["reader", "voices", "contents", "book_notes", "search"].includes(screen)) { cells--; continue; }
            events.length = 0;
            if (!(await seedLanguage(lang))) { findings.push({ cell, kind: "lang", detail: "could not set the cell's language" }); continue; }
            await send("Page.navigate", { url: `http://localhost:${PORT}/?${query}` });
            await sleep(900);
            await evalJs(`localStorage.removeItem("readease.theme")`);
            let reached = true;
            // A wait may name WHERE to look (a third element, a selector):
            // the search tab, its box and the toolbar's search button all
            // carry one name, and only the checked tab proves the panel.
            for (const [kind, re, within] of steps) {
              const ok = kind === "click" ? await findAndClick(re)
                : kind === "click?" ? (await findAndClick(re, 600), true)
                : kind === "open-figure" ? await openFigure()
                : await waitFor(re, 6000, within);
              if (!ok) { reached = false; findings.push({ cell, kind: "unreachable", detail: `${kind} ${re}` }); break; }
            }
            if (!reached) continue;
            await sleep(500);
            const errs = events.filter((m) =>
              m.method === "Runtime.exceptionThrown" ||
              (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") ||
              (m.method === "Log.entryAdded" && m.params.entry.level === "error"));
            for (const m of errs) {
              const detail = m.method === "Runtime.exceptionThrown" ? (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text)
                : m.method === "Log.entryAdded" ? m.params.entry.text
                : m.params.args.map((a) => a.value ?? a.description ?? "").join(" ");
              findings.push({ cell, kind: "console", detail: String(detail).split("\n")[0].slice(0, 200) });
            }
            const probe = await evalJs(`(() => {
              const text = document.body.innerText;
              const leaked = [...new Set((text.match(/\\b[a-z_]+\\.[a-z_0-9]+\\b/g) || []))];
              const over = [...document.querySelectorAll("*")].filter((e) => { const s = getComputedStyle(e); return e.scrollWidth > e.clientWidth + 1 && s.overflowX !== "auto" && s.overflowX !== "scroll" && s.overflowX !== "hidden" && e.clientWidth > 0; })
                .map((e) => e.tagName.toLowerCase() + (e.className && typeof e.className === "string" ? "." + e.className.split(" ").slice(0, 2).join(".") : "")).slice(0, 4);
              let voice; try { voice = JSON.parse(localStorage.getItem("readease.mock-settings") || "{}").voice; } catch {}
              const plates = [...document.querySelectorAll("[data-figure] img")].map((img) => getComputedStyle(img).backgroundColor);
              const large = document.querySelector("[data-lightbox] img");
              const lightboxPlate = large ? getComputedStyle(large).backgroundColor : null;
              return { leaked, over, docWide: document.documentElement.scrollWidth > document.documentElement.clientWidth, themeAttr: document.documentElement.dataset.theme, textLen: text.length, voice, htmlLang: document.documentElement.lang, plates, lightboxPlate }; })()`);
            for (const k of probe.leaked) if (KEYS.has(k)) findings.push({ cell, kind: "i18n-leak", detail: k });
            // No cell picks a voice, so the saved one (the mock's "Thu Hà")
            // must still be the saved one after the walk. Start-up once
            // overwrote it with the first voice before reading it (15/09),
            // in a gap only a bridge that answers a tick later opens.
            if (probe.voice !== undefined && probe.voice !== "Thu Hà") findings.push({ cell, kind: "voice-lost", detail: `saved voice became ${probe.voice}` });
            if (probe.docWide) findings.push({ cell, kind: "overflow-x", detail: `document scrolls horizontally at ${W}px` + (probe.over.length ? ` (${probe.over.join(", ")})` : "") });
            if (probe.themeAttr !== theme) findings.push({ cell, kind: "theme", detail: `data-theme=${probe.themeAttr}, wanted ${theme}` });
            // The page says which language it is in (WCAG 3.1.1): VoiceOver
            // picks its voice from <html lang>, and a cell is only the
            // language it claims if the page agrees.
            if (probe.htmlLang !== lang) findings.push({ cell, kind: "lang", detail: `<html lang="${probe.htmlLang}">, wanted ${lang}` });
            if (probe.textLen < 20) findings.push({ cell, kind: "blank", detail: `only ${probe.textLen} chars of text` });
            // Pictures sit on a sheet of paper where their ground is dark
            // (HIG 3.9, 3.10): on the dark page, and in the lightbox in both
            // themes. Line art on a transparent ground was drawn for white.
            const PAPER = "rgb(255, 255, 255)";
            const bare = theme === "dark" ? probe.plates.filter((c) => c !== PAPER) : [];
            if (bare.length) findings.push({ cell, kind: "figure-plate", detail: `${bare.length}/${probe.plates.length} pictures on the dark page have no sheet (${bare[0]})` });
            if (probe.lightboxPlate !== null && probe.lightboxPlate !== PAPER) findings.push({ cell, kind: "figure-plate", detail: `the picture in the lightbox has no sheet (${probe.lightboxPlate})` });
            if (screen === "lightbox" && probe.lightboxPlate === null) findings.push({ cell, kind: "figure-plate", detail: "the lightbox did not open" });
            if (AXE) {
              // Injected per navigation (the page was reloaded for this cell),
              // then run against the whole document. `axe.run` resolves with
              // violations; a failure to load must not pass as "clean".
              await evalJs(AXE_SOURCE);
              const report = await evalJs(`(async () => {
                try {
                  const found = await axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa"] }, resultTypes: ["violations"] });
                  return { ok: true, violations: found.violations.map((v) => ({ id: v.id, impact: v.impact,
                    targets: v.nodes.slice(0, 3).map((n) => String(n.target[0]).slice(0, 80)) })) };
                } catch (error) { return { ok: false, error: String((error && error.message) || error) }; }
              })()`);
              if (!report || !report.ok) findings.push({ cell, kind: "axe-failed", detail: report?.error || "axe did not answer" });
              else for (const violation of report.violations) for (const target of violation.targets) {
                const key = `${violation.id} ${target}`;
                if (!axeSeen.has(key)) axeSeen.set(key, { cell, impact: violation.impact || "minor", id: violation.id, target });
              }
            }
            if (SHOTS) { const { result } = await send("Page.captureScreenshot", { format: "png" }); writeFileSync(join(SHOTS, cell.replaceAll("/", "__") + ".png"), Buffer.from(result.data, "base64")); }
          }
        }
      }
    }
    // The keyboard's way through the floating layers (HIG 4.2, point 3). A
    // panel opened with Enter holds the focus and Escape hands it back to
    // the button that opened it - also through a panel opened from inside
    // another, whose row is gone by then; a menu puts the focus on its first
    // item and the arrows move it; a sheet over the scrim keeps Tab inside
    // it. And a MOUSE click moves nothing: the opener lets go of the focus,
    // nothing is pulled into the panel and no tooltip is left hanging over it
    // (owner, 06/09 and 16/09). Vietnamese, light, the default state.
    let keyChecks = 0;
    if (KEYS_ONLY || !ONLY) {
      const CODES = { Enter: 13, Escape: 27, Tab: 9, ArrowDown: 40, ArrowUp: 38 };
      const key = async (name, { shift = false, pause = 350 } = {}) => {
        const base = { key: name, code: name, windowsVirtualKeyCode: CODES[name], modifiers: shift ? 8 : 0 };
        await send("Input.dispatchKeyEvent", { type: "keyDown", ...base, ...(name === "Enter" ? { text: "\r" } : {}) });
        await send("Input.dispatchKeyEvent", { type: "keyUp", ...base });
        await sleep(pause);
      };
      // Put the focus on a button by its name, the way Tab would have left
      // it; `mark` makes it the opener the checks below expect to get back.
      const focusOn = (re, { inDialog = false, mark = true } = {}) => evalJs(`(() => {
        const re = ${re.toString()};
        const scope = ${inDialog ? 'document.querySelector("[role=dialog]")' : "document"};
        const el = scope && [...scope.querySelectorAll("button,[role=button]")]
          .find((e) => re.test((e.getAttribute("aria-label") || e.textContent || "").trim())
            && !e.closest("[inert]") && e.getBoundingClientRect().width > 0);
        if (!el) return false;
        if (${mark}) {
          document.querySelectorAll("[data-audit-opener]").forEach((e) => e.removeAttribute("data-audit-opener"));
          el.setAttribute("data-audit-opener", "");
        }
        el.focus(); return true; })()`);
      const where = () => evalJs(`(() => { const a = document.activeElement;
        return { body: !a || a === document.body, opener: !!(a && a.hasAttribute && a.hasAttribute("data-audit-opener")),
          dialog: (a && a.closest && a.closest("[role=dialog]") && a.closest("[role=dialog]").getAttribute("aria-label")) || null,
          item: a && a.getAttribute && a.getAttribute("role") === "menuitem" ? a.textContent.trim() : null,
          tip: !!document.querySelector("[role=tooltip]") }; })()`);
      const said = (w) => w.body ? "the page itself" : w.item ? `menu item "${w.item}"` : w.dialog ? `the panel "${w.dialog}"` : w.opener ? "the opener" : "some other control";
      const expect = (scenario, ok, detail) => { keyChecks++; if (!ok) findings.push({ cell: `keys/${scenario}`, kind: "keys", detail }); };
      const goto = async (steps) => {
        events.length = 0;
        await seedLanguage("vi");
        await send("Page.navigate", { url: `http://localhost:${PORT}/?` });
        await sleep(900);
        await evalJs(`localStorage.removeItem("readease.theme")`);
        for (const [kind, re, within] of steps) {
          const ok = kind === "click" ? await findAndClick(re)
            : kind === "click?" ? (await findAndClick(re, 600), true)
            : await waitFor(re, 6000, within);
          if (!ok) return false;
        }
        await sleep(400);
        return true;
      };
      const crashed = (scenario) => {
        for (const m of events) if (m.method === "Runtime.exceptionThrown") findings.push({ cell: `keys/${scenario}`, kind: "console", detail: String(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text).split("\n")[0].slice(0, 200) });
      };
      const inAndBack = async (scenario, trigger) => {
        if (!(await focusOn(trigger))) return expect(scenario, false, `no button named ${trigger}`);
        await key("Enter");
        let w = await where();
        expect(scenario, !!w.dialog, `Enter left the focus on ${said(w)}, not in the panel it opened`);
        await key("Escape");
        w = await where();
        expect(scenario, w.opener, `Escape left the focus on ${said(w)}, not on the button that opened the panel`);
      };
      await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });

      if (!(await goto(OPEN_BOOK))) expect("reader", false, "could not open a document");
      else {
        await inAndBack("reading-settings", /^Cài đặt đọc$/);
        await inAndBack("voice-settings", /^Cài đặt giọng đọc$/);
        // A picture opens large from the keyboard and hands the focus back
        // (HIG 3.10, 25/09): it was an <img> with a click handler, which
        // Tab never reached.
        await inAndBack("figure", /^Xem ảnh lớn/);
        // A panel opened from a row of another, which closes as it opens.
        if (!(await focusOn(/^Cài đặt giọng đọc$/))) expect("manage-voices", false, "no voice settings button");
        else {
          await key("Enter");
          if (!(await focusOn(/^Quản lý giọng/, { inDialog: true, mark: false }))) expect("manage-voices", false, "no Manage voices row in the voice settings");
          else {
            await key("Enter");
            let w = await where();
            expect("manage-voices", !!w.dialog && w.dialog !== "Cài đặt giọng đọc", `Enter on Manage voices left the focus on ${said(w)}`);
            await key("Escape");
            w = await where();
            expect("manage-voices", w.opener, `Escape left the focus on ${said(w)}, not on the voice settings button in the footer`);
          }
        }
        // The mouse: nothing moves, no tooltip over the panel.
        if (!(await findAndClick(/^Cài đặt đọc$/))) expect("mouse", false, "no reading settings button");
        else {
          const w = await where();
          expect("mouse", !w.dialog && !w.opener, `a mouse click put the focus on ${said(w)}`);
          expect("mouse", !w.tip, "a tooltip hangs over the panel a mouse click opened");
          await findAndClick(/^Cài đặt đọc$/);
        }
        // The transport is a named group (HIG 4.2, point 1): VoiceOver says
        // what the buttons are FOR before it reads them one by one. No cell
        // of the matrix is mid-reading, so this is the only place it is seen.
        if (!(await findAndClick(/^Đọc tiếp$/))) expect("transport", false, "no Continue button to start a reading");
        else if (!(await waitFor(/^Tạm dừng$/, 6000, "button"))) expect("transport", false, "the reading did not start");
        else {
          const group = await evalJs(`(() => { const pause = [...document.querySelectorAll("button")].find((b) => b.getAttribute("aria-label") === "Tạm dừng");
            const g = pause && pause.closest("[role=group]"); return g ? (g.getAttribute("aria-label") || "") : null; })()`);
          expect("transport", !!group, group === null ? "the transport is not a group" : "the transport group has no name");
          // The bar is at the bottom of the window, so its voice menu opens
          // up, where it can be seen (owner, 25/09: opened down, it fell out
          // of the window and nothing showed).
          if (!(await findAndClick(/^Đổi giọng$/))) expect("transport", false, "no Change voice button while reading");
          else {
            const box = await evalJs(`(() => { const m = document.querySelector('[role="menu"]'); if (!m) return null;
              const r = m.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: innerHeight }; })()`);
            expect("transport", !!box && box.top >= 0 && box.bottom <= box.height,
              box ? `the Change voice menu spans ${Math.round(box.top)}-${Math.round(box.bottom)} px of a ${box.height} px window` : "the Change voice menu did not open");
            await key("Escape");
          }
          await findAndClick(/^Dừng$/);
        }
        crashed("reader");
      }

      if (!(await goto([]))) expect("menu", false, "home did not load");
      else {
        if (!(await focusOn(/^Đổi chế độ$/))) expect("menu", false, "no mode switch");
        else {
          await key("Enter");
          let w = await where();
          const first = w.item;
          expect("menu", !!first, `Enter left the focus on ${said(w)}, not on the menu's first item`);
          await key("ArrowDown");
          w = await where();
          expect("menu", !!w.item && w.item !== first, `ArrowDown left the focus on ${said(w)}`);
          await key("Escape");
          w = await where();
          expect("menu", w.opener, `Escape left the focus on ${said(w)}, not on the mode switch`);
        }
        crashed("menu");
      }

      if (!(await goto([...UNFOLD, ["click", /^Thư viện$|^Library$/]]))) expect("sheet", false, "could not reach the library");
      else {
        if (!(await focusOn(/^Giọng đọc & mô hình$/))) expect("sheet", false, "no hub button");
        else {
          await key("Enter");
          let w = await where();
          expect("sheet", w.dialog === "Giọng đọc & mô hình", `Enter left the focus on ${said(w)}, not in the sheet`);
          let escaped = null;
          for (let i = 0; i < 24 && !escaped; i++) {
            await key("Tab", { shift: i % 3 === 2, pause: 60 });
            const at = await where();
            if (at.dialog !== "Giọng đọc & mô hình") escaped = at;
          }
          expect("sheet", !escaped, `Tab left the sheet for ${escaped ? said(escaped) : ""}`);
          await key("Escape");
          w = await where();
          expect("sheet", w.opener, `Escape left the focus on ${said(w)}, not on the hub button`);
        }
        crashed("sheet");
      }

      // The basic journey, the level the owner chose (HIG 4.2, 25/09): import
      // a document, choose one, read and pause - from the library, by Tab,
      // Enter and Space alone. The focus is moved by Tab, never set by the
      // script, so a control Tab cannot reach fails here even with a name.
      const nameOf = () => evalJs(`(() => { const a = document.activeElement;
        if (!a || a === document.body) return "";
        return (a.getAttribute("aria-label") || a.textContent || "").trim().replace(/\\s+/g, " "); })()`);
      const tabTo = async (re, most = 80) => {
        for (let i = 0; i < most; i++) {
          await key("Tab", { pause: 40 });
          if (re.test(await nameOf())) return true;
        }
        return false;
      };
      const liveSays = () => evalJs(`(() => { const live = document.querySelector('.sr-only[aria-live="polite"]');
        return live ? live.textContent.trim() : null; })()`);
      const shelfCount = () => evalJs(`document.querySelectorAll('button[aria-label^="Mở "]:not([aria-label^="Mở PDF"])').length`);
      const space = async () => {
        const base = { key: " ", code: "Space", windowsVirtualKeyCode: 32 };
        await send("Input.dispatchKeyEvent", { type: "keyDown", ...base, text: " " });
        await send("Input.dispatchKeyEvent", { type: "keyUp", ...base });
        await sleep(500);
      };
      if (!(await goto([...UNFOLD, ["click", /^Thư viện$|^Library$/]]))) expect("journey", false, "could not reach the library");
      else {
        await evalJs(`document.activeElement && document.activeElement.blur()`);
        const before = await shelfCount();
        if (!(await tabTo(/^Mở PDF hoặc EPUB$/))) expect("journey", false, 'Tab never reached "Mở PDF hoặc EPUB"');
        else {
          await key("Enter", { pause: 1200 });
          const after = await shelfCount();
          expect("journey", after > before, `Enter on "Mở PDF hoặc EPUB" imported nothing (${before} -> ${after} documents)`);
        }
        await evalJs(`document.activeElement && document.activeElement.blur()`);
        if (!(await tabTo(/^Mở (?!PDF)/))) expect("journey", false, "Tab never reached a document on the shelf");
        else {
          const chosen = await nameOf();
          await key("Enter", { pause: 600 });
          const opened = await waitFor(/^Quay lại thư viện$/, 6000);
          expect("journey", opened, `Enter on "${chosen}" did not open it`);
          if (opened) {
            if (!(await tabTo(/^Đọc tiếp$|^Đọc từ đầu$/))) expect("journey", false, "Tab never reached the read button");
            else {
              await key("Enter", { pause: 400 });
              const reading = await waitFor(/^Tạm dừng$/, 8000, "button");
              expect("journey", reading, "Enter on the read button did not start the reading");
              const started = await liveSays();
              expect("journey", /chuẩn bị|Bắt đầu đọc/.test(started || ""), `the live region said "${started}" when the reading started`);
              if (reading) {
                await space();
                const paused = await liveSays();
                expect("journey", paused === "Đã tạm dừng", `Space during the reading left the live region at "${paused}", not "Đã tạm dừng"`);
                await findAndClick(/^Dừng$/);
              }
            }
          }
        }
        crashed("journey");
      }
    }

    ws.close();
    // Serious and critical fail the gate; the rest are printed to watch.
    const axeFindings = [...axeSeen.values()];
    const blocking = axeFindings.filter((a) => a.impact === "serious" || a.impact === "critical");
    const watching = axeFindings.filter((a) => !(a.impact === "serious" || a.impact === "critical"));
    for (const a of watching) console.log(`  axe-watch   ${a.cell.padEnd(34)} ${a.impact} ${a.id} ${a.target}`);
    for (const a of blocking) findings.push({ cell: a.cell, kind: "axe", detail: `${a.impact} ${a.id} ${a.target}` });
    const byKind = {}; for (const f of findings) byKind[f.kind] = (byKind[f.kind] || 0) + 1;
    for (const f of findings) console.log(`  ${f.kind.padEnd(11)} ${f.cell.padEnd(34)} ${f.detail}`);
    const summary = Object.entries(byKind).map(([k, v]) => `${k}=${v}`).join(" ") || "clean";
    if (findings.length) { console.log(`RENDER_AUDIT RED cells=${cells} ${summary}`); process.exitCode = 1; }
    else if (KEYS_ONLY) console.log(`RENDER_AUDIT PASS keys=${keyChecks} — bàn phím vào được lớp nổi và về đúng nút, chuột không đổi gì, nhóm điều khiển đọc có tên`);
    else console.log(`RENDER_AUDIT PASS cells=${cells}${AXE ? ` axe-watch=${watching.length}` : " (axe skipped)"}${keyChecks ? ` keys=${keyChecks}` : ""} — mọi màn render ở ${W}×${H}, không lỗi console, không lộ key, không tràn ngang`);
  } finally { clearTimeout(killer); chrome.kill("SIGKILL"); }
}
main().catch((e) => { console.error(`RENDER_AUDIT RED ${e.message}`); process.exit(2); });
