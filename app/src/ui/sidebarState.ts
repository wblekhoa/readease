/** The side column's state machine, as a pure function (HIG 3.16).
 *
 * What "thông minh" means, written down so node:test can hold it (owner,
 * 16/09: "cột trái sẽ có thể ẩn hiện thông minh tuỳ vào nhu cầu. User có thể
 * tắt/mở giống codex"):
 *
 * 1. A hand beats the automation. The toggle button and ⌥⌘S are a CHOICE,
 *    kept for the session and remembered across launches; after one, the
 *    window's width never opens or closes the column again.
 * 2. Until a choice is made, the width decides: narrower than `NARROW`
 *    closed, wider open, live as the window is dragged - so the default
 *    1060 px window opens with the page at full width (the owner's 02/09
 *    worry about a fixed column eating the page).
 * 3. Context changes what the column SHOWS, never whether it shows: a book
 *    puts the contents up, leaving it puts the navigation back.
 * 4. Asking for a list (▤, the notes button, ⌘F, a paragraph's note icon)
 *    opens the column on that tab - that is a choice too. Asking for the
 *    tab already showing closes the column: a real switch, not a button
 *    that only knows how to open.
 */

export type SidebarTab = "contents" | "notes" | "search";
/** What the person last said with their hands; "auto" until they say. */
export type SidebarChoice = "auto" | "open" | "closed";

export interface SidebarState {
  choice: SidebarChoice;
  /** Whether the window is narrower than `NARROW`. */
  narrow: boolean;
  /** Whether a book is open, which is what puts the lists in the column. */
  book: boolean;
  tab: SidebarTab;
}

/** Below this window width the column closes on its own (a 240 px column
 * beside the two-page spread's 1040 px minimum leaves nothing at 1100). */
export const NARROW = 1100;

export const STORAGE_KEY = "readease.sidebar";

/** The column's width, when the person drags its edge (owner, 16/09:
 * "sidebar có thể nắm kéo để resize"): 240 by default, never narrower
 * than a chapter title can live in, never wider than a third of the
 * narrowest window. Remembered on its own. */
export const WIDTH_KEY = "readease.sidebar-width";
export const DEFAULT_WIDTH = 240;
export const MIN_WIDTH = 200;
export const MAX_WIDTH = 400;

export function clampWidth(width: number): number {
  if (!Number.isFinite(width)) return DEFAULT_WIDTH;
  return Math.round(Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, width)));
}

/** The remembered width, or the default for anything unusable. */
export function storedWidth(remembered: string | null): number {
  const width = Number(remembered);
  return remembered === null || !Number.isFinite(width) ? DEFAULT_WIDTH : clampWidth(width);
}

export type SidebarEvent =
  /** The toggle button or ⌥⌘S. */
  | { type: "toggle" }
  /** The window crossed the width threshold, or was measured at start. */
  | { type: "width"; narrow: boolean }
  /** A book opened (true) or was left (false). */
  | { type: "book"; open: boolean }
  /** A list was asked for by name: ▤, the notes button, ⌘F, a note icon. */
  | { type: "show"; tab: SidebarTab };

export function sidebarOpen(state: SidebarState): boolean {
  return state.choice === "auto" ? !state.narrow : state.choice === "open";
}

export function sidebar(state: SidebarState, event: SidebarEvent): SidebarState {
  switch (event.type) {
    case "toggle":
      return { ...state, choice: sidebarOpen(state) ? "closed" : "open" };
    case "width":
      return { ...state, narrow: event.narrow };
    case "book":
      // Leaving a book returns the contents tab for the next one: notes and
      // search were about the book that was just closed.
      return { ...state, book: event.open, tab: event.open ? state.tab : "contents" };
    case "show":
      if (sidebarOpen(state) && state.book && state.tab === event.tab) {
        return { ...state, choice: "closed" };
      }
      return { ...state, choice: "open", tab: event.tab };
  }
}

/** The state to start from: the remembered choice, the window as it is. */
export function initialSidebar(remembered: string | null, narrow: boolean): SidebarState {
  const choice: SidebarChoice = remembered === "open" || remembered === "closed" ? remembered : "auto";
  return { choice, narrow, book: false, tab: "contents" };
}
