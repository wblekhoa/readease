import { useCallback, useEffect, useMemo, useReducer, useRef, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { AppTabs } from "./ui/AppTabs";
import { readingFault, faultKey } from "./ui/voiceFault";
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
  BookClosedIcon,
  StopIcon,
  PagesIcon,
  ScrollIcon,
  InfoIcon,
  SlidersIcon,
  CoinIcon,
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
import { CostPanel } from "./ui/CostPanel";
import {
  buttonCost,
  isPaidVoice,
  PROVIDERS,
  rememberScope,
  storedScope,
  type Estimate,
} from "./ui/readingCost";
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

/** Where a layer hung from a control gets pinned: the control's centre and
 * its top edge, in viewport coordinates. Read once when the layer opens - a
 * hover panel that outlived a scroll would be pointing at nothing anyway, and
 * it closes when the pointer leaves. */
function anchor(element: HTMLElement) {
  const rect = element.getBoundingClientRect();
  return { centre: rect.left + rect.width / 2, top: rect.top };
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
  const toggleReadingMode = useCallback(() => {
    setReadingMode((current) => {
      const next = current === "pages" ? "scroll" : "pages";
      rememberReadingMode(next);
      return next;
    });
  }, []);

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
  const rememberVoice = useCallback((id: string) => {
    setVoiceId(id);
    remember("voice", id);
  }, [remember]);
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
    const result = await invoke<{ ok: boolean; code?: string }>("engine_request", {
      method: "config.verify_key",
      params: { provider, value: key },
    }).catch(() => ({ ok: false, code: "network" }));
    if (result.ok) {
      const list = await invoke<Voice[]>("engine_voices").catch(() => [] as Voice[]);
      setVoices(list);
    }
    setKeysSet((current) => ({ ...current, [provider]: result.ok }));
    return { ok: result.ok, code: result.code ?? null };
  }, []);

  const changeBudget = useCallback((usd: number | null) => {
    setBudget(usd);
    remember("external_voice_budget", usd === null ? "" : String(usd));
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
        <div ref={headerRow} className="relative z-10 px-6 pb-6 pt-4">
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
                <BookClosedIcon />
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
              <Notice tone="error">{key ? text(key) : fault.raw}</Notice>
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
                      {/* The same glyph the transport wears for "play", so
                          the button that STARTS a reading and the control
                          that resumes one say the same thing. Drawn in this
                          app rather than imported: DOL sources icons from DS
                          Studio's DsIcon and that registry is not consumable
                          outside the DS repo (ui/icons.tsx, same gap note as
                          ToggleButtonGroup). */}
                      <PlayIcon />
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
                                /* "tối đa" only where there IS a scope to be
                                   the ceiling OF. Pasted text has no chapters
                                   and no click-to-read: the whole of it is
                                   what gets read, so the figure is exact and
                                   hedging it would overstate the doubt. */
                                (estimate?.paid && estimate.chapters > 0
                                  ? `· ${text("cost.at_most", { usd: buttonCost(estimate) })}`
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
          <div className="flex min-w-0 items-center justify-end gap-2 justify-self-end">
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
                title={text("player.settings_open")}
                className={`shrink-0 ${settingsOpen ? "text-ink" : ""}`}
              >
                <SlidersIcon />
                {/* Without a voice the old chip read " · 1.25×", a
                    separator with nothing on its left. And a paid voice's id
                    is `openai:tts-1:alloy`, which is an address, not a name -
                    the chip shows what the catalogue calls it. */}
                <span className="font-normal">
                  {voiceId ? `${voiceName(voices.find((voice) => voice.id === voiceId)?.label ?? "") || voiceId} · ` : ""}
                  {rate}×
                </span>
              </Button>
            )}
          </div>
        </div>
      </footer>
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
          paidVoices={voices.filter((voice) => isPaidVoice(voice.id))}
          keysSet={keysSet}
          scope={scope}
          budget={budget}
          spent={spent}
          onSaveKey={saveKey}
          onScope={changeScope}
          onBudget={changeBudget}
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
