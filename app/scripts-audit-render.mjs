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
// `--dump-text <file>`: every reached cell's words - what is on the page
// plus the names, tooltips and placeholders a person meets - written out,
// so `scripts-string-coverage.mjs` can say which interface strings no cell
// has ever shown (27/09: three defects in a day sat in screens no cell
// had opened).
const DUMP = opt("--dump-text", null);
const seen = [];
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const CDP_PORT = 9333 + Math.floor(Math.random() * 500);
// tauri.conf.json minWidth/minHeight - the floor a person can shrink to. A
// larger window is asked for by name (`--size 1440x900`): the floor is where
// things run out of room, a large window where they run out of shape.
const [W, H] = opt("--size", "960x600").split("x").map(Number);

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
const TRANSFER_PLAN = [...UNFOLD, ["click", /^Chuyển ghi chú$|^Move notes$/],
  ["choose", /^Lấy ghi chú từ$|^Take notes from$/, "nb-1"], ["choose", /^Chuyển sang$|^Move them to$/, "nb-4"],
  ["click", /^Xem trước$|^Preview$/], ["wait", /^Sẽ chép \d+ mục\.$|^\d+ items? would be copied\.$/, "span"]];
const SHELF = [...UNFOLD, ["click", /^Thư viện$|^Library$/]];
const VOICES = [...OPEN_BOOK, ["click", /^Cài đặt giọng đọc$|^Voice settings$/], ["click", /^Quản lý giọng|^Manage voices/], ["wait", /^Danh sách giọng đọc$|^Voices$/]];
const APPLE = [...SHELF, ["click", /^Từ Apple Books$|^From Apple Books$/], ["wait", /^Tài liệu trong Apple Books$|^Items in Apple Books$/, "[role=dialog]"]];
const SEARCH = [...OPEN_BOOK, ["click", /^Tìm trong tài liệu$|^Search in document$/], ["wait", /^Tìm trong tài liệu$|^Search in document$/, "[role=radio]"]];
const HUB = [...SHELF, ["click", /^Giọng đọc & mô hình$|^Voices & models$/], ["wait", /^Giọng đọc & mô hình$|^Voices & models$/]];
const NOTE_EDITOR = [...OPEN_BOOK, ["click", /^Highlight và ghi chú$|^Highlights and notes$/], ["wait", /^\d+ highlights?$/],
  ["click", /những phương án đầu tiên của họ/], ["click-at", "button.note-nudge"], ["wait", /^Sửa ghi chú$|^Edit this note$/, "textarea"]];
