/** The shelf as the app's frame sees it, lifted out of App: the list the
 * engine keeps, refreshed whenever the person is back on the home screens
 * (leaving a document is when progress moved), the five documents with a
 * saved place heard most recently for the column's "Đang đọc" group, and
 * the files the system asked the app to open (HIG 3.18).
 */
import { useCallback, useEffect, useRef } from "react";
import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { engineMessage } from "../i18n";
import { bookPaths } from "./bookPaths";
import { drainBookImports } from "./bookImport";
import type { LibraryBook } from "../screens/Library";

export function useShelf({
  inBook,
  inWindow,
  onOpen,
  refreshKey,
}: {
  inBook: boolean;
  /** Whether a host is there to ask (the preview harness has none). */
  inWindow: boolean;
  /** Open a document the system handed the app. */
  onOpen: (book: LibraryBook) => void;
  refreshKey?: string;
}) {
  const [shelf, setShelf] = useState<LibraryBook[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const queue = useRef<string[]>([]);
  const draining = useRef(false);
  const loadShelf = useCallback(async () => {
    try {
      const reply = await invoke<{ result: { books: LibraryBook[] } }>("engine_request", { method: "library.list", params: {} });
      setShelf(reply.result.books); setError(null); return reply.result.books;
    } catch (cause) { setError(engineMessage(cause)); return null; }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { if (!inBook) void loadShelf(); }, [inBook, refreshKey, loadShelf]);


  /* Documents the system asked the app to open (HIG 3.18): import each -
     the engine returns the book it already had for a file it has seen -
     reload the shelf, and open the last one, the way Preview opens the
     file you double-clicked. Drained on mount and on every nudge, so a
     file that launched the app is not lost and none is opened twice. */
  // Home picker, Home drop and Finder all take the same path-based import.
  const openPaths = useCallback(async (paths: string[]) => {
    queue.current.push(...bookPaths(paths));
    if (draining.current || !queue.current.length) return;
    draining.current = true; setImporting(true); setError(null);
    try {
      const { book, error: failed } = await drainBookImports(queue.current, async path => {
        const reply = await invoke<{ result: { book_id: string } }>("engine_request", { method: "library.import", params: { path } });
        return reply.result.book_id;
      }, loadShelf);
      if (failed) setError(engineMessage(failed));
      if (book) onOpen(book);
    } finally { draining.current = false; setImporting(false); }
  }, [loadShelf, onOpen]);
  const openFiles = useCallback(async () => {
    const paths = await invoke<string[]>("take_opened_files").catch(() => [] as string[]);
    await openPaths(paths);
  }, [openPaths]);
  useEffect(() => {
    if (!inWindow && !("__TAURI_INTERNALS__" in window)) return;
    void openFiles();
    const nudged = listen("files:opened", () => { void openFiles(); });
    return () => { nudged.then((unlisten) => unlisten()).catch(() => undefined); };
  }, [inWindow, openFiles]);

  return { shelf, loading, error, importing, openPaths, reload: loadShelf };
}
