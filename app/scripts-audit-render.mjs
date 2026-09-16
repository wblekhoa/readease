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
 * into the page as text, and horizontal overflow at the window floor.
 *
 *   node scripts-audit-render.mjs            # against http://localhost:1420
 *   node scripts-audit-render.mjs --port N   # elsewhere
 *   node scripts-audit-render.mjs --shots DIR  # also write a PNG per cell
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
const ONLY = opt("--only", null); // e.g. "voices/default" narrows a run to one screen/state
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const CDP_PORT = 9333 + Math.floor(Math.random() * 500);
const W = 960, H = 600; // tauri.conf.json minWidth/minHeight - the floor a person can shrink to

// Every key the interface can print, so a leaked one is recognisable by name.
const I18N = readFileSync(join(HERE, "src/i18n.ts"), "utf8");
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
  book_notes: [...OPEN_BOOK, ["click", /^Highlight và ghi chú$|^Highlights and notes$/], ["wait", /^Ghi chú( · \d+)?$|^Notes( · \d+)?$/]],
  search: [...OPEN_BOOK, ["click", /^Tìm trong sách$|^Search in book$/], ["wait", /^Tìm$|^Search$/]],
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
  const killer = setTimeout(() => { console.error("RENDER_AUDIT RED chrome lifetime exceeded"); chrome.kill("SIGKILL"); process.exit(2); }, 35 * 60 * 1000); // 620 cells at ~2.3 s each (16/09)
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
    const findAndClick = async (re, patience = 4000) => {
      await waitFor(re, patience);
      const box = await evalJs(`(() => {
        const re = ${re.toString()};
        const el = [...document.querySelectorAll("button,[role=button],[role=radio],[role=tab],a,summary")]
          .find((e) => re.test((e.getAttribute("aria-label") || e.textContent || "").trim()));
        if (!el) return null; el.scrollIntoView({ block: "center" }); const r = el.getBoundingClientRect();
        return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()`);
      if (!box) return false;
      for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) await send("Input.dispatchMouseEvent", { type, x: box.x, y: box.y, button: "left", clickCount: 1 });
      await sleep(350); return true;
    };
    async function waitFor(re, ms = 6000) {
      const until = Date.now() + ms;
      while (Date.now() < until) {
        if (await evalJs(`!![...document.querySelectorAll("button,[role=button],a,h1,h2,h3")].find((e) => ${re.toString()}.test((e.getAttribute("aria-label") || e.textContent || "").trim()))`)) return true;
        await sleep(150);
      }
      return false;
    }
    const setLanguage = async (lang) => {
      await evalJs(`(() => { const s = document.querySelector('select[aria-label]'); if (!s) return false;
        const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value").set; setter.call(s, ${JSON.stringify(lang)});
        s.dispatchEvent(new Event("change", { bubbles: true })); return true; })()`);
      await sleep(300);
    };

    if (SHOTS) mkdirSync(SHOTS, { recursive: true });
    const findings = []; let cells = 0;
    for (const [stateName, query] of Object.entries(STATES)) {
      for (const lang of LANGS) {
        for (const theme of THEMES) {
          await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: theme }] });
          for (const screen of Object.keys(SCREENS)) {
            const cell = `${screen}/${stateName}/${lang}/${theme}`;
            if (ONLY && !cell.startsWith(ONLY)) continue;
            cells++;
            // With no model on the machine the shell shows the setup screen
            // and nothing else - there are no tabs to reach. That screen is
            // the cell; walking to a tab would be walking into a wall.
            const steps = stateName === "model_missing" ? [["wait", /Chọn cách đọc để bắt đầu|Choose how to read/]] : SCREENS[screen];
            // An empty shelf has no book to open: the reader and the voice
            // panel do not exist in that state, so neither does the cell.
            if (stateName === "empty" && ["reader", "voices", "contents", "book_notes", "search"].includes(screen)) { cells--; continue; }
            events.length = 0;
            await send("Page.navigate", { url: `http://localhost:${PORT}/?${query}` });
            await sleep(900);
            await evalJs(`localStorage.removeItem("readease.theme")`);
            if (lang === "en") await setLanguage("en");
            let reached = true;
            for (const [kind, re] of steps) {
              const ok = kind === "click" ? await findAndClick(re)
                : kind === "click?" ? (await findAndClick(re, 600), true)
                : await waitFor(re);
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
              return { leaked, over, docWide: document.documentElement.scrollWidth > document.documentElement.clientWidth, themeAttr: document.documentElement.dataset.theme, textLen: text.length, voice }; })()`);
            for (const k of probe.leaked) if (KEYS.has(k)) findings.push({ cell, kind: "i18n-leak", detail: k });
            // No cell picks a voice, so the saved one (the mock's "Thu Hà")
            // must still be the saved one after the walk. Start-up once
            // overwrote it with the first voice before reading it (15/09),
            // in a gap only a bridge that answers a tick later opens.
            if (probe.voice !== undefined && probe.voice !== "Thu Hà") findings.push({ cell, kind: "voice-lost", detail: `saved voice became ${probe.voice}` });
            if (probe.docWide) findings.push({ cell, kind: "overflow-x", detail: `document scrolls horizontally at ${W}px` + (probe.over.length ? ` (${probe.over.join(", ")})` : "") });
            if (probe.themeAttr !== theme) findings.push({ cell, kind: "theme", detail: `data-theme=${probe.themeAttr}, wanted ${theme}` });
            if (probe.textLen < 20) findings.push({ cell, kind: "blank", detail: `only ${probe.textLen} chars of text` });
            if (SHOTS) { const { result } = await send("Page.captureScreenshot", { format: "png" }); writeFileSync(join(SHOTS, cell.replaceAll("/", "__") + ".png"), Buffer.from(result.data, "base64")); }
          }
        }
      }
    }
    ws.close();
    const byKind = {}; for (const f of findings) byKind[f.kind] = (byKind[f.kind] || 0) + 1;
    for (const f of findings) console.log(`  ${f.kind.padEnd(11)} ${f.cell.padEnd(34)} ${f.detail}`);
    const summary = Object.entries(byKind).map(([k, v]) => `${k}=${v}`).join(" ") || "clean";
    if (findings.length) { console.log(`RENDER_AUDIT RED cells=${cells} ${summary}`); process.exitCode = 1; }
    else console.log(`RENDER_AUDIT PASS cells=${cells} — mọi màn render ở ${W}×${H}, không lỗi console, không lộ key, không tràn ngang`);
  } finally { clearTimeout(killer); chrome.kill("SIGKILL"); }
}
main().catch((e) => { console.error(`RENDER_AUDIT RED ${e.message}`); process.exit(2); });
