import { useCallback, useEffect, useMemo, useReducer, useRef, useState, type CSSProperties } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { AppTabs } from "./ui/AppTabs";
import { GradientBlur, Toolbar } from "./ui/patterns";
import { External, type ExternalEntry } from "./screens/External";
import { Button, IconButton, Notice, SectionTitle, Select, Surface, Textarea } from "./ui/controls";
import { SettingsPanel } from "./ui/SettingsPanel";
import { useShortcut } from "./ui/useShortcut";
import {
  ChevronLeftIcon,
  NextIcon,
  PauseIcon,
  PlayIcon,
  PreviousIcon,
  SidebarIcon,
  StopIcon,
  PagesIcon,
  ScrollIcon,
  InfoIcon,
  SlidersIcon,
  SunIcon,
  MoonIcon,
  BookIcon,
  ClipboardIcon,
  CursorTextIcon,
  TransferIcon,
} from "./ui/icons";
import { IDLE, playback } from "./ui/playback";
import {
  READING_SIZES,
  rememberReadingSize,
  storedReadingSize,
} from "./ui/readingSize";
import { rememberReadingMode, storedReadingMode, type ReadingMode } from "./ui/readingMode";
import { nextTheme, rememberThemePreference, resolveTheme, storedThemePreference, type Theme, type ThemePreference } from "./ui/theme";
import { Library, type LibraryBook } from "./screens/Library";
import { Reader, type PageInfo } from "./screens/Reader";
import { Setup } from "./screens/Setup";
import { Transfer } from "./screens/Transfer";
import { currentLanguage, setLanguage, text, type Language } from "./i18n";

const PASTE_LIMIT = 100_000;
const RATES = [0.5, 0.75, 1.0, 1.15, 1.2, 1.25, 1.5, 2.0];

type Voice = { id: string; label: string };
type ModelGate = "checking" | "setup" | "ready";

/** Light or dark onto the DS token switch: the reader's own choice when
 * they have made one (the toolbar switch, owner 02/09), the macOS
 * appearance otherwise - followed live. */
function useAppearance(): [Theme, () => void] {
  const [preference, setPreference] = useState<ThemePreference>(storedThemePreference);
  const [systemDark, setSystemDark] = useState(
    () => window.matchMedia("(prefers-color-scheme: dark)").matches,
  );
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const follow = () => setSystemDark(media.matches);
    media.addEventListener("change", follow);
    return () => media.removeEventListener("change", follow);
  }, []);
  const theme = resolveTheme(preference, systemDark);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  const toggle = useCallback(() => {
    const next = nextTheme(theme);
    rememberThemePreference(next);
    setPreference(next);
  }, [theme]);
  return [theme, toggle];
}

