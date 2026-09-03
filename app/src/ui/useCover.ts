/** A book's cover as a data URL, cached for the life of the app.
 *
 * Covers outlive any one screen: the shelf is left and re-entered every
 * time a book is opened, and the Apple Books sheet shows the same covers,
 * so re-asking the engine for the same bytes would send megabytes down the
 * audio pipe for nothing. undefined = still loading, null = the book has
 * none (or the engine could not read it - a shelf shows the title then,
 * never an error).
 */
import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";

const covers = new Map<string, string | null>();

export function forgetCover(bookId: string): void {
  covers.delete(bookId);
}

export function useCover(bookId: string | null): string | null | undefined {
  const [source, setSource] = useState<string | null | undefined>(
    bookId ? covers.get(bookId) : null,
  );
  useEffect(() => {
    if (!bookId) { setSource(null); return; }
    if (covers.has(bookId)) { setSource(covers.get(bookId)); return; }
    let live = true;
    invoke<{ result: { media_type: string | null; data: string | null } }>(
      "engine_request",
      { method: "book.cover", params: { book_id: bookId } },
    )
      .then((reply) => {
        const { media_type, data } = reply.result;
        const value = media_type && data ? `data:${media_type};base64,${data}` : null;
        covers.set(bookId, value);
        if (live) setSource(value);
      })
      .catch(() => { if (live) setSource(null); });
    return () => { live = false; };
  }, [bookId]);
  return source;
}
