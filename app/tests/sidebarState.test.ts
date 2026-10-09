import assert from "node:assert/strict";
import { test } from "node:test";
import {
  DEFAULT_WIDTH, MAX_WIDTH, MIN_WIDTH, clampWidth, dragTarget, initialSidebar, sidebar, sidebarOpen, storedWidth,
  type SidebarEvent, type SidebarState,
} from "../src/ui/sidebarState.ts";

function run(events: SidebarEvent[], from: SidebarState = initialSidebar(null, false)) {
  return events.reduce(sidebar, from);
}

test("nobody has chosen: a wide window opens the column, a narrow one closes it, live", () => {
  const wide = initialSidebar(null, false);
  assert.equal(sidebarOpen(wide), true);
  const narrowed = sidebar(wide, { type: "width", narrow: true });
  assert.equal(sidebarOpen(narrowed), false);
  const widened = sidebar(narrowed, { type: "width", narrow: false });
  assert.equal(sidebarOpen(widened), true);
});

test("the default 1060 px window starts closed, so the page keeps its width", () => {
  assert.equal(sidebarOpen(initialSidebar(null, true)), false);
});

test("a hand beats the automation: opened at a narrow window it stays open when narrowed again", () => {
  const opened = run([{ type: "toggle" }], initialSidebar(null, true));
  assert.equal(sidebarOpen(opened), true);
  assert.equal(opened.choice, "open");
  assert.equal(sidebarOpen(sidebar(opened, { type: "width", narrow: true })), true);
});

test("closed by hand at a wide window, widening does not reopen it", () => {
  const closed = run([{ type: "toggle" }], initialSidebar(null, false));
  assert.equal(closed.choice, "closed");
  assert.equal(sidebarOpen(sidebar(closed, { type: "width", narrow: false })), false);
});

test("the remembered choice is the starting point; anything else means no choice yet", () => {
  assert.equal(initialSidebar("open", true).choice, "open");
  assert.equal(initialSidebar("closed", false).choice, "closed");
  assert.equal(initialSidebar("garbage", false).choice, "auto");
  assert.equal(initialSidebar(null, false).choice, "auto");
});

test("a book changes what the column shows, not whether it shows", () => {
  const closed = run([{ type: "toggle" }]);
  const inBook = sidebar(closed, { type: "book", open: true });
  assert.equal(inBook.book, true);
  assert.equal(inBook.tab, "contents");
  assert.equal(sidebarOpen(inBook), false);
  const open = run([{ type: "book", open: true }]);
  assert.equal(sidebarOpen(open), true);
});

test("leaving a book puts the contents back for the next one", () => {
  const searching = run([{ type: "book", open: true }, { type: "show", tab: "search" }]);
  assert.equal(searching.tab, "search");
  const left = sidebar(searching, { type: "book", open: false });
  assert.equal(left.book, false);
  assert.equal(left.tab, "contents");
});

test("asking for a list opens the column on that tab, even when it was closed by hand", () => {
  const closed = run([{ type: "toggle" }, { type: "book", open: true }]);
  assert.equal(sidebarOpen(closed), false);
  const shown = sidebar(closed, { type: "show", tab: "notes" });
  assert.equal(sidebarOpen(shown), true);
  assert.equal(shown.tab, "notes");
  assert.equal(shown.choice, "open");
});

test("asking for the tab already showing closes the column: a real switch", () => {
  // Open on the contents (the book put it there); ▤ pressed once: closed.
  const contents = run([{ type: "book", open: true }]);
  assert.equal(sidebarOpen(contents), true);
  assert.equal(contents.tab, "contents");
  const closed = sidebar(contents, { type: "show", tab: "contents" });
  assert.equal(sidebarOpen(closed), false);
  // Another tab while open switches without closing; the same tab then closes.
  const search = sidebar(contents, { type: "show", tab: "search" });
  assert.equal(sidebarOpen(search), true);
  assert.equal(search.tab, "search");
  assert.equal(sidebarOpen(sidebar(search, { type: "show", tab: "search" })), false);
});

test("outside a book, asking for a list only opens the column (nothing to toggle against)", () => {
  const home = run([{ type: "toggle" }]);
  const shown = sidebar(home, { type: "show", tab: "contents" });
  assert.equal(sidebarOpen(shown), true);
  assert.equal(sidebarOpen(sidebar(shown, { type: "show", tab: "contents" })), true);
});

test("a dragged width stays between the bounds, and a remembered one is read back or ignored", () => {
  assert.equal(clampWidth(MIN_WIDTH - 50), MIN_WIDTH);
  assert.equal(clampWidth(MAX_WIDTH + 50), MAX_WIDTH);
  assert.equal(clampWidth(311.6), 312);
  assert.equal(clampWidth(Number.NaN), DEFAULT_WIDTH);
  assert.equal(storedWidth(null), DEFAULT_WIDTH);
  assert.equal(storedWidth("garbage"), DEFAULT_WIDTH);
  assert.equal(storedWidth("300"), 300);
  assert.equal(storedWidth("9999"), MAX_WIDTH);
});

test("a drag on the edge opens past halfway to the narrowest column and folds below it", () => {
  const rail = 80;
  const line = (rail + MIN_WIDTH) / 2;
  assert.deepEqual(dragTarget(rail + 10, rail), { open: false, width: rail });
  assert.deepEqual(dragTarget(line - 1, rail), { open: false, width: rail });
  // Open, it is never narrower than a chapter title needs.
  assert.deepEqual(dragTarget(line, rail), { open: true, width: MIN_WIDTH });
  assert.deepEqual(dragTarget(300, rail), { open: true, width: 300 });
  assert.deepEqual(dragTarget(MAX_WIDTH + 90, rail), { open: true, width: MAX_WIDTH });
  // Where the column hides outright (a book), the line is halfway to 0.
  assert.deepEqual(dragTarget(MIN_WIDTH / 2 - 1, 0), { open: false, width: 0 });
  assert.deepEqual(dragTarget(MIN_WIDTH / 2, 0), { open: true, width: MIN_WIDTH });
});
