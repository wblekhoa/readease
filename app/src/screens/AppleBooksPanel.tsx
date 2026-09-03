/** The Apple Books shelf, brought over on request - a secondary tool.
 *
 * One way only: ReadEase reads Apple's library and highlight databases and
 * never writes to them. The sheet has the macOS shape: a short header, the
 * list grouped by what can happen to each book, and the one primary action
 * at the bottom next to what it will do. "Đồng bộ N cuốn" walks the shelf one
 * book at a time (each import is its own request, so the sheet can say where
 * it is and the engine stays free between books).
 */
import { useCallback, useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { text } from "../i18n";
import { Button, IconButton, Input, Notice, Surface } from "../ui/controls";
import { BookTile, MenuButton, MiniCover } from "../ui/patterns";
import { BookIcon, ChevronDownIcon, CloseIcon, ImportIcon, LockIcon, SyncIcon } from "../ui/icons";
import { useCover } from "../ui/useCover";
import { SEARCH_ABOVE, matchesQuery, orderShelfItems } from "../ui/shelfFilter";

/** What comes over with a book: nothing, the highlighted passages, only
 * the passages that carry a note, or everything (owner, 02/09: an import
 * brings nothing by default). */
export type SyncMode = "none" | "highlights" | "notes" | "both";

export type ShelfBook = {
  asset_id: string;
  title: string;
  status: "linked" | "importable" | "encrypted" | "too_large" | "missing";
  book_id: string | null;
  paired_title: string | null;
  highlights: number;
};

function request<T>(method: string, params: object): Promise<T> {
  return invoke<{ result: T }>("engine_request", { method, params }).then((reply) => reply.result);
}

const ERROR_KEYS = {
  not_permitted: "apple.error.not_permitted",
  encrypted: "apple.error.encrypted",
  too_large: "apple.error.too_large",
  book_missing: "apple.error.book_missing",
  not_in_library: "apple.error.not_in_library",
} as const;

function errorText(raw: unknown): string {
  const token = String(raw).replace(/^.*failed: /, "") as keyof typeof ERROR_KEYS;
  return token in ERROR_KEYS ? text(ERROR_KEYS[token]) : String(raw);
}

/** One book as a tile (owner, 02/09: two to a row, short, no colour). The
 * real cover once the book is here, a quiet panel with a glyph when it is
 * not; blocked books stand back and carry no action. */
function ShelfTile({ book, busy, onRun }: { book: ShelfBook; busy: boolean; onRun: (mode: SyncMode) => void }) {
  const cover = useCover(book.status === "linked" ? book.book_id : null);
  const blocked = book.status !== "importable" && book.status !== "linked";
  const facts = [
    book.highlights ? text("apple.highlights", { count: book.highlights }) : null,
    book.status === "linked"
      ? (book.paired_title && book.paired_title !== book.title
          ? text("apple.paired", { title: book.paired_title })
          : text("apple.status_linked"))
      : book.status === "encrypted"
        ? text("apple.status_encrypted")
        : book.status === "too_large"
          ? text("apple.status_too_large")
          : book.status === "missing"
            ? text("apple.status_missing")
            : null,
  ].filter(Boolean).join(" · ");
  const action =
    book.status === "importable"
      ? (
        <MenuButton
          icon={<ImportIcon />}
          label={text("apple.import_options")}
          disabled={busy}
          items={[
            { label: text("apple.import_only"), hint: text("apple.default"), onSelect: () => onRun("none") },
            ...(book.highlights > 0 ? [
              { label: text("apple.import_highlights"), onSelect: () => onRun("highlights") },
              { label: text("apple.import_notes"), onSelect: () => onRun("notes") },
              { label: text("apple.import_both"), onSelect: () => onRun("both") },
            ] : []),
          ]}
        />
      )
      : book.status === "linked" && book.highlights > 0
        ? (
          <MenuButton
            icon={<SyncIcon />}
            label={text("apple.sync_options")}
            disabled={busy}
            items={[
              { label: text("apple.sync_both"), hint: text("apple.default"), onSelect: () => onRun("both") },
              { label: text("apple.sync_highlights"), onSelect: () => onRun("highlights") },
              { label: text("apple.sync_notes_only"), onSelect: () => onRun("notes") },
            ]}
          />
        )
        : undefined;
  return (
    <BookTile
      cover={<MiniCover size="md" source={cover} muted={blocked} fallback={blocked ? <LockIcon /> : <BookIcon />} />}
      title={book.title}
      meta={facts || undefined}
      action={action}
      muted={blocked}
    />
  );
}

export function AppleBooksPanel({
  onClose,
  onLibraryChanged,
}: {
  onClose: () => void;
  onLibraryChanged: () => void;
}) {
  const [shelf, setShelf] = useState<ShelfBook[] | null>(null);
  const [working, setWorking] = useState<{ done: number; total: number; title: string } | null>(null);
  const [notice, setNotice] = useState<{ tone: "ok" | "error"; message: string } | null>(null);
  const [query, setQuery] = useState("");

  const refresh = useCallback(() => {
    request<{ books: ShelfBook[] }>("applebooks.shelf", {})
      .then((reply) => setShelf(reply.books))
      .catch((error) => { setShelf([]); setNotice({ tone: "error", message: errorText(error) }); });
  }, []);
  useEffect(refresh, [refresh]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !working) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, working]);

  /** Import (if needed) then bring over what `mode` asks for. */
  const run = useCallback(async (books: ShelfBook[], mode: SyncMode) => {
    let imported = 0, matched = 0, unmatched = 0;
    const errors: string[] = [];
    let touched = false;
    for (const [index, book] of books.entries()) {
      setWorking({ done: index + 1, total: books.length, title: book.title });
      try {
        if (book.status === "importable") {
          const result = await request<{ was_existing: boolean }>("applebooks.import", { asset_id: book.asset_id });
          if (!result.was_existing) imported += 1;
          touched = true;
        }
        if (mode !== "none" && book.highlights > 0 && (book.status === "importable" || book.status === "linked")) {
          const result = await request<{ matched: number; unmatched: number }>("applebooks.sync_notes", { asset_id: book.asset_id, mode });
          matched += result.matched;
          unmatched += result.unmatched;
        }
      } catch (error) {
        errors.push(`${book.title}: ${errorText(error)}`);
      }
    }
    setWorking(null);
    setNotice(errors.length
      ? { tone: "error", message: errors.join(" · ") }
      : { tone: "ok", message: text("apple.summary", { imported, matched, unmatched }) });
    refresh();
    if (touched) onLibraryChanged();
  }, [refresh, onLibraryChanged]);

  const books = shelf ?? [];
  const importable = books.filter((book) => book.status === "importable");
  const linked = books.filter((book) => book.status === "linked");
  const blocked = books.filter((book) => !["importable", "linked"].includes(book.status));
  const actionable = [...importable, ...linked.filter((book) => book.highlights > 0)];
  // One list, most useful first; a search box only once the shelf is long
  // enough to need one (owner, 02/09: "tối giản", "filter thông minh").
  const ordered = orderShelfItems(books).filter((book) => matchesQuery(book, query));
  const searchable = books.length > SEARCH_ABOVE;

  return (
    <Surface
      edge="strong"
      radius="sheet"
      className="absolute left-1/2 top-1/2 z-30 flex max-h-[84%] w-[38rem] -translate-x-1/2 -translate-y-1/2 flex-col shadow-lifted"
    >
      <div className="flex items-start gap-3 px-6 pb-4 pt-5">
        <div className="min-w-0 flex-1">
          <h3 className="m-0 text-base font-bold">{text("apple.title")}</h3>
          <p className="m-0 mt-1 text-xs text-ink-mute">{text("apple.one_way")}</p>
        </div>
        <IconButton onClick={onClose} disabled={!!working} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>

      {searchable && (
        <div className="px-6 pb-3">
          <Input
            type="search"
            value={query}
            placeholder={text("apple.search")}
            onChange={(event) => setQuery(event.target.value)}
            className="w-full"
          />
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-4">
        {shelf !== null && books.length === 0 && !notice && (
          <p className="m-0 text-sm text-ink-mute">{text("apple.empty")}</p>
        )}
        {books.length > 0 && ordered.length === 0 && (
          <p className="m-0 text-sm text-ink-mute">{text("apple.no_match")}</p>
        )}
        {ordered.length > 0 && (
          <div className="grid grid-cols-2 gap-3">
            {ordered.map((book) => (
              <ShelfTile key={book.asset_id} book={book} busy={!!working} onRun={(mode) => void run([book], mode)} />
            ))}
          </div>
        )}
      </div>

      {/* The one primary action, at the bottom beside what it will do - the
          macOS sheet shape; a summary or the progress takes the same spot. */}
      <div className="flex items-center gap-4 border-t border-edge px-6 py-4">
        <div className="min-w-0 flex-1">
          {working ? (
            <Notice className="truncate">{text("apple.working", working)}</Notice>
          ) : notice ? (
            <Notice tone={notice.tone} className="truncate">{notice.message}</Notice>
          ) : shelf ? (
            <Notice className="truncate">
              {actionable.length
                ? text("apple.ready_summary", { importable: importable.length, linked: linked.length, blocked: blocked.length })
                : text("apple.nothing_to_do")}
            </Notice>
          ) : null}
        </div>
        <span className="flex items-center gap-1">
          <Button
            variant="primary"
            disabled={!!working || actionable.length === 0}
            onClick={() => void run(actionable, "none")}
          >
            {actionable.length ? text("apple.sync_count", { count: actionable.length }) : text("apple.sync_all")}
          </Button>
          <MenuButton
            icon={<ChevronDownIcon />}
            label={text("apple.import_options")}
            disabled={!!working || actionable.length === 0}
            items={[
              { label: text("apple.import_only"), hint: text("apple.default"), onSelect: () => void run(actionable, "none") },
              { label: text("apple.import_highlights"), onSelect: () => void run(actionable, "highlights") },
              { label: text("apple.import_notes"), onSelect: () => void run(actionable, "notes") },
              { label: text("apple.import_both"), onSelect: () => void run(actionable, "both") },
            ]}
          />
        </span>
      </div>
    </Surface>
  );
}
