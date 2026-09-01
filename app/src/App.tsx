import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { AppTabs } from "./ui/AppTabs";
import { Toolbar } from "./ui/patterns";
import { External, type ExternalEntry } from "./screens/External";
import { Button, Field, Notice, SectionTitle, Select, Textarea } from "./ui/controls";
import { ModelPanel } from "./ui/ModelPanel";
import { useShortcut } from "./ui/useShortcut";
import { Library, type LibraryBook } from "./screens/Library";
import { Reader } from "./screens/Reader";
import { Setup } from "./screens/Setup";
import { Transfer } from "./screens/Transfer";
import { currentLanguage, setLanguage, text, type Language } from "./i18n";

const PASTE_LIMIT = 100_000;
const RATES = [0.5, 0.75, 1.0, 1.15, 1.2, 1.25, 1.5, 2.0];

type Voice = { id: string; label: string };
type ReadingState = "idle" | "reading" | "paused";
type ModelGate = "checking" | "setup" | "ready";

/** Mirror macOS appearance onto the DS token switch. */
function useAppearance() {
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      document.documentElement.dataset.theme = media.matches ? "dark" : "light";
    };
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, []);
}

export default function App() {
  useAppearance();
  const [tab, setTab] = useState("paste");
  const [voices, setVoices] = useState<Voice[]>([]);
  const [voiceId, setVoiceId] = useState<string>("");
  const [rate, setRate] = useState(1.0);
  const [reading, setReading] = useState<ReadingState>("idle");
  const [content, setContent] = useState("");
  const [openBook, setOpenBook] = useState<LibraryBook | null>(null);
  const [segments, setSegments] = useState<string[]>([]);
  const [position, setPosition] = useState<string | null>(null);
  const [externalHistory, setExternalHistory] = useState<ExternalEntry[]>([]);
  const [externalStatus, setExternalStatus] = useState<string | null>(null);
  const [readError, setReadError] = useState<string | null>(null);
  const [modelPrecision, setModelPrecision] = useState<string | null>(null);
  const [modelPanel, setModelPanel] = useState(false);
  const [gate, setGate] = useState<ModelGate>("checking");
  const [warming, setWarming] = useState(false);
  const [language, setLanguageState] = useState<Language>(currentLanguage());

  const applyLanguage = useCallback((next: Language) => {
    setLanguage(next);
    setLanguageState(next);
    void invoke("engine_request", {
      method: "config.set",
      params: { key: "ui_language", value: next },
    }).catch(() => undefined);
  }, []);

  const { accelerator, change: changeShortcut } = useShortcut();
  const speech = useRef({ voiceId: "", rate: 1.0 });
  speech.current = { voiceId, rate };

  useEffect(() => {
    invoke<Voice[]>("engine_voices")
      .then((list) => {
        setVoices(list);
        if (list.length && !voiceId) setVoiceId(list[0].id);
      })
      .catch(console.error);
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
        setReading("idle");
        // A reading that failed must say so; a silent stop reads as a bug.
        setReadError(event.payload.ok ? null : event.payload.error ?? null);
      },
    );
    const moved = listen<{ segment_id: string }>("reading:position", (event) =>
      setPosition(event.payload.segment_id),
    );
    const started = listen("reading:started", () => setWarming(false));
    // The global shortcut hands the captured text to the webview, which owns
    // the voice and rate, and the webview asks the engine to speak it.
    const external = listen<{ text: string }>("reading:external", (event) => {
      const captured = event.payload.text;
      setExternalHistory((history) =>
        [{ at: Date.now(), text: captured }, ...history].slice(0, 50),
      );
      setReading("reading");
      invoke("read_selection_text", {
        text: captured,
        voiceId: speech.current.voiceId,
        rate: speech.current.rate,
      }).catch((error) => {
        console.error(error);
        setReading("idle");
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
    setReading("reading");
    setWarming(true);
    try {
      await invoke("read_text", { text: content, voiceId, rate });
    } catch (error) {
      console.error(error);
      setReading("idle");
    }
  }, [content, voiceId, rate]);

  const readBookFrom = useCallback(async (segmentId: string | null) => {
    if (!openBook || !voiceId) return;
    setReading("reading");
    setWarming(true);
    try {
      await invoke("read_book", {
        bookId: openBook.id, segmentId, voiceId, rate,
      });
    } catch (error) {
      console.error(error);
      setReading("idle");
    }
  }, [openBook, voiceId, rate]);

  const readNeighbour = useCallback(async (step: number) => {
    const anchor = position ?? openBook?.segment_id ?? null;
    if (anchor === null) return;
    const index = segments.indexOf(anchor) + step;
    if (index < 0 || index >= segments.length) return;
    await invoke("stop_reading");
    await readBookFrom(segments[index]);
  }, [segments, position, openBook, readBookFrom]);

  const stopReading = useCallback(async () => {
    await invoke("stop_reading");
    setReading("idle");
  }, []);

  const togglePause = useCallback(async () => {
    if (reading === "reading") {
      await invoke("pause_audio");
      setReading("paused");
    } else if (reading === "paused") {
      await invoke("resume_audio");
      setReading("reading");
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

  const tabs = useMemo(() => ([
    { value: "library", label: text("nav.library") },
    { value: "paste", label: text("nav.paste") },
    { value: "external", label: text("nav.external") },
    { value: "transfer", label: text("nav.transfer") },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ]), [language]);

  const overLimit = content.length > PASTE_LIMIT;
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
    canStart || speechSettings || reading !== "idle" || readError !== null;

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
    <div key={language} className="flex h-screen flex-col px-6 pt-4 pb-0">
      <Toolbar
        leading={
          <AppTabs
            ariaLabel={text("aria.workspace")}
            items={tabs}
            value={tab}
            onChange={setTab}
          />
        }
        trailing={
          <Select
            pill
            aria-label={text("aria.language")}
            value={language}
            onChange={(event) => applyLanguage(event.target.value as Language)}
          >
            <option value="vi">🇻🇳 VI</option>
            <option value="en">🇬🇧 EN</option>
          </Select>
        }
      />

      <main className="flex min-h-0 flex-1 flex-col pt-5">
        {tab === "library" ? (
          openBook ? (
            <Reader
              bookId={openBook.id}
              currentSegment={position}
              onBack={() => { setOpenBook(null); setSegments([]); }}
              onSegments={setSegments}
              onReadFrom={(segmentId) => { void readBookFrom(segmentId); }}
              onReadSelection={(selected) => {
                setReading("reading");
                void invoke("read_selection_text", {
                  text: selected, voiceId, rate,
                }).catch(() => setReading("idle"));
              }}
            />
          ) : (
            <Library onOpen={(book) => { setPosition(null); setOpenBook(book); }} onPaste={() => setTab("paste")} />
          )
        ) : tab === "external" ? (
          <External
            history={externalHistory}
            status={externalStatus}
            shortcut={accelerator}
            onChangeShortcut={changeShortcut}
            onReplay={(entry) => {
              setReading("reading");
              void invoke("read_selection_text", {
                text: entry.text,
                voiceId,
                rate,
              }).catch(() => setReading("idle"));
            }}
          />
        ) : tab === "transfer" ? (
          <Transfer />
        ) : tab === "paste" ? (
          <section className="flex min-h-0 flex-1 flex-col">
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
            </div>
          </section>
        ) : (
          <section className="flex flex-1 items-center justify-center text-sm text-ink-mute">
            {text("milestone.later")}
          </section>
        )}
      </main>

      {showFooter && (
      <footer className="-mx-6 mt-2 px-6 pb-4 pt-2">
        <div className="flex items-center gap-2">
          {reading === "idle" ? (
            canStart && (
              <Button
                variant="primary"
                className="px-5"
                disabled={startDisabled}
                onClick={() => {
                  if (screen === "reader") void readBookFrom(null);
                  else void startReading();
                }}
              >
                {screen === "reader" ? text("player.play") : text("paste.read")}
              </Button>
            )
          ) : (
            <>
              <Button className="px-4" onClick={togglePause}>
                {reading === "paused" ? text("player.resume") : text("player.pause")}
              </Button>
              <Button className="px-4" onClick={stopReading}>
                {text("player.stop")}
              </Button>
              {screen === "reader" && (
                <>
                  <Button className="px-3" onClick={() => { void readNeighbour(-1); }}>
                    {text("player.previous")}
                  </Button>
                  <Button className="px-3" onClick={() => { void readNeighbour(1); }}>
                    {text("player.next")}
                  </Button>
                </>
              )}
            </>
          )}
          {reading !== "idle" && warming && (
            <Notice>{text("player.warming")}</Notice>
          )}
          {readError && (
            <Notice tone="error" className="min-w-0 truncate">
              {readError}
            </Notice>
          )}
          <div className="flex-1" />
          {speechSettings && modelPrecision && (
            <Field label={text("player.quality")}>
              <Button
                className="px-3 font-normal"
                onClick={() => setModelPanel((value) => !value)}
                title={text("model.quality")}
              >
                {modelPrecision === "fp32"
                  ? text("model.quality_maximum")
                  : text("model.quality_standard")}
              </Button>
            </Field>
          )}
          {speechSettings && (
            <>
              <Field label={text("player.voice")}>
                <Select
                  value={voiceId}
                  onChange={(event) => setVoiceId(event.target.value)}
                >
                  {voices.map((voice) => (
                    <option key={voice.id} value={voice.id}>{voice.label}</option>
                  ))}
                </Select>
              </Field>
              <Field label={text("player.speed")} className="ml-2">
                <Select
                  value={rate}
                  onChange={(event) => setRate(Number(event.target.value))}
                >
                  {RATES.map((value) => (
                    <option key={value} value={value}>{value}×</option>
                  ))}
                </Select>
              </Field>
            </>
          )}
        </div>
      </footer>
      )}
      {modelPanel && (
        <ModelPanel
          reading={reading !== "idle"}
          onClose={() => {
            setModelPanel(false);
            invoke<Voice[]>("engine_voices")
              .then((list) => {
                setVoices(list);
                if (list.length && !list.some((voice) => voice.id === voiceId)) {
                  setVoiceId(list[0].id);
                }
              })
              .catch(() => undefined);
            invoke<{ result: { precision: string | null } }>("engine_request", {
              method: "model.status",
              params: {},
            })
              .then((reply) => setModelPrecision(reply.result.precision))
              .catch(() => undefined);
          }}
        />
      )}
    </div>
  );
}
