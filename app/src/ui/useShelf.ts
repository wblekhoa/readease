/** The shelf as the app's frame sees it, lifted out of App: the list the
 * engine keeps, refreshed whenever the person is back on the home screens
 * (leaving a document is when progress moved), the five most recent
 * documents with a saved place for the column's "Đang đọc" group, and the
 * files the system asked the app to open (HIG 3.18).
 */
import { useCallback, useEffect, useMemo } from "react";
import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { bookPaths } from "./bookPaths";
import { orderShelf } from "./libraryOrder";
import type { LibraryBook } from "../screens/Library";

export function useShelf({
  inBook,
  inWindow,
  onOpen,
}: {
  inBook: boolean;
  /** Whether a host is there to ask (the preview harness has none). */
  inWindow: boolean;
  /** Open a document the system handed the app. */
  onOpen: (book: LibraryBook) => void;
}) {
  const [shelf, setShelf] = useState<LibraryBook[]>([]);

  const loadShelf = useCallback(() => {
    invoke<{ result: { books: LibraryBook[] } }>("engine_request", { method: "library.list", params: {} })
      .then((reply) => setShelf(reply.result.books))
      .catch(() => undefined);
  }, []);
  useEffect(() => { if (!inBook) loadShelf(); }, [inBook, loadShelf]);

  const readingNow = useMemo(
    () => orderShelf(shelf.filter((book) => book.segment_id)).slice(0, 5),
    [shelf],
  );

  /* Documents the system asked the app to open (HIG 3.18): import each -
     the engine returns the book it already had for a file it has seen -
     reload the shelf, and open the last one, the way Preview opens the
     file you double-clicked. Drained on mount and on every nudge, so a
     file that launched the app is not lost and none is opened twice. */
  const openFiles = useCallback(async () => {
    const paths = bookPaths(await invoke<string[]>("take_opened_files").catch(() => [] as string[]));
    if (!paths.length) return;
    let last: string | null = null;
    for (const path of paths) {
      try {
        const reply = await invoke<{ result: { book_id: string } }>(
          "engine_request",
          { method: "library.import", params: { path } },
        );
        last = reply.result.book_id;
      } catch (error) {
        console.error("[open] import failed:", path, error);
      }
    }
    const listed = await invoke<{ result: { books: LibraryBook[] } }>(
      "engine_request",
      { method: "library.list", params: {} },
    ).catch(() => null);
    if (!listed) return;
    setShelf(listed.result.books);
    const book = listed.result.books.find((entry) => entry.id === last);
    if (book) onOpen(book);
  }, [onOpen]);
  useEffect(() => {
    if (!inWindow) return;
    void openFiles();
    const nudged = listen("files:opened", () => { void openFiles(); });
    return () => { nudged.then((unlisten) => unlisten()).catch(() => undefined); };
  }, [inWindow, openFiles]);

  return { readingNow };
}
