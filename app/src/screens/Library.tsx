import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { text } from "../i18n";
import { formatSize } from "../ui/format";
import { Button, IconButton, Notice, SectionTitle } from "../ui/controls";
import { BookCard, BookCover, BookGrid, EmptyState } from "../ui/patterns";
import { orderShelf } from "../ui/libraryOrder";
import { forgetCover, useCover } from "../ui/useCover";
import { AppleBooksIcon, ShelfIcon, TrashIcon } from "../ui/icons";
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
  /** The pairing with Apple Books still holds, so a note sync lands on this
   * book. False for a book that arrived by hand. */
  from_apple_books?: boolean;
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
  // One line under a 150px cover holds about 24 characters: the fact that
  // changes what you do (how far you are) leads, the format - which only
  // tells two copies of one title apart - trails and is the first to clip.
  const meta = [
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
        <span
          title={
            book.progress_chapter
              ? text("library.at_chapter", { chapter: book.progress_chapter })
              : undefined
          }
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
      onOpen={onOpen}
      openLabel={text("library.open_book", { title: book.title })}
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
        ) : undefined
      }
    />
  );
}


type NoticeState = { tone: "ok" | "error"; message: string } | null;

export function Library({
  onOpen,
  onPaste,
}: {
  onOpen: (book: LibraryBook) => void;
  onPaste: () => void;
}) {
  const [books, setBooks] = useState<LibraryBook[] | null>(null);
  const [notice, setNotice] = useState<NoticeState>(null);
  const [importing, setImporting] = useState(false);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [applePanel, setApplePanel] = useState(false);
  const picker = useRef<HTMLInputElement>(null);

  const refresh = useCallback(() => {
    invoke<{ result: { books: LibraryBook[] } }>("engine_request", {
      method: "library.list",
      params: {},
    })
      .then((reply) => setBooks(reply.result.books))
      .catch((error) => {
        console.error(error);
        setBooks([]);
      });
  }, []);

  useEffect(refresh, [refresh]);

  const importFile = useCallback(async (file: File) => {
    setImporting(true);
    setNotice(null);
    try {
      const buffer = new Uint8Array(await file.arrayBuffer());
      let binary = "";
      const step = 0x8000;
      for (let index = 0; index < buffer.length; index += step) {
        binary += String.fromCharCode(...buffer.subarray(index, index + step));
      }
      const reply = await invoke<{ result: { was_existing: boolean } }>(
        "import_book_bytes",
        { name: file.name, dataBase64: btoa(binary) },
      );
      setNotice({
        tone: "ok",
        message: reply.result.was_existing
          ? text("library.duplicate")
          : text("library.imported"),
      });
      refresh();
    } catch (error) {
      setNotice({ tone: "error", message: String(error) });
    } finally {
      setImporting(false);
    }
  }, [refresh]);

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
      setNotice({ tone: "error", message: String(error) });
    }
  }, [refresh]);

  const openPicker = () => picker.current?.click();

  // The picker input stays mounted whatever the screen shows - the ref is
  // what opens it.
  const filePicker = (
    <input
      ref={picker}
      type="file"
      accept=".pdf,.epub"
      className="hidden"
      onChange={(event) => {
        const file = event.target.files?.[0];
        if (file) void importFile(file);
        event.target.value = "";
      }}
    />
  );

  const importButton = (
    <Button onClick={openPicker} disabled={importing}>
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
    <section
      className={
        empty
          ? "shell-inset flex min-h-0 flex-1 flex-col"
          : "min-h-0 flex-1 overflow-y-auto pr-1"
      }
    >
      {filePicker}
      {applePanel && (
        <AppleBooksPanel onClose={() => setApplePanel(false)} onLibraryChanged={refresh} />
      )}
      <div className={empty ? "flex min-h-0 flex-1 flex-col" : "shell-inset-content"}>
        <div className="flex items-center gap-3">
          <SectionTitle className="flex-1">{text("library.title")}</SectionTitle>
          {books !== null && books.length > 0 && (
            <>
              {appleButton}
              {importButton}
            </>
          )}
        </div>
        {notice && (
          <Notice tone={notice.tone} className="mt-2">
            {notice.message}
          </Notice>
        )}
        {empty ? (
          // Nothing to list means the invitation IS the content: the way in
          // stands where the books will be, the constraint sits beside the
          // choice it constrains - the layout the Qt shell settled on.
          <EmptyState actions={emptyActions} note={text("library.description")} />
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
