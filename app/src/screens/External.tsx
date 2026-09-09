import { useEffect, useRef, useState } from "react";
import {
  checkAccessibilityPermission,
  requestAccessibilityPermission,
} from "tauri-plugin-macos-permissions-api";
import { invoke } from "@tauri-apps/api/core";
import { openUrl } from "@tauri-apps/plugin-opener";
import { text, type TextKey } from "../i18n";
import { Button, IconButton, Kbd, Notice, SectionTitle, Surface } from "../ui/controls";
import { ChevronDownIcon, InfoIcon, PlayIcon } from "../ui/icons";
import { currentPart, isOpen, summarise } from "../ui/scanHistory";
import { comboFromEvent, displayShortcut } from "../ui/useShortcut";

export type ExternalEntry = { at: number; text: string };

type ScanPart = { segment_id: string; text: string };

/** One captured passage, openable, with the voice's place marked in it.
 *
 * The list used to clamp each passage to two lines and hang the replay
 * tooltip on the text, so hovering the words offered to read them again
 * instead of showing them. Scanning is how this app is USED - the passage
 * is the content, not a label for it (owner, 09/09). */
function ScanEntry({
  entry,
  open,
  current,
  onToggle,
  onReplay,
  onReadPart,
}: {
  entry: ExternalEntry;
  open: boolean;
  current: string | null;
  onToggle: () => void;
  onReplay: () => void;
  onReadPart: (segmentId: string) => void;
}) {
  /* Split by the ENGINE, never here. The ids painted below arrive in
   * `reading:position`, and the engine's `text.parts` answers from the same
   * builder the reading speaks from - a second splitting rule in the shell
   * would drift and put the marker on the wrong paragraph. */
  const [parts, setParts] = useState<ScanPart[] | null>(null);
  const here = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open || parts !== null) return;
    let alive = true;
    void invoke<{ result: { parts: ScanPart[] } }>("engine_request", {
      method: "text.parts",
      params: { text: entry.text },
    })
      .then((reply) => {
        if (alive) setParts(reply.result.parts);
      })
      // The engine can be busy or gone; the words were captured either way,
      // and hiding them because a split failed would take away the one
      // thing this screen is for.
      .catch(() => {
        if (alive) setParts([{ segment_id: "", text: entry.text }]);
      });
    return () => {
      alive = false;
    };
  }, [open, parts, entry.text]);

  useEffect(() => {
    if (current) here.current?.scrollIntoView({ block: "nearest" });
  }, [current]);

  return (
    /* No fill of its own. `band` marks where the voice is, and measured
       against a `wash/40` card (09/09) the two were six per cent apart -
       the marker all but gone. The reader's line is painted on the plain
       page for exactly this reason; one colour means current position, and
       nothing sits under it. */
    <div className="rounded-2xl">
      <div className="flex items-center gap-1 pr-1.5">
        <button
          onClick={onToggle}
          title={open ? text("external.close_text") : text("external.open_text")}
          className="flex min-w-0 flex-1 items-center gap-2 rounded-2xl px-3 py-2 text-left"
        >
          <ChevronDownIcon
            className={`shrink-0 text-ink-mute transition-transform ${
              open ? "" : "-rotate-90"
            }`}
          />
          <span className={`min-w-0 flex-1 text-sm leading-snug ${open ? "font-semibold" : "truncate"}`}>
            {open ? summarise(entry.text, 40) : summarise(entry.text)}
          </span>
        </button>
        <IconButton title={text("external.replay")} onClick={onReplay}>
          <PlayIcon />
        </IconButton>
      </div>
      {open && (
        <div className="flex flex-col gap-0.5 px-2 pb-2">
          {parts === null ? (
            <p className="m-0 px-2 py-1 text-sm text-ink-mute">
              {text("external.parts_loading")}
            </p>
          ) : (
            parts.map((part, index) => (
              <button
                key={part.segment_id || index}
                ref={part.segment_id === current ? here : undefined}
                onClick={() => part.segment_id && onReadPart(part.segment_id)}
                /* The fallback block (the engine could not be asked) has no
                   id, so it cannot be read from. It must not offer to be:
                   a tooltip promising something the click will not do is
                   the same lie the old replay tooltip told. */
                title={part.segment_id ? text("external.read_from_here") : undefined}
                className={`rounded-2xl px-2 py-1 text-left text-sm leading-relaxed whitespace-pre-line transition-colors ${
                  part.segment_id === current ? "bg-band" : ""
                } ${part.segment_id ? "hover:bg-wash" : "cursor-default"}`}
              >
                {part.text}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

const ACCESSIBILITY_PANE =
  "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility";

export function External({
  history,
  status,
  shortcut,
  readingAt,
  position,
  onChangeShortcut,
  onReplay,
  onReadPart,
  onClearHistory,
}: {
  history: ExternalEntry[];
  status: string | null;
  shortcut: string;
  /** Which captured passage the voice is in, or null when it is elsewhere. */
  readingAt: number | null;
  /** The part id the voice has reached. One value for the whole app, so it
   * only means something once `readingAt` says which passage it is in. */
  position: string | null;
  onChangeShortcut: (accelerator: string) => Promise<void>;
  onReplay: (entry: ExternalEntry) => void;
  onReadPart: (entry: ExternalEntry, segmentId: string) => void;
  onClearHistory: () => void;
}) {
  const [granted, setGranted] = useState<boolean | null>(null);
  const [asked, setAsked] = useState(false);
  const [toggled, setToggled] = useState<Record<number, boolean>>({});
  const [recording, setRecording] = useState(false);
  const [shortcutError, setShortcutError] = useState(false);

  useEffect(() => {
    if (!recording) return;
    const onKey = (event: KeyboardEvent) => {
      event.preventDefault();
      event.stopPropagation();
      if (event.key === "Escape") {
        setRecording(false);
        return;
      }
      const combo = comboFromEvent(event);
      if (!combo) return;
      setRecording(false);
      setShortcutError(false);
      onChangeShortcut(combo).catch(() => setShortcutError(true));
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [recording, onChangeShortcut]);

  useEffect(() => {
    checkAccessibilityPermission().then(setGranted).catch(() => setGranted(null));
  }, []);

  const statusMessage =
    status && status !== "reading"
      ? text(`status.${status}` as TextKey)
      : status === "reading"
        ? text("external.reading")
        : null;

  return (
    /* One column, not two. The left column used to give a one-time setup -
       a shortcut you learn once and three steps you read once - the same
       413 px the passages themselves got (measured at a 1060 px window,
       09/09). Scanning is what this screen DOES; the setup is what it
       needed once. So the setup is one bar across the top and the passages
       have the width (owner, 09/09). */
    <section className="shell-inset flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <SectionTitle>{text("external.title")}</SectionTitle>
        <span className="text-sm text-ink-mute">{text("external.shortcut")}</span>
        {recording ? (
          <span className="text-sm text-ink-mute">
            {text("external.shortcut_recording")}
          </span>
        ) : (
          <Kbd>{displayShortcut(shortcut)}</Kbd>
        )}
        <Button size="sm" onClick={() => setRecording((value) => !value)}>
          {text("external.shortcut_change")}
        </Button>
        {/* Once it works, how-to is reference: on the icon, not on the page.
            Before it works, the same words are the task itself and stay
            open below. */}
        {granted === true && (
          <IconButton
            title={
              <span className="block max-w-[44ch] whitespace-pre-line text-left">
                {text("external.steps")}
              </span>
            }
          >
            <InfoIcon />
          </IconButton>
        )}
        <span className="flex-1" />
        {history.length > 0 && (
          /* The Qt shell could empty this list; the rewrite dropped the
             action until the parity audit found it (2026-09-02). */
          <Button variant="ghost" size="sm" onClick={onClearHistory}>
            {text("external.history_clear")}
          </Button>
        )}
      </div>

      {recording && (
        <p className="m-0 mt-2 max-w-[52ch] text-sm text-ink-mute">
          {text("external.shortcut_hint")}
        </p>
      )}
      {shortcutError && (
        <Notice tone="error" className="mt-2 max-w-[52ch]">
          {text("external.shortcut_taken")}
        </Notice>
      )}
      {statusMessage && (
        <Notice tone="error" className="mt-3 max-w-[52ch]">
          {statusMessage}
        </Notice>
      )}

      {granted === false && (
        <Surface className="mt-4 max-w-[60ch] p-4">
          <p className="m-0 text-sm leading-relaxed text-ink-mute">
            {text("external.permission_note")}
          </p>
          <div className="mt-3 flex gap-2">
            <Button
              variant="primary"
              onClick={() => {
                setAsked(true);
                void requestAccessibilityPermission();
              }}
            >
              {text("external.open_settings")}
            </Button>
            <Button className="px-3" onClick={() => void openUrl(ACCESSIBILITY_PANE)}>
              {text("external.open_system_settings")}
            </Button>
          </div>
          {asked && (
            <p className="m-0 mt-3 text-sm font-medium">
              {text("external.permission_restart")}
            </p>
          )}
        </Surface>
      )}
      {granted !== true && (
        <p className="m-0 mt-4 max-w-[60ch] whitespace-pre-line text-xs leading-relaxed text-ink-mute">
          {text("external.steps")}
        </p>
      )}

      {history.length === 0 ? (
        <p className="m-0 mt-4 text-sm text-ink-mute">
          {text("external.history_empty")}
        </p>
      ) : (
        /* Capped at a readable measure rather than stretched: the passages
           are prose, and prose that runs the whole window is harder to
           follow than the narrow column this replaced. */
        <div className="mt-3 flex min-h-0 max-w-[80ch] flex-1 flex-col gap-1 overflow-y-auto">
          {history.map((entry) => (
            <ScanEntry
              key={entry.at}
              entry={entry}
              open={isOpen(entry.at, readingAt, toggled)}
              current={currentPart(entry.at, readingAt, position)}
              onToggle={() =>
                setToggled((was) => ({
                  ...was,
                  [entry.at]: !isOpen(entry.at, readingAt, was),
                }))
              }
              onReplay={() => onReplay(entry)}
              onReadPart={(segmentId) => onReadPart(entry, segmentId)}
            />
          ))}
        </div>
      )}
    </section>
  );
}