const SCREENS = {
  shelf:  [...UNFOLD, ["click", /^Thư viện$|^Library$/]],
  paste:  [...UNFOLD, ["click", /^Dán nội dung$|^Paste text$/]],
  // Pasted text past the limit (100 000 characters): the count turns to
  // danger and a line says what to do. No cell had typed into the box.
  paste_over: [...UNFOLD, ["click", /^Dán nội dung$|^Paste text$/], ["click-at", "textarea"], ["type", "chữ ".repeat(25_001)],
    ["wait", /^Nội dung dài hơn giới hạn|^Longer than the limit/, "span"]],
  scan:   [...UNFOLD, ["click", /^Quét đọc$|^Read a selection$/]],
  notes:  [...UNFOLD, ["click", /^Chuyển ghi chú$|^Move notes$/]],
  reader: OPEN_BOOK,
  voices: VOICES,
  // The list's own tools at the window's floor (HIG 3.13): its filters fold
  // behind a button there, and a search can find nothing. Until 27/09 no
  // cell had opened the one or typed into the other.
  voices_filters: [...VOICES, ["click", /^Lọc danh sách$|^Filter the list$/], ["wait", /^Tất cả giới tính$|^All genders$/]],
  voices_search_none: [...VOICES, ["click", /^Tìm giọng…$|^Search voices…$/], ["type", "qwxz"],
    ["wait", /^Không có giọng nào khớp|^No voice matches/, "p,div,span"]],
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
  search: SEARCH,
  // What a search says past its first letters (HIG 3.9): nothing found, and
  // a word so common the list stops at its cap. Until 27/09 no cell typed a
  // query, so neither line had been on a screen.
  search_none: [...SEARCH, ["type", "qwxz"], ["wait", /^Không thấy trong tài liệu này\.$|^Nothing in this document\.$/, "p"]],
  search_capped: [...SEARCH, ["type", "ng"], ["wait", /^Hiện \d+ kết quả đầu|^Showing the first \d+/, "p"]],
  // The two floating settings panels over an open document (HIG 4.2): until
  // 23/09 no cell opened either, so axe had never seen a control in them -
  // and four of their selects had no name. The reading panel opens its finer
  // choices too, or the sliders and switches under "Tuỳ chỉnh" stay unseen.
  player_settings: [...OPEN_BOOK, ["click", /^Cài đặt giọng đọc$|^Voice settings$/], ["wait", /^Cài đặt giọng đọc$|^Voice settings$/, "[role=dialog]"]],
  // The Voice picker open over its panel (HIG 3.13, owner 26/09): its rows,
  // their two buttons, and where it lands in a 600px window - over its own
  // button, since neither side of it holds the whole list.
  voice_picker: [...OPEN_BOOK, ["click", /^Cài đặt giọng đọc$|^Voice settings$/], ["wait", /^Cài đặt giọng đọc$|^Voice settings$/, "[role=dialog]"],
    ["click-at", '[role="dialog"] [aria-haspopup="dialog"]'], ["wait", /^Chọn giọng$|^Choose a voice$/, "[role=dialog]"]],
  reading_settings: [...OPEN_BOOK, ["click", /^Cài đặt đọc$|^Reading settings$/], ["wait", /^Cài đặt đọc$|^Reading settings$/, "[role=dialog]"],
    ["click", /^Tuỳ chỉnh$|^Customize$/], ["wait", /^Giãn dòng$|^Line spacing$/, "input"]],
  // A picture opened large (HIG 3.10). Its ground is black in both themes,
  // where line art on a transparent ground disappears - so the cell exists
  // to measure the sheet the picture sits on (25/09). The picture is opened
  // the way its click handler is reached, not by where it happens to be on
  // the page: every chapter's figures are in the DOM, most off-page.
  // Reached through the contents, like a reader would: the sample's sketch
  // on a transparent ground sits in "Chương 6 Bài tập 02".
  // The paid voice's cost and scope panel, from the coin by the read
  // button: never opened by any cell until 27/09.
  cost: [...OPEN_BOOK, ["click", /^Chi phí và phạm vi$|^Cost and scope$/], ["wait", /^Giọng trả phí$|^Paid voice$/, "[role=dialog]"]],
  // The Apple Books sheet (HIG 3.12), from the shelf's own button: until
  // 27/09 no cell had opened it - the coverage map listed it at zero.
  apple_books: APPLE,
  // The sheet's two menus and what an import says when done (HIG 3.12):
  // until 27/09 no cell had opened either menu or run anything from them.
  apple_import_menu: [...APPLE, ["click", /^Tuỳ chọn nhập$|^Import options$/], ["wait", /^Chỉ nhập tài liệu|^Document only/, "[role=menuitem]"]],
  apple_imported: [...APPLE, ["click", /^Tuỳ chọn nhập$|^Import options$/], ["wait", /^Chỉ nhập tài liệu|^Document only/, "[role=menuitem]"],
    ["click", /^Chỉ nhập tài liệu|^Document only/], ["wait", /^Đã nhập \d+ tài liệu|^\d+ documents? imported/, "p"]],
  apple_sync_menu: [...APPLE, ["click", /^Đồng bộ ghi chú$|^Sync highlights$/], ["wait", /^Highlight và ghi chú|^Highlights and notes/, "[role=menuitem]"]],
  // The update sheet (HIG 3.20), the way every reader reaches a new version:
  // opened through the dispatcher "Kiểm tra bản mới…" calls, in its four
  // resting states - a new version, already the latest, the check failing,
  // a download under way (held at ~40 %). Until 27/09 no cell had ever
  // rendered it.
  update_available: [["perform", "check-updates"], ["wait", /^Có ReadEase 0\.1\.20\.$|^ReadEase 0\.1\.20 is available\.$/, "[role=dialog] p"]],
  update_none: [["perform", "check-updates", "none"], ["wait", /^Bạn đang dùng bản mới nhất \(0\.1\.19\)\.$|^You are on the latest version \(0\.1\.19\)\.$/, "[role=dialog] p"]],
  update_failed: [["perform", "check-updates", "failed"], ["wait", /^Không kiểm tra được|^Could not check/, "[role=dialog] p"]],
  update_downloading: [["perform", "check-updates", "slow"], ["wait", /^Có ReadEase|is available\.$/, "[role=dialog] p"],
    ["click", /^Tải và cài$|^Download and Install$/], ["wait", /^Đang tải bản 0\.1\.20… \d+%$|^Downloading 0\.1\.20… \d+%$/, "[role=dialog] p"]],
  // The Move-notes preview, its confirmation and what it says when done:
  // until 27/09 no cell had chosen two copies, so none of it had been
  // rendered. nb-1 and nb-4 share an edition, so all three verdicts show.
  transfer_plan: TRANSFER_PLAN,
  transfer_confirm: [...TRANSFER_PLAN, ["click", /^Chép sang$|^Copy across$/], ["wait", /^Chép ghi chú sang bản kia\?$|^Copy notes across\?$/, "p"]],
  transfer_done: [...TRANSFER_PLAN, ["click", /^Chép sang$|^Copy across$/], ["wait", /^Chép ghi chú sang bản kia\?$|^Copy notes across\?$/, "p"],
    ["click", /^Chép sang$|^Copy across$/], ["wait", /^Đã chép \d+ mục|^Copied \d+ items?/, "p"]],
  // A reading under way (HIG 3.5, 3.24): the transport, the forecast of
  // what is left, a pause - and the moment before the voice's first sound.
  // The core of the app, and no cell had ever drawn it: every cell was idle.
  reading_now: [...OPEN_BOOK, ["click", /^Đọc tiếp|^Continue/], ["wait", /^Dừng$|^Stop$/], ["wait", /còn ~|left$/, "span"], ["rest"]],
  reading_paused: [...OPEN_BOOK, ["click", /^Đọc tiếp|^Continue/], ["wait", /^Dừng$|^Stop$/], ["click", /^Tạm dừng$|^Pause$/],
    ["wait", /^Tiếp tục$|^Resume$/], ["rest"]],
  reading_warming: [...OPEN_BOOK, ["click", /^Đọc tiếp|^Continue/], ["wait", /^Đang chuẩn bị giọng đọc…$|^Preparing the voice…$/, "p"], ["rest"]],
  // A reading that fails, and the line that says why (HIG 3.5): the mock
  // has refused a reading on demand since the eight failure sentences were
  // written, and no cell had pressed read - so none of them had been on a
  // screen. The states below pick the failure.
  reading_failed: [...OPEN_BOOK, ["click", /^Đọc tiếp|^Continue/], ["wait", /./, "[role=alert]"], ["rest"]],
  // A model download in flight and cancelled (HIG 3.13, the first thing a
  // new person does): no cell had pressed "Tải và dùng" or "Tải về", so the
  // progress, its message and the cancel had never been on a screen. The
  // mock holds the download at 38 % (`download=hold`).
  model_downloading: [...HUB, ["click", /^Tải và dùng$|^Download and use$/], ["wait", /^Huỷ tải$|^Cancel download$/]],
  model_cancelled: [...HUB, ["click", /^Tải và dùng$|^Download and use$/], ["wait", /^Huỷ tải$|^Cancel download$/],
    ["click", /^Huỷ tải$|^Cancel download$/], ["wait", /^Đã huỷ tải|^Download cancelled/, "p"]],
  model_english_downloading: [...HUB, ["click", /^Tải về$|^Download$/], ["wait", /^Huỷ tải$|^Cancel download$/]],
  // The same download from the first-run screen, where it is the point.
  first_run_download: [["wait", /Chọn cách đọc để bắt đầu|Choose how to read/], ["click", /^Tải và dùng$|^Download and use$/],
    ["wait", /^Huỷ tải$|^Cancel download$/]],
  // The primary button under the pointer (HIG 2, hover): its label must
  // hold its contrast on the hover fill in both themes (27/09).
  primary_hover: [...OPEN_BOOK, ["hover", /^Đọc tiếp|^Continue/]],
  // Adding a provider's key (HIG 3.13): the form, and a key the provider
  // refuses (`keyfail=bad_key`). The words typed are a made-up test string
  // on the mock, which answers locally and hands no key back. Until 27/09
  // no cell had opened the form, so none of it had been on a screen.
  key_form: [...HUB, ["click", /^Thêm khoá$|^Add key$/], ["wait", /^Lưu$|^Save$/]],
  key_refused: [...HUB, ["click", /^Thêm khoá$|^Add key$/], ["wait", /^Lưu$|^Save$/], ["type", "khoa-thu-nghiem"],
    ["click", /^Lưu$|^Save$/], ["wait", /./, "[role=alert]"], ["rest"]],
  // The shelf's own changes (HIG 3.11): a document added through the open
  // panel (the mock answers it with one path), the same file added again,
  // and a removal - asked, then done. Until 27/09 no cell had pressed
  // either button, so none of what they say had been on a screen.
  shelf_import: [...SHELF, ["click", /^Mở PDF hoặc EPUB$|^Open PDF or EPUB$/], ["wait", /^Đã thêm tài liệu vào thư viện\.$|^Document added to the library\.$/, "p"]],
  shelf_duplicate: [...SHELF, ["click", /^Mở PDF hoặc EPUB$|^Open PDF or EPUB$/], ["wait", /^Đã thêm tài liệu vào thư viện\.$|^Document added to the library\.$/, "p"],
    ["click", /^Mở PDF hoặc EPUB$|^Open PDF or EPUB$/], ["wait", /^Tài liệu này đã có trong thư viện\.$|^This document is already in the library\.$/, "p"]],
  shelf_remove: [...SHELF, ["click", /^Xoá$|^Remove$/], ["wait", /^Giữ lại$|^Keep$/]],
  shelf_removed: [...SHELF, ["click", /^Xoá$|^Remove$/], ["wait", /^Giữ lại$|^Keep$/],
    ["click", /^Xoá$|^Remove$/], ["wait", /^Đã xoá khỏi thư viện\.$|^Removed from the library\.$/, "p"]],
  // Writing a note where it sits (HIG 3.14): until 27/09 no cell had
  // opened the editor. Reached the way a reader would - the notes list
  // jumps to a highlight, and its note button opens the editor on the page.
  note_editor: NOTE_EDITOR,
  // And a save the engine refuses: the reason is said inside the editor.
  note_save_failed: [...NOTE_EDITOR, ["type", " Xem lại."], ["click", /^Lưu$|^Save$/], ["wait", /./, "[role=alert]"]],
  // Past the download: installed, waiting for a relaunch - reached by the
  // keys pass in Vietnamese only, never looked at in both languages.
  update_installed: [["perform", "check-updates"], ["wait", /^Có ReadEase 0\.1\.20\.$|^ReadEase 0\.1\.20 is available\.$/, "[role=dialog] p"],
    ["click", /^Tải và cài$|^Download and Install$/], ["wait", /^Khởi động lại$|^Relaunch$/]],
  lightbox: [...OPEN_BOOK, ["click?", /^Hiện mục lục$|^Show contents$/], ["click", /Bài tập 02/],
    ["open-figure"], ["wait", /^Đóng ảnh$|^Close image$/]],
};
// A panel is opened only in the states that change what is in it. The two
// settings panels follow the models and the voice, not the library's
// states: opened in all sixteen they would add 120 cells (~6 min of a
// ~31 min run) saying the same thing, for these 28.
const ONLY_IN = {
  player_settings: ["default", "sidebar", "english_missing", "english_partial", "vietnamese_missing", "paid"],
  voice_picker: ["default"],
  reading_settings: ["default", "sidebar"],
  lightbox: ["default"],
  reading_failed: ["voicefail", "voicefail_network", "voicefail_blocked", "voicefail_budget"],
  reading_now: ["default"],
  reading_paused: ["default"],
  reading_warming: ["warm_hold"],
  note_editor: ["default"],
  shelf_import: ["default"],
  key_form: ["default"],
  primary_hover: ["default"],
  model_downloading: ["download_hold"],
  model_cancelled: ["download_hold"],
  model_english_downloading: ["english_hold"],
  first_run_download: ["first_run_hold"],
  search_none: ["default"],
  paste_over: ["default"],
  apple_import_menu: ["default"],
  voices_filters: ["default"],
  voices_search_none: ["default"],
  apple_imported: ["default"],
  apple_sync_menu: ["default"],
  search_capped: ["default"],
  key_refused: ["keyfail"],
  shelf_duplicate: ["default"],
  shelf_remove: ["default"],
  shelf_removed: ["default"],
  note_save_failed: ["note_fail"],
  transfer_plan: ["default"],
  transfer_confirm: ["default"],
  transfer_done: ["default"],
  apple_books: ["default", "empty"],
  cost: ["paid", "price_failed", "paid_eleven"],
  update_available: ["default"],
  update_none: ["default"],
  update_failed: ["default"],
  update_downloading: ["default"],
  update_installed: ["default"],
};
// What a screen logs on purpose. A refused reading is caught and shown, and
// the page also logs it (every caught failure is console.error'd) - on the
// screen that exists to refuse a reading, that line is the state, not a
// fault. Exceptions are never excused.
const EXPECTED_CONSOLE = { reading_failed: /^voice_(failed|unavailable): /, note_save_failed: /annotations\.update/, price_failed: /estimate/ };
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
  // Names as long as the owner's library has them (27/09, counted numbers
  // only: a 98-character title, a 133-character contents line).
  long: "long=1",
  // A paid voice in use: the cost button and its panel exist only here.
  paid: "voice=paid",
  // An ElevenLabs voice: counted credits, so a ceiling and a unit count.
  paid_eleven: "voice=elevenlabs",
  // Reading failures on a paid voice, beside `voicefail` (quota): the
  // commonest (network), the longest sentence (a blocked account, 175
  // characters in English) and one stopped before any provider was asked
  // (our own ceiling).
  voicefail_network: "voice=paid&voicefail=network",
  voicefail_blocked: "voice=paid&voicefail=account_blocked",
  voicefail_budget: "voice=paid&voicefail=budget",
  // A note the engine will not save.
  note_fail: "fail=annotations.update",
  // A paid voice whose price could not be worked out: the read button must
  // stay locked, saying so, and the cost panel must say why (27/09).
  price_failed: "voice=paid&fail=estimate",
  // A model download that stays in flight (the mock stops at 38 %).
  download_hold: "download=hold",
  english_hold: "english=missing&download=hold",
  first_run_hold: "model=missing&download=hold",
  // A reading whose voice has not made its first sound.
  warm_hold: "warm=hold",
};
// A state that only reaches some screens: the long names show on these.
const STATE_ON = {
  long: ["shelf", "reader", "contents", "book_notes", "search"],
  paid: ["reader", "cost", "player_settings"],
  paid_eleven: ["reader", "cost"],
  voicefail_network: ["reading_failed"],
  voicefail_blocked: ["reading_failed"],
  voicefail_budget: ["reading_failed"],
  note_fail: ["note_save_failed"],
  price_failed: ["reader", "cost"],
  download_hold: ["model_downloading", "model_cancelled"],
  english_hold: ["model_english_downloading"],
  first_run_hold: ["first_run_download"],
  warm_hold: ["reading_warming"],
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
  // 27/09: 812 cells took 43.5 min and the matrix keeps growing - 90 min,
  // for the same reason the bound went past 15 once.
  const killer = setTimeout(() => { console.error("RENDER_AUDIT RED chrome lifetime exceeded"); chrome.kill("SIGKILL"); process.exit(2); }, 90 * 60 * 1000); // 620 cells took 31 min run screen by screen (16/09); 35 was cut twice; 648 with the two settings panels took 31m38s (23/09)
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
    // The first VISIBLE match, as a hand would find it: the folded column
    // keeps its tabs in the DOM at zero width behind \`inert\`, and a tab
    // named like the toolbar button ("Tìm trong tài liệu") used to be
    // found first and clicked at the fold (16/09, search unreachable).
    const locate = (re) => evalJs(`(() => {
        const re = ${re.toString()};
        const el = [...document.querySelectorAll("button,[role=button],[role=radio],[role=tab],a,summary")]
          .find((e) => re.test((e.getAttribute("aria-label") || e.textContent || "").trim())
            && !e.closest("[inert]") && e.getBoundingClientRect().width > 0);
        if (!el) return null; el.scrollIntoView({ block: "center" }); const r = el.getBoundingClientRect();
        return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()`);
    const findAndClick = async (re, patience = 4000) => {
      await waitFor(re, patience);
      const box = await locate(re);
      if (!box) return false;
      for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) await send("Input.dispatchMouseEvent", { type, x: box.x, y: box.y, button: "left", clickCount: 1 });
      await sleep(350); return true;
    };
    // The pointer resting on a control, not pressing it: a cell that measures
    // a hover state (27/09 - the primary button's hover had never been
    // looked at, and in the dark theme it took its label under AA).
    const hover = async (re, patience = 4000) => {
      await waitFor(re, patience);
      const box = await locate(re);
      if (!box) return false;
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.x, y: box.y });
      await sleep(350); return true;
    };
    // A menu command, through the app's own dispatcher: the browser has no
    // menu bar, so the dev build hands the harness the dispatcher (HIG
    // 3.20). A third element picks the mock's answer to the update check.
    const perform = (command, variant) => evalJs(`(() => {
      if (typeof window.__readeasePerform !== "function") return false;
      ${variant ? `window.__mockUpdate = ${JSON.stringify(variant)};` : ""}
      window.__readeasePerform(${JSON.stringify(command)}); return true; })()`);
    // A native select, chosen the way a person's choice reaches React: the
    // value set through the element's own setter, then a change event. Found
    // by its label - the Move-notes pickers say "Lấy ghi chú từ" and
    // "Chuyển sang". Until 27/09 no cell had chosen anything in one, so the
    // preview behind them had never been rendered.
    const choose = (label, value) => evalJs(`(() => {
      const el = [...document.querySelectorAll("select")].find((e) => new RegExp(${JSON.stringify(label.source)}).test(e.getAttribute("aria-label") ?? ""));
      if (!el) return false;
      Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value").set.call(el, ${JSON.stringify(value)});
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return el.value === ${JSON.stringify(value)}; })()`);
    // The pointer taken off the page, to the window's top-left corner: a
    // cell measures the page at rest, and a click leaves the pointer on the
    // button it pressed, in its hover colours.
    const rest = async () => { await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 1, y: 1 }); return true; };
    // Words typed where the focus is, the way a keyboard would insert them.
    const type = async (words) => { await send("Input.insertText", { text: words }); return true; };
    // A control found by WHERE it is rather than by a name: the Voice
    // picker's button is named by its row ("Giọng") plus the voice it shows,
    // which changes as the checks pick voices. Pressed at its centre, with
    // the mouse, the way findAndClick presses.
    const clickAt = async (selector, patience = 4000) => {
      const until = Date.now() + patience;
      while (Date.now() < until) {
        const box = await evalJs(`(() => {
          const el = [...document.querySelectorAll(${JSON.stringify(selector)})].find((e) => !e.closest("[inert]") && e.getBoundingClientRect().width > 0);
          if (!el) return null; el.scrollIntoView({ block: "nearest" }); const r = el.getBoundingClientRect();
          return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()`);
        if (box) {
          for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) await send("Input.dispatchMouseEvent", { type, x: box.x, y: box.y, button: "left", clickCount: 1 });
          await sleep(350); return true;
        }
        await sleep(150);
      }
      return false;
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
            if (STATE_ON[stateName] && !STATE_ON[stateName].includes(screen)) continue;
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
                : kind === "click-at" ? await clickAt(re)
                : kind === "perform" ? await perform(re, within)
                : kind === "choose" ? await choose(re, within)
                : kind === "rest" ? await rest()
                : kind === "type" ? await type(re)
                : kind === "hover" ? await hover(re)
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
              if (m.method === "Runtime.consoleAPICalled" && (EXPECTED_CONSOLE[screen] ?? EXPECTED_CONSOLE[stateName])?.test(String(detail))) continue;
              findings.push({ cell, kind: "console", detail: String(detail).split("\n")[0].slice(0, 200) });
            }
            if (DUMP) seen.push({ cell, text: await evalJs(`(() => [document.body.innerText,
              ...[...document.querySelectorAll("[aria-label],[title],[placeholder]")].flatMap((e) => ["aria-label", "title", "placeholder"].map((a) => e.getAttribute(a)).filter(Boolean))].join("\\n"))()`) });
            const probe = await evalJs(`(() => {
              const text = document.body.innerText;
              const leaked = [...new Set((text.match(/\\b[a-z_]+\\.[a-z_0-9]+\\b/g) || []))];
              const over = [...document.querySelectorAll("*")].filter((e) => { const s = getComputedStyle(e); return e.scrollWidth > e.clientWidth + 1 && s.overflowX !== "auto" && s.overflowX !== "scroll" && s.overflowX !== "hidden" && e.clientWidth > 0; })
                .map((e) => e.tagName.toLowerCase() + (e.className && typeof e.className === "string" ? "." + e.className.split(" ").slice(0, 2).join(".") : "")).slice(0, 4);
              let voice; try { voice = JSON.parse(localStorage.getItem("readease.mock-settings") || "{}").voice; } catch {}
              const plates = [...document.querySelectorAll("[data-figure] img")].map((img) => getComputedStyle(img).backgroundColor);
              const large = document.querySelector("[data-lightbox] img");
              const lightboxPlate = large ? getComputedStyle(large).backgroundColor : null;
              // Inside a layer too: a fixed sheet never widens the document,
              // so text running out of its box there went unreported - the
              // update sheet's error URL ran past its edge (27/09).
              const escaped = [...document.querySelectorAll('[role="dialog"] *')].filter((e) => { if (e.closest("[inert]") || !(e instanceof HTMLElement)) return false;
                const s = getComputedStyle(e); return e.clientWidth > 0 && e.scrollWidth > e.clientWidth + 1 && s.overflowX === "visible"; })
                .map((e) => (e.textContent || "").trim().slice(0, 48)).slice(0, 3);
              return { leaked, over, escaped, docWide: document.documentElement.scrollWidth > document.documentElement.clientWidth, themeAttr: document.documentElement.dataset.theme, textLen: text.length, voice, htmlLang: document.documentElement.lang, plates, lightboxPlate }; })()`);
            for (const k of probe.leaked) if (KEYS.has(k)) findings.push({ cell, kind: "i18n-leak", detail: k });
            // No cell picks a voice, so the saved one (the mock's "Thu Hà")
            // must still be the saved one after the walk. Start-up once
            // overwrote it with the first voice before reading it (15/09),
            // in a gap only a bridge that answers a tick later opens.
            if (probe.voice !== undefined && probe.voice !== "Thu Hà") findings.push({ cell, kind: "voice-lost", detail: `saved voice became ${probe.voice}` });
            if (probe.docWide) findings.push({ cell, kind: "overflow-x", detail: `document scrolls horizontally at ${W}px` + (probe.over.length ? ` (${probe.over.join(", ")})` : "") });
            for (const text of probe.escaped) findings.push({ cell, kind: "overflow-layer", detail: `text runs out of its box in a layer: ${JSON.stringify(text)}` });
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
                    // A contrast finding carries its own measure (27/09): the
                    // selector alone left the colours to be guessed.
                    targets: v.nodes.slice(0, 3).map((n) => String(n.target[0]).slice(0, 80)
                      + (v.id === "color-contrast" && n.any?.[0]?.data ? \` (\${n.any[0].data.fgColor} on \${n.any[0].data.bgColor}, \${n.any[0].data.contrastRatio}:1)\` : "")) })) };
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
      const CODES = { Enter: 13, Escape: 27, Tab: 9, ArrowDown: 40, ArrowUp: 38, ArrowLeft: 37, ArrowRight: 39, Home: 36, End: 35 };
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
      const goto = async (steps, lang = "vi", query = "") => {
        events.length = 0;
        await seedLanguage(lang);
        await send("Page.navigate", { url: `http://localhost:${PORT}/?${query}` });
        await sleep(900);
        await evalJs(`localStorage.removeItem("readease.theme")`);
        for (const [kind, re, within] of steps) {
          const ok = kind === "click" ? await findAndClick(re)
            : kind === "click?" ? (await findAndClick(re, 600), true)
            : kind === "click-at" ? await clickAt(re)
            : kind === "perform" ? await perform(re, within)
            : kind === "choose" ? await choose(re, within)
            : kind === "rest" ? await rest()
            : kind === "type" ? await type(re)
            : kind === "hover" ? await hover(re)
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

      // The Apple Books sheet: in with the keyboard, back to its button.
      if (!(await goto([...UNFOLD, ["click", /^Thư viện$/]]))) expect("apple-books", false, "could not open the shelf");
      else await inAndBack("apple-books", /^Từ Apple Books$/);

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
        // Every opener, not one (27/09): the hub's gear in the column's foot
        // kept the focus after a mouse press, so its tooltip hung over the
        // sheet it had opened - the owner's 06/09 and 16/09 complaint, back
        // through a button the one-opener check never pressed. Each is
        // pressed on a fresh page and read after the tooltip's own delay.
        // And with a paid voice in use, where the coin that opens the cost
        // panel exists.
        const openersIn = async (query) => { if (!(await goto(OPEN_BOOK, "vi", query))) return [];
          return (await evalJs(`[...document.querySelectorAll("button[aria-haspopup][aria-label]")]
          .filter((b) => b.getBoundingClientRect().width > 0 && !b.closest("[inert]") && !b.disabled).map((b) => b.getAttribute("aria-label"))`)) ?? []; };
        const openers = [...(await openersIn("")).map((name) => ["", name]), ...(await openersIn("voice=paid")).filter((name) => name === "Chi phí và phạm vi").map((name) => ["voice=paid", name])];
        for (const [query, name] of openers) {
          if (!(await goto(OPEN_BOOK, "vi", query))) { expect("mouse", false, "could not reopen the document"); break; }
          if (!(await clickAt(`button[aria-label="${name}"]`))) { expect("mouse", false, `no opener named ${name}`); continue; }
          await sleep(900);
          const after = await evalJs(`(() => { const b = document.querySelector('button[aria-label="${name}"]');
            return { kept: !!b && document.activeElement === b, tip: document.querySelector("[role=tooltip]")?.textContent ?? null }; })()`);
          expect("mouse", !after.kept && after.tip === null, `${name}: after a mouse press the opener ${after.kept ? "kept the focus" : "let go"}${after.tip ? `, and the tooltip "${after.tip}" hangs over what it opened` : ""}`);
        }
        // A press puts the tooltip away, as the Mac's help tags go when you
        // click (27/09): it came back - by focus in this browser, by the hover
        // timer in WebKit, where a click does not focus a button - over what
        // the press had just done. A plain button, not an opener, so an
        // opener's own blur cannot hide it.
        if (!(await goto(OPEN_BOOK))) expect("mouse", false, "could not reopen the document");
        else {
          const theme = await evalJs(`[...document.querySelectorAll("button")].find((b) => /^Chuyển sang nền (tối|sáng)$/.test(b.getAttribute("aria-label") || "") && b.getBoundingClientRect().width > 0)?.getAttribute("aria-label") ?? null`);
          if (!theme) expect("mouse", false, "no theme switch to press");
          else {
            await clickAt(`button[aria-label="${theme}"]`);
            await sleep(900);
            const tip = await evalJs(`document.querySelector("[role=tooltip]")?.textContent ?? null`);
            expect("mouse", tip === null, `after a mouse press on "${theme}" its tooltip "${tip}" came back`);
          }
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
          // A search hit or a note is a place the reader went to LOOK at,
          // and the page stays there while the voice reads on in another
          // chapter; "Về chỗ đang đọc" is the way back (owner, 25/09: the
          // page was pulled back to the voice the next time it moved on).
          // Pages hold one chapter at a time and the side column's rows
          // carry no data-segment, so the chapters in the document are the
          // page's. The mock moves the voice every 1.2 s: 3 s is two
          // chances to snap back - once it is MOVING. Warming up it holds
          // no place, and a page nobody pulls back proves nothing.
          const chapterShown = () => evalJs(`[...new Set([...document.querySelectorAll("[data-segment]")]
            .map((e) => e.dataset.segment.replace(/-seg-.*$/, "")))].join(",")`);
          const spoken = () => evalJs(`document.querySelector('[aria-current="true"][data-segment]')?.dataset.segment ?? null`);
          const moving = async () => {
            const first = await spoken();
            for (let i = 0; i < 40; i++) { await sleep(250); const now = await spoken(); if (now && now !== first) return true; }
            return false;
          };
          const stays = async (leg, go) => {
            if (!(await moving())) return expect("look", false, `${leg}: the voice never moved on`);
            const before = await chapterShown();
            if (!(await go())) return;
            await sleep(400);
            const landed = await chapterShown();
            expect("look", landed !== before, `${leg}: 0.4 s after the click the page was in ${before} again (or never left it)`);
            await sleep(3000);
            const after = await chapterShown();
            expect("look", after === landed, `${leg}: the page went back to the voice within 3 s (${landed} -> ${after})`);
            expect("look", await waitFor(/^Về chỗ đang đọc$/, 500, "button"), `${leg}: no "Về chỗ đang đọc" while the page is away from the voice`);
          };
          await stays("search hit", async () => {
            if (!(await findAndClick(/^Tìm trong tài liệu$/))) return expect("look", false, "no search button while reading");
            await send("Input.insertText", { text: "hoạt động" });
            await sleep(600);
            // The last hit: the far end of the document, never the voice's chapter.
            const hit = await evalJs(`(() => { const rows = [...document.querySelectorAll("button mark[data-search]")].map((m) => m.closest("button"));
              if (!rows.length) return false; rows[rows.length - 1].click(); return true; })()`);
            if (!hit) expect("look", false, 'searching "hoạt động" found nothing to go to');
            return hit;
          });
          // Back with the voice (the pill, if the first leg left one), then
          // the same from a note - one in a chapter the voice is NOT in:
          // the mock reads from the top, and its notes sit in chapters 1-2.
          await findAndClick(/^Về chỗ đang đọc$/, 500);
          await stays("note", async () => {
            if (!(await findAndClick(/^Highlight và ghi chú$/))) return expect("look", false, "no Highlights and notes button while reading");
            const elsewhere = (await spoken() ?? "").startsWith("ch-0-") ? /những phương án đầu tiên/ : /sản phẩm phải hoạt động/;
            if (!(await findAndClick(elsewhere))) return expect("look", false, "no note row to go to");
            return true;
          });
          await findAndClick(/^Dừng$/);
        }
        crashed("reader");
      }

      // A starred voice stands first (HIG 3.13; owner, 25/09). Starred in
      // the voices sheet, its row stays where it is while the sheet is
      // open; the next time the sheet opens it heads the list under "Yêu
      // thích"; the voice select lists it first; and it is still starred
      // after a reload (the mock keeps its settings across one, as the
      // engine keeps settings.json). "Thái Sơn" is one of the five switched
      // on from the start, so the select offers it.
      const VOICES_SHEET = [["click", /^Cài đặt giọng đọc$/], ["click", /^Quản lý giọng/], ["wait", /^Danh sách giọng đọc$/]];
      const heads = () => evalJs(`[...document.querySelectorAll('[role="dialog"] h3')].map((h) => h.textContent.trim())`);
      // Where the row stands is its place among the rows, not its pixels:
      // clicking scrolls the list to put the button in view.
      const star = () => evalJs(`(() => { const rows = [...document.querySelectorAll('[role="dialog"] button[aria-label^="Yêu thích "]')];
        const at = rows.findIndex((e) => e.getAttribute("aria-label") === "Yêu thích Thái Sơn");
        return at < 0 ? null : { pressed: rows[at].getAttribute("aria-pressed"), at }; })()`);
      const firstStar = () => evalJs(`document.querySelector('[role="dialog"] button[aria-label^="Yêu thích "]')?.getAttribute("aria-label") ?? null`);
      const starredGroup = async () => {
        const [, first] = await heads();
        return first === "Yêu thích (1)" && (await firstStar()) === "Yêu thích Thái Sơn";
      };
      if (!(await goto([...OPEN_BOOK, ...VOICES_SHEET]))) expect("favorite", false, "could not open the voices sheet");
      else {
        const before = await star();
        if (!before) expect("favorite", false, 'no star on "Thái Sơn" in the voices sheet');
        else {
          await findAndClick(/^Yêu thích Thái Sơn$/);
          const after = await star();
          expect("favorite", before.pressed === "false" && after?.pressed === "true", `the star went ${before.pressed} -> ${after?.pressed}`);
          expect("favorite", after?.at === before.at, `the row moved from place ${before.at} to ${after?.at} while the sheet was open`);
          await key("Escape");
          for (const [, re] of VOICES_SHEET.slice(0, 2)) await findAndClick(re);
          expect("favorite", await starredGroup(), `reopened, the sheet starts ${JSON.stringify((await heads()).slice(1, 2))} / ${await firstStar()}, not "Yêu thích (1)" / Thái Sơn`);
          await key("Escape");
          // The Voice picker in the settings panel (HIG 3.13 - a select until
          // 26/09) opens on its Favourites group, the starred voice first.
          await findAndClick(/^Cài đặt giọng đọc$/);
          await clickAt('[role="dialog"] [aria-haspopup="dialog"]');
          const listed = await evalJs(`(() => { const box = document.querySelector('[role="dialog"][aria-label="Chọn giọng"]'); if (!box) return null;
            return [box.querySelector("h3")?.textContent.trim() ?? null,
              box.querySelector("[data-voice-row] button[aria-pressed]")?.getAttribute("aria-label") ?? null]; })()`);
          expect("favorite", listed?.[0] === "Yêu thích" && listed?.[1] === "Yêu thích Thái Sơn", `the Voice picker starts ${JSON.stringify(listed)}, not Yêu thích / Thái Sơn`);
          await key("Escape");
          await key("Escape");
          if (!(await goto([...OPEN_BOOK, ...VOICES_SHEET]))) expect("favorite", false, "could not reopen the voices sheet after a reload");
          else {
            expect("favorite", await starredGroup(), "after a reload the voice is no longer starred first");
            // While reading, Change voice lists it first, with its star -
            // which carries the word for a screen reader.
            await key("Escape");
            if ((await findAndClick(/^Đọc tiếp$/)) && (await waitFor(/^Tạm dừng$/, 6000, "button"))) {
              await findAndClick(/^Đổi giọng$/);
              const first = await evalJs(`document.querySelector('[role="menu"] [role="menuitem"]')?.textContent.trim() ?? null`);
              expect("favorite", /^Thái Sơn\s*Yêu thích/.test(first ?? ""), `Change voice starts with ${JSON.stringify(first)}, not the starred "Thái Sơn"`);
              await key("Escape");
              await findAndClick(/^Dừng$/);
            } else expect("favorite", false, "could not start a reading to open Change voice");
            for (const [, re] of VOICES_SHEET.slice(0, 2)) await findAndClick(re);
            await findAndClick(/^Yêu thích Thái Sơn$/);
          }
        }
        crashed("favorite");
      }

      // In a scroll, a jump far down the document lands where it was aimed
      // even when pictures above load on the way (campaign 26/09: the first
      // jump stopped 2 771 px short - nine pictures grew under the scroll).
      // The pictures keep their room before their bytes arrive.
      await evalJs(`localStorage.setItem("readease.reading-mode", "scroll")`);
      if (!(await goto([...OPEN_BOOK, ["click", /^Tìm trong tài liệu$/]]))) expect("scroll-jump", false, "could not open search in a scroll");
      else {
        await send("Input.insertText", { text: "hoạt động" });
        await sleep(600);
        const clicked = await evalJs(`(() => { const rows = [...document.querySelectorAll("button mark[data-search]")].map((m) => m.closest("button"));
          if (!rows.length) return false; rows[rows.length - 1].click(); return true; })()`);
        await sleep(3000);
        const where = await evalJs(`(() => { const m = document.querySelector('[data-segment] mark[data-search="current"]');
          return m ? Math.round(m.getBoundingClientRect().top) : null; })()`);
        expect("scroll-jump", clicked && where !== null && where > 0 && where < H,
          clicked ? `the hit's mark ended at ${where} px after the jump, not in the ${H} px window` : "no search hit to jump to");
        crashed("scroll-jump");
      }
      await evalJs(`localStorage.removeItem("readease.reading-mode")`);

      // The Speaker row names where the voice goes (HIG 3.21), asked of the
      // host once the page is up. The mock answers the way the host does, so
      // a row still saying "Chưa biết" means the page never asked (campaign
      // 26/09: no gate had ever shown the named row).
      if (!(await goto(SCREENS.player_settings))) expect("speaker", false, "could not open Voice settings");
      else {
        const row = await evalJs(`(() => { const title = [...document.querySelectorAll('[role="dialog"] *')].find((e) => !e.childElementCount && e.textContent.trim() === "Loa");
          return title ? title.parentElement.textContent.trim() : null; })()`);
        expect("speaker", row === "LoaMock speakers · Thiết bị ra âm mặc định của hệ",
          `the Speaker row reads ${JSON.stringify(row)}, not "Loa" / "Mock speakers · Thiết bị ra âm mặc định của hệ"`);
        crashed("speaker");
      }

      // The Voice picker (HIG 3.13 and 4.2, owner 26/09: "nâng cấp dropdown
      // chọn giọng cũng có thể preview voice và favorite luôn"). The keyboard
      // goes in onto the voice in use and comes back to the button; ↑ ↓ keep
      // the column; Escape closes the picker and not the panel under it; a
      // star changes the star, not where the row stands; a sample shows Stop
      // and ends when the picker closes; while something is read no sample
      // can start, and the picker says why; a pick closes it and the button
      // names the new voice.
      const PICKER = '[role="dialog"][aria-label="Chọn giọng"]';
      const TRIGGER = '[role="dialog"] [aria-haspopup="dialog"]';
      const picked = () => evalJs(`(() => {
        const button = document.querySelector('${TRIGGER}');
        const box = document.querySelector('${PICKER}');
        const rows = box ? [...box.querySelectorAll("[data-voice-row]")] : [];
        const a = document.activeElement;
        const row = a && a.closest ? a.closest("[data-voice-row]") : null;
        return {
          open: button?.getAttribute("aria-expanded") === "true",
          panel: !!document.querySelector('[role="dialog"][aria-label="Cài đặt giọng đọc"]'),
          shows: button?.textContent.trim() ?? null,
          names: rows.map((r) => r.querySelector("button[aria-pressed]").getAttribute("aria-label").replace(/^Yêu thích /, "")),
          stars: rows.map((r) => r.querySelector("button[aria-pressed]").getAttribute("aria-pressed")),
          heads: box ? [...box.querySelectorAll("h3")].map((h) => h.textContent.trim()) : [],
          current: rows.findIndex((r) => r.querySelector('button[aria-current="true"]')),
          at: row ? rows.indexOf(row) : -1,
          column: row ? [...row.querySelectorAll("button")].indexOf(a) : -1,
          back: !!(a && a.hasAttribute && a.hasAttribute("data-audit-opener")),
          stopping: rows.findIndex((r) => r.querySelectorAll("button")[1].getAttribute("aria-label") === "Dừng nghe thử"),
          locked: rows.length > 0 && rows.every((r) => r.querySelectorAll("button")[1].disabled),
          why: !!box && box.textContent.includes("Đang đọc nên không nghe thử được"),
          reading: [...document.querySelectorAll("button")].some((b) => (b.getAttribute("aria-label") || b.textContent || "").trim() === "Tạm dừng"),
        }; })()`);
      // Press a row's button - 0 the voice, 1 hear, 2 star - with the mouse.
      const pressIn = async (row, column) => {
        const box = await evalJs(`(() => { const rows = [...document.querySelectorAll('${PICKER} [data-voice-row]')];
          const b = rows[${row}] && rows[${row}].querySelectorAll("button")[${column}]; if (!b) return null;
          b.scrollIntoView({ block: "nearest" }); const r = b.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()`);
        if (!box) return false;
        for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) await send("Input.dispatchMouseEvent", { type, x: box.x, y: box.y, button: "left", clickCount: 1 });
        await sleep(450); return true;
      };
      if (!(await goto(SCREENS.player_settings))) expect("picker", false, "could not open Voice settings");
      else {
        const marked = await evalJs(`(() => { const el = document.querySelector('${TRIGGER}'); if (!el) return false;
          document.querySelectorAll("[data-audit-opener]").forEach((e) => e.removeAttribute("data-audit-opener"));
          el.setAttribute("data-audit-opener", ""); el.focus(); return true; })()`);
        if (!marked) expect("picker", false, "no Voice picker button in Voice settings");
        else {
          const shownBefore = (await picked()).shows;
          await key("Enter");
          let p = await picked();
          expect("picker", p.open && p.current >= 0 && p.at === p.current && p.column === 0,
            `Enter left the focus on row ${p.at}, column ${p.column} - not on the voice in use (row ${p.current})`);
          const rows = p.names.length;
          await key("ArrowDown");
          p = await picked();
          expect("picker", p.at === (p.current + 1) % rows && p.column === 0, `ArrowDown went to row ${p.at}, column ${p.column}`);
          await key("Tab");
          p = await picked();
          expect("picker", p.at === (p.current + 1) % rows && p.column === 1, `Tab went to row ${p.at}, column ${p.column}, not to that row's Nghe thử`);
          await key("ArrowUp");
          p = await picked();
          expect("picker", p.at === p.current && p.column === 1, `ArrowUp went to row ${p.at}, column ${p.column}, not up the same column`);
          await key("Escape");
          p = await picked();
          expect("picker", !p.open && p.panel && p.back, `Escape left the picker ${p.open ? "open" : "closed"}, the panel ${p.panel ? "open" : "closed"}, the focus ${p.back ? "on the button" : "elsewhere"}`);

          // A star from the picker: the star changes, the row stays; the
          // next opening has a Favourites group with that voice first.
          await clickAt(TRIGGER);
          p = await picked();
          const other = (p.current + 1) % rows;
          const name = p.names[other];
          const before = p.names.join("|");
          await pressIn(other, 2);
          p = await picked();
          expect("picker", p.stars[other] === "true" && p.names.join("|") === before,
            `the star on "${name}" went ${p.stars[other]}, and the rows went ${before} -> ${p.names.join("|")}`);
          await key("Escape");
          await clickAt(TRIGGER);
          p = await picked();
          expect("picker", p.heads[0] === "Yêu thích" && p.names[0] === name, `reopened, the picker starts ${JSON.stringify(p.heads[0])} / ${p.names[0]}, not Yêu thích / ${name}`);

          // A sample from the picker shows Stop on its row, leaves the other
          // rows' buttons pressable, and ends when the picker closes.
          const sampled = p.names.indexOf(name);
          await pressIn(sampled, 1);
          p = await picked();
          expect("picker", p.stopping === sampled && !p.locked, `a sample left Stop on row ${p.stopping}, not ${sampled}${p.locked ? ", and locked every row" : ""}`);
          // Quickly: the mock's sample is one sentence, over in ~1.35 s.
          await key("Escape", { pause: 200 });
          p = await picked();
          expect("picker", !p.open && !p.reading, `the sample ${p.reading ? "kept playing" : "stopped"} after the picker closed`);

          // A pick closes it, and the button names the voice picked.
          await clickAt(TRIGGER);
          p = await picked();
          const last = p.names.length - 1;
          const target = p.names[last];
          await pressIn(last, 0);
          p = await picked();
          expect("picker", !p.open && p.shows === target, `picking "${target}" left the picker ${p.open ? "open" : "closed"} and the button saying ${JSON.stringify(p.shows)}`);

          // Put the star back off. The first voice cannot come back this way,
          // and should not: it was offered only while it was the one in use
          // (the switch decides what is offered, HIG 3.13).
          await clickAt(TRIGGER);
          p = await picked();
          const starredAt = p.names.indexOf(name);
          await pressIn(starredAt, 2);
          p = await picked();
          expect("picker", p.stars[starredAt] === "false" && !p.names.includes(shownBefore),
            `unstarring "${name}" left it ${p.stars[starredAt]}; "${shownBefore}" ${p.names.includes(shownBefore) ? "is still offered after another voice was picked" : "left the list"}`);
          await key("Escape");
        }
        crashed("picker");
      }
      // While a reading plays, no sample can start: every Nghe thử in the
      // picker is locked, and the picker says why (a locked button shows no
      // tooltip).
      if (!(await goto([...OPEN_BOOK]))) expect("picker", false, "could not open a document to read");
      else if ((await findAndClick(/^Đọc tiếp$/)) && (await waitFor(/^Tạm dừng$/, 6000, "button"))) {
        await findAndClick(/^Cài đặt giọng đọc$/);
        await clickAt(TRIGGER);
        const p = await picked();
        expect("picker", p.open && p.locked && p.why, `while reading, the picker was ${p.open ? "open" : "closed"}, samples ${p.locked ? "locked" : "not locked"}, reason ${p.why ? "said" : "missing"}`);
        await key("Escape");
        await key("Escape");
        await findAndClick(/^Dừng$/);
        crashed("picker");
      } else expect("picker", false, "could not start a reading");
      // In a scroll the page follows the voice (Reader.tsx), and changing
      // voice mid-reading is an ordinary thing to do (HIG 3.13): the page
      // scrolling must not shut the picker - only a scroll that moves the
      // picker's own button may (26/09).
      await evalJs(`localStorage.setItem("readease.reading-mode", "scroll")`);
      if (!(await goto([...OPEN_BOOK]))) expect("picker", false, "could not open a document in a scroll");
      else if ((await findAndClick(/^Đọc tiếp$/)) && (await waitFor(/^Tạm dừng$/, 6000, "button"))) {
        await findAndClick(/^Cài đặt giọng đọc$/);
        await clickAt(TRIGGER);
        const opened = (await picked()).open;
        const scrolled = await evalJs(`(() => { let el = document.querySelector("[data-segment]");
          while (el && !(el.scrollHeight > el.clientHeight + 1 && /auto|scroll/.test(getComputedStyle(el).overflowY))) el = el.parentElement;
          if (!el) return false; el.scrollTop += 200; return true; })()`);
        await sleep(500);
        const p = await picked();
        expect("picker", opened && scrolled && p.open,
          !opened ? "the picker did not open over a reading in a scroll" : !scrolled ? "found no scrolling page to move" : "the page scrolling under it (as it does to follow the voice) closed the picker");
        await key("Escape");
        await key("Escape");
        await findAndClick(/^Dừng$/);
        crashed("picker");
      } else expect("picker", false, "could not start a reading in a scroll");
      await evalJs(`localStorage.removeItem("readease.reading-mode")`);

      // Motion that is Apple-smooth and stays cheap (HIG 3.17, owner 26/09:
      // "đẹp nhưng vẫn phải đảm bảo hiệu suất"). A segmented row has ONE pill
      // that slides on the control spring - seen part-way, then exactly under
      // the option, never more than a few percent past it - and lands at once
      // under Reduce Motion; the side column's compact tabs resize it on the
      // way. The Voice picker is a popover that grows from its button. A star
      // bounces when it is pressed, and a list that opens with it on stays
      // still. Sampled in the page, frame by frame, from the click.
      const slide = (group) => evalJs(`(async () => {
        const group = document.querySelector('[role="radiogroup"][aria-label="${group}"]');
        const thumb = group && group.querySelector(".segment-thumb");
        const target = group && [...group.querySelectorAll('[role="radio"]')].find((r) => r.getAttribute("aria-checked") !== "true" && !r.disabled);
        if (!thumb || !target) return { error: !group ? "no row" : !thumb ? "no pill" : "no other option" };
        const g = group.getBoundingClientRect();
        const left = () => thumb.getBoundingClientRect().left - g.left;
        const from = left();
        target.click();
        const frames = [];
        let easing = null;
        let fading = null;
        const start = performance.now();
        while (performance.now() - start < 700) {
          await new Promise((r) => requestAnimationFrame(r));
          frames.push(left());
          // Read while it moves: at rest the pill is "still", no transition.
          if (easing === null) easing = getComputedStyle(thumb).transitionTimingFunction;
          // And whether the chosen option's words are fading in with it.
          if (fading === null) fading = [...target.querySelectorAll("*")].some((e) => e.getAnimations().length > 0);
        }
        const r = target.getBoundingClientRect();
        return { from, to: r.left - g.left, frames, width: thumb.getBoundingClientRect().width, wanted: r.width, easing, fading };
      })()`);
      const judged = (m) => {
        if (!m || m.error) return m?.error ?? "nothing measured";
        const lo = Math.min(m.from, m.to) + 0.5, hi = Math.max(m.from, m.to) - 0.5;
        const travel = Math.abs(m.to - m.from);
        const past = Math.max(...m.frames.map((x) => (m.to > m.from ? x - m.to : m.to - x)));
        const last = m.frames[m.frames.length - 1];
        if (!m.frames.some((x) => x > lo && x < hi)) return `the pill jumped from ${Math.round(m.from)} to ${Math.round(m.to)} px - never seen on the way`;
        if (Math.abs(last - m.to) > 1 || Math.abs(m.width - m.wanted) > 1) return `the pill stopped at ${last.toFixed(1)} px, ${m.width.toFixed(1)} wide - not under the option (${m.to.toFixed(1)}, ${m.wanted.toFixed(1)})`;
        if (past > travel * 0.05 + 1) return `the pill ran ${past.toFixed(1)} px past its option on a ${travel.toFixed(1)} px move`;
        if (!/linear\(/.test(m.easing)) return `the pill is not on the spring (${m.easing.slice(0, 40)})`;
        return null;
      };
      if (!(await goto(SCREENS.reading_settings.slice(0, -2)))) expect("motion", false, "could not open Reading settings");
      else {
        const verdict = judged(await slide("Giao diện"));
        expect("motion", verdict === null, `Giao diện: ${verdict}`);
        await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
        const still = await slide("Giao diện");
        await send("Emulation.setEmulatedMedia", { features: [] });
        expect("motion", !still?.error && Math.abs(still.frames[0] - still.to) <= 1,
          still?.error ? `Reduce Motion: ${still.error}` : `under Reduce Motion the pill was at ${still.frames[0].toFixed(1)} px one frame after the click, not at ${still.to.toFixed(1)}`);
        crashed("motion");
      }
      if (!(await goto([...OPEN_BOOK, ["click?", /^Hiện mục lục$/], ["wait", /^Mục lục$/]]))) expect("motion", false, "could not open the side column");
      else {
        const tabs = await slide("Danh sách của tài liệu");
        const verdict = judged(tabs);
        expect("motion", verdict === null, `side column tabs: ${verdict}`);
        // A compact tab's words arrive with the pill, not ahead of it (27/09).
        expect("motion", tabs?.fading === true, `the chosen tab's words appeared at once (fading: ${tabs?.fading}) - they should fade in as the pill slides`);
        crashed("motion");
      }
      if (!(await goto(SCREENS.player_settings))) expect("motion", false, "could not open Voice settings");
      else {
        const opening = await evalJs(`(async () => {
          const button = document.querySelector('${TRIGGER}');
          button.click();
          const seen = [];
          const start = performance.now();
          while (performance.now() - start < 500) {
            await new Promise((r) => requestAnimationFrame(r));
            const box = document.querySelector('${PICKER}');
            if (box) seen.push(parseFloat(getComputedStyle(box).opacity));
          }
          const box = document.querySelector('${PICKER}');
          if (!box) return null;
          const b = button.getBoundingClientRect(), l = box.getBoundingClientRect();
          const side = l.top >= b.bottom ? "origin-top-right" : l.bottom <= b.top ? "origin-bottom-right" : "origin-right";
          return { popover: box.classList.contains("layer-popover"), origin: [...box.classList].find((c) => c.startsWith("origin-")) ?? null, side,
            rising: seen.some((o) => o > 0 && o < 1), last: seen[seen.length - 1] };
        })()`);
        expect("motion", opening?.popover && opening.origin === opening.side && opening.rising && opening.last === 1,
          `the Voice picker opened ${JSON.stringify(opening)} - wanted a popover growing from ${opening?.side}`);
        await key("Escape");
        crashed("motion");
      }
      const STAR = '[role="dialog"] button[aria-label="Yêu thích Thái Sơn"]';
      if (!(await goto([...OPEN_BOOK, ...VOICES_SHEET]))) expect("motion", false, "could not open the voices sheet");
      else {
        const knob = await evalJs(`(() => { const s = document.querySelector('[role="dialog"] input[role="switch"]'); const spans = s ? s.closest("label").querySelectorAll("span") : [];
          return spans.length ? getComputedStyle(spans[spans.length - 1]).transitionTimingFunction : null; })()`);
        expect("motion", /linear\(/.test(knob ?? ""), `the switch knob is not on the spring (${String(knob).slice(0, 40)})`);
        const pressed = await evalJs(`(async () => { const star = document.querySelector('${STAR}'); if (!star) return null;
          const was = star.getAttribute("aria-pressed"); star.click();
          await new Promise((r) => requestAnimationFrame(r));
          return { was, now: star.getAttribute("aria-pressed"), running: star.querySelector("svg")?.getAnimations().length ?? -1 }; })()`);
        expect("motion", pressed?.was === "false" && pressed.now === "true" && pressed.running > 0, `pressing the star gave ${JSON.stringify(pressed)} - wanted it on, bouncing`);
        await sleep(700);
        await key("Escape");
        for (const [, re] of VOICES_SHEET.slice(0, 2)) await findAndClick(re);
        await waitFor(/^Danh sách giọng đọc$/);
        const resting = await evalJs(`(() => { const svg = document.querySelector('${STAR} svg'); return svg ? svg.getAnimations().length : -1; })()`);
        expect("motion", resting === 0, `a star already on moved when the list opened (${resting} animation(s))`);
        await findAndClick(/^Yêu thích Thái Sơn$/);
        crashed("motion");
      }

      // A colour an icon button is given is the colour it shows (26/09):
      // IconButton's own resting `text-ink-mute` came later in the stylesheet
      // than every colour named before "ink-mute", so an opener's "open" ink,
      // the transport's ink and a playing sample's brand never showed.
      const inks = () => evalJs(`(() => { const probe = (cls) => { const s = document.createElement("span"); s.className = cls; document.body.append(s);
        const c = getComputedStyle(s).color; s.remove(); return c; }; return { ink: probe("text-ink"), mute: probe("text-ink-mute"), brand: probe("text-brand-600") }; })()`);
      if (!(await goto([...OPEN_BOOK, ["click", /^Cài đặt đọc$/], ["wait", /^Cài đặt đọc$/, "[role=dialog]"]]))) expect("ink", false, "could not open Reading settings");
      else {
        const tone = await inks();
        const opener = await evalJs(`(() => { const b = document.querySelector('button[aria-label="Cài đặt đọc"][aria-expanded="true"]') || [...document.querySelectorAll("button")].find((e) => e.getAttribute("aria-label") === "Cài đặt đọc");
          return b ? getComputedStyle(b).color : null; })()`);
        expect("ink", opener === tone.ink, `the Reading settings button, its panel open, is ${opener} - not ink ${tone.ink} (mute is ${tone.mute})`);
        // Faint is the locked shade (owner 17/09: "mờ quá"): a button that
        // can be pressed never wears it, now that a colour passed in shows.
        const faint = await evalJs(`(() => { const probe = document.createElement("span"); probe.className = "text-ink-faint"; document.body.append(probe);
          const shade = getComputedStyle(probe).color; probe.remove();
          return [...document.querySelectorAll(".icon-button")].filter((b) => !b.disabled && b.getBoundingClientRect().width > 0 && !b.closest("[inert]") && getComputedStyle(b).color === shade)
            .map((b) => b.getAttribute("aria-label")); })()`);
        expect("ink", faint.length === 0, `enabled icon buttons in the locked shade: ${faint.join(", ")}`);
        crashed("ink");
      }
      if (!(await goto([...OPEN_BOOK, ...VOICES_SHEET]))) expect("ink", false, "could not open the voices sheet");
      else {
        const tone = await inks();
        await findAndClick(/^Nghe thử$/);
        await sleep(200);
        const playing = await evalJs(`(() => { const b = document.querySelector('[role="dialog"] button[aria-label="Dừng nghe thử"]'); return b ? getComputedStyle(b).color : null; })()`);
        expect("ink", playing === tone.brand, `a playing sample's Stop is ${playing} - not the brand ${tone.brand} (mute is ${tone.mute})`);
        await findAndClick(/^Dừng nghe thử$/);
        crashed("ink");
      }
      // The words a person reads about a voice are in their language (26/09):
      // the Voice row said the SDK's own "Nữ · Mỹ" in the English interface,
      // right above a picker that said "Female · American".
      if (!(await goto(SCREENS.player_settings, "en"))) expect("words", false, "could not open Voice settings in English");
      else {
        // The row the Voice picker names itself by - its title's own line.
        const line = await evalJs(`(() => { const button = document.querySelector('[role="dialog"] [aria-haspopup="dialog"]');
          const title = button && document.getElementById(button.getAttribute("aria-labelledby").split(" ")[0]);
          return title ? title.parentElement.textContent.trim().replace(/^Voice/, "") : null; })()`);
        expect("words", line !== null && /^[\x20-\x7E·]*$/.test(line), `the Voice row reads ${JSON.stringify(line)} in the English interface`);
        crashed("words");
      }
      // The update sheet in English (27/09): its date and its notes were the
      // Vietnamese half, and code marks showed as backticks.
      if (!(await goto([], "en"))) expect("words", false, "could not load the English interface");
      else {
        await perform("check-updates");
        await waitFor(/is available\.$/, 6000, "[role=dialog] p");
        const said = await evalJs(`(() => { const d = [...document.querySelectorAll('[role="dialog"]')].find((e) => e.getAttribute("aria-label") === "Software Update");
          return d ? d.textContent : null; })()`);
        // The Vietnamese HALF, not a quoted name: 0.1.19's English notes quote
        // a button by its Vietnamese label (a slip in the notes, not the app),
        // so the measure is how many letters carry Vietnamese marks - the
        // Vietnamese half runs at 20-25 %, the English one under 1 %.
        const letters = (said ?? "").match(/\p{L}/gu)?.length ?? 0;
        const marked = ((said ?? "").match(/[ăâđêôơưàáạảãằắặẳẵầấậẩẫèéẹẻẽềếệểễìíịỉĩòóọỏõồốộổỗờớợởỡùúụủũừứựửữỳýỵỷỹ]/giu) ?? []).length;
        const dated = /Released \d{1,2}\s(January|February|March|April|May|June|July|August|September|October|November|December)\s\d{4}/.test(said ?? "");
        expect("words", said !== null && letters > 0 && marked / letters < 0.03 && dated && !said.includes("`"),
          said === null ? "the English update sheet did not open" : `the English update sheet: ${(100 * marked / Math.max(letters, 1)).toFixed(1)} % Vietnamese-marked letters, date ${dated ? "in English" : "not in English"}, ${said.split("`").length - 1} backticks - ${JSON.stringify(said.slice(0, 100))}`);
        crashed("words");
      }
      // The paid voice's cost panel in English (27/09): money, counts and the
      // price's day were written the Vietnamese way - "$0,04", "11.800
      // characters", "1 chapters", a raw "2026-09-10" - and so was the read
      // button's figure beside it.
      if (!(await goto(SCREENS.cost, "en", STATES.paid))) expect("words", false, "could not open the paid voice's cost panel in English");
      else {
        const said = await evalJs(`(() => { const d = [...document.querySelectorAll('[role="dialog"]')].find((e) => e.getAttribute("aria-label") === "Paid voice");
          const read = [...document.querySelectorAll("button")].map((b) => b.textContent ?? "").find((t) => t.includes("$"));
          return d ? d.textContent + " | " + (read ?? "") : null; })()`);
        const wrong = [/\$\d+,\d{2}/, /\b\d{1,3}\.\d{3}\b/, /\b1 chapters\b/, /\d{4}-\d{2}-\d{2}/].filter((re) => re.test(said ?? "")).map(String);
        expect("words", said !== null && said.includes("$") && wrong.length === 0,
          said === null ? "the English cost panel did not open" : `the English cost panel writes ${wrong.join(" ")} - ${JSON.stringify(said.slice(0, 200))}`);
        crashed("words");
      }
      // What a copy says when it worked (27/09): the Move-notes screen drew
      // every outcome - "Copied 2 items…" included - as an error, in the
      // danger colour and as an alert.
      if (!(await goto(SCREENS.transfer_done, "en"))) expect("transfer", false, "could not copy notes across in the mock");
      else {
        const tone = await inks();
        const done = await evalJs(`(() => { const p = [...document.querySelectorAll("p")].find((e) => /^Copied \\d+ items?/.test(e.textContent ?? ""));
          return p ? { role: p.getAttribute("role"), color: getComputedStyle(p).color } : null; })()`);
        expect("transfer", done !== null && done.role !== "alert" && done.color === tone.mute,
          done === null ? "no notice after copying" : `a copy that worked is reported as role=${done.role}, colour ${done.color} (mute is ${tone.mute})`);
        crashed("transfer");
      }
      // A reading that fails says why, and nothing covers it (27/09): the
      // read button's preview of where it would start belongs to the button
      // at rest, but its state outlived the press - it came back the moment
      // the refused reading returned to idle, over the line saying why.
      // The preview itself still opens on a hover at rest - the fix closes it
      // on the press, not for good.
      if (!(await goto(OPEN_BOOK, "vi", STATES.voicefail))) expect("reading-failed", false, "could not open the book");
      else {
        const box = await evalJs(`(() => { const b = [...document.querySelectorAll("button")].find((e) => /^Đọc tiếp/.test(e.textContent.trim()));
          if (!b) return null; const r = b.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()`);
        if (box) await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.x, y: box.y });
        const opened = box !== null && await waitFor(/^Bấm để tới chỗ này$/, 3000, "span");
        const failed = (await findAndClick(/^Đọc tiếp|^Continue/)) && (await waitFor(/./, 6000, "[role=alert]"));
        await sleep(300);
        const seen = failed ? await evalJs(`(() => { const a = document.querySelector("[role=alert]"); const r = a.getBoundingClientRect();
          const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
          return { covered: !a.contains(top), tip: document.body.innerText.includes("Bấm để tới chỗ này") }; })()`) : null;
        expect("reading-failed", opened && seen !== null && !seen.covered && !seen.tip,
          seen === null ? `no failure line after a refused reading (preview ${opened ? "opened" : "never opened"} on hover)`
            : `hover ${opened ? "opened" : "did not open"} the preview; after the refused reading the failure line is ${seen.covered ? "covered" : "visible"} and the preview is ${seen.tip ? "open" : "closed"}`);
        crashed("reading-failed");
      }
      // A note opened for writing is written ON (27/09): the editor took the
      // focus with the caret at the start, so words typed into an existing
      // note landed in front of it.
      if (!(await goto(NOTE_EDITOR, "vi"))) expect("note-caret", false, "could not open a note for writing");
      else {
        await type(" thêm");
        const said = await evalJs(`(() => { const box = document.querySelector("textarea"); return box ? box.value : null; })()`);
        expect("note-caret", said !== null && said.endsWith(" thêm"),
          said === null ? "no note editor" : `typing into an opened note wrote ${JSON.stringify(said)} - not at its end`);
        crashed("note-caret");
      }
      // A refused key is told what to do HERE (27/09): the key form reused
      // the reading's sentences, which send a person "to the voice
      // settings" (they are in them) or to "press read again".
      for (const [lang, code, wanted, wrong] of [
        ["vi", "bad_key", /dán lại vào đây/, /trong phần giọng đọc/],
        ["en", "network", /press Save again/, /press read again/],
      ]) {
        if (!(await goto([...HUB, ["click", /^Thêm khoá$|^Add key$/], ["wait", /^Lưu$|^Save$/], ["type", "khoa-thu-nghiem"],
          ["click", /^Lưu$|^Save$/], ["wait", /./, "[role=alert]"]], lang, `keyfail=${code}`))) { expect("key-words", false, `no refusal for keyfail=${code}`); continue; }
        const said = await evalJs(`(() => { const a = document.querySelector("[role=alert]"); return a ? a.textContent : null; })()`);
        expect("key-words", said !== null && wanted.test(said) && !wrong.test(said), `a ${code} refusal in the key form (${lang}) says ${JSON.stringify(said)}`);
        crashed("key-words");
      }
      // Pasted text past the limit (27/09): the count and the line saying
      // what to do sat in one run of text - "100.004 / 100.000 ký tựNội
      // dung dài hơn giới hạn". They are two things; there is room between.
      if (!(await goto(SCREENS.paste_over, "vi"))) expect("paste-words", false, "could not paste past the limit");
      else {
        const gap = await evalJs(`(() => { const over = [...document.querySelectorAll("span")].find((e) => /^Nội dung dài hơn giới hạn/.test(e.textContent));
          const count = over && over.previousElementSibling; if (!over || !count) return null;
          const a = count.getBoundingClientRect(), b = over.getBoundingClientRect();
          return b.top >= a.bottom - 1 ? 99 : Math.round(b.left - a.right); })()`);
        expect("paste-words", gap !== null && gap >= 4, gap === null ? "no over-limit line" : `the count and the over-limit line are ${gap}px apart`);
        crashed("paste-words");
      }
      // What an Apple Books import says when done is read whole (27/09): the
      // footer cut it to one line - "1 document imported · 0 highlights
      // matched · 0 not fou…" - at the window's floor.
      if (!(await goto(SCREENS.apple_imported, "en"))) expect("apple-summary", false, "could not import from the Apple Books sheet");
      else {
        const cut = await evalJs(`(() => { const p = [...document.querySelectorAll("[role=dialog] p")].find((e) => /documents? imported/.test(e.textContent));
          return p ? { wide: p.scrollWidth > p.clientWidth + 1, tall: p.scrollHeight > p.clientHeight + 1, said: p.textContent } : null; })()`);
        expect("apple-summary", cut !== null && !cut.wide && !cut.tall, cut === null ? "no summary after the import" : `the import summary is clipped (${cut.wide ? "width" : "height"}): ${JSON.stringify(cut.said)}`);
        crashed("apple-summary");
      }
      // No money without a price (owner, 04/09): a paid voice whose price
      // could not be worked out leaves the read button locked, and says so.
      if (!(await goto(OPEN_BOOK, "vi", STATES.price_failed))) expect("price-lock", false, "could not open a book with a paid voice");
      else {
        await sleep(900);
        const button = await evalJs(`(() => { const b = [...document.querySelectorAll("button")].find((e) => /^Đọc tiếp/.test(e.textContent.trim()));
          return b ? { disabled: b.disabled, said: b.textContent.trim() } : null; })()`);
        expect("price-lock", button !== null && button.disabled && /chưa có giá/.test(button.said),
          button === null ? "no read button" : `with no price the read button is ${button.disabled ? "locked" : "OPEN"} and says ${JSON.stringify(button.said)}`);
        crashed("price-lock");
      }
      // The field being typed into stays put (27/09): the voice list hangs
      // from its bottom edge and shrank with its matches, so each keystroke
      // that dropped a voice slid the search box down under the typing.
      if (!(await goto([...VOICES, ["click", /^Tìm giọng…$|^Search voices…$/]], "vi"))) expect("voice-search", false, "could not open the voice search");
      else {
        const top = () => evalJs(`(() => { const f = document.querySelector('[role=dialog] input[type=search], [role=dialog] input'); return f ? Math.round(f.getBoundingClientRect().top) : null; })()`);
        await sleep(300);
        const before = await top();
        await type("qwxz");
        await sleep(400);
        const after = await top();
        expect("voice-search", before !== null && after !== null && Math.abs(after - before) <= 1,
          `typing a query that matches nothing moved the search field from y=${before} to y=${after}`);
        crashed("voice-search");
      }
      // The same for the Apple Books sheet's search, at the top of a sheet
      // that sizes itself to its tiles.
      if (!(await goto([...APPLE, ["click-at", "[role=dialog] input"]], "vi"))) expect("apple-search", false, "could not open the Apple Books sheet");
      else {
        const top = () => evalJs(`(() => { const f = document.querySelector('[role=dialog] input'); return f ? Math.round(f.getBoundingClientRect().top) : null; })()`);
        await sleep(300);
        const before = await top();
        await type("qwxz");
        await sleep(400);
        const after = await top();
        expect("apple-search", before !== null && after !== null && Math.abs(after - before) <= 1,
          `typing a query that matches nothing moved the Apple Books search from y=${before} to y=${after}`);
        crashed("apple-search");
      }
      // A download shows itself where the person is (27/09): pressing "Tải và
      // dùng" greyed every button, Close included, while the progress and its
      // Cancel sat at the end of the sheet's scrolling body - out of view at
      // the window's floor.
      if (!(await goto([...HUB, ["click", /^Tải và dùng$|^Download and use$/], ["wait", /^Huỷ tải$|^Cancel download$/]], "vi", STATES.download_hold))) expect("model-progress", false, "could not start a download in the hub");
      else {
        const seen = await evalJs(`(() => { const b = [...document.querySelectorAll("[role=dialog] button")].find((e) => e.textContent.trim() === "Huỷ tải");
          if (!b) return null; const r = b.getBoundingClientRect(); const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
          return { visible: !!top && b.contains(top), y: Math.round(r.y) }; })()`);
        expect("model-progress", seen !== null && seen.visible, seen === null ? "no Cancel download button" : `the download's Cancel is out of view (y=${seen.y}) while every other button is locked`);
        crashed("model-progress");
      }
      // What a download says, in the reader's language (27/09): the engine
      // writes its progress in Vietnamese and the shell has every sentence in
      // English (RUNTIME_EN) - but the download line showed the engine's
      // words untranslated.
      if (!(await goto([...HUB, ["click", /^Download$/], ["wait", /^Cancel download$/]], "en", STATES.english_hold))) expect("model-words", false, "could not start the English download");
      else {
        await sleep(900);
        const said = await evalJs(`(() => { const b = [...document.querySelectorAll("[role=dialog] button")].find((e) => e.textContent.trim() === "Cancel download");
          const p = b && b.closest("div.flex")?.parentElement?.querySelector("p"); return p ? p.textContent : null; })()`);
        const marked = /[ăâđêôơưàáạảãằắặẳẵầấậẩẫèéẹẻẽềếệểễìíịỉĩòóọỏõồốộổỗờớợởỡùúụủũừứựửữỳýỵỷỹ]/i.test(said ?? "");
        expect("model-words", said !== null && !marked, said === null ? "no download line" : `the English download says ${JSON.stringify(said)}`);
        crashed("model-words");
      }
      // The same on the first-run screen - the first thing a new person
      // sees, and the one place a download is the whole point.
      if (!(await goto([["wait", /Chọn cách đọc để bắt đầu|Choose how to read/], ["click", /^Tải và dùng$|^Download and use$/], ["wait", /^Huỷ tải$|^Cancel download$/]],
        "vi", "model=missing&download=hold"))) expect("first-run-progress", false, "could not start a download on the first-run screen");
      else {
        const seen = await evalJs(`(() => { const b = [...document.querySelectorAll("button")].find((e) => e.textContent.trim() === "Huỷ tải");
          if (!b) return null; const r = b.getBoundingClientRect(); const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
          return { visible: !!top && b.contains(top), y: Math.round(r.y) }; })()`);
        expect("first-run-progress", seen !== null && seen.visible, seen === null ? "no Cancel download button" : `on the first-run screen the download's Cancel is out of view (y=${seen.y})`);
        crashed("first-run-progress");
      }

      // The update sheet's moving parts (HIG 3.20) - what a still cell cannot
      // show. Opened through the dispatcher, it is modal: the keyboard lands
      // inside and Tab stays there. Escape closes it while nothing runs, and
      // NOT while a download does (work in flight is not hidden). Download
      // and Install walks downloading -> installing -> installed and offers
      // Relaunch; Install When Quitting closes it and the next opening says
      // it is armed; Skip This Version closes it.
      const sheet = () => evalJs(`(() => { const d = [...document.querySelectorAll('[role="dialog"]')].find((e) => e.getAttribute("aria-label") === "Bản mới");
        if (!d) return null; const a = document.activeElement;
        return { headline: d.querySelector("p")?.textContent.trim() ?? null, inside: !!(a && d.contains(a)),
          buttons: [...d.querySelectorAll("button")].map((b) => (b.getAttribute("aria-label") || b.textContent).trim()) }; })()`);
      const until = async (probe, test, ms = 6000) => { const end = Date.now() + ms; let v = await probe(); while (!test(v) && Date.now() < end) { await sleep(150); v = await probe(); } return v; };
      const OFFER = "Có ReadEase 0.1.20.";
      if (!(await goto([]))) expect("update", false, "home did not load");
      else {
        const reached = await perform("check-updates");
        let u = await until(sheet, (v) => v?.headline === OFFER);
        expect("update", reached && u?.headline === OFFER && u.inside, `the update sheet opened ${JSON.stringify(u)} - wanted "${OFFER}" with the focus inside`);
        for (let i = 0; i < (u?.buttons.length ?? 0) + 2; i++) await key("Tab", { pause: 120 });
        u = await sheet();
        expect("update", !!u?.inside, "Tab left the update sheet - it is modal");
        await key("Escape");
        expect("update", (await sheet()) === null, "Escape did not close the update sheet while nothing was running");
        await perform("check-updates");
        await until(sheet, (v) => v?.headline === OFFER);
        await findAndClick(/^Tải và cài$/);
        await key("Escape", { pause: 150 });
        u = await sheet();
        expect("update", u !== null && /^Đang tải bản 0\.1\.20/.test(u.headline ?? ""), `Escape during the download left ${JSON.stringify(u?.headline ?? "no sheet")} - a download stays in view`);
        u = await until(sheet, (v) => !!v?.buttons.includes("Khởi động lại"), 8000);
        expect("update", u?.headline === "Đã cài bản 0.1.20. Khởi động lại để dùng." && u.buttons.includes("Khởi động lại"), `after the install the sheet said ${JSON.stringify(u?.headline)} with ${JSON.stringify(u?.buttons)}`);
        crashed("update");
      }
      if (!(await goto([]))) expect("update", false, "home did not load again");
      else {
        await perform("check-updates");
        await until(sheet, (v) => v?.headline === OFFER);
        await findAndClick(/^Cài đặt khi thoát$/);
        const closed = await until(sheet, (v) => v === null, 8000);
        expect("update", closed === null, "Install When Quitting left the sheet open");
        await perform("check-updates");
        const armed = await until(sheet, (v) => v !== null);
        expect("update", armed?.headline === "Sẽ cài ReadEase 0.1.20 khi bạn thoát app.", `reopened after Install When Quitting, the sheet said ${JSON.stringify(armed?.headline)}`);
        await key("Escape");
        crashed("update");
      }
      if (!(await goto([]))) expect("update", false, "home did not load a third time");
      else {
        await perform("check-updates");
        await until(sheet, (v) => v?.headline === OFFER);
        await findAndClick(/^Bỏ qua phiên bản này$/);
        expect("update", (await until(sheet, (v) => v === null)) === null, "Skip This Version left the sheet open");
        crashed("update");
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
    if (DUMP) writeFileSync(DUMP, JSON.stringify(seen));
    if (findings.length) { console.log(`RENDER_AUDIT RED cells=${cells} ${summary}`); process.exitCode = 1; }
    else if (KEYS_ONLY) console.log(`RENDER_AUDIT PASS keys=${keyChecks} — bàn phím vào được lớp nổi và về đúng nút, chuột không đổi gì, nhóm điều khiển đọc có tên`);
    else console.log(`RENDER_AUDIT PASS cells=${cells}${AXE ? ` axe-watch=${watching.length}` : " (axe skipped)"}${keyChecks ? ` keys=${keyChecks}` : ""} — mọi màn render ở ${W}×${H}, không lỗi console, không lộ key, không tràn ngang`);
  } finally { clearTimeout(killer); chrome.kill("SIGKILL"); }
}
main().catch((e) => { console.error(`RENDER_AUDIT RED ${e.message}`); process.exit(2); });
