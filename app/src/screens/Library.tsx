import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { invoke } from "@tauri-apps/api/core";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { open } from "@tauri-apps/plugin-dialog";
import { engineMessage, text } from "../i18n";
import { BOOK_EXTENSIONS, bookPaths } from "../ui/bookPaths";
import { formatSize, hoverText } from "../ui/format";
import { Button, IconButton, Notice } from "../ui/controls";
import { BookCard, BookCover, BookGrid, DropZone, EmptyState } from "../ui/patterns";
import { Presence } from "../ui/motion";
import { dropHeadline, importNotice, type ImportTally } from "../ui/importFeedback";
import { orderShelf } from "../ui/libraryOrder";
import { forgetCover, useCover } from "../ui/useCover";
import { AppleBooksIcon, ImportIcon, ShelfIcon, TrashIcon } from "../ui/icons";
import { AppleBooksPanel } from "./AppleBooksPanel";

export type LibraryBook = {
  id: string;
  title: string;
  source_format: string;
  segment_id: string | null;
  /** 0..1 - where the voice got to; null until the book is started. */
  progress_ratio: number | null;
  progress_chapter: string | null;
  chapters: number;
  size_bytes: number | null;
  imported_at: string | null;
  /** When a passage of it was last heard (the engine's progress row) - the
   * order of the books being read, most recent first. Null until then. */
  listened_at?: string | null;
  /** The pairing with Apple Books still holds, so a note sync lands on this
   * book. False for a book that arrived by hand. */
  from_apple_books?: boolean;
  /** Which language this book gets read in - "vi" or "en". */
  language?: string;
  /** True when a reader SET that, rather than the engine reading it off the
   * text. The decision is sticky: the book is not read again on the next
   * launch. */
  language_set?: boolean;
  /** What the book's own words read as, whatever was decided. The two differ
   * only when a reader disagreed with the text, and that is exactly when the
   * voices panel has a suggestion to offer. */
  language_detected?: string;
  /** The engine could not decode this book's stored data. It stays on the
   * shelf so it can be removed or healed by importing the file again; it
   * cannot be opened. */
  damaged?: boolean;
};

/** The cover as a data URL: undefined while loading, null when the book has
 * none (or the engine could not read it - a shelf never shows an error for
 * a missing picture, it shows the title). */
