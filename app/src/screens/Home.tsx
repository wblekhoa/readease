/** RE-HOME-001: one place to start reading, resume and reach existing settings. */
import { useEffect, useState, type ReactNode } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { currentLanguage, engineMessage, text } from "../i18n";
import { Button, Notice, Surface } from "../ui/controls";
import { DropZone, GradientBlur, IconTile } from "../ui/patterns";
import { BookIcon, ClipboardIcon, CursorTextIcon, ImportIcon, VoiceIcon } from "../ui/icons";
import { BOOK_EXTENSIONS, bookPaths } from "../ui/bookPaths";
import { homeRecents, relativeDay, type HomeRecent } from "../ui/homeReading";
import { summarise } from "../ui/scanHistory";
import type { LibraryBook } from "./Library";
import type { ExternalEntry } from "./External";

type Item = HomeRecent<LibraryBook, ExternalEntry>;
const RECENT_LIMIT = 8;
const when = (at: number) => relativeDay(at, Date.now(), currentLanguage(), {
  today: text("home.today"), yesterday: text("home.yesterday"), daysAgo: days => text("home.days_ago", { days }),
});
/* One line per item (owner, 20/10: minimal): a kind glyph, the title, and
   the day - plus progress for a started document. The kind and the details
   the second line used to spell out stay in the accessible name. */
function RecentRow({ item, kept, onOpen }: { item: Item; kept: boolean; onOpen: () => void }) {
  const title = item.kind === "book" ? item.source.title : summarise(item.source.text);
  const kind = text(item.kind === "book" ? "home.document" : item.kind === "paste" ? "nav.paste" : "nav.external");
  const detail = item.kind === "book" && item.source.progress_ratio !== null
    ? `${Math.round(item.source.progress_ratio * 100)}%${item.source.progress_chapter ? ` · ${item.source.progress_chapter}` : ""}`
    : item.kind === "external" && item.source.target ? text("home.translated", { language: item.source.target.toUpperCase() })
      : item.kind !== "book" ? text(item.id === "paste" ? "home.draft" : kept ? "home.saved" : "home.session") : item.source.source_format.toUpperCase();
  const progress = item.kind === "book" && item.source.progress_ratio ? `${Math.round(item.source.progress_ratio * 100)}%` : null;
  const date = when(item.at);
  return <Button variant="ghost" onClick={onOpen} aria-label={`${text("home.open_recent", { title })} · ${kind} · ${detail}`}
    className="!h-auto w-full !justify-start gap-3 !rounded-2xl !px-3 !py-2.5 text-left">
    <span className="flex h-5 w-5 shrink-0 items-center justify-center text-ink-mute [&_svg]:h-[18px] [&_svg]:w-[18px]">{item.kind === "book" ? <BookIcon /> : item.kind === "paste" ? <ClipboardIcon /> : <CursorTextIcon />}</span>
    <span className="min-w-0 flex-1 truncate font-normal text-ink">{title}</span>
    {progress && <span className="shrink-0 text-xs tabular-nums text-ink-mute">{progress}</span>}
    <span className="w-24 shrink-0 text-right text-xs text-ink-mute">{date}</span>
  </Button>;
}
export function Home({ books, loading, error, importing, paste, pastes = [], onOpenPaste, historyKept = false, captures, active, onImport, onPaste, onScan, onOpenBook, onOpenCapture, onRetry, onSettings, onTranslation, voice, translation, settingsBlocked }: {
  books: readonly LibraryBook[]; loading: boolean; error: string | null; importing: boolean;
  paste: { text: string; at: number }; captures: readonly ExternalEntry[];
  /** Pastes kept in the history (RE-HIST-001), and how to reopen one. */
  pastes?: readonly { text: string; at: number }[]; onOpenPaste?: (text: string) => void;
  /** Whether pastes and scans are kept on this Mac, which is what their row says. */
  historyKept?: boolean;
  active?: { title: string; paused: boolean; onToggle: () => void; onOpen: () => void };
  onImport: (paths: string[]) => void; onPaste: () => void; onScan: () => void;
  onOpenBook: (book: LibraryBook) => void; onOpenCapture: (entry: ExternalEntry) => void;
  onRetry: () => void; onSettings: () => void; onTranslation: () => void;
  voice: string; translation: string; settingsBlocked: boolean;
}) {
  const everything = homeRecents(books, paste, captures, pastes, 200);
  const recent = everything.slice(0, RECENT_LIMIT);
  const empty = !loading && !error && everything.length === 0 && !active;
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
      const paths = await open({ multiple: true, filters: [{ name: text("files.filter_name"), extensions: [...BOOK_EXTENSIONS] }] });
      if (paths) onImport(bookPaths(paths));
    } catch (cause) { setFileError(engineMessage(cause)); }
  };
  /* Minimal (owner, 20/10): an icon and a name; the longer hint is the
     button's tooltip, not a second line on every visit. */
  const action = (label: string, detail: string, icon: ReactNode, onClick: () => void, disabled = false) => <Button variant="ghost" onClick={onClick} disabled={disabled} title={detail}
    className="!h-auto !justify-start gap-3 !rounded-2xl !px-3 !py-3 text-left">
    <IconTile>{icon}</IconTile>
    <span className="min-w-0 truncate font-semibold">{label}</span>
  </Button>;
  return <section className="shell-inset relative flex min-h-0 flex-1 flex-col">
    <div className="selection-scroll-mask min-h-0 flex-1 overflow-y-auto">
      <div className={`@container mx-auto w-full max-w-[56rem] px-2 pb-24 ${empty ? "pt-10" : "pt-4"}`}>
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
        {everything.length > 0 && <section className="mt-7" aria-label={text("home.recent")}>
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h3 className="m-0 text-sm font-semibold">{text("home.recent")}</h3>

          </div>
          <div className="flex flex-col">{recent.map(item => <RecentRow key={item.id} item={item} kept={historyKept} onOpen={() => {
            if (item.kind === "book") onOpenBook(item.source);
            else if (item.kind === "external") onOpenCapture(item.source);
            else if (item.id !== "paste" && onOpenPaste) onOpenPaste(item.source.text);
            else onPaste();
          }} />)}</div></section>}
      </div>
    </div>
    {/* Reading settings stay at the foot of the screen (owner, 20/10):
        always in reach, never scrolled away, and out of the content. */}
    {/* Right-aligned: the voice and translation panels open from the
        bottom-right corner, as they do above the reader's transport, so the
        buttons sit under them (owner, 20/10).
        Edge to edge, past the main column's px-6: inside it the blur
        stopped 24 px short of each side and showed as a cropped box
        (owner, 20/10). The row keeps the content's inset. */}
    <footer className="absolute -left-6 -right-6 bottom-0 z-20" aria-label={text("home.settings")}>
      <GradientBlur edge="bottom" />
      <div data-shell-footer className="relative z-10 flex flex-wrap items-center justify-end gap-2 px-6 pb-4 pt-6">
      <Button size="sm" variant="ghost" data-popover-trigger disabled={settingsBlocked} onClick={onSettings}><VoiceIcon /><span className="max-w-[24ch] truncate">{voice || text("translation.choose_voice")}</span></Button>
      <Button size="sm" variant="ghost" data-popover-trigger disabled={settingsBlocked} onClick={onTranslation}>{text("translation.short")} · {translation}</Button>
      </div>
    </footer>
    {dragging !== null && <DropZone icon={<ImportIcon />} headline={text(dragging ? "home.drop" : "home.file_types")} tone={dragging ? "ok" : "error"} />}
  </section>;
}
