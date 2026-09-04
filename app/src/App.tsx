import { useCallback, useEffect, useMemo, useReducer, useRef, useState, type CSSProperties } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { AppTabs } from "./ui/AppTabs";
import { GradientBlur, MenuButton, Toolbar } from "./ui/patterns";
import { External, type ExternalEntry } from "./screens/External";
import { Button, IconButton, Notice, SectionTitle, Select, Surface, Textarea } from "./ui/controls";
import { SettingsPanel } from "./ui/SettingsPanel";
import { VoicesPanel } from "./ui/VoicesPanel";
import {
  initialShortlist,
  offeredVoices,
  serializeShortlist,
  toggleShortlist,
  voiceName,
  type Voice,
} from "./ui/voiceShortlist";
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
  NoteIcon,
  CursorTextIcon,
  TransferIcon,
  SpeakerIcon,
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
  /** Why there are no voices to offer. An empty catalogue is a claim - "this
   * Mac has no voices" - and a failed request is not that claim. */
  const [voicesError, setVoicesError] = useState<string | null>(null);
  const [voiceId, setVoiceId] = useState<string>("");
  const [rate, setRate] = useState(1.0);
  /** The voices worth offering mid-reading, in the person's own words:
   * twenty is a catalogue, this is the handful they switch between. */
  const [shortlist, setShortlist] = useState<string[]>([]);
  const [voicesOpen, setVoicesOpen] = useState(false);
  /** The voice whose sample is speaking, so the row can offer Stop. */
  const [previewing, setPreviewing] = useState<string | null>(null);
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
  /* What is being read RIGHT NOW, and how to ask for it again.
   *
   * Not `origin`: that answers "where do I go back to" and deliberately says
   * "book" for a selection read inside a book. Changing the voice has to
   * re-issue the actual request, so it needs the actual request. A preview
   * records nothing - switching voices mid-preview would be a loop. */
  const current = useRef<
    | { kind: "book"; bookId: string }
    | { kind: "text"; text: string }
    | { kind: "preview" }
    | null
  >(null);
  /* Where the voice is, readable from a callback without making every
   * callback depend on it - the same reason `speech` is a ref. */
  const where = useRef<string | null>(null);
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
    current.current = { kind: "text", text: selection };
    setPosition(null);
    void invoke("read_selection_text", { text: selection, segmentId: null, voiceId, rate })
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
  /* The notes panel and which note it should land on, when it was opened by
   * pressing a note's own icon in the text. */
  const [notes, setNotes] = useState<{ open: boolean; focus: string | null }>({ open: false, focus: null });
  /** "Take me to where reading would resume" - the stamp lets the same place
   * be asked for twice. */
  const [reveal, setReveal] = useState<{ segmentId: string; at: number } | null>(null);
  const [resumeTip, setResumeTip] = useState(false);
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
  const rememberShortlist = useCallback((ids: string[]) => {
    setShortlist(ids);
    // config.* is answered between audio chunks, so this saves even while a
    // chapter is being read - which is exactly when the list gets edited.
    remember("voice_shortlist", serializeShortlist(ids));
  }, [remember]);

  const { accelerator, change: changeShortcut } = useShortcut();
  const speech = useRef({ voiceId: "", rate: 1.0 });
  speech.current = { voiceId, rate };
  where.current = position;

  useEffect(() => {
    // The Qt shell remembered the voice and the speed; losing that in the
    // rewrite would be a downgrade nobody asked for. Same settings file, same
    // two keys, so an existing choice carries over.
    invoke<Voice[]>("engine_voices")
      .then(async (list) => {
        setVoices(list);
        setVoicesError(null);
        if (!list.length) return;
        const saved = await invoke<{ result: { value: string | null } }>(
          "engine_request",
          { method: "config.get", params: { key: "voice" } },
        ).catch(() => null);
        // Inside this chain because the starting five have to be filtered
        // against the catalogue this build actually ships.
        const kept = await invoke<{ result: { value: string | null } }>(
          "engine_request",
          { method: "config.get", params: { key: "voice_shortlist" } },
        ).catch(() => null);
        setShortlist(initialShortlist(kept?.result.value, list));
        const wanted = saved?.result.value;
        // A remembered voice that this build no longer ships must not leave
        // the picker empty - fall back to the first one, as the Qt shell did.
        setVoiceId(
          wanted && list.some((voice) => voice.id === wanted)
            ? wanted
            : list[0].id,
        );
      })
      .catch((error) => {
        console.error(error);
        setVoicesError(String(error));
      });
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
        // Whatever it was, it is over: the preview row goes back to offering
        // Play, and nothing is left to restart in another voice.
        setPreviewing(null);
        current.current = null;
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
      current.current = { kind: "text", text: captured };
      setPosition(null);
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
    current.current = { kind: "text", text: content };
    setPosition(null);
    try {
      await invoke("read_text", { text: content, segmentId: null, voiceId, rate });
    } catch (error) {
      console.error(error);
      onPlayer({ type: "failed", error: String(error) });
    }
  }, [content, voiceId, rate]);

  const readBookFrom = useCallback(async (segmentId: string | null) => {
    if (!openBook || !voiceId) return;
    onPlayer({ type: "start" });
    setOrigin({ kind: "book", book: openBook });
    current.current = { kind: "book", bookId: openBook.id };
    try {
      await invoke("read_book", {
        bookId: openBook.id, segmentId, voiceId, rate,
      });
    } catch (error) {
      console.error(error);
      onPlayer({ type: "failed", error: String(error) });
    }
  }, [openBook, voiceId, rate]);

  /** Change the voice, and carry on with it.
   *
   * The engine has no "swap the voice mid-sentence": a voice is chosen when a
   * reading starts. So this restarts the SAME reading at the part the ear had
   * reached - the paragraph in a book, the part of a pasted passage - which is
   * why plain reads were given addressable parts. The seam is the start of the
   * current paragraph, not the current word; anything finer would need the
   * engine to know where in the audio it is.
   *
   * The new id is passed as an argument rather than read back from state:
   * `setVoiceId` has not landed by the time this issues the request, and the
   * closure would send the old voice - the shell's oldest trap.
   */
  const switchVoice = useCallback((id: string) => {
    rememberVoice(id);
    const live = current.current;
    if (player.reading === "idle" || live === null || live.kind === "preview") return;
    const at = where.current;
    onPlayer({ type: "start" });
    const request = live.kind === "book"
      ? invoke("read_book", { bookId: live.bookId, segmentId: at, voiceId: id, rate })
      : invoke("read_text", {
        text: live.text,
        // A book segment id left over from an earlier reading is not a part
        // of THIS text; the engine would refuse it, so start from the top.
        segmentId: at && at.startsWith("part-") ? at : null,
        voiceId: id,
        rate,
      });
    request.catch((error) => {
      console.error(error);
      onPlayer({ type: "failed", error: String(error) });
    });
  }, [player.reading, rate, rememberVoice]);

  /** Speak one sentence in a voice, so a choice can be heard before it is made.
   *
   * Only when nothing is being read: the engine speaks one thing at a time, so
   * a sample would cancel the chapter it was meant to help you choose for. The
   * origin is cleared with it, or the footer would offer to take you "back" to
   * a book that a preview interrupted.
   */
  const previewVoice = useCallback((id: string) => {
    onPlayer({ type: "start" });
    setOrigin(null);
    current.current = { kind: "preview" };
    setPreviewing(id);
    setPosition(null);
    invoke("read_text", {
      text: text("voices.sample"),
      segmentId: null,
      voiceId: id,
      rate,
    }).catch((error) => {
      console.error(error);
      onPlayer({ type: "failed", error: String(error) });
      setPreviewing(null);
    });
  }, [rate]);

  const readNeighbour = useCallback(async (step: number) => {
    const anchor = position ?? openBook?.segment_id ?? null;
    if (anchor === null) return;
    const here = segments.indexOf(anchor);
    // A plain read (a selection, a pasted passage) reports "part-2", which is
    // not in this book: indexOf gives -1, and -1 + 1 used to walk to the first
    // segment of the book - a skip button that jumped somewhere else entirely.
    if (here < 0) return;
    const index = here + step;
    if (index < 0 || index >= segments.length) return;
    // No stop first: starting a reading cancels the one in flight, in the
    // one place that can do it without a race (the Rust client).
    await readBookFrom(segments[index]);
  }, [segments, position, openBook, readBookFrom]);

  const stopPreview = useCallback(() => {
    setPreviewing(null);
    onPlayer({ type: "stop" });
    current.current = null;
    void invoke("stop_reading").catch(() => undefined);
  }, []);

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
                onClick={() => {
                  setNotes({ open: false, focus: null });
                  setShowToc((value) => !value);
                }}
                aria-label={showToc ? text("reader.toc_hide") : text("reader.toc_show")}
                title={showToc ? text("reader.toc_hide") : text("reader.toc_show")}
                className={showToc ? "text-ink" : ""}
              >
                <SidebarIcon />
              </IconButton>
              {/* Only when the book carries something: a button that opens
                  an empty panel is a button that lies about the book. */}
              {(pageInfo?.annotations ?? 0) > 0 && (
                <IconButton
                  onClick={() => {
                    setShowToc(false);
                    setNotes((value) => ({ open: !value.open, focus: null }));
                  }}
                  aria-label={text("notes.open")}
                  title={text("notes.count", { count: pageInfo?.annotations ?? 0 })}
                  className={notes.open ? "text-ink" : ""}
                >
                  <NoteIcon />
                </IconButton>
              )}
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
                    /* Pinned to the WINDOW's left inset, under the header -
                       not to the icon. The icon drifts with the length of the
                       book's title, so anchoring to it overflows one edge or
                       the other depending on where it lands, and no static
                       left/right choice is right for both (owner, 03/09: it
                       ran off the edge). Fixed positioning plus a width cap
                       is the only version that cannot leave the screen. The
                       cost is that it no longer points at the icon; it reads
                       as a status line under the bar instead, which is what
                       it is. */
                    className="pointer-events-none fixed left-6 top-[calc(var(--shell-top-h)-0.25rem)] z-30 hidden max-w-[calc(100vw-3rem)] whitespace-nowrap px-3 py-1.5 text-xs leading-relaxed shadow-lifted group-hover:flex group-focus-within:flex items-center gap-1.5"
                  >
                    {pageInfo.page !== undefined && pageInfo.pages !== undefined && (
                      <>
                        <span className="font-semibold text-ink">
                          {text("reader.page_of", { page: pageInfo.page, total: pageInfo.pages })}
                        </span>
                        <span className="text-ink-faint">·</span>
                      </>
                    )}
                    {/* The part that gives when there is no room: a chapter
                        title can be a sentence, the page number cannot. */}
                    <span className="min-w-0 max-w-[22em] truncate text-ink">{pageInfo.chapterTitle}</span>
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
              /* Only a BOOK position belongs to the book. A plain read
                 reports "part-2", which matches no segment and would blank
                 the highlight the eye is following. */
              currentSegment={position && position.startsWith("part-") ? null : position}
              currentFigure={figureCue}
              reading={reading !== "idle"}
              mode={readingMode}
              showToc={showToc}
              onHideToc={() => setShowToc(false)}
              reveal={reveal}
              showNotes={notes.open}
              notesFocus={notes.focus}
              onNotes={(open, focus = null) => {
                if (open) setShowToc(false);
                setNotes({ open, focus });
              }}
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
              current.current = { kind: "text", text: entry.text };
              setPosition(null);
              void invoke("read_selection_text", {
                text: entry.text,
                segmentId: null,
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
                  <Button variant="primary" onClick={readSelection}>
                    {text("reader.selection")}
                  </Button>
                )}
                {canStart && (
                  /* The button says only what it DOES; what it would read is
                     shown on hover instead of crammed into the label, where a
                     chapter title was truncated to nothing useful anyway
                     (owner, 04/09).

                     Open state, not `group-hover`: this tooltip is REACHABLE
                     - its text is a link to the place - so it has to survive
                     the pointer travelling into it, and it has to be
                     verifiable. The `pb-2` on its wrapper is the bridge that
                     keeps the subtree contiguous, so `onMouseLeave` on the
                     group does not fire on the way up. */
                  <span
                    className="relative inline-flex"
                    onMouseEnter={() => setResumeTip(true)}
                    onMouseLeave={() => setResumeTip(false)}
                    onFocusCapture={() => setResumeTip(true)}
                    onBlurCapture={() => setResumeTip(false)}
                  >
                    <Button
                      variant={selection ? "secondary" : "primary"}
                      disabled={startDisabled}
                      onClick={() => {
                        if (screen === "reader") void readBookFrom(null);
                        else void startReading();
                      }}
                    >
                      {screen !== "reader"
                        ? text("paste.read")
                        : pageInfo?.resumeChapterTitle
                          ? text("player.play_resume")
                          : pageInfo
                            ? text("player.play_start")
                            : text("player.play")}
                    </Button>
                    {resumeTip && screen === "reader" && pageInfo?.resumeExcerpt && pageInfo.resumeSegmentId && (
                      <span className="absolute bottom-full left-1/2 block -translate-x-1/2 pb-2">
                        <Surface
                          edge="strong"
                          className="w-[24rem] max-w-[calc(100vw-3rem)] p-3 shadow-lifted"
                        >
                          <span className="block text-xs text-ink-mute">
                            {pageInfo.resumeChapterTitle}
                          </span>
                          <button
                            type="button"
                            onClick={() => {
                              setResumeTip(false);
                              setReveal({
                                segmentId: pageInfo.resumeSegmentId!,
                                at: Date.now(),
                              });
                            }}
                            className="-mx-1 mt-1 block w-full rounded-lg px-1 py-1 text-left text-sm leading-relaxed hover-wash"
                          >
                            <span className="line-clamp-3">{pageInfo.resumeExcerpt}</span>
                            <span className="mt-1 block text-xs text-ink-faint">
                              {text("player.resume_goto")}
                            </span>
                          </button>
                        </Surface>
                      </span>
                    )}
                  </span>
                )}
              </>
            ) : (
              /* Playing: the bar is a TRANSPORT, in the middle the way every
                 player puts it - plus the one setting that now means something
                 mid-reading. The voice can be changed and the reading carries
                 on (owner, 03/09); speed still cannot, so it stays out of
                 reach rather than pretending. The menu offers the shortlist,
                 not all twenty - the shortlist is defined as exactly this: the
                 voices worth reaching for while listening. */
              <>
                {selection && (
                  <Button variant="primary" size="sm" onClick={readSelection}>
                    {text("reader.selection")}
                  </Button>
                )}
                {speechSettings && previewing === null && (
                  <MenuButton
                    icon={<SpeakerIcon />}
                    label={text("voices.switch")}
                    align="left"
                    items={[
                      ...offeredVoices(voices, shortlist, voiceId).map((voice) => ({
                        label: voiceName(voice.label) || voice.id,
                        hint: voice.id === voiceId ? text("voices.in_use") : undefined,
                        onSelect: () => switchVoice(voice.id),
                      })),
                      { label: text("voices.manage"), onSelect: () => setVoicesOpen(true) },
                    ]}
                  />
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
          {/* Right: what the voice is up to, and which voice that is. The
              settings chip moved out of the middle group (owner, 03/09): the
              middle is what a CLICK DOES, and the chip is a standing fact
              about the reading with a way in - it belongs beside the state,
              not inside the actions. Its panel stays centred over the bar. */}
          <div className="flex min-w-0 items-center justify-end gap-2 justify-self-end">
            {reading !== "idle" && player.warming && (
              <Notice className="min-w-0 truncate whitespace-nowrap">{text("player.warming")}</Notice>
            )}
            {player.error && (
              <Notice tone="error" className="min-w-0 truncate">
                {player.error}
              </Notice>
            )}
            {speechSettings && (
              <Button
                variant="ghost"
                onClick={() => {
                  // One floating layer at a time: the voices sheet sits above
                  // this panel, so opening settings under it would put a
                  // panel where nobody can reach it.
                  if (previewing !== null) stopPreview();
                  setVoicesOpen(false);
                  setSettingsOpen((value) => !value);
                }}
                aria-label={text("player.settings_open")}
                title={text("player.settings_open")}
                className={`shrink-0 ${settingsOpen ? "text-ink" : ""}`}
              >
                <SlidersIcon />
                {/* Without a voice the old chip read " · 1.25×", a
                    separator with nothing on its left. */}
                <span className="font-normal">{voiceId ? `${voiceId} · ` : ""}{rate}×</span>
              </Button>
            )}
          </div>
        </div>
      </footer>
      )}
      {settingsOpen && speechSettings && (
        <SettingsPanel
          /* Only the voices switched on (plus the one in use): the shortlist
             is the person's list of voices, and it governs both the place a
             voice is chosen and the menu that switches between them. */
          voices={offeredVoices(voices, shortlist, voiceId)}
          voiceId={voiceId}
          rate={rate}
          rates={RATES}
          reading={reading !== "idle"}
          shortlisted={shortlist.length}
          voicesError={voicesError}
          onVoice={switchVoice}
          onRate={rememberRate}
          onManageVoices={() => { setSettingsOpen(false); setVoicesOpen(true); }}
          onClose={() => {
            setSettingsOpen(false);
            invoke<Voice[]>("engine_voices")
              .then(setVoices)
              .catch(() => undefined);
          }}
        />
      )}
      {voicesOpen && (
        <VoicesPanel
          error={voicesError}
          voices={voices}
          shortlist={shortlist}
          voiceId={voiceId}
          reading={reading !== "idle" && previewing === null}
          previewing={previewing}
          onToggle={(id) => rememberShortlist(toggleShortlist(shortlist, id))}
          onPreview={previewVoice}
          onStopPreview={stopPreview}
          onClose={() => {
            if (previewing !== null) stopPreview();
            setVoicesOpen(false);
          }}
        />
      )}
    </div>
  );
}