function ShelfBook({
  book,
  confirming,
  onOpen,
  onAskRemove,
  onRemove,
  onKeep,
}: {
  book: LibraryBook;
  confirming: boolean;
  onOpen: () => void;
  onAskRemove: () => void;
  onRemove: () => void;
  onKeep: () => void;
}) {
  const cover = useCover(book.id);
  const reading = book.segment_id !== null;
  // A damaged book has one fact - that it is damaged - and one thing to do
  // about it. Its cover is the one way in, and the way in is the removal
  // question, not the reader.
  const damaged = book.damaged === true;
  // One line under a 150px cover holds about 24 characters: the fact that
  // changes what you do (how far you are) leads, the format - which only
  // tells two copies of one title apart - trails and is the first to clip.
  const meta = damaged ? text("library.damaged") : [
    reading && book.progress_ratio !== null
      ? text("library.progress", { percent: Math.round(book.progress_ratio * 100) })
      : reading && text("library.in_progress"),
    Number.isFinite(book.chapters) && text("library.chapter_count", { count: book.chapters }),
    formatSize(book.size_bytes),
    book.source_format.toUpperCase(),
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <BookCard
      cover={<BookCover source={cover} title={book.title} />}
      title={book.title}
      meta={
        // The chapter the voice is in rides as a tooltip on the fact line:
        // the one line under a cover has no room for it, and it only
        // matters for the book you are about to pick up again.
        //
        // The facts lead it. Measured 09/09: this line is truncated on every
        // shelved book at the narrowest window, and the tooltip that sat
        // here answered about the chapter instead - so hovering the words
        // that were cut off returned a different subject. Own text first.
        <span
          title={hoverText(
            meta,
            book.progress_chapter
              ? text("library.at_chapter", { chapter: book.progress_chapter })
              : null,
          )}
        >
          {meta}
        </span>
      }
      progress={reading ? book.progress_ratio ?? 0 : null}
      tag={
        /* No paper chip behind it: the app mark is already a solid coloured
           square with its own edge, so a white disc under it would be a
           second badge around a badge. Its own shadow does the separating on
           a dark cover. */
        book.from_apple_books ? (
          <span className="block h-5 w-5 overflow-hidden rounded-[5px] shadow-raised">
            <AppleBooksIcon className="h-full w-full" />
            {/* The glyph takes no pointer events, so it cannot carry a
                tooltip without stealing clicks from the cover. The words go
                to the accessibility tree instead. */}
            <span className="sr-only">{text("library.from_apple_books")}</span>
          </span>
        ) : undefined
      }
      onOpen={damaged ? onAskRemove : onOpen}
      openLabel={text(damaged ? "library.damaged_open" : "library.open_book", { title: book.title })}
      accessory={
        !confirming && (
          <IconButton
            onClick={onAskRemove}
            aria-label={text("library.remove")}
            title={text("library.remove")}
            className="bg-paper shadow-raised hover:text-danger"
          >
            <TrashIcon />
          </IconButton>
        )
      }
      caption={
        confirming ? (
          <div className="flex flex-col gap-1.5 text-sm">
            <span className="text-ink-mute">{text("library.remove_confirm")}</span>
            <span className="flex gap-1.5">
              <Button variant="danger" size="sm" onClick={onRemove}>
                <TrashIcon />
                {text("library.remove")}
              </Button>
              <Button variant="ghost" size="sm" onClick={onKeep}>
                {text("library.remove_keep")}
              </Button>
            </span>
          </div>
        ) : damaged ? (
          // The caption stands in for title and fact line, so a damaged
          // book keeps its name and gains the two lines that matter: what
          // is wrong, and what to do about it. Nothing here clips - the
          // next step must be readable, not hovered for.
          <div className="flex min-w-0 flex-col gap-1 text-sm">
            <span className="line-clamp-2 font-semibold leading-snug" title={hoverText(book.title)}>
              {book.title}
            </span>
            <span className="text-xs text-danger">{text("library.damaged")}</span>
            <span className="text-xs text-ink-mute">{text("library.damaged_hint")}</span>
          </div>
        ) : undefined
      }
    />
  );
}


type NoticeState = { tone: "ok" | "error"; message: string } | null;

