/** RE-HOME-001: one place to start reading, resume and reach existing settings. */
import { useEffect, useState, type ReactNode } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { currentLanguage, engineMessage, text } from "../i18n";
import { Button, Notice, Surface } from "../ui/controls";
import { DropZone, MiniCover } from "../ui/patterns";
import { BookIcon, ClipboardIcon, CursorTextIcon, ImportIcon, VoiceIcon } from "../ui/icons";
import { BOOK_EXTENSIONS, bookPaths } from "../ui/bookPaths";
import { homeRecents, type HomeRecent } from "../ui/homeReading";
import { summarise } from "../ui/scanHistory";
import { useCover } from "../ui/useCover";
import type { LibraryBook } from "./Library";
import type { ExternalEntry } from "./External";

type Item = HomeRecent<LibraryBook, ExternalEntry>;
function RecentBookCover({ id }: { id: string }) {
  const cover = useCover(id);
  return <MiniCover source={cover} fallback={<BookIcon />} />;
}
function RecentRow({ item, onOpen }: { item: Item; onOpen: () => void }) {
  const title = item.kind === "book" ? item.source.title : summarise(item.source.text);
  const kind = text(item.kind === "book" ? "home.document" : item.kind === "paste" ? "nav.paste" : "nav.external");
  const detail = item.kind === "book" && item.source.progress_ratio !== null
    ? `${Math.round(item.source.progress_ratio * 100)}%${item.source.progress_chapter ? ` · ${item.source.progress_chapter}` : ""}`
    : item.kind === "external" && item.source.target ? text("home.translated", { language: item.source.target.toUpperCase() })
      : item.kind !== "book" ? text("home.session") : item.source.source_format.toUpperCase();
  const date = item.at ? new Intl.DateTimeFormat(currentLanguage(), { day: "numeric", month: "short" }).format(item.at) : "";
  return <Button variant="ghost" onClick={onOpen} aria-label={text("home.open_recent", { title })}
    className="!h-auto w-full !justify-start gap-3 !px-3 !py-3 text-left">
    {item.kind === "book" ? <RecentBookCover id={item.source.id} /> : <span className="flex h-12 w-8 shrink-0 items-center justify-center text-ink-mute">{item.kind === "paste" ? <ClipboardIcon /> : <CursorTextIcon />}</span>}
    <span className="min-w-0 flex-1">
      <span className="block truncate font-medium text-ink">{title}</span>
      <span className="mt-1 block truncate text-xs text-ink-mute">{kind} · {detail}</span>
    </span>
    <span className="shrink-0 text-xs text-ink-mute">{date}</span>
  </Button>;
}
export function Home({ books, loading, error, importing, paste, captures, active, onImport, onPaste, onScan, onOpenBook, onOpenCapture, onRetry, onSettings, onTranslation, voice, translation, settingsBlocked }: {
  books: readonly LibraryBook[]; loading: boolean; error: string | null; importing: boolean;
  paste: { text: string; at: number }; captures: readonly ExternalEntry[];
  active?: { title: string; paused: boolean; onToggle: () => void; onOpen: () => void };
  onImport: (paths: string[]) => void; onPaste: () => void; onScan: () => void;
  onOpenBook: (book: LibraryBook) => void; onOpenCapture: (entry: ExternalEntry) => void;
  onRetry: () => void; onSettings: () => void; onTranslation: () => void;
  voice: string; translation: string; settingsBlocked: boolean;
}) {
  const recent = homeRecents(books, paste, captures);
  const empty = !loading && !error && recent.length === 0 && !active;
  const [dragging, setDragging] = useState<number | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    const listener = getCurrentWebview().onDragDropEvent(event => {
      if (!live) return;
      if (event.payload.type === "enter") setDragging(bookPaths(event.payload.paths).length);
      else if (event.payload.type === "leave") setDragging(null);
      else if (event.payload.type === "drop") {
        setDragging(null);
        const paths = bookPaths(event.payload.paths);
        if (paths.length) { setFileError(null); onImport(paths); }
        else setFileError(text("home.file_types"));
      }
    });
    return () => { live = false; listener.then(unlisten => unlisten()).catch(() => undefined); };
  }, [onImport]);
  const pick = async () => {
    setFileError(null);
    try {
      const paths = await open({ multiple: true, filters: [{ name: "PDF, EPUB", extensions: [...BOOK_EXTENSIONS] }] });
      if (paths) onImport(bookPaths(paths));
    } catch (cause) { setFileError(engineMessage(cause)); }
  };
  const action = (label: string, detail: string, icon: ReactNode, onClick: () => void, disabled = false) => <Button onClick={onClick} disabled={disabled}
    className="!h-auto !items-start !justify-start gap-3 !px-4 !py-4 text-left">
    <span className="mt-0.5 shrink-0 text-ink-mute">{icon}</span>
    <span className="min-w-0 whitespace-normal"><span className="block font-semibold">{label}</span><span className="mt-1 block text-xs font-normal leading-relaxed text-ink-mute">{detail}</span></span>
  </Button>;
  return <section className="shell-inset flex min-h-0 flex-1 flex-col">
    <div className="selection-scroll-mask min-h-0 flex-1 overflow-y-auto">
      <div className={`@container mx-auto w-full max-w-[56rem] px-2 pb-8 ${empty ? "pt-10" : "pt-4"}`}>
        {empty && <div className="mb-7 text-center"><span className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-tint text-ink-mute"><BookIcon /></span>
          <h1 className="m-0 text-xl font-semibold">{text("home.empty_title")}</h1><p className="m-0 mt-2 text-sm text-ink-mute">{text("home.empty_hint")}</p></div>}
        <div className="grid grid-cols-1 gap-3 @min-[36rem]:grid-cols-3">
          {action(importing ? text("library.importing") : text("home.open_file"), text("home.file_hint"), <ImportIcon />, () => void pick(), importing)}
          {action(text("home.paste"), text("home.paste_hint"), <ClipboardIcon />, onPaste)}
          {action(text("nav.external"), text("home.scan_hint"), <CursorTextIcon />, onScan)}
        </div>
        {(error || fileError) && <Notice tone="error" className="mt-4">{error || fileError}<Button size="sm" variant="ghost" onClick={() => { setFileError(null); onRetry(); }}>{text("update.retry")}</Button></Notice>}
        {loading && <p role="status" className="my-6 text-sm text-ink-mute">{text("home.loading")}</p>}
        {active && <Surface className="mt-6 flex items-center gap-3 p-4">
          <span className="min-w-0 flex-1"><span className="block text-xs text-ink-mute">{text(active.paused ? "home.paused" : "home.reading")}</span><span className="mt-1 block truncate text-sm font-semibold">{active.title}</span></span>
          <Button variant="ghost" onClick={active.onOpen}>{text("home.open_content")}</Button>
          <Button variant="primary" onClick={active.onToggle}>{text(active.paused ? "home.resume" : "player.pause")}</Button>
        </Surface>}
        {recent.length > 0 && <section className="mt-7" aria-label={text("home.recent")}><h3 className="m-0 mb-2 text-sm font-semibold">{text("home.recent")}</h3>
          <div className="divide-y divide-edge-alpha">{recent.map(item => <RecentRow key={item.id} item={item} onOpen={() => {
            if (item.kind === "book") onOpenBook(item.source);
            else if (item.kind === "external") onOpenCapture(item.source);
            else onPaste();
          }} />)}</div></section>}
        <section className={`${empty ? "mt-10" : "mt-7"} border-t border-edge-alpha pt-5`} aria-label={text("home.settings")}>
          <h3 className="m-0 text-sm font-semibold">{text("home.settings")}</h3><p className="m-0 mt-1 text-xs leading-relaxed text-ink-mute">{text("home.settings_hint")}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button data-popover-trigger disabled={settingsBlocked} onClick={onSettings}><VoiceIcon /><span className="max-w-[24ch] truncate">{voice || text("translation.choose_voice")}</span></Button>
            <Button data-popover-trigger disabled={settingsBlocked} onClick={onTranslation}>{text("home.scan_translation")} · {translation}</Button>
          </div>
        </section>
      </div>
    </div>
    {dragging !== null && <DropZone icon={<ImportIcon />} headline={text(dragging ? "home.drop" : "home.file_types")} tone={dragging ? "ok" : "error"} />}
  </section>;
}