export default function App() {
  const [theme, toggleTheme] = useAppearance();
  const [tab, setTab] = useState("paste");
  const [voices, setVoices] = useState<Voice[]>([]);
  const [voiceId, setVoiceId] = useState<string>("");
  const [rate, setRate] = useState(1.0);
  // One reducer owns every transition of the transport. Five hand-written
  // setReading calls used to; two of them forgot the warming notice.
  const [player, onPlayer] = useReducer(playback, IDLE);

  /* The named insets are MEASURED, not declared twice: whatever the bars
     actually occupy (an error line wrapping in the footer, a taller row in
     another language) is what the screens pad by - the guideline's rule
     against a padding written in two places. The inline values above are
     only the first paint, before the observer has run. */
  const shell = useRef<HTMLDivElement>(null);
  const headerBar = useRef<HTMLDivElement>(null);
  const footerBar = useRef<HTMLElement>(null);
  useEffect(() => {
    const root = shell.current;
    if (!root) return;
    const apply = () => {
      root.style.setProperty("--shell-top-h", `${headerBar.current?.offsetHeight ?? 0}px`);
      root.style.setProperty("--shell-bottom-h", `${footerBar.current?.offsetHeight ?? 0}px`);
    };
    apply();
    const observer = new ResizeObserver(apply);
    if (headerBar.current) observer.observe(headerBar.current);
    if (footerBar.current) observer.observe(footerBar.current);
    return () => observer.disconnect();
  });
  const reading = player.reading;
  const [content, setContent] = useState("");
  const [openBook, setOpenBook] = useState<LibraryBook | null>(null);
  const [segments, setSegments] = useState<string[]>([]);
  const [position, setPosition] = useState<string | null>(null);
  const [figureCue, setFigureCue] = useState<string | null>(null);
  const [externalHistory, setExternalHistory] = useState<ExternalEntry[]>([]);
  const [externalStatus, setExternalStatus] = useState<string | null>(null);
  const [modelPrecision, setModelPrecision] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [pageInfo, setPageInfo] = useState<PageInfo | null>(null);
  const [selection, setSelection] = useState("");
  const readSelection = useCallback(() => {
    if (!selection) return;
    onPlayer({ type: "start" });
    if (openBook) setOrigin({ kind: "book", book: openBook });
    void invoke("read_selection_text", { text: selection, voiceId, rate })
      .catch((error) => onPlayer({ type: "failed", error: String(error) }));
    window.getSelection()?.removeAllRanges();
    setSelection("");
  }, [selection, openBook, voiceId, rate]);
  /* Where the voice was started from, so a reader who walks off to another
     screen mid-reading can be shown the way back (owner, 02/09). null once
     nothing is playing. */
  const [origin, setOrigin] = useState<
    { kind: "book"; book: LibraryBook } | { kind: "paste" } | { kind: "external" } | null
  >(null);
  const [gate, setGate] = useState<ModelGate>("checking");
  const [language, setLanguageState] = useState<Language>(currentLanguage());
  // The reader's chrome lives in the toolbar, so its state lives here.
  // The contents are a popover in both modes and start closed - open, they
  // would cover the book they point into (owner, 02/09).
  const [showToc, setShowToc] = useState(false);
  const [readingSize, setReadingSize] = useState(storedReadingSize);
  const [readingMode, setReadingMode] = useState<ReadingMode>(storedReadingMode);
  const toggleReadingMode = useCallback(() => {
    setReadingMode((current) => {
      const next = current === "pages" ? "scroll" : "pages";
      rememberReadingMode(next);
      return next;
    });
  }, []);

  const changeReadingSize = useCallback((step: number) => {
    setReadingSize((current) => {
      const index = READING_SIZES.indexOf(current) + step;
      const next = READING_SIZES[Math.min(READING_SIZES.length - 1, Math.max(0, index))];
      rememberReadingSize(next);
      return next;
    });
  }, []);

  const applyLanguage = useCallback((next: Language) => {
    setLanguage(next);
    setLanguageState(next);
    void invoke("engine_request", {
      method: "config.set",
      params: { key: "ui_language", value: next },
    }).catch(() => undefined);
  }, []);

  /** Speech choices outlive the window, exactly as they did in the Qt shell. */
  const remember = useCallback((key: string, value: string | number) => {
    void invoke("engine_request", {
      method: "config.set",
      params: { key, value },
    }).catch(() => undefined);
  }, []);
  const rememberVoice = useCallback((id: string) => {
    setVoiceId(id);
    remember("voice", id);
  }, [remember]);
  const rememberRate = useCallback((value: number) => {
    setRate(value);
    remember("rate", value);
  }, [remember]);

  const { accelerator, change: changeShortcut } = useShortcut();
  const speech = useRef({ voiceId: "", rate: 1.0 });
  speech.current = { voiceId, rate };

  useEffect(() => {
    // The Qt shell remembered the voice and the speed; losing that in the
    // rewrite would be a downgrade nobody asked for. Same settings file, same
    // two keys, so an existing choice carries over.
    invoke<Voice[]>("engine_voices")
      .then(async (list) => {
        setVoices(list);
        if (!list.length) return;
        const saved = await invoke<{ result: { value: string | null } }>(
          "engine_request",
          { method: "config.get", params: { key: "voice" } },
        ).catch(() => null);
        const wanted = saved?.result.value;
        // A remembered voice that this build no longer ships must not leave
        // the picker empty - fall back to the first one, as the Qt shell did.
        setVoiceId(
          wanted && list.some((voice) => voice.id === wanted)
            ? wanted
            : list[0].id,
        );
      })
      .catch(console.error);
    invoke<{ result: { value: string | null } }>("engine_request", {
      method: "config.get",
      params: { key: "rate" },
    })
      .then((reply) => {
        const saved = Number(reply.result.value);
        if (RATES.includes(saved)) setRate(saved);
      })
      .catch(() => undefined);
    invoke<{ result: { value: string | null } }>("engine_request", {
      method: "config.get",
      params: { key: "ui_language" },
    })
      .then((reply) => {
        if (reply.result.value === "en" || reply.result.value === "vi") {
          setLanguage(reply.result.value);
          setLanguageState(reply.result.value);
        }
      })
      .catch(() => undefined);
    invoke<{ result: { precision: string | null; ready: boolean } }>(
      "engine_request",
      { method: "model.status", params: {} },
    )
      .then((reply) => {
        setModelPrecision(reply.result.precision);
        setGate(reply.result.ready ? "ready" : "setup");
      })
      // A dead engine still deserves a visible app: errors surface on use,
      // a blank window surfaces nothing.
      .catch(() => setGate("ready"));
    const done = listen<{ ok: boolean; error?: string }>(
      "reading:done",
      (event) => {
        // A reading that failed must say so; a silent stop reads as a bug.
        onPlayer({
          type: "done",
          error: event.payload.ok ? null : event.payload.error ?? null,
        });
      },
    );
    const moved = listen<{ segment_id: string; figure_id?: string }>(
      "reading:position",
      (event) => {
        setPosition(event.payload.segment_id);
        // The cue for a picture rides the same playback-anchored event, so
        // the picture comes into view when the ear hears "Xem hình 3", not
        // when the model wrote it.
        setFigureCue(event.payload.figure_id ?? null);
      },
    );
    const started = listen("reading:started", () => onPlayer({ type: "voice" }));
    // The global shortcut hands the captured text to the webview, which owns
    // the voice and rate, and the webview asks the engine to speak it.
    const external = listen<{ text: string }>("reading:external", (event) => {
      const captured = event.payload.text;
      setExternalHistory((history) =>
        [{ at: Date.now(), text: captured }, ...history].slice(0, 50),
      );
      onPlayer({ type: "start" });
      setOrigin({ kind: "external" });
      invoke("read_selection_text", {
        text: captured,
        voiceId: speech.current.voiceId,
        rate: speech.current.rate,
      }).catch((error) => {
        console.error(error);
        onPlayer({ type: "failed", error: String(error) });
      });
    });
    const externalState = listen<{ reason: string }>(
      "external:status",
      (event) => setExternalStatus(event.payload.reason),
    );
    return () => {
      done.then((unlisten) => unlisten());
      moved.then((unlisten) => unlisten());
      started.then((unlisten) => unlisten());
      external.then((unlisten) => unlisten());
      externalState.then((unlisten) => unlisten());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startReading = useCallback(async () => {
    if (!content.trim() || !voiceId) return;
    onPlayer({ type: "start" });
    setOrigin({ kind: "paste" });
    try {
      await invoke("read_text", { text: content, voiceId, rate });
    } catch (error) {
      console.error(error);
      onPlayer({ type: "failed", error: String(error) });
    }
  }, [content, voiceId, rate]);

  const readBookFrom = useCallback(async (segmentId: string | null) => {
    if (!openBook || !voiceId) return;
    onPlayer({ type: "start" });
    setOrigin({ kind: "book", book: openBook });
    try {
      await invoke("read_book", {
        bookId: openBook.id, segmentId, voiceId, rate,
      });
    } catch (error) {
      console.error(error);
      onPlayer({ type: "failed", error: String(error) });
    }
  }, [openBook, voiceId, rate]);

  const readNeighbour = useCallback(async (step: number) => {
    const anchor = position ?? openBook?.segment_id ?? null;
    if (anchor === null) return;
    const index = segments.indexOf(anchor) + step;
    if (index < 0 || index >= segments.length) return;
    // No stop first: starting a reading cancels the one in flight, in the
    // one place that can do it without a race (the Rust client).
    await readBookFrom(segments[index]);
  }, [segments, position, openBook, readBookFrom]);

  const stopReading = useCallback(() => {
    // The transport answers the finger, not the engine: stopping takes a
    // moment on the other side (the engine replies between utterances) and a
    // button that waits for it reads as a button that did nothing.
    onPlayer({ type: "stop" });
    invoke("stop_reading").catch(console.error);
  }, []);

  const togglePause = useCallback(() => {
    if (reading === "reading") {
      onPlayer({ type: "toggle" });
      invoke("pause_audio").catch(console.error);
    } else if (reading === "paused") {
      onPlayer({ type: "toggle" });
      invoke("resume_audio").catch(console.error);
    }
  }, [reading]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.code !== "Space") return;
      const target = event.target as HTMLElement | null;
      if (target && ("value" in target || target.isContentEditable)) return;
      if (reading === "idle") return;
      event.preventDefault();
      void togglePause();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [reading, togglePause]);

  /* Two tiers of feature (owner, 02/09: "phân chia rõ tính năng phụ và
     tính năng chính"). PRIMARY = the ways to get something read: a book
     from the library, or pasted text - they live in the rail with a glyph
     each. SECONDARY = tools around reading: reading a selection from
     another app, and moving notes between copies of a book - a quieter
     cluster at the right, same glyph language. */
  const tabs = useMemo(() => ([
    { value: "library", label: text("nav.library"), icon: <BookIcon /> },
    { value: "paste", label: text("nav.paste"), icon: <ClipboardIcon /> },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ]), [language]);
  const tools = useMemo(() => ([
    { value: "external", label: text("nav.external"), icon: <CursorTextIcon /> },
    { value: "transfer", label: text("nav.transfer"), icon: <TransferIcon /> },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ]), [language]);

  const overLimit = content.length > PASTE_LIMIT;
  const atOrigin =
    origin === null ||
    (origin.kind === "book"
      ? tab === "library" && openBook?.id === origin.book.id
      : tab === origin.kind);
  const locale = language === "vi" ? "vi-VN" : "en-US";

  // What the screen in front of the person can actually do - the footer
  // carries that and nothing else (HIG §3.5). "reader" is a book open inside
  // the library tab; the library LIST has nothing to start yet.
  const screen = tab === "library" && openBook ? "reader" : tab;
  const canStart = screen === "reader" || screen === "paste";
  const startDisabled =
    screen === "paste"
      ? !content.trim() || overLimit || !voiceId
      : !openBook || !voiceId;
  // Voice and speed also drive the global shortcut, so they belong on the
  // selection screen too - just not on the notes utility.
  const speechSettings = canStart || screen === "external";
  // A shortcut read can fail while any screen is open, and its error lands
  // here: never hide the bar out from under one.
  const showFooter =
    canStart || speechSettings || reading !== "idle" || player.error !== null;

  if (gate === "checking") return null;
  if (gate === "setup") {
    return (
      <Setup
        precision={modelPrecision}
        onReady={() => {
          setGate("ready");
          invoke<Voice[]>("engine_voices")
            .then((list) => {
              setVoices(list);
              if (list.length) setVoiceId(list[0].id);
            })
            .catch(console.error);
          invoke<{ result: { precision: string | null } }>("engine_request", {
            method: "model.status", params: {},
          })
            .then((reply) => setModelPrecision(reply.result.precision))
            .catch(() => undefined);
        }}
      />
    );
  }

  return (
    /* The DOL premium-blur shell (owner, 02/09): header and footer are
       overlays and the page scrolls UNDER them, which is the only way a
       backdrop blur has anything to blur. Screens learn the bars' heights
       from two named insets and pad themselves - nothing is coupled to a
       padding value written twice. */
    <div
      key={language}
      ref={shell}
      className="relative h-screen overflow-hidden"
      style={{ "--shell-top-h": "76px", "--shell-bottom-h": showFooter ? "76px" : "0px" } as CSSProperties}
    >
      <div ref={headerBar} className="absolute inset-x-0 top-0 z-20">
        <GradientBlur edge="top" />
        <div className="relative z-10 px-6 pb-6 pt-4">
      <Toolbar
        leading={
          /* A book pushes its own chrome into the one row the window has: the
             tabs step aside and back returns to them. Two stacked rows of
             chrome above a page of text is what this buys back. */
          screen === "reader" && openBook ? (
            <div className="flex min-w-0 items-center gap-1">
              <IconButton
                onClick={() => { setOpenBook(null); setSegments([]); }}
                aria-label={text("reader.back")}
                title={text("reader.back")}
              >
                <ChevronLeftIcon />
              </IconButton>
              <IconButton
                onClick={() => setShowToc((value) => !value)}
                aria-label={showToc ? text("reader.toc_hide") : text("reader.toc_show")}
                title={showToc ? text("reader.toc_hide") : text("reader.toc_show")}
                className={showToc ? "text-ink" : ""}
              >
                <SidebarIcon />
              </IconButton>
              <h2 className="m-0 min-w-0 flex-1 truncate px-1 text-base font-bold">
                {openBook.title}
              </h2>
              {pageInfo && (
                /* Where you are, on request: the page keeps nothing but the
                   book (owner, 02/09). A hover or a focus shows it. */
                <span className="group relative flex shrink-0">
                  <IconButton aria-label={text("reader.page_info")} className="text-ink-faint hover:text-ink">
                    <InfoIcon />
                  </IconButton>
                  <Surface
                    edge="strong"
                    className="pointer-events-none absolute left-1/2 top-full z-30 mt-1 hidden -translate-x-1/2 whitespace-nowrap px-3 py-1.5 text-xs leading-relaxed shadow-lifted group-hover:flex group-focus-within:flex items-center gap-1.5"
                  >
                    {pageInfo.page !== undefined && pageInfo.pages !== undefined && (
                      <>
                        <span className="font-semibold text-ink">
                          {text("reader.page_of", { page: pageInfo.page, total: pageInfo.pages })}
                        </span>
                        <span className="text-ink-faint">·</span>
                      </>
                    )}
                    <span className="max-w-[22em] truncate text-ink">{pageInfo.chapterTitle}</span>
                    <span className="text-ink-faint">·</span>
                    <span className="text-ink-mute">{text("library.progress", { percent: pageInfo.percent })}</span>
                  </Surface>
                </span>
              )}
            </div>
          ) : (
            <AppTabs
              ariaLabel={text("aria.workspace")}
              items={tabs}
              value={tab}
              onChange={setTab}
            />
          )
        }
        trailing={
          <>
            {screen === "reader" && (
              <>
                <IconButton
                  onClick={() => changeReadingSize(-1)}
                  disabled={readingSize === READING_SIZES[0]}
                  aria-label={text("reader.text_smaller")}
                  title={text("reader.text_smaller")}
                >
                  <span className="text-xs font-bold">A</span>
                </IconButton>
                <IconButton
                  onClick={() => changeReadingSize(1)}
                  disabled={readingSize === READING_SIZES[READING_SIZES.length - 1]}
                  aria-label={text("reader.text_larger")}
                  title={text("reader.text_larger")}
                >
                  <span className="text-base font-bold">A</span>
                </IconButton>
                <IconButton
                  onClick={toggleReadingMode}
                  aria-label={text(readingMode === "pages" ? "reader.mode_pages" : "reader.mode_scroll")}
                  title={text(readingMode === "pages" ? "reader.mode_pages" : "reader.mode_scroll")}
                >
                  {readingMode === "pages" ? <PagesIcon /> : <ScrollIcon />}
                </IconButton>
              </>
            )}
          {!(screen === "reader" && openBook) && (
            <>
              {tools.map((tool) => (
                <Button
                  key={tool.value}
                  variant="ghost"
                  onClick={() => setTab(tool.value)}
                  aria-pressed={tab === tool.value}
                  className={`rounded-full ${tab === tool.value ? "bg-wash text-ink" : ""}`}
                >
                  {tool.icon}
                  {tool.label}
                </Button>
              ))}
              <span aria-hidden="true" className="mx-1 h-5 w-px bg-edge" />
            </>
          )}
          <IconButton
            onClick={toggleTheme}
            aria-label={text(theme === "dark" ? "aria.theme_to_light" : "aria.theme_to_dark")}
            title={text(theme === "dark" ? "aria.theme_to_light" : "aria.theme_to_dark")}
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
          </IconButton>
          {/* The UI language belongs to the home screens (owner, 02/09): a
              book's toolbar carries only what serves the book. */}
          {!(screen === "reader" && openBook) && (
            <Select
              pill
              aria-label={text("aria.language")}
              value={language}
              onChange={(event) => applyLanguage(event.target.value as Language)}
            >
              <option value="vi">🇻🇳 VI</option>
              <option value="en">🇬🇧 EN</option>
            </Select>
          )}
          </>
        }
      />
        </div>
      </div>

      <main className="absolute inset-0 flex flex-col px-6">
        {tab === "library" ? (
          openBook ? (
            <Reader
              bookId={openBook.id}
              currentSegment={position}
              currentFigure={figureCue}
              reading={reading !== "idle"}
              mode={readingMode}
              showToc={showToc}
              onHideToc={() => setShowToc(false)}
              size={readingSize}
              onSegments={setSegments}
              onReadFrom={(segmentId) => { void readBookFrom(segmentId); }}
              onPageInfo={setPageInfo}
              onSelection={setSelection}
            />
          ) : (
            <Library onOpen={(book) => { setPosition(null); setOpenBook(book); }} onPaste={() => setTab("paste")} />
          )
        ) : tab === "external" ? (
          <External
            history={externalHistory}
            onClearHistory={() => setExternalHistory([])}
            status={externalStatus}
            shortcut={accelerator}
            onChangeShortcut={changeShortcut}
            onReplay={(entry) => {
              onPlayer({ type: "start" });
              setOrigin({ kind: "external" });
              void invoke("read_selection_text", {
                text: entry.text,
                voiceId,
                rate,
              }).catch((error) => onPlayer({ type: "failed", error: String(error) }));
            }}
          />
        ) : tab === "transfer" ? (
          <Transfer />
        ) : tab === "paste" ? (
          <section className="shell-inset flex min-h-0 flex-1 flex-col">
            <SectionTitle>{text("paste.title")}</SectionTitle>
            <p className="m-0 mt-0.5 text-sm text-ink-mute">
              {text("paste.description")}
            </p>
            <Textarea
              className="mt-3 min-h-0 flex-1"
              placeholder={text("paste.placeholder")}
              value={content}
              onChange={(event) => setContent(event.target.value)}
            />
            <div className="py-2 text-xs text-ink-mute">
              <span className={overLimit ? "font-semibold text-danger" : ""}>
                {text("paste.count", {
                  count: content.length.toLocaleString(locale),
                  limit: PASTE_LIMIT.toLocaleString(locale),
                })}
              </span>
              {overLimit && (
                <span className="font-medium text-danger">
                  {text("paste.over_limit")}
                </span>
              )}
            </div>
          </section>
        ) : (
          <section className="flex flex-1 items-center justify-center text-sm text-ink-mute">
            {text("milestone.later")}
          </section>
        )}
      </main>

      {showFooter && (
      <footer ref={footerBar} className="absolute inset-x-0 bottom-0 z-20">
        <GradientBlur edge="bottom" />
        {/* Same height as the header (76px): the frost's room sits on the
            inner edge of each bar - the header's bottom, the footer's top
            (owner, 02/09: "tương đồng với header"). */}
        <div className="relative z-10 grid min-h-[76px] grid-cols-[1fr_auto_1fr] items-center gap-2 px-6 pb-4 pt-6">
          {/* Left: the other way in. Middle: what a click does. Right: what
              the voice is up to. A grid keeps the middle in the middle
              whatever the sides say - and gives the bar its height (an
              absolute group gave it none: 40px, owner 02/09). */}
          <div className="flex min-w-0 items-center gap-2 justify-self-start">
            {reading === "idle" && screen === "reader" && (
              <span className="text-xs text-ink-mute">{text("player.hint_click")}</span>
            )}
            {reading !== "idle" && origin && !atOrigin && (
              /* Playing, but the reader has walked off: say what is being
                 read and offer the way back. Silent while they are where the
                 voice is - the pill inside the book handles that case. */
              <>
                <span className="min-w-0 truncate text-xs text-ink-mute">
                  {origin.kind === "book"
                    ? text("player.reading_book", { title: origin.book.title })
                    : origin.kind === "paste"
                      ? text("player.reading_paste")
                      : text("player.reading_external")}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    if (origin.kind === "book") {
                      setTab("library");
                      setOpenBook(origin.book);
                    } else {
                      setTab(origin.kind);
                    }
                  }}
                >
                  <ChevronLeftIcon />
                  {text("player.return")}
                </Button>
              </>
            )}
          </div>
          <div className="flex items-center gap-2 justify-self-center">
            {reading === "idle" ? (
              /* Idle: what a click would do and where it would start, and
                 the voice it would use, side by side - one kind of thing,
                 one place (owner, 02/09: "cùng loại thì đi chung"). */
              <>
                {selection && (
                  <Button variant="primary" className="px-5" onClick={readSelection}>
                    {text("reader.selection")}
                  </Button>
                )}
                {canStart && (
                  <Button
                    variant={selection ? "secondary" : "primary"}
                    className="px-5"
                    disabled={startDisabled}
                    onClick={() => {
                      if (screen === "reader") void readBookFrom(null);
                      else void startReading();
                    }}
                  >
                    {screen !== "reader"
                      ? text("paste.read")
                      : pageInfo?.resumeChapterTitle
                        ? (
                          <>
                            {text("player.play_resume")}
                            <span className="max-w-[14em] truncate font-normal opacity-85">
                              · {pageInfo.resumeChapterTitle}
                            </span>
                          </>
                        )
                        : pageInfo
                          ? text("player.play_start")
                          : text("player.play")}
                  </Button>
                )}
                {speechSettings && (
                  <Button
                    variant="ghost"
                    onClick={() => setSettingsOpen((value) => !value)}
                    aria-label={text("player.settings_open")}
                    title={text("player.settings_open")}
                    className={settingsOpen ? "text-ink" : ""}
                  >
                    <SlidersIcon />
                    <span className="font-normal">{voiceId} · {rate}×</span>
                  </Button>
                )}
              </>
            ) : (
              /* Playing: the bar is a TRANSPORT and nothing else, in the
                 middle the way every player puts it. Voice/speed/quality are
                 out of reach - they are read once, at the start. */
              <>
                {selection && (
                  <Button variant="primary" size="sm" onClick={readSelection}>
                    {text("reader.selection")}
                  </Button>
                )}
                {screen === "reader" && (
                  <IconButton
                    onClick={() => { void readNeighbour(-1); }}
                    aria-label={text("player.previous")}
                    title={text("player.previous")}
                  >
                    <PreviousIcon />
                  </IconButton>
                )}
                <IconButton
                  onClick={togglePause}
                  aria-label={reading === "paused" ? text("player.resume") : text("player.pause")}
                  title={reading === "paused" ? text("player.resume") : text("player.pause")}
                  className="text-ink"
                >
                  {reading === "paused" ? <PlayIcon /> : <PauseIcon />}
                </IconButton>
                {/* Stop is the one transport action that ENDS the reading, so
                    it is the one that gets a name and the danger tone. */}
                <Button variant="danger" size="sm" onClick={stopReading}>
                  <StopIcon />
                  {text("player.stop")}
                </Button>
                {screen === "reader" && (
                  <IconButton
                    onClick={() => { void readNeighbour(1); }}
                    aria-label={text("player.next")}
                    title={text("player.next")}
                  >
                    <NextIcon />
                  </IconButton>
                )}
              </>
            )}
          </div>
          <div className="min-w-0 justify-self-end">
            {reading !== "idle" && player.warming && (
              <Notice className="min-w-0 truncate whitespace-nowrap">{text("player.warming")}</Notice>
            )}
            {player.error && (
              <Notice tone="error" className="min-w-0 truncate">
                {player.error}
              </Notice>
            )}
          </div>
        </div>
      </footer>
      )}
      {settingsOpen && speechSettings && (
        <SettingsPanel
          voices={voices}
          voiceId={voiceId}
          rate={rate}
          rates={RATES}
          reading={reading !== "idle"}
          onVoice={rememberVoice}
          onRate={rememberRate}
          onClose={() => {
            setSettingsOpen(false);
            invoke<Voice[]>("engine_voices")
              .then(setVoices)
              .catch(() => undefined);
          }}
        />
      )}
    </div>
  );
}