export function Library({
  onOpen,
  onPaste,
  actionsSlot,
  request = null,
  onRequestDone,
}: {
  onOpen: (book: LibraryBook) => void;
  onPaste: () => void;
  /** Where the shelf's actions stand: the toolbar's trailing cluster, the
   * way a book's actions stand beside its title (16/09). The shelf owns
   * the buttons and their state; the toolbar owns the place. */
  actionsSlot: HTMLElement | null;
  /** A command from the menu bar (HIG 4.1) that only the shelf can carry
   * out: the file picker, or the Apple Books sheet. Taken once, on mount
   * or on arrival, and handed back as done. */
  request?: "add" | "apple-books" | null;
  onRequestDone?: () => void;
}) {
  const [books, setBooks] = useState<LibraryBook[] | null>(null);
  /** Why the shelf could not be listed - kept apart from `books`, because
   * they are different claims and only one of them is true here. */
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notice, setNotice] = useState<NoticeState>(null);
  const [importing, setImporting] = useState(false);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [applePanel, setApplePanel] = useState(false);
  /** Something is being dragged over the window: how many of the things in
   * hand are books. Null when nothing is. The overlay says what a drop will
   * do instead of making the person drop to find out. */
  const [dragging, setDragging] = useState<number | null>(null);
  /** Paths waiting to be imported, in the order they arrived. A second drop
   * or pick while one is running joins the same queue and the same report,
   * rather than racing it for the notice line. */
  const queue = useRef<string[]>([]);
  const draining = useRef(false);

  const refresh = useCallback(() => {
    invoke<{ result: { books: LibraryBook[] } }>("engine_request", {
      method: "library.list",
      params: {},
    })
      .then((reply) => {
        setBooks(reply.result.books);
        setLoadError(null);
      })
      .catch((error) => {
        // Deliberately NOT `setBooks([])`, which is what this used to do.
        // An empty shelf is a claim about the library - "you have no books"
        // - and the truth here is "I could not ask". Someone who has just
        // installed a new build over the old one reads the first as the
        // second, and concludes the update ate everything they had. The
        // engine dies this way for real: it opens the store in `main()`
        // with nothing catching the failure, so a store it cannot read
        // takes the whole sidecar down and every request after it fails.
        // Books already on screen stay on screen: a refresh that fails
        // after an import is no reason to empty a shelf that was right a
        // second ago.
        console.error(error);
        setLoadError(engineMessage(error));
      });
  }, []);

  useEffect(refresh, [refresh]);

  /** Import by PATH. The engine copies the file once, into the library,
   * and never sees more than that. The old way took the bytes through the
   * webview - read, spelled out as a string, base64, JSON, IPC, decoded,
   * written to a temp file, then copied again by the engine: seven copies
   * and about a second of the interface frozen for a 46 MB book (measured
   * 14/09), and the 200 MiB the engine accepts was out of reach. A path
   * costs nothing to carry.
   *
   * One file at a time, in order, until the queue is empty; a file that
   * fails does not stop the ones behind it, it is counted and named. */
  const importPaths = useCallback(async (paths: string[]) => {
    queue.current.push(...paths);
    if (draining.current || !queue.current.length) return;
    draining.current = true;
    setImporting(true);
    setNotice(null);
    const tally: ImportTally = { added: 0, existing: 0, failed: 0, lastError: null };
    try {
      while (queue.current.length) {
        const path = queue.current.shift() as string;
        try {
          const reply = await invoke<{ result: { was_existing: boolean } }>(
            "engine_request",
            { method: "library.import", params: { path } },
          );
          if (reply.result.was_existing) tally.existing += 1;
          else tally.added += 1;
        } catch (error) {
          tally.failed += 1;
          tally.lastError = engineMessage(error);
        }
      }
      setNotice(importNotice(tally));
    } finally {
      draining.current = false;
      setImporting(false);
      refresh();
    }
  }, [refresh]);

  // Dropped from Finder: the window hands over paths, the same paths the
  // picker would. Registered once for the life of the shelf.
  useEffect(() => {
    let live = true;
    const listening = getCurrentWebview().onDragDropEvent((event) => {
      if (!live) return;
      const kind = event.payload.type;
      if (kind === "enter") setDragging(bookPaths(event.payload.paths).length);
      else if (kind === "leave") setDragging(null);
      else if (kind === "drop") {
        setDragging(null);
        void importPaths(bookPaths(event.payload.paths));
      }
    });
    return () => {
      live = false;
      listening.then((unlisten) => unlisten()).catch(() => undefined);
    };
  }, [importPaths]);

  const removeBook = useCallback(async (bookId: string) => {
    try {
      await invoke("engine_request", {
        method: "library.remove",
        params: { book_id: bookId },
      });
      forgetCover(bookId);
      setNotice({ tone: "ok", message: text("library.removed") });
      setConfirming(null);
      refresh();
    } catch (error) {
      setNotice({ tone: "error", message: engineMessage(error) });
    }
  }, [refresh]);

  // The system's own open panel, which answers with paths. Several at
  // once, because a person adding a shelf's worth of books should not have
  // to come back for each one.
  const openPicker = async () => {
    const picked = await open({
      multiple: true,
      filters: [{ name: "PDF, EPUB", extensions: [...BOOK_EXTENSIONS] }],
    }).catch(() => null);
    if (picked) void importPaths(bookPaths(picked));
  };

  // The menu's request, once the shelf is here to answer it.
  useEffect(() => {
    if (!request) return;
    onRequestDone?.();
    if (request === "add") void openPicker();
    else setApplePanel(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request]);

  const importButton = (
    <Button onClick={() => void openPicker()} disabled={importing} title={text("library.drop_invite")}>
      {importing ? text("library.importing") : text("toolbar.open")}
    </Button>
  );
  /* The other way in: what Apple Books already holds. A secondary tool,
     so it sits beside "Mở PDF hoặc EPUB" as a quiet button, and appears in
     the empty state - the quickest way to a full shelf. */
  const appleButton = (
    <Button variant="ghost" onClick={() => setApplePanel(true)}>
      <ShelfIcon />
      {text("library.apple_books")}
    </Button>
  );

  // Only the empty state offers the paste route: with books on screen, a
  // "Dán nội dung" button here would just repeat the tab standing above it.
  const emptyActions = (
    <>
      {importButton}
      {appleButton}
      <Button onClick={onPaste}>{text("nav.paste")}</Button>
    </>
  );

  const empty = books !== null && books.length === 0;

  return (
    // The scroller spans the window and carries the side inset itself, so
    // the scrollbar sits at the window's edge, outside the shelf's margin,
    // the way a Mac list scrolls - not inside the padding, flush against
    // the last column of covers (owner, 15/09). The gutter is reserved
    // whether or not the shelf scrolls yet, so adding the book that makes
    // it scroll does not shift every column by the bar's width.
    <section
      className={
        empty
          ? "shell-inset flex min-h-0 flex-1 flex-col"
          : "-mx-6 min-h-0 flex-1 overflow-y-auto px-6 [scrollbar-gutter:stable]"
      }
    >
      <Presence open={applePanel}>
        <AppleBooksPanel onClose={() => setApplePanel(false)} onLibraryChanged={refresh} />
      </Presence>
      {dragging !== null && (
        <DropZone
          icon={<ImportIcon className="h-10 w-10" />}
          headline={dropHeadline(dragging).headline}
          detail={dropHeadline(dragging).detail}
          tone={dropHeadline(dragging).tone}
        />
      )}
      <div className={empty ? "flex min-h-0 flex-1 flex-col" : "shell-inset-content"}>
        {/* The shelf's name and actions are the toolbar's now (16/09): the
            name as the screen's title, the actions through this portal. */}
        {actionsSlot && books !== null && books.length > 0 && createPortal(
          <>
            {appleButton}
            {importButton}
          </>,
          actionsSlot,
        )}
        {loadError && (
          <Notice tone="error" className="mt-2">
            {text("library.load_failed")} ({loadError})
          </Notice>
        )}
        {notice && (
          <Notice tone={notice.tone} className="mt-2">
            {notice.message}
          </Notice>
        )}
        {empty ? (
          // Nothing to list means the invitation IS the content: the way in
          // stands where the books will be, the constraint sits beside the
          // choice it constrains - the layout the Qt shell settled on.
          <EmptyState
            actions={emptyActions}
            note={
              <>
                {text("library.drop_invite")}
                <br />
                {text("library.description")}
              </>
            }
          />
        ) : (
          <div className="mt-4">
            <BookGrid>
              {orderShelf(books ?? []).map((book) => (
                <ShelfBook
                  key={book.id}
                  book={book}
                  confirming={confirming === book.id}
                  onOpen={() => onOpen(book)}
                  onAskRemove={() => setConfirming(book.id)}
                  onRemove={() => void removeBook(book.id)}
                  onKeep={() => setConfirming(null)}
                />
              ))}
            </BookGrid>
          </div>
        )}
      </div>
    </section>
  );
}
