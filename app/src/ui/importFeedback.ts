/** What the shelf says about a drop or an import, before and after.
 *
 * Pure, so the harness (which has no Finder) and a node test can both ask
 * the same questions the window asks: what will this drop do, and what did
 * that import do.
 */
import { text } from "../i18n.ts";

/** What the overlay says while something is being dragged over the window:
 * the number of books in hand, or that there are none. */
export function dropHeadline(books: number): { headline: string; detail: string } {
  if (books <= 0) {
    return { headline: text("library.drop_none"), detail: text("library.drop_none_hint") };
  }
  return {
    headline: books === 1 ? text("library.drop_hint") : text("library.drop_many", { count: books }),
    detail: text("library.drop_anywhere"),
  };
}

export type ImportTally = {
  added: number;
  existing: number;
  failed: number;
  /** The engine's sentence for the last failure, already in the reader's
   * language; null when nothing failed. */
  lastError: string | null;
};

/** One line for the whole batch. A single file keeps the two sentences the
 * shelf always had; several files get the counts, and a failure among them
 * names itself rather than hiding behind "added 2". */
export function importNotice(tally: ImportTally): { tone: "ok" | "error"; message: string } {
  const total = tally.added + tally.existing + tally.failed;
  if (tally.failed > 0) {
    if (total === 1) return { tone: "error", message: tally.lastError ?? "" };
    return {
      tone: "error",
      message: text("library.import_failed_some", {
        added: tally.added,
        failed: tally.failed,
        error: tally.lastError ?? "",
      }),
    };
  }
  if (total === 1) {
    return { tone: "ok", message: text(tally.existing ? "library.duplicate" : "library.imported") };
  }
  return {
    tone: "ok",
    message: text("library.imported_many", { added: tally.added, existing: tally.existing }),
  };
}
