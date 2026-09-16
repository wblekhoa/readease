import { useCallback, useEffect, useMemo, useReducer, useRef, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { readingFault, faultKey } from "./ui/voiceFault";
import { GradientBlur, MenuButton, RailGroup, RailItem, SideColumn, Toolbar } from "./ui/patterns";
import { NARROW, STORAGE_KEY as SIDEBAR_KEY, initialSidebar, sidebar, sidebarOpen, type SidebarTab } from "./ui/sidebarState";
import { orderShelf } from "./ui/libraryOrder";
import { WINDOW_BUTTONS_IN_PAGE } from "./ui/host";
import { External, type ExternalEntry } from "./screens/External";
import { Button, IconButton, Notice, SegmentedControl, Select, SuggestionDot, Surface, Textarea } from "./ui/controls";
import { languageName, SettingsPanel } from "./ui/SettingsPanel";
import { VoicesPanel } from "./ui/VoicesPanel";
import {
  canSpeak,
  initialShortlist,
  offeredVoices,
  serializeShortlist,
  sampleLanguage,
  toggleShortlist,
  voiceName,
  type Voice, chipName } from "./ui/voiceShortlist";
import {
  firstRunNeeded,
  initialReadingLanguage,
  isLanguage,
  languageHint,
  languageOfVoice,
  offeredFor,
  voiceForTab,
  type Language as ReadingLanguage,
  type ModelStatus,
} from "./ui/readingSources";
import { useModels } from "./ui/useModels";
import { SourcesHub } from "./ui/SourcesHub";
import { useShortcut } from "./ui/useShortcut";
import {
  ArrowLeftIcon,
  NextIcon,
  PauseIcon,
  AiSpeakerIcon,
  PlayIcon,
  PreviousIcon,
  BookClosedIcon,
  StopIcon,
  ReadingSettingsIcon,
  SearchIcon,
  InfoIcon,
  VoiceIcon,
  CoinIcon,
  SunIcon,
  MoonIcon,
  BookIcon,
  ClipboardIcon,
  NoteIcon,
  CursorTextIcon,
  TransferIcon,
  SpeakerIcon,
  SidebarIcon,
} from "./ui/icons";
import { IDLE, playback } from "./ui/playback";
import {
  READING_SIZES,
  rememberReadingSize,
  storedReadingSize,
} from "./ui/readingSize";
import { rememberReadingMode, storedReadingMode, type ReadingMode } from "./ui/readingMode";
import { rememberReadingPrefs, storedReadingPrefs, type ReadingPrefs } from "./ui/readingPrefs";
import { ReadingSettingsPanel } from "./ui/ReadingSettingsPanel";
import { CostPanel } from "./ui/CostPanel";
import {
  buttonCost,
  costPhrase,
  isPaidVoice,
  PROVIDERS,
  rememberScope,
  storedScope,
  type Estimate,
} from "./ui/readingCost";
import { keyVerdict, type KeyReply } from "./ui/keyVerdict";
import { nextTheme, rememberThemePreference, resolveTheme, storedThemePreference, type Theme, type ThemePreference } from "./ui/theme";
import { Library, type LibraryBook } from "./screens/Library";
import { Reader, type PageInfo } from "./screens/Reader";
import { FirstRun } from "./screens/Setup";
import { Transfer } from "./screens/Transfer";
import { currentLanguage, engineMessage, setLanguage, text, type Language } from "./i18n";

const PASTE_LIMIT = 100_000;
const RATES = [0.5, 0.75, 1.0, 1.15, 1.2, 1.25, 1.5, 2.0];

type ModelGate = "checking" | "setup" | "ready";

/** Light or dark onto the DS token switch: the reader's own choice when
 * they have made one (the toolbar switch, owner 02/09), the macOS
 * appearance otherwise - followed live. */
function useAppearance(): [Theme, () => void, ThemePreference, (preference: ThemePreference) => void] {
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
  const choose = useCallback((next: ThemePreference) => {
    rememberThemePreference(next);
    setPreference(next);
  }, []);
  return [theme, toggle, preference, choose];
}

/** Where a layer hung from a control gets pinned: the control's centre and
 * its top edge, in viewport coordinates. Read once when the layer opens - a
 * hover panel that outlived a scroll would be pointing at nothing anyway, and
 * it closes when the pointer leaves. */
function anchor(element: HTMLElement) {
  const rect = element.getBoundingClientRect();
  return { centre: rect.left + rect.width / 2, top: rect.top };
}

export default function App() {
  const [theme, toggleTheme, appearance, chooseAppearance] = useAppearance();
  // The library first (owner, 16/09): the first tab of the rail is the
  // first screen. An empty shelf offers the paste screen itself.
  const [tab, setTab] = useState("library");
  const [voices, setVoices] = useState<Voice[]>([]);
  /** Why there are no voices to offer. An empty catalogue is a claim - "this
   * Mac has no voices" - and a failed request is not that claim. */
  const [voicesError, setVoicesError] = useState<string | null>(null);
  const [voiceId, setVoiceId] = useState<string>("");
  /** The saved voice the first listing could not honour because its
   * provider had not answered yet: id, and what was chosen instead. */
  const stillWanted = useRef<{ id: string; fallback: string } | null>(null);
  /** The stored shortlist as read at start-up, and whether the person has
   * edited it since. A paid entry keeps its place while its provider is
   * still being asked (the list only filters at display time), but its
   * MODEL can only be brought up to date against the full catalogue. */
  const storedShortlist = useRef<{ value: string | null; touched: boolean }>({ value: null, touched: false });
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
  /* The rows the CONTROLS sit in, inside each bar. A floating layer belongs
     12px from the button that opened it, and the bar's box stops 24px past
     that button - so a panel measured from the box is a panel measured from
     the wrong edge (owner, 04/09). */
  const headerRow = useRef<HTMLDivElement>(null);
  const footerRow = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const root = shell.current;
    if (!root) return;
    const apply = () => {
      root.style.setProperty("--shell-top-h", `${headerBar.current?.offsetHeight ?? 0}px`);
      root.style.setProperty("--shell-bottom-h", `${footerBar.current?.offsetHeight ?? 0}px`);
      // …and where the controls themselves stop, in the shell's own
      // coordinates, which is what an absolutely positioned layer uses.
      const box = root.getBoundingClientRect();
      /* Where the CONTROLS stop, measured off the controls themselves.
       *
       * Not the bar's box (24px of frost room past them) and not the row's
       * content box either (a 30px button centred in a 36px row leaves
       * slack). The row's own children hug the buttons, so their edge is the
       * one a person sees and the one a layer should sit 12px from. */
      const edge = (row: HTMLElement | null, side: "top" | "bottom") => {
        // The controls THEMSELVES, however deeply the bar nests them: a
        // wrapper is a couple of pixels taller than what it wraps, and those
        // pixels land in the gap a person is looking at.
        const controls = row
          ? [...row.querySelectorAll("button, select, input, a")]
          : [];
        if (!controls.length) return null;
        const rects = controls.map((control) => control.getBoundingClientRect());
        return side === "top"
          ? Math.max(...rects.map((rect) => rect.bottom))
          : Math.min(...rects.map((rect) => rect.top));
      };
      const top = edge(headerRow.current, "top");
      const bottom = edge(footerRow.current, "bottom");
      root.style.setProperty(
        "--shell-top-inner",
        `${top === null ? headerBar.current?.offsetHeight ?? 0 : Math.round(top - box.top)}px`,
      );
      root.style.setProperty(
        "--shell-bottom-inner",
        `${bottom === null ? footerBar.current?.offsetHeight ?? 0 : Math.round(box.bottom - bottom)}px`,
      );
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
  /* WHICH captured passage the voice is in. `position` alone cannot say:
   * every passage in the history has a `part-2`, so without this the marker
   * would land in all of them at once. */
  const [readingAt, setReadingAt] = useState<number | null>(null);
  const [externalStatus, setExternalStatus] = useState<string | null>(null);
  /* The two models on this Mac and any download in flight - one owner, so
     the first-run screen, the hub and the settings panel never disagree
     about what is installed or what is being fetched. */
  const models = useModels();
  const [settingsOpen, setSettingsOpen] = useState(false);
  /** The hub: what this Mac reads, by language, and how to add to it. */
  const [hubOpen, setHubOpen] = useState(false);
  /** The language the reader chose to read in (owner, 15/09: choose the
   * language first, then see its voices). Kept in step with the voice: a
   * voice made for one language moves this to it. */
  const [readingLanguage, setReadingLanguage] = useState<ReadingLanguage>("vi");
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
  /* The side column (HIG 3.16): whether it shows, and which of a book's
     lists it shows, under the rules in ui/sidebarState.ts. The remembered
     choice and the window's width at start are its starting point. */
  const [side, dispatchSide] = useReducer(sidebar, undefined, () => {
    let remembered: string | null = null;
    try { remembered = localStorage.getItem(SIDEBAR_KEY); } catch { /* private window */ }
    return initialSidebar(remembered, window.innerWidth < NARROW);
  });
  const sideOpen = sidebarOpen(side);
  /** The list on show in a book, or null: folded, or not in a book. */
  const sideTab: SidebarTab | null = sideOpen && side.book ? side.tab : null;
  /* Which note the notes tab should land on, when it was opened from the
     note's own editor. */
  const [notesFocus, setNotesFocus] = useState<string | null>(null);
  /* Where the column's body is, for the reader to render a book's lists
     into (a portal). A callback ref, so the reader re-renders when the
     column comes and goes. */
  const [sideSlot, setSideSlot] = useState<HTMLElement | null>(null);
  /* And where a home screen's actions stand: the toolbar's trailing
     cluster, the way a book's stand beside its title. */
  const [actionsSlot, setActionsSlot] = useState<HTMLElement | null>(null);
  /* The books being read, for the column's "Đang đọc" - asked for at start
     and whenever a book is left, since leaving is when progress moves. */
  const [shelf, setShelf] = useState<LibraryBook[]>([]);
  /** "Take me to where reading would resume" - the stamp lets the same place
   * be asked for twice. */
  const [reveal, setReveal] = useState<{ segmentId: string; at: number } | null>(null);
  /* Not a boolean: the panel is drawn in a PORTAL now (see the read button),
     so it carries the anchor it was opened from. */
  const [resumeTip, setResumeTip] = useState<{ centre: number; top: number } | null>(null);
  /* What a paid voice would cost this press of the button, and how far the
     press reaches. `null` estimate means "still counting", and the button
     stays disabled until it is not - the owner's rule (04/09): nobody spends
     money by pressing a button that had not yet told them the price. */
  const [scope, setScope] = useState<number | null>(storedScope);
  const [budget, setBudget] = useState<number | null>(null);
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [estimateFailed, setEstimateFailed] = useState(false);
  /** Provider id → whether a key is stored. Never the key: the engine
   *  answers `config.get` for these with the fact and nothing else. */
  const [keysSet, setKeysSet] = useState<Record<string, boolean>>({});
  const [spent, setSpent] = useState(0);
  const [costOpen, setCostOpen] = useState(false);
  const [readingSize, setReadingSize] = useState(storedReadingSize);
  const [readingMode, setReadingMode] = useState<ReadingMode>(storedReadingMode);
  const chooseReadingMode = useCallback((next: ReadingMode) => {
    rememberReadingMode(next);
    setReadingMode(next);
  }, []);
  /* The finer setting of the page (ui/readingPrefs), and the two panels the
     book's toolbar opens: reading settings and search in the book (owner,
     06/09: "học hỏi theo Apple Books"). One floating layer at a time. */
  const [prefs, setPrefs] = useState<ReadingPrefs>(storedReadingPrefs);
  const choosePrefs = useCallback((next: ReadingPrefs) => {
    rememberReadingPrefs(next);
    setPrefs(next);
  }, []);
  const [readingSettingsOpen, setReadingSettingsOpen] = useState(false);

  const paidVoice = isPaidVoice(voiceId);
  /* Whether there is anything to put a price ON. An empty paste box is not
     a reading that is still being counted - it is no reading at all, and a
     button claiming "Đang tính…" over an empty box counts for ever. */
  const pricing = paidVoice && (openBook !== null || content.trim().length > 0);

  /* Re-price whenever anything the price depends on moves: the book, where
     the voice would resume, which voice, how far. Every one of those changes
     the number in the button, so every one of them must invalidate it first
     - a stale price on a button that spends money is worse than no price. */
  useEffect(() => {
    // Priced on BOTH screens. A paste can be 100,000 characters, which is one
    // press of a button and ten dollars on the dearer voices - it was the
    // case that needed the number most and the one screen that never had it.
    const params = openBook
      ? {
        book_id: openBook.id,
        segment_id: position ?? openBook.segment_id ?? null,
        voice_id: voiceId,
        chapters: scope,
      }
      : content.trim()
        ? { text: content, voice_id: voiceId }
        : null;
    if (!params || !voiceId) {
      setEstimate(null);
      return;
    }
    let live = true;
    setEstimate(null);
    setEstimateFailed(false);
    void invoke<{ result: Estimate & { spent_usd?: number } }>("engine_request", {
      method: "estimate",
      params,
    })
      .then((reply) => {
        if (!live) return;
        setEstimate(reply.result);
        setSpent(reply.result.spent_usd ?? 0);
      })
      .catch((error) => {
        // The button stays LOCKED - guessing a price would be the one thing
        // worse than waiting - but it says so rather than sitting there
        // claiming to still be counting.
        console.error(error);
        if (live) setEstimateFailed(true);
      });
    return () => {
      live = false;
    };
  }, [openBook, position, voiceId, scope, content]);

  const changeScope = useCallback((chapters: number | null) => {
    setScope(chapters);
    rememberScope(chapters);
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
  /** The voice last chosen under each language, so switching back to a
   * language brings its voice back. Read once at start-up, written when a
   * voice is picked. */
  const voiceByLanguage = useRef<Record<string, string>>({});
  /* Whether start-up has finished reading the saved voice. Until it has,
     the catalogue arrives with no voice chosen yet, and the one automatic
     voice change below would take that for "nothing fits" and write the
     first voice over the saved one before the saved one was even read -
     every launch, on every Mac (seen 15/09: the owner's choice replaced by
     the first Vietnamese voice). */
  const startupSettled = useRef(false);
  /* A mirror of `readingLanguage` for callbacks that must not be rebuilt
     on every change of it: the shortcut's reading closure, the voice
     memory. */
  const readingLanguageRef = useRef<ReadingLanguage>("vi");
  const chooseReadingLanguage = useCallback((language: ReadingLanguage) => {
    readingLanguageRef.current = language;
    setReadingLanguage(language);
    remember("reading_language", language);
  }, [remember]);
  const rememberVoice = useCallback((id: string) => {
    setVoiceId(id);
    remember("voice", id);
    // A voice made for one language moves the reading language to it - the
    // mid-reading switcher lists every marked voice, and picking Heart there
    // is choosing English. A voice that names none (OpenAI) is filed under
    // the language whose tab it was picked from.
    const language = languageOfVoice(voices.find((voice) => voice.id === id))
      ?? readingLanguageRef.current;
    voiceByLanguage.current[language] = id;
    remember(`voice_${language}`, id);
    if (language !== readingLanguageRef.current) chooseReadingLanguage(language);
  }, [remember, voices, chooseReadingLanguage]);
  const rememberRate = useCallback((value: number) => {
    setRate(value);
    remember("rate", value);
  }, [remember]);
  const refreshKeys = useCallback(() => {
    for (const provider of PROVIDERS) {
      void invoke<{ result: { set?: boolean } }>("engine_request", {
        method: "config.get",
        params: { key: provider.settingsKey },
      })
        .then((reply) =>
          setKeysSet((current) => ({ ...current, [provider.id]: reply.result.set === true })),
        )
        .catch(() => undefined);
    }
  }, []);

  useEffect(refreshKeys, [refreshKeys]);

  /** Save a key, then CHECK it by asking for the catalogue again.
   *
   * A provider that answers with no voices has not been set up, whatever the
   * key looked like - and being told that while typing beats being told
   * mid-chapter, when a reading somebody was waiting for stops instead. */
  /* The engine asks the PROVIDER whether this key works, and only saves it
     if the answer is yes.

     What this replaced: save it, re-list the catalogue, and take "a paid
     voice appeared" as proof. That is proof for a provider whose catalogue
     is a live authenticated call - and none at all for OpenAI, whose nine
     voices are a constant that never leaves this Mac. Any non-empty string
     was accepted and the panel said it had been checked; the first thing
     that actually knew was a chapter half read (owner, 04/09). */
  const saveKey = useCallback(async (provider: string, key: string) => {
    const reply = await invoke<KeyReply>(
      "engine_request",
      { method: "config.verify_key", params: { provider, value: key } },
    ).catch(() => null);
    // Which `ok` counts is decided in keyVerdict, which has tests on it.
    const { ok, code } = keyVerdict(reply);
    if (ok) {
      const list = await invoke<Voice[]>("engine_voices").catch(() => [] as Voice[]);
      setVoices(list);
    }
    setKeysSet((current) => ({ ...current, [provider]: ok }));
    return { ok, code };
  }, []);

  const changeBudget = useCallback((usd: number | null) => {
    setBudget(usd);
    remember("external_voice_budget", usd === null ? "" : String(usd));
  }, [remember]);
    const rememberShortlist = useCallback((ids: string[]) => {
    storedShortlist.current.touched = true;
    setShortlist(ids);
    // config.* is answered between audio chunks, so this saves even while a
    // chapter is being read - which is exactly when the list gets edited.
    remember("voice_shortlist", serializeShortlist(ids));
  }, [remember]);

  /* Nothing here moves the voice when a book opens. It did, for a day: a
     book opened in a voice made for its language, and the effect re-ran on
     every voice change and put the old one back - the loudest way of
     forcing "the right voice" the app ever had. The owner's decision
     (15/09): the voice is the reader's, and the app SUGGESTS - see `hint`
     below, the settings panel and the chip. */

  /** A reader's word about which language the open book is in.
   *
   * The engine answers with what the book is in NOW - the language it chose
   * when the decision was withdrawn, not the one that was just cleared - so
   * the panel shows the real answer rather than an optimistic one. Anything
   * else and withdrawing a decision would leave the row on the language that
   * had just been removed.
   */
  const setBookLanguage = useCallback((language: string | null) => {
    setOpenBook((book) => {
      if (!book) return book;
      void invoke<{
        result: {
          language?: string;
          language_set?: boolean;
          language_detected?: string;
        };
      }>(
        "engine_request",
        {
          method: "book.set_language",
          params: { book_id: book.id, language },
        },
      )
        .then((answer) => {
          const settled = answer?.result;
          if (!settled?.language) return;
          setOpenBook((current) =>
            current && current.id === book.id
              ? {
                  ...current,
                  language: settled.language,
                  language_set: Boolean(settled.language_set),
                  language_detected: settled.language_detected,
                }
              : current,
          );
        })
        .catch(() => undefined);
      return book;
    });
  }, []);

  const { accelerator, change: changeShortcut } = useShortcut();
  const speech = useRef({ voiceId: "", rate: 1.0 });
  speech.current = { voiceId, rate };
  where.current = position;

  useEffect(() => {
    // FIRST, because the engine answers one request at a time and this is
    // the one that decides which screen to show: until it lands the window
    // is blank. It used to queue behind the voice listing, which loaded
    // the model - 1.5-2 s of nothing on screen at every launch (measured
    // 14/09), more with a paid provider to ask over the network.
    //
    // The first-run screen shows only while NOTHING on this Mac can read:
    // no model of either language and no provider key. A key counts before
    // its voices are listed - they arrive by event, and an API-only reader
    // must not see the setup screen flash on every launch.
    const keys = Promise.all(PROVIDERS.map((provider) =>
      invoke<{ result: { set?: boolean } }>("engine_request", {
        method: "config.get", params: { key: provider.settingsKey },
      })
        .then((reply) => [provider.id, reply.result.set === true] as const)
        .catch(() => [provider.id, false] as const)));
    Promise.all([
      invoke<{ result: ModelStatus }>("engine_request", { method: "model.status", params: {} }),
      keys,
    ])
      .then(([reply, found]) => {
        models.setStatus(reply.result);
        const keysSet = Object.fromEntries(found);
        setKeysSet((current) => ({ ...current, ...keysSet }));
        setGate(firstRunNeeded(reply.result, keysSet) ? "setup" : "ready");
      })
      // A dead engine still deserves a visible app: errors surface on use,
      // a blank window surfaces nothing.
      .catch(() => setGate("ready"));
    // The Qt shell remembered the voice and the speed; losing that in the
    // rewrite would be a downgrade nobody asked for. Same settings file, same
    // two keys, so an existing choice carries over.
    invoke<Voice[]>("engine_voices")
      .then(async (list) => {
        setVoices(list);
        setVoicesError(null);
        // The language tab opens where it was left; failing that, on the
        // saved voice's language; failing that, on the interface's. Read
        // before the voices are looked at: a Mac with no voice yet still
        // opens its panel on the language the reader last chose.
        const storedLanguage = await invoke<{ result: { value: string | null } }>(
          "engine_request",
          { method: "config.get", params: { key: "reading_language" } },
        ).catch(() => null);
        const saved = await invoke<{ result: { value: string | null } }>(
          "engine_request",
          { method: "config.get", params: { key: "voice" } },
        ).catch(() => null);
        const before = saved?.result.value;
        const known = before ? list.find((voice) => voice.id === before) : undefined;
        const opening = initialReadingLanguage(storedLanguage?.result.value, known, currentLanguage());
        readingLanguageRef.current = opening;
        setReadingLanguage(opening);
        if (!list.length) {
          startupSettled.current = true;
          return;
        }
        for (const language of ["vi", "en"]) {
          const chosen = await invoke<{ result: { value: string | null } }>(
            "engine_request",
            { method: "config.get", params: { key: `voice_${language}` } },
          ).catch(() => null);
          if (chosen?.result.value) voiceByLanguage.current[language] = chosen.result.value;
        }
        // The voice saved before there was a memory per language is filed
        // under the language it was made for, so switching languages and
        // back finds it again.
        const madeFor = languageOfVoice(known);
        if (madeFor && !voiceByLanguage.current[madeFor] && known) {
          voiceByLanguage.current[madeFor] = known.id;
          remember(`voice_${madeFor}`, known.id);
        }
        // Inside this chain because the starting five have to be filtered
        // against the catalogue this build actually ships.
        const kept = await invoke<{ result: { value: string | null } }>(
          "engine_request",
          { method: "config.get", params: { key: "voice_shortlist" } },
        ).catch(() => null);
        storedShortlist.current = { value: kept?.result.value ?? null, touched: false };
        setShortlist(initialShortlist(kept?.result.value, list));
        const wanted = saved?.result.value;
        // A remembered voice that this build no longer ships must not leave
        // the picker empty - fall back to the first one, as the Qt shell did.
        // A remembered PAID voice may simply not be listed yet - its
        // provider is still being asked in the background - so the wish is
        // kept until the catalogue event says whether it can be honoured.
        const present = Boolean(wanted && list.some((voice) => voice.id === wanted));
        if (wanted && !present) stillWanted.current = { id: wanted, fallback: list[0].id };
        // Failing the saved voice: the first that fits the language the
        // tab opens on, so an English-only Mac does not start on nothing
        // while its six voices sit further down the list.
        const fallback = list.find((voice) => voice.id === voiceForTab(null, offeredFor(list, [], "", opening))) ?? list[0];
        const starting = present ? (wanted as string) : fallback.id;
        setVoiceId(starting);
        // The tab follows the voice in use: a Mac with the English model
        // alone starts on Heart, and its panel must open on English, not on
        // an empty Vietnamese tab beside a speaking English voice.
        const spoken = languageOfVoice(list.find((voice) => voice.id === starting));
        if (spoken && spoken !== opening) {
          readingLanguageRef.current = spoken;
          setReadingLanguage(spoken);
        }
        startupSettled.current = true;
      })
      .catch((error) => {
        console.error(error);
        setVoicesError(engineMessage(error));
        // Settled all the same: a Mac whose first listing failed must
        // still get its first voice when a download brings one.
        startupSettled.current = true;
      });
    invoke<{ result: { value: string | null } }>("engine_request", {
      method: "config.get",
      params: { key: "external_voice_budget" },
    })
      .then((reply) => {
        const saved = Number(reply.result.value);
        if (Number.isFinite(saved) && saved > 0) setBudget(saved);
      })
      .catch(() => undefined);
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
    // A paid provider's catalogue arrives after the first listing, fetched
    // in the background so the launch never waits on the network. The
    // engine says when it is in; the list grows, the choice stays.
    const catalogue = listen("engine:voices", () => {
      invoke<Voice[]>("engine_voices")
        .then((list) => {
          // An empty list is a real answer now - the last model removed,
          // no key - not a listing to wait out.
          setVoices(list);
          if (!list.length) return;
          // Re-read the stored shortlist against the whole catalogue, so a
          // paid voice whose model moved is re-homed the way it would have
          // been had its provider answered in time - unless the person has
          // edited the list since, in which case their edit stands.
          if (!storedShortlist.current.touched) {
            setShortlist(initialShortlist(storedShortlist.current.value, list));
          }
          const wish = stillWanted.current;
          if (wish && list.some((voice) => voice.id === wish.id)) {
            stillWanted.current = null;
            // Only if nobody chose something else in the meantime.
            setVoiceId((current) => (current === wish.fallback ? wish.id : current));
          }
        })
        .catch(() => undefined);
    });
    // The global shortcut hands the captured text to the webview, which owns
    // the voice and rate, and the webview asks the engine to speak it.
    const external = listen<{ text: string }>("reading:external", (event) => {
      const captured = event.payload.text;
      const at = Date.now();
      setExternalHistory((history) =>
        [{ at, text: captured }, ...history].slice(0, 50),
      );
      // Opens itself in the history, so the reader can follow the words
      // being spoken instead of only hearing them.
      setReadingAt(at);
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
    /* The running total, as the engine counts it up.
     *
     * It also rides back on every `estimate` reply, and that was the ONLY
     * way it moved until 10/09 - so auditioning five paid voices left the
     * figure under "Phiên này đã tiêu" exactly where it started, while the
     * panel above it says previewing is charged to the ceiling. Estimates
     * re-run when the book, position, voice, scope or text changes; tapping
     * Preview changes none of those.
     *
     * The engine already emitted this and the Rust host already forwarded it
     * under `engine:<name>`; nothing was listening. Assignment, not
     * addition: `usd` is the session's whole total, from one counter that
     * only grows while the app is open. A superseded reading's spend is
     * deliberately NOT filtered out the way its audio is - money that went
     * out was still spent. */
    const spent = listen<{ usd: number }>(
      "engine:spend",
      (event) => setSpent(event.payload.usd),
    );
    return () => {
      done.then((unlisten) => unlisten());
      moved.then((unlisten) => unlisten());
      catalogue.then((unlisten) => unlisten());
      started.then((unlisten) => unlisten());
      external.then((unlisten) => unlisten());
      externalState.then((unlisten) => unlisten());
      spent.then((unlisten) => unlisten());
    };
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
        // How far this press may reach. Outside it, nothing is ever sent -
        // which for a paid voice is the difference between a chapter and a
        // book.
        bookId: openBook.id, segmentId, voiceId, rate, chapters: scope,
      });
    } catch (error) {
      console.error(error);
      onPlayer({ type: "failed", error: String(error) });
    }
  }, [openBook, voiceId, rate, scope]);

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
      ? invoke("read_book", { bookId: live.bookId, segmentId: at, voiceId: id, rate, chapters: scope })
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
  }, [player.reading, rate, rememberVoice, scope]);

  /** The reader picks a language: the tab moves, and the voice last used
   * under it comes back - failing that the first that fits, local before
   * paid. Nothing fits: the tab moves alone and shows how to get a voice. */
  const switchReadingLanguage = useCallback((language: ReadingLanguage) => {
    chooseReadingLanguage(language);
    const wanted = voiceForTab(
      voiceByLanguage.current[language],
      offeredFor(voices, shortlist, voiceId, language),
    );
    if (wanted && wanted !== voiceId) switchVoice(wanted);
  }, [chooseReadingLanguage, voices, shortlist, voiceId, switchVoice]);

  /* The one time the voice moves without a tap: a model was just fetched
     for the language the tab is on, and no voice in use fits that language.
     The reader chose the language and pressed its download - starting its
     first voice is the end of that action, not a choice made for them. A
     paid voice is never chosen this way (`voiceForTab` runs on the local
     ones only here): that would spend money nobody chose to spend. */
  useEffect(() => {
    // Not while start-up is still reading the saved voice: an empty
    // `voiceId` here is "not read yet", not "nothing fits". (Not `!voiceId`
    // either - a Mac that entered with nothing and downloads from the
    // panel has an empty one legitimately, and must get its first voice.)
    if (!startupSettled.current || !voices.length) return;
    const current = voices.find((voice) => voice.id === voiceId);
    if (current && canSpeak(current, readingLanguage)) return;
    const local = offeredFor(voices, shortlist, voiceId, readingLanguage)
      .filter((voice) => !isPaidVoice(voice.id));
    const wanted = voiceForTab(voiceByLanguage.current[readingLanguage], local);
    if (wanted && wanted !== voiceId) switchVoice(wanted);
    // Only when the catalogue changes: a tab switch has its own rule.
  }, [voices]);

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
    // In a language this voice can actually speak. One Vietnamese sentence
    // for every voice meant an English-only voice auditioned by stumbling
    // through Vietnamese - which says nothing about the voice.
    const voice = voices.find((candidate) => candidate.id === id);
    const spoken = sampleLanguage(voice ?? {}, currentLanguage());
    invoke("read_text", {
      text: text(spoken === "en" ? "voices.sample_en" : "voices.sample"),
      segmentId: null,
      voiceId: id,
      rate,
      // This sentence is the app's, not the reader's, so the engine may keep
      // the clip - which is what stops a second audition of a paid voice
      // being a second charge.
      appText: true,
    }).catch((error) => {
      console.error(error);
      onPlayer({ type: "failed", error: String(error) });
      setPreviewing(null);
    });
  }, [rate, voices]);

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

  /* The side column's keys (HIG §4): ⌃⌘S folds and unfolds it - the Mac's
     own "Toggle Sidebar" chord - and ⌘F in a book opens the search tab. */
  const inBook = tab === "library" && openBook !== null;
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase();
      if (event.metaKey && event.ctrlKey && !event.altKey && key === "s") {
        event.preventDefault();
        dispatchSide({ type: "toggle" });
      } else if (event.metaKey && !event.ctrlKey && !event.altKey && !event.shiftKey && key === "f" && inBook) {
        event.preventDefault();
        dispatchSide({ type: "show", tab: "search" });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [inBook]);

  /* A choice made by hand is remembered; the automation's answer is not
     (it is recomputed from the window each launch). */
  useEffect(() => {
    if (side.choice === "auto") return;
    try { localStorage.setItem(SIDEBAR_KEY, side.choice); } catch { /* private window */ }
  }, [side.choice]);

  /* The width, live: `change` is the precise signal, `resize` the backstop
     for a host that resizes without a media-query event (useShortWindow
     learned that from the preview harness, 07/09). */
  useEffect(() => {
    const media = window.matchMedia(`(max-width: ${NARROW - 1}px)`);
    const follow = () => dispatchSide({ type: "width", narrow: media.matches });
    follow();
    media.addEventListener("change", follow);
    window.addEventListener("resize", follow);
    return () => {
      media.removeEventListener("change", follow);
      window.removeEventListener("resize", follow);
    };
  }, []);

  /* A book puts its lists in the column; leaving it puts the navigation
     back - and refreshes "Đang đọc", since leaving is when progress moved. */
  useEffect(() => {
    dispatchSide({ type: "book", open: inBook });
    if (!inBook) setNotesFocus(null);
  }, [inBook]);
  const loadShelf = useCallback(() => {
    invoke<{ result: { books: LibraryBook[] } }>("engine_request", { method: "library.list", params: {} })
      .then((reply) => setShelf(reply.result.books))
      .catch(() => undefined);
  }, []);
  useEffect(() => { if (!inBook) loadShelf(); }, [inBook, loadShelf]);
  const readingNow = useMemo(
    () => orderShelf(shelf.filter((book) => book.segment_id)).slice(0, 5),
    [shelf],
  );

  /* Two tiers of feature (owner, 02/09: "phân chia rõ tính năng phụ và
     tính năng chính"). PRIMARY = the ways to get something read: a book
     from the library, or pasted text - they live in the rail with a glyph
     each. SECONDARY = tools around reading: reading a selection from
     another app, and moving notes between copies of a book - a quieter
     cluster at the right, same glyph language. */
  const tabs = useMemo(() => ([
    { value: "library", label: text("nav.library"), icon: <BookIcon /> },
    { value: "paste", label: text("nav.paste"), icon: <ClipboardIcon /> },
  ]), [language]);
  const tools = useMemo(() => ([
    { value: "external", label: text("nav.external"), icon: <CursorTextIcon /> },
    { value: "transfer", label: text("nav.transfer"), icon: <TransferIcon /> },
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
  /* What the text in front of the reader is in: the book's language, or the
     one the estimate found the pasted passage to be in. A captured
     selection has none - it is read the moment it lands. */
  const contentLanguage = screen === "reader"
    ? openBook?.language ?? null
    : screen === "paste" && content.trim()
      ? estimate?.language ?? null
      : null;
  /* The nudge, and never more than a nudge (owner, 15/09): the voice in use
     was not made for the language in front of the reader. */
  const hint = languageHint(
    contentLanguage,
    voices.find((voice) => voice.id === voiceId),
    isLanguage(contentLanguage) ? offeredFor(voices, shortlist, voiceId, contentLanguage) : [],
  );
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
      <FirstRun
        models={models}
        voices={voices}
        keysSet={keysSet}
        onSaveKey={saveKey}
        reading={false}
        onEnter={() => {
          setGate("ready");
          // Whatever was fetched: the catalogue and the voice in use follow
          // it. A model's voices arrive by event too, but a person who
          // pressed nothing still gets a fresh listing on the way in.
          invoke<Voice[]>("engine_voices")
            .then((list) => {
              setVoices(list);
              if (list.length && !list.some((voice) => voice.id === voiceId)) {
                const first = voiceForTab(null, offeredFor(list, [], "", readingLanguageRef.current)) ?? list[0].id;
                rememberVoice(first);
              }
            })
            .catch(console.error);
          models.refresh();
        }}
      />
    );
  }

  /* The column's foot: what the app carries everywhere - the hub, the
     appearance, the language (owner, 02/09, moved here 16/09). */
  const themeSwitch = (
    <IconButton
      onClick={toggleTheme}
      aria-label={text(theme === "dark" ? "aria.theme_to_light" : "aria.theme_to_dark")}
      title={text(theme === "dark" ? "aria.theme_to_light" : "aria.theme_to_dark")}
    >
      {theme === "dark" ? <SunIcon /> : <MoonIcon />}
    </IconButton>
  );
  const chrome = (
    <>
      <IconButton
        onClick={() => { setSettingsOpen(false); setVoicesOpen(false); setHubOpen(true); }}
        aria-label={text("hub.title")}
        title={text("hub.title")}
        className={hubOpen ? "text-ink" : ""}
        data-popover-trigger
      >
        <ReadingSettingsIcon />
      </IconButton>
      {themeSwitch}
      <Select
        pill
        aria-label={text("aria.language")}
        value={language}
        onChange={(event) => applyLanguage(event.target.value as Language)}
      >
        <option value="vi">🇻🇳 VI</option>
        <option value="en">🇬🇧 EN</option>
      </Select>
    </>
  );

  return (
    <div key={language} className="flex h-screen overflow-hidden">
      {/* The side column (HIG 3.16): navigation at home, a book's lists
          inside one. A real column - the content beside it is pushed, not
          covered (owner, 16/09). */}
      <SideColumn
        open={sideOpen}
        onToggle={() => dispatchSide({ type: "toggle" })}
        toggleLabel={text(sideOpen ? "sidebar.close" : "sidebar.open")}
        foot={chrome}
      >
        {inBook ? (
          <>
            <SegmentedControl
              className="mx-3 mb-3 shrink-0"
              label={text("sidebar.lists")}
              value={side.tab}
              onChange={(next) => dispatchSide({ type: "show", tab: next })}
              options={[
                { value: "contents" as SidebarTab, label: text("reader.toc_title") },
                {
                  value: "notes" as SidebarTab,
                  label: (pageInfo?.annotations ?? 0) > 0
                    ? `${text("sidebar.notes_tab")} · ${pageInfo?.annotations}`
                    : text("sidebar.notes_tab"),
                },
                { value: "search" as SidebarTab, label: text("sidebar.search_tab") },
              ]}
            />
            {/* The reader fills this through a portal; the slot is handed
                over as an element so the reader re-renders when it appears. */}
            <div ref={setSideSlot} className="flex min-h-0 flex-1 flex-col" />
          </>
        ) : (
          <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
            <nav aria-label={text("aria.workspace")} className="flex flex-col gap-0.5">
              {[...tabs, ...tools].map((item) => (
                <RailItem
                  key={item.value}
                  icon={item.icon}
                  label={item.label}
                  active={tab === item.value}
                  onPress={() => setTab(item.value)}
                />
              ))}
            </nav>
            {readingNow.length > 0 && (
              <RailGroup title={text("sidebar.reading")}>
                {readingNow.map((book) => (
                  <RailItem
                    key={book.id}
                    label={book.title}
                    onPress={() => { setTab("library"); setPosition(null); setOpenBook(book); }}
                  />
                ))}
              </RailGroup>
            )}
          </div>
        )}
      </SideColumn>
    {/* The DOL premium-blur shell (owner, 02/09): header and footer are
       overlays and the page scrolls UNDER them, which is the only way a
       backdrop blur has anything to blur. Screens learn the bars' heights
       from two named insets and pad themselves - nothing is coupled to a
       padding value written twice. Since 16/09 this is the content column
       beside the side column; the insets are measured inside it. */}
    <div
      ref={shell}
      className="relative min-w-0 flex-1 overflow-hidden"
      style={{ "--shell-top-h": "76px", "--shell-bottom-h": showFooter ? "76px" : "0px" } as CSSProperties}
    >
      {/* The window's title bar is an overlay, so this strip is what a
          person drags the window by (data-tauri-drag-region: a mousedown
          on the strip itself, never on a control inside it). */}
      <div ref={headerBar} data-tauri-drag-region className="absolute inset-x-0 top-0 z-20">
        <GradientBlur edge="top" />
        <div ref={headerRow} data-tauri-drag-region className="relative z-10 px-6 pb-6 pt-4">
      <Toolbar
        leading={
          <div className="flex min-w-0 items-center gap-1">
          {/* Folded, the column's head is gone and the Mac's window buttons
              sit over this corner instead: room for them, then - on the home
              screens - the switch that brings the column back, Codex's own
              arrangement. A book's toolbar has no such switch (owner, 16/09:
              "UI đọc sách thì sẽ không cần icon sidebar"): its ▤, notes and
              search buttons each unfold the column on their own list. */}
          {!sideOpen && WINDOW_BUTTONS_IN_PAGE && <span aria-hidden="true" className="w-[52px] shrink-0" />}
          {!sideOpen && !(screen === "reader" && openBook) && (
            <IconButton
              onClick={() => dispatchSide({ type: "toggle" })}
              aria-label={text("sidebar.open")}
              title={text("sidebar.open")}
            >
              <SidebarIcon />
            </IconButton>
          )}
          {/* The screen's name, where a book's title stands when a book is
              open (owner, 16/09: "title của trang tính năng... bên trái sẽ
              là nút sidebar"). One headline per screen: the pages no longer
              repeat it under the toolbar. */}
          {!(screen === "reader" && openBook) && (
            <h2 className="m-0 min-w-0 truncate px-1 text-base font-bold">
              {[...tabs, ...tools].find((item) => item.value === tab)?.label}
            </h2>
          )}
          {/* A book pushes its own chrome into the one row the window has;
             back returns to the shelf. Two stacked rows of chrome above a
             page of text is what this buys back. */}
          {screen === "reader" && openBook && (
            <>
              <IconButton
                onClick={() => { setOpenBook(null); setSegments([]); }}
                aria-label={text("reader.back")}
                title={text("reader.back")}
              >
                <ArrowLeftIcon />
              </IconButton>
              {/* The lists' switches (HIG 3.16): each opens the column on
                  its tab, and pressing the one already showing folds the
                  column - a real switch, decided in sidebarState. */}
              <IconButton
                onClick={(event) => {
                  event.currentTarget.blur();
                  dispatchSide({ type: "show", tab: "contents" });
                }}
                aria-label={sideTab === "contents" ? text("reader.toc_hide") : text("reader.toc_show")}
                title={sideTab === "contents" ? text("reader.toc_hide") : text("reader.toc_show")}
                className={sideTab === "contents" ? "text-ink" : ""}
              >
                <BookClosedIcon />
              </IconButton>
              {/* Only when the book carries something: a button that opens
                  an empty list is a button that lies about the book. */}
              {(pageInfo?.annotations ?? 0) > 0 && (
                <IconButton
                  onClick={(event) => {
                    event.currentTarget.blur();
                    setNotesFocus(null);
                    dispatchSide({ type: "show", tab: "notes" });
                  }}
                  aria-label={text("notes.open")}
                  title={text("notes.count", { count: pageInfo?.annotations ?? 0 })}
                  className={sideTab === "notes" ? "text-ink" : ""}
                >
                  <NoteIcon />
                </IconButton>
              )}
              <h2 className="m-0 min-w-0 flex-1 truncate px-1 text-base font-bold">
                {openBook.title}
              </h2>
              {pageInfo && (
                /* Where you are, on request: the page keeps nothing but the
                   book (owner, 02/09). A hover or a focus shows it.

                   Hung from the ICON, through the same measured-and-clamped
                   tooltip every other icon button gets from controls.tsx. It
                   used to be pinned to the window's left inset instead: the
                   icon drifts with the length of the book's title, and back
                   when the tooltip could only pick a static side, anchoring
                   to it overflowed one edge or the other. Pinning cured the
                   overflow by pointing at nothing - it landed a whole title's
                   width away from the thing under the pointer (owner, 04/09:
                   "bị chệch về bên trái thay vì nằm giữa icon hover").
                   Measuring the button solves what choosing a side could not.

                   Two lines, because the bubble is 16rem and this used to be
                   a window-wide strip: the count and the percentage are short
                   and belong together, a chapter title is a sentence and gets
                   the line under them rather than a truncation. */
                <IconButton
                  aria-label={text("reader.page_info")}
                  className="shrink-0 text-ink-faint hover:text-ink"
                  title={
                    <span className="block">
                      <span className="block">
                        {pageInfo.page !== undefined && pageInfo.pages !== undefined && (
                          <>
                            <span className="font-semibold text-ink">
                              {text("reader.page_of", { page: pageInfo.page, total: pageInfo.pages })}
                            </span>
                            <span className="text-ink-faint"> · </span>
                          </>
                        )}
                        <span className="text-ink-mute">
                          {text("library.progress", { percent: pageInfo.percent })}
                        </span>
                      </span>
                      <span className="mt-0.5 block text-ink">{pageInfo.chapterTitle}</span>
                    </span>
                  }
                >
                  <InfoIcon />
                </IconButton>
              )}
            </>
          )}
          </div>
        }
        trailing={
          <>
            {screen === "reader" && (
              <>
                {/* Books' pair: "AA" for how the page is set, a lens for
                    finding words in it. Size, pages/scroll and the finer
                    choices live behind AA; the appearance switch stands
                    beside them while the column is folded (owner, 06/09;
                    the column's foot carries it otherwise). */}
                <IconButton
                  data-popover-trigger
                  /* The tooltip follows focus, and a mouse click leaves the
                     button focused - so the tip sat over the panel it had
                     just opened (owner's screenshot, 06/09). Let it go. */
                  onClick={(event) => {
                    event.currentTarget.blur();
                    setReadingSettingsOpen((value) => !value);
                  }}
                  aria-label={text("reader.settings")}
                  title={text("reader.settings")}
                  className={readingSettingsOpen ? "text-ink" : ""}
                >
                  <ReadingSettingsIcon />
                </IconButton>
                <IconButton
                  onClick={(event) => {
                    event.currentTarget.blur();
                    setReadingSettingsOpen(false);
                    dispatchSide({ type: "show", tab: "search" });
                  }}
                  aria-label={text("reader.search")}
                  title={text("reader.search")}
                  className={sideTab === "search" ? "text-ink" : ""}
                >
                  <SearchIcon />
                </IconButton>
              </>
            )}
          {/* A home screen's own actions (the shelf's import and Apple Books
              buttons) land here through a portal, beside the screen's title
              the way a book's actions stand beside its. */}
          {tab === "library" && !openBook && (
            <span ref={setActionsSlot} className="contents" />
          )}
          {/* What the column's foot carries - the hub, the appearance, the
              language - is here only while the column is folded: one place
              at a time (HIG 3.16). A book's toolbar takes the appearance
              switch alone (owner, 06/09: beside AA; 16/09: "tối ưu UI tuỳ
              layout") - the hub and the language are one unfold away. */}
          {!sideOpen && (screen === "reader" && openBook ? themeSwitch : chrome)}
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
              prefs={prefs}
              sidebarTab={sideOpen ? side.tab : null}
              sidebarSlot={sideOpen ? sideSlot : null}
              reveal={reveal}
              notesFocus={notesFocus}
              onShowNotes={(focus) => {
                setNotesFocus(focus);
                dispatchSide({ type: "show", tab: "notes" });
              }}
              size={readingSize}
              onSegments={setSegments}
              onReadFrom={(segmentId) => { void readBookFrom(segmentId); }}
              onPageInfo={setPageInfo}
              onSelection={setSelection}
            />
          ) : (
            <Library
              onOpen={(book) => { setPosition(null); setOpenBook(book); }}
              onPaste={() => setTab("paste")}
              actionsSlot={actionsSlot}
            />
          )
        ) : tab === "external" ? (
          <External
            history={externalHistory}
            onClearHistory={() => setExternalHistory([])}
            status={externalStatus}
            shortcut={accelerator}
            onChangeShortcut={changeShortcut}
            /* `position` is app-wide; it only names a part of a SCANNED
               passage while a scan is what is playing. */
            readingAt={origin?.kind === "external" ? readingAt : null}
            position={position}
            onReplay={(entry) => {
              onPlayer({ type: "start" });
              setOrigin({ kind: "external" });
              setReadingAt(entry.at);
              current.current = { kind: "text", text: entry.text };
              setPosition(null);
              void invoke("read_selection_text", {
                text: entry.text,
                segmentId: null,
                voiceId,
                rate,
              }).catch((error) => onPlayer({ type: "failed", error: String(error) }));
            }}
            /* The reader's own way in: the same "read from here" a book's
               paragraph offers, on a passage that was never a book. */
            onReadPart={(entry, segmentId) => {
              onPlayer({ type: "start" });
              setOrigin({ kind: "external" });
              setReadingAt(entry.at);
              current.current = { kind: "text", text: entry.text };
              setPosition(segmentId);
              void invoke("read_selection_text", {
                text: entry.text,
                segmentId,
                voiceId,
                rate,
              }).catch((error) => onPlayer({ type: "failed", error: String(error) }));
            }}
          />
        ) : tab === "transfer" ? (
          <Transfer />
        ) : tab === "paste" ? (
          <section className="shell-inset flex min-h-0 flex-1 flex-col">
            <p className="m-0 text-sm text-ink-mute">
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
        {/* A reading that stopped says WHY, in a whole sentence, across the
            whole bar. It used to be a chip in the right-hand column under
            `truncate`: the engine names its failures precisely and eight
            sentences were written for those names, and what reached the
            reader was `voice_failed: quota: You exceeded...` with the end cut
            off. A failure that has just cost somebody money is the one thing
            that has earned the room (owner's "đừng hiện quá nhiều thông tin"
            is about what is FINE, not about what went wrong).

            Outside `footerRow` on purpose: the panels hang off the measured
            inset of the CONTROLS, so a wrapped error line must not push them
            up. The bar's own height is observed, so it grows to fit. */}
        {player.error && (() => {
          const fault = readingFault(player.error);
          const key = faultKey(fault);
          return (
            <div className="relative z-10 px-6 pt-3">
              <Notice tone="error">{key ? text(key) : engineMessage(fault.raw)}</Notice>
            </div>
          );
        })()}
        {/* Same height as the header (76px): the frost's room sits on the
            inner edge of each bar - the header's bottom, the footer's top
            (owner, 02/09: "tương đồng với header"). */}
        <div ref={footerRow} className="relative z-10 grid min-h-[76px] grid-cols-[1fr_auto_1fr] items-center gap-2 px-6 pb-4 pt-6">
          {/* Left: the other way in. Middle: what a click does. Right: what
              the voice is up to. A grid keeps the middle in the middle
              whatever the sides say - and gives the bar its height (an
              absolute group gave it none: 40px, owner 02/09). */}
          {/* The side columns STRETCH to their track (no `justify-self-*`): a
              grid item aligned to an edge takes its content's width and, when
              the track is narrower, spills across the neighbouring column -
              which is how the voice chip slid under the transport at the
              narrowest window (owner, 06/09). Stretched, the column is exactly
              the track, and what is inside shrinks and truncates. */}
          <div className="flex min-w-0 items-center gap-2">
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
                  <ArrowLeftIcon />
                  {text("player.return")}
                </Button>
              </>
            )}
          </div>
          {/* The transport keeps an open panel open (owner, 10/09): these
              buttons act ON the reading the panel is about, so treating a
              pause as "the reader went back to the book" was wrong. */}
          <div data-keeps-popover className="flex items-center gap-2 justify-self-center">
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
                    onMouseEnter={(event) => setResumeTip(anchor(event.currentTarget))}
                    onMouseLeave={() => setResumeTip(null)}
                    onFocusCapture={(event) => setResumeTip(anchor(event.currentTarget))}
                    onBlurCapture={() => setResumeTip(null)}
                  >
                    <Button
                      size="lg"
                      variant={selection ? "secondary" : "primary"}
                      /* A paid voice cannot be started until its price is
                         known: the owner's rule (04/09) is that the figure
                         lives IN this button, so pressing it before the
                         figure arrives would be spending money the button
                         had not yet quoted. */
                      disabled={startDisabled || (pricing && estimate === null)}
                      onClick={() => {
                        if (screen === "reader") void readBookFrom(null);
                        else void startReading();
                      }}
                    >
                      {/* The speaker with a sparkle - the owner's own
                          "ai-speaker" glyph (14/09) - on the button that
                          STARTS a reading: a voice about to speak, which is
                          what this button does. The transport keeps the
                          plain play for resuming. */}
                      <AiSpeakerIcon />
                      {/* The words travel together, inset 4px from the icon
                          and from the edge. A `span` rather than the `div`
                          asked for: a button may only contain phrasing
                          content, and as a flex item the two lay out the
                          same. It keeps the button's own `gap-1.5` inside
                          itself, or grouping would close the space between
                          the label and the figure. */}
                      <span className="inline-flex items-center gap-1.5 px-1">
                        {screen !== "reader"
                          ? text("paste.read")
                          : pageInfo?.resumeChapterTitle
                            ? text("player.play_resume")
                            : pageInfo
                              ? text("player.play_start")
                              : text("player.play")}
                        {pricing && (
                          <span className="font-normal">
                            {estimateFailed
                              ? `· ${text("cost.unavailable")}`
                              : estimate === null
                                ? `· ${text("cost.measuring")}`
                                : buttonCost(estimate) &&
                                /* Which promise the figure can carry lives in
                                   `costPhrase`: a ceiling over a scope, an
                                   approximation where the provider bills
                                   something the text cannot be counted into,
                                   or the bare number for pasted text. */
                                (costPhrase(estimate) === "at_most"
                                  ? `· ${text("cost.at_most", { usd: buttonCost(estimate) })}`
                                  : costPhrase(estimate) === "about"
                                    ? `· ${text("cost.about", { usd: buttonCost(estimate) })}`
                                    : `· ${buttonCost(estimate)}`)}
                          </span>
                        )}
                      </span>
                    </Button>
                    {resumeTip && screen === "reader" && pageInfo?.resumeExcerpt && pageInfo.resumeSegmentId && createPortal(
                      /* Drawn on the BODY, hung from the button's measured
                         top edge. Kept inside the footer it could never win:
                         the cost and settings panels are siblings of
                         `<footer>` at the same z and render after it, so 21px
                         of this panel's head sat under an open one whatever
                         z-index it was given - a child cannot outrank its own
                         stacking context (owner, 04/09: "cho hover của button
                         đọc đè lên trên cùng chứ đừng đổi popover"). The
                         panels are left exactly as they are.

                         Still a React child of the hovering span, so the
                         pointer moving into it does not read as leaving the
                         group; and `pb-2` still rides inside this element, so
                         the 8px it has to cross on the way up belongs to the
                         panel rather than to whatever is behind it. */
                      <span
                        className="fixed z-50 block -translate-x-1/2 -translate-y-full pb-2"
                        style={{ left: resumeTip.centre, top: resumeTip.top }}
                      >
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
                              setResumeTip(null);
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
                      </span>,
                      document.body,
                    )}
                  </span>
                )}
                {/* Everything else about the money is one press away, not on
                    the outside of the app (owner, 04/09: "đừng hiện quá
                    nhiều thông tin ra ngoài, nếu cần thì ẩn chúng đi"). */}
                {pricing && (
                  <IconButton
                    onClick={() => {
                      // One floating layer at a time. The settings panel and
                      // this one both stand over the book in the same place,
                      // so opening this on top of that put a panel where the
                      // one underneath could not be read or reached - and
                      // even the tooltip landed across it (owner, 04/09).
                      setSettingsOpen(false);
                      setVoicesOpen(false);
                      setCostOpen((open) => !open);
                    }}
                    aria-label={text("cost.open")}
                    title={text("cost.open")}
                    data-popover-trigger
                    className={costOpen ? "text-ink" : ""}
                  >
                    <CoinIcon />
                  </IconButton>
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
          <div className="flex min-w-0 items-center justify-end gap-2">
            {reading !== "idle" && player.warming && (
              <Notice className="min-w-0 truncate whitespace-nowrap">{text("player.warming")}</Notice>
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
                  setCostOpen(false);
                  setSettingsOpen((value) => !value);
                }}
                aria-label={text("player.settings_open")}
                title={
                  hint
                    ? text(hint.kind === "switch" ? "hint.mismatch" : "hint.no_voice", { language: languageName(hint.content) })
                    : text("player.settings_open")
                }
                /* It toggles, so the outside-click that closes the panel has
                   to leave this button alone - see `useDismiss`. */
                data-popover-trigger
                /* `min-w-0` + `truncate`, never `shrink-0`: at the narrowest
                   window this is the one thing in the footer allowed to give
                   way, so it shortens to "Phạm T…" and finally to its icon
                   instead of sliding under the transport (owner, 06/09). */
                className={`min-w-0 ${settingsOpen ? "text-ink" : ""}`}
              >
                <VoiceIcon />
                {/* The nudge, at chip size: the text in front of the reader
                    is in a language this voice was not made for. The words
                    are in the title above and in the panel it opens. */}
                {hint && (
                  <SuggestionDot />
                )}
                {/* A reminder, not a description: the name that tells this
                    voice apart from the others on offer, and the speed only
                    when it is not the plain 1×. Without a voice the old chip
                    read " · 1.25×", a separator with nothing on its left; a
                    paid voice's id is `openai:gpt-4o-mini-tts:alloy`, an address, so
                    the chip shows what the catalogue calls it. */}
                {(voiceId || rate !== 1) && (
                  <span className="min-w-0 truncate font-normal">
                    {voiceId
                      ? chipName(
                          voices.find((voice) => voice.id === voiceId) ?? { id: voiceId, label: voiceId },
                          offeredVoices(voices, shortlist, voiceId),
                        )
                      : ""}
                    {voiceId && rate !== 1 ? " · " : ""}
                    {rate !== 1 ? `${rate}×` : ""}
                  </span>
                )}
              </Button>
            )}
          </div>
        </div>
      </footer>
      )}
      {readingSettingsOpen && screen === "reader" && openBook && (
        <ReadingSettingsPanel
          size={readingSize}
          sizes={READING_SIZES}
          onSize={changeReadingSize}
          mode={readingMode}
          onMode={chooseReadingMode}
          appearance={appearance}
          onAppearance={chooseAppearance}
          prefs={prefs}
          onPrefs={choosePrefs}
          onClose={() => setReadingSettingsOpen(false)}
        />
      )}
      {costOpen && pricing && (
        <CostPanel
          estimate={estimate}
          failed={estimateFailed}
          /* Pasted text has no chapters, so there is no scope to choose -
             the whole of what was pasted is what gets read. Hiding the row
             beats offering a choice that does nothing. */
          scoped={openBook !== null}
          scope={scope}
          budget={budget}
          spent={spent}
          onScope={changeScope}
          onBudget={changeBudget}
          onClose={() => setCostOpen(false)}
        />
      )}
      {settingsOpen && speechSettings && (
        <SettingsPanel
          /* The whole catalogue and the shortlist: the panel narrows to the
             language's voices itself - the marked ones plus the one in use,
             the same list the mid-reading switcher shows (owner, 03/09: one
             list means one list everywhere; the way to add to it is Quản
             lý giọng). */
          voices={voices}
          shortlist={shortlist}
          voiceId={voiceId}
          rate={rate}
          rates={RATES}
          reading={reading !== "idle"}
          shortlisted={shortlist.length}
          voicesError={voicesError}
          readingLanguage={readingLanguage}
          contentLanguage={contentLanguage}
          hint={hint}
          models={models}
          keysSet={keysSet}
          scope={scope}
          budget={budget}
          spent={spent}
          onReadingLanguage={switchReadingLanguage}
          onScope={changeScope}
          onBudget={changeBudget}
          onVoice={switchVoice}
          onRate={rememberRate}
          onManageVoices={() => { setSettingsOpen(false); setVoicesOpen(true); }}
          onOpenHub={() => { setSettingsOpen(false); setHubOpen(true); }}
          /* Just close. This used to re-list the catalogue on the way out,
             in case a key had been added while the panel was open - but
             `saveKey` already re-lists the moment a key is accepted, and
             ElevenLabs' catalogue is a live network call with no cache
             behind it. Now that a click on the book closes this panel, that
             would be a request to their servers every time somebody
             dismissed it. */
          onClose={() => setSettingsOpen(false)}
        />
      )}
      {hubOpen && (
        <SourcesHub
          models={models}
          voices={voices}
          keysSet={keysSet}
          onSaveKey={saveKey}
          reading={reading !== "idle"}
          onClose={() => setHubOpen(false)}
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
          bookLanguage={openBook?.language ?? null}
          detectedLanguage={openBook?.language_detected ?? null}
          onSetLanguage={setBookLanguage}
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
    </div>
  );
}
