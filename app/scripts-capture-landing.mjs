/* The landing page's six screenshots, from the app's own UI under the dev
 * mock's opt-in showcase fixture (?showcase=vi|en): no real library, model or
 * account. A three-step story (07/10): the library, a reading under way, the
 * voice settings over that reading. 1152x738 CSS px at DPR 1600/1152 gives a
 * 1600x1025 PNG with the interface a little larger than life.
 *
 *   pnpm exec vite --port 1420 --strictPort        (the dev server)
 *   node scripts-capture-landing.mjs [vi] [en]     (writes ../assets/screenshots)
 *
 * Also checks one thing it walks past: the floating reading status steps
 * aside while the quick voice menu is open, and comes back when it closes.
 */
import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";

const ASSETS = fileURLToPath(new URL("../assets/screenshots/", import.meta.url));
const LOCALES = process.argv.slice(2).length ? process.argv.slice(2) : ["vi", "en"];
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9333, W = 1152, H = 738, SCALE = 1600 / 1152;
const sleep = ms => new Promise(r => setTimeout(r, ms));

const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${PORT}`,
  `--window-size=${W},${H}`, `--user-data-dir=${join(tmpdir(), `readease-capture-${process.pid}`)}`, "about:blank"], { stdio: "ignore" });
const killer = setTimeout(() => { console.error("timeout"); chrome.kill("SIGKILL"); process.exit(2); }, 5 * 60 * 1000);
let code = 0;
try {
  let wsUrl;
  for (let i = 0; i < 60 && !wsUrl; i++) {
    try { wsUrl = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find(t => t.type === "page")?.webSocketDebuggerUrl; } catch {}
    if (!wsUrl) await sleep(250);
  }
  const ws = new WebSocket(wsUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let id = 0; const pending = new Map();
  ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
  const send = (method, params = {}) => new Promise(r => { const n = ++id; pending.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
  const js = async expr => (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result?.result?.value;
  await send("Page.enable"); await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: SCALE, mobile: false });
  await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }] });

  const box = re => js(`(() => { const re = ${re}; const el = [...document.querySelectorAll("button,[role=button],[role=radio],[role=tab],a")]
    .find(e => re.test((e.getAttribute("aria-label") || e.textContent || "").trim()) && !e.closest("[inert]") && e.getBoundingClientRect().width > 0);
    if (!el) return null; const r = el.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()`);
  const press = async ({ x, y }) => { for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) await send("Input.dispatchMouseEvent", { type, x, y, button: "left", clickCount: 1 }); };
  const click = async (re, ms = 6000) => { const until = Date.now() + ms; while (Date.now() < until) { const b = await box(re); if (b) { await press(b); await sleep(450); return true; } await sleep(150); } throw new Error(`no ${re}`); };
  const rest = () => send("Input.dispatchMouseEvent", { type: "mouseMoved", x: W - 2, y: 2 });
  const shot = async name => { await rest(); await sleep(500); const { result } = await send("Page.captureScreenshot", { format: "png" }); const [lang, file] = name.split("-"); const dir = lang === "en" ? join(ASSETS, "en") : ASSETS;
    mkdirSync(dir, { recursive: true }); writeFileSync(join(dir, file), Buffer.from(result.data, "base64")); console.log("wrote", lang, file); };

  for (const lang of LOCALES) {
    const vi = lang === "vi";
    await send("Page.navigate", { url: "http://localhost:1420/?" }); await sleep(800);
    await js(`localStorage.clear(); sessionStorage.clear(); true`);
    await send("Page.navigate", { url: `http://localhost:1420/?showcase=${lang}` }); await sleep(1500);
    // 1. The library.
    for (let i = 0; i < 60 && !(await box(vi ? /^Mở PDF hoặc EPUB$/ : /^Open PDF or EPUB$/)); i++) await sleep(150);
    await sleep(600); // covers arrive a tick after the shelf
    await shot(`${lang}-shelf.png`);
    // 2. The reader, reading: open the book, start from a paragraph mid-page.
    await click(vi ? /^Mở Nguyên tắc/ : /^Open Principles/);
    await sleep(1200);
    // The English fixture translates the chapter, not the table of contents.
    if (!vi) { await click(/^Hide contents$/); await sleep(500); }
    const target = await js(`(() => { const p = [...document.querySelectorAll('[data-segment]')].find(e => /${vi ? "^Người làm trải nghiệm" : "^People who work"}/.test(e.textContent.trim()))
      || [...document.querySelectorAll('[data-segment]')].filter(e => e.getBoundingClientRect().top > 120)[1];
      p.scrollIntoView({ block: "center" }); const r = p.getBoundingClientRect(); return { x: r.x + 40, y: r.y + r.height / 2, text: p.textContent.slice(0, 40) }; })()`);
    console.log(lang, "reading from", target.text);
    await press(target);
    for (let i = 0; i < 40 && !(await js(`!!document.querySelector('.voice-here')`)); i++) await sleep(100);
    await sleep(500);
    console.log(lang, "voice at", await js(`document.querySelector('.voice-here')?.textContent.slice(0, 50)`));
    await shot(`${lang}-reader.png`);
    // 3. Voices, over the same reading.
    await click(vi ? /^Đổi giọng$/ : /^Change voice$/);
    const hidden = await js(`!document.querySelector('[data-reading-status]')`);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
    await sleep(500);
    const back = await js(`!!document.querySelector('[data-reading-status]')`);
    console.log(lang, "status hidden under the voice menu:", hidden, "back after closing:", back);
    if (!hidden || !back) code = 1;
    await click(vi ? /^Cài đặt giọng đọc$/ : /^Voice settings$/);
    await sleep(900);
    await shot(`${lang}-voices.png`);
  }
} catch (error) { console.error(error); code = 1; }
finally { clearTimeout(killer); chrome.kill("SIGKILL"); }
process.exit(code);
