/** The side column's whole life (HIG 3.16), lifted out of App: whether it
 * shows and which of a document's lists it shows (the rules are the pure
 * reducer in `sidebarState.ts`), the width the person drags, and the note
 * the notes tab should land on. App only reads the answers and forwards
 * the person's choices.
 */
import { useCallback, useEffect, useReducer, useState } from "react";
import {
  NARROW,
  STORAGE_KEY,
  WIDTH_KEY,
  clampWidth,
  initialSidebar,
  sidebar,
  sidebarOpen,
  storedWidth,
  type SidebarTab,
} from "./sidebarState";

export function useSideColumn(inBook: boolean) {
  /* The remembered choice and the window's width at start are the
     column's starting point. */
  const [side, dispatchSide] = useReducer(sidebar, undefined, () => {
    let remembered: string | null = null;
    try { remembered = localStorage.getItem(STORAGE_KEY); } catch { /* private window */ }
    return initialSidebar(remembered, window.innerWidth < NARROW);
  });
  const sideOpen = sidebarOpen(side);

  /* The column's width, the person's to drag; remembered when the hand
     lets go, not per move. */
  const [sideWidth, setSideWidth] = useState(() => {
    try { return storedWidth(localStorage.getItem(WIDTH_KEY)); } catch { return storedWidth(null); }
  });
  const resizeSide = useCallback((width: number | null) => {
    if (width === null) {
      setSideWidth((current) => {
        try { localStorage.setItem(WIDTH_KEY, String(current)); } catch { /* private window */ }
        return current;
      });
      return;
    }
    setSideWidth(clampWidth(width));
  }, []);

  /** The list on show in a document, or null: folded, or not in one. */
  const sideTab: SidebarTab | null = sideOpen && side.book ? side.tab : null;

  /* Which note the notes tab should land on, when it was opened from the
     note's own editor. */
  const [notesFocus, setNotesFocus] = useState<string | null>(null);

  /* A choice made by hand is remembered; the automation's answer is not
     (it is recomputed from the window each launch). */
  useEffect(() => {
    if (side.choice === "auto") return;
    try { localStorage.setItem(STORAGE_KEY, side.choice); } catch { /* private window */ }
  }, [side.choice]);

  /* The width, live: `change` is the precise signal, `resize` the backstop
     for a host that resizes without a media-query event (useShortWindow
     learned that from the preview harness, 07/09). */
  useEffect(() => {
    const media = window.matchMedia(`(max-width: ${NARROW - 1}px)`);
    const follow = () => dispatchSide({ type: "width", narrow: media.matches });
    follow();
    media.addEventListener("change", follow);
    window.addEventListener("resize", follow);
    return () => {
      media.removeEventListener("change", follow);
      window.removeEventListener("resize", follow);
    };
  }, []);

  /* A document puts its lists in the column; leaving it puts the
     navigation back. */
  useEffect(() => {
    dispatchSide({ type: "book", open: inBook });
    if (!inBook) setNotesFocus(null);
  }, [inBook]);

  return { side, dispatchSide, sideOpen, sideWidth, resizeSide, sideTab, notesFocus, setNotesFocus };
}
