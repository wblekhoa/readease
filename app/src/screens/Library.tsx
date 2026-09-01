import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { text } from "../i18n";
import { formatDate, formatSize } from "../ui/format";
import { Button, IconButton, Notice, SectionTitle } from "../ui/controls";
import { EmptyState, ListRow } from "../ui/patterns";
import { BookIcon, TrashIcon } from "../ui/icons";

export type LibraryBook = {
  id: string;
  title: string;
  source_format: string;
  segment_id: string | null;
  chapters: number;
  size_bytes: number | null;
  imported_at: string | null;
};


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

  // Only the empty state offers the paste route: with books on screen, a
  // "Dán nội dung" button here would just repeat the tab standing above it.
  const emptyActions = (
    <>
      {importButton}
      <Button onClick={onPaste}>{text("nav.paste")}</Button>
    </>
  );

  return (
    <section className="flex min-h-0 flex-1 flex-col">
      {filePicker}
      <div className="flex items-center gap-3">
        <SectionTitle className="flex-1">{text("library.title")}</SectionTitle>
        {books !== null && books.length > 0 && importButton}
      </div>
      {notice && (
        <Notice tone={notice.tone} className="mt-2">
          {notice.message}
        </Notice>
      )}
      {books !== null && books.length === 0 ? (
        // Nothing to list means the invitation IS the content: the way in
        // stands where the books will be, the constraint sits beside the
        // choice it constrains - the layout the Qt shell settled on.
        <EmptyState actions={emptyActions} note={text("library.description")} />
      ) : (
        <div className="mt-3 min-h-0 flex-1 overflow-y-auto">
          {books?.map((book) => (
            <ListRow
              key={book.id}
              leading={<BookIcon />}
              onPress={() => onOpen(book)}
              title={
                <>
                  <span className="truncate text-sm font-semibold">{book.title}</span>
                  <span className="shrink-0 text-xs font-semibold uppercase tracking-wide text-ink-faint">
                    {book.source_format}
                  </span>
                </>
              }
              subtitle={[
                Number.isFinite(book.chapters) &&
                  text("library.chapter_count", { count: book.chapters }),
                formatSize(book.size_bytes),
                formatDate(book.imported_at) &&
                  text("library.imported_on", { date: formatDate(book.imported_at)! }),
                book.segment_id && text("library.in_progress"),
              ]
                .filter(Boolean)
                .join(" · ")}
              trailing={
                confirming === book.id ? (
                  <span className="flex shrink-0 items-center gap-2 text-sm">
                    <span className="text-ink-mute">{text("library.remove_confirm")}</span>
                    <Button variant="danger" size="sm" onClick={() => void removeBook(book.id)}>
                      <TrashIcon />
                      {text("library.remove")}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setConfirming(null)}
                    >
                      {text("library.remove_keep")}
                    </Button>
                  </span>
                ) : (
                  <IconButton
                    onClick={() => setConfirming(book.id)}
                    aria-label={text("library.remove")}
                    title={text("library.remove")}
                    className="shrink-0 opacity-0 hover:text-danger group-hover:opacity-100 focus-visible:opacity-100"
                  >
                    <TrashIcon />
                  </IconButton>
                )
              }
            />
          ))}
        </div>
      )}
    </section>
  );
}
