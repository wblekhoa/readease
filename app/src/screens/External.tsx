import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  checkAccessibilityPermission,
  requestAccessibilityPermission,
} from "tauri-plugin-macos-permissions-api";
import { invoke } from "@tauri-apps/api/core";
import { openUrl } from "@tauri-apps/plugin-opener";
import { text, type TextKey } from "../i18n";
import { Button, IconButton, Kbd, Notice, SectionTitle, Surface, Switch } from "../ui/controls";
import { ArrowLeftIcon, CursorTextIcon, InfoIcon, PlayIcon } from "../ui/icons";
import { EmptyState } from "../ui/patterns";
import { ScanEntry, type ExternalEntry } from "../ui/ScanEntry";
export type { ExternalEntry } from "../ui/ScanEntry";
import { currentPart, isOpen, summarise } from "../ui/scanHistory";
import { comboFromEvent, displayShortcut } from "../ui/useShortcut";

const ACCESSIBILITY_PANE =
  "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility";

export function External({
  focusAt = null,
  readingActionSlot,
  translating = false,
  history,
  status,
  shortcut,
  readingAt,
  position,
  playback,
  onTogglePlayback,
  onChangeShortcut,
  onReplay,
  onReadPart,
  onClearHistory,
}: {
  translating?: boolean;
  history: ExternalEntry[];
  focusAt?: number | null;
  readingActionSlot: HTMLElement | null;
  status: string | null;
  shortcut: string;
  /** Which captured passage the voice is in, or null when it is elsewhere. */
  readingAt: number | null;
  /** The part id the voice has reached. One value for the whole app, so it
   * only means something once `readingAt` says which passage it is in. */
  position: string | null;
  playback: "reading" | "paused" | null;
  onTogglePlayback: () => void;
  onChangeShortcut: (accelerator: string) => Promise<void>;
  onReplay: (entry: ExternalEntry) => void;
  onReadPart: (entry: ExternalEntry, segmentId: string) => void;
  onClearHistory: () => void;
}) {
  const [granted, setGranted] = useState<boolean | null>(null);
  const [asked, setAsked] = useState(false);
  /* A moment of "you have it now" after the grant is seen, then nothing:
     the card is gone and the line is not kept (owner, 19/09). */
  const [justGranted, setJustGranted] = useState(false);
  /* Following the voice, as the reader does (HIG 3.9): a scroll by hand
     turns it off, the button turns it on again and brings the part being
     read to the middle. */
  const [following, setFollowing] = useState(true);
  const [jump, setJump] = useState(0);
  const [toggled, setToggled] = useState<Record<number, boolean>>({});
  /* One passage, alone. Kept by `at` and looked up each render, so clearing
     the history takes the reader back to the list instead of leaving them
     staring at a passage that no longer exists. */
  const [alone, setAlone] = useState<number | null>(focusAt);
  const [recording, setRecording] = useState(false);
  const [shortcutError, setShortcutError] = useState(false);
  const [floating, setFloating] = useState(true);
  const [savingFloating, setSavingFloating] = useState(false);
  const [floatingError, setFloatingError] = useState(false);
  useEffect(() => {
    let alive = true;
    void invoke<boolean>("floating_controller_enabled").then((enabled) => {
      if (alive && typeof enabled === "boolean") setFloating(enabled);
    }).catch(() => undefined);
    return () => { alive = false; };
  }, []);

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

  /* Asked LIVE, not once: the grant happens in System Settings, and the
     reader comes back to this window expecting the card to be gone. So the
     question is asked again whenever the window is focused or shown, and
     every 1.5 s while the card is up (owner, 19/09: "đã cấp quyền rồi thì
     ẩn khung đó đi nhanh chóng"). macOS re-evaluates the trust on each
     call, so no relaunch is needed for the answer to change. */
  const grantedBefore = useRef<boolean | null>(null);
  useEffect(() => {
    let alive = true;
    const check = () => {
      checkAccessibilityPermission()
        .then((ok) => {
          if (!alive) return;
          if (grantedBefore.current === false && ok) {
            setAsked(false);
            setJustGranted(true);
          }
          grantedBefore.current = ok;
          setGranted(ok);
        })
        .catch(() => { if (alive) setGranted(null); });
    };
    check();
    window.addEventListener("focus", check);
    document.addEventListener("visibilitychange", check);
    const poll = granted === false ? window.setInterval(check, 1500) : null;
    return () => {
      alive = false;
      window.removeEventListener("focus", check);
      document.removeEventListener("visibilitychange", check);
      if (poll !== null) window.clearInterval(poll);
    };
  }, [granted]);
  useEffect(() => {
    if (!justGranted) return;
    const timer = window.setTimeout(() => setJustGranted(false), 3000);
    return () => window.clearTimeout(timer);
  }, [justGranted]);
  // A new reading is followed until the reader says otherwise.
  useEffect(() => { setFollowing(true); }, [readingAt]);
  const backToReading = () => {
    if (readingAt === null) return;
    setToggled((was) => ({ ...was, [readingAt]: true }));
    setFollowing(true);
    setJump((n) => n + 1);
  };
  const readingAction = status === "reading" && readingActionSlot
    ? createPortal(
        <Button variant="ghost" size="sm" onClick={backToReading}>
          {text("reader.follow")}
        </Button>,
        readingActionSlot,
      )
    : null;
  /* Only a HAND on the scroller ends the following: wheel, touch, or a
     scrolling key. The scroll event itself is not used - the app's own
     scrollIntoView fires it too. */
  const byHand = () => { if (readingAt !== null) setFollowing(false); };
  const scrollKeys = new Set(["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "]);
  const byKey = (event: React.KeyboardEvent) => { if (scrollKeys.has(event.key)) byHand(); };

  const statusMessage = translating ? text("translation.translating") :
    status && status !== "reading" ? text(`status.${status}` as TextKey) : null;

  /* Nothing captured yet: the screen has no content to be a header FOR, so
     the header stops being a header. Name, shortcut and the way in gather in
     the middle as one block - the shape the Library's empty shelf already
     uses, where the invitation IS the content (owner, 09/09). The bar goes
     back to the top the moment a passage lands. */
  const bare = history.length === 0;
  const soloEntry = history.find((entry) => entry.at === alone) ?? null;

  const setup = (
    <>
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
          aria-label={text("external.open_text")}
          title={
            <span className="block max-w-[44ch] whitespace-pre-line text-left">
              {text("external.steps")}
            </span>
          }
        >
          <InfoIcon />
        </IconButton>
      )}
    </>
  );

  const setupBar = (
    <div
      className={`flex flex-wrap items-center gap-x-3 gap-y-2 ${
        bare ? "justify-center" : ""
      }`}
    >
      {setup}
      {!bare && <span className="flex-1" />}
      {!bare && (
        /* The Qt shell could empty this list; the rewrite dropped the
           action until the parity audit found it (2026-09-02). */
        <Button variant="ghost" size="sm" onClick={onClearHistory}>
          {text("external.history_clear")}
        </Button>
      )}
    </div>
  );

  const asides = (
    <>
      <div className="flex max-w-[52ch] items-center gap-3 text-sm text-ink-mute">
        <Switch checked={floating} disabled={savingFloating} label={text("external.floating_controller")}
          onChange={(enabled) => {
            setSavingFloating(true);
            setFloatingError(false);
            void invoke("set_floating_controller_enabled", { enabled })
              .then(() => setFloating(enabled))
              .catch(() => setFloatingError(true))
              .finally(() => setSavingFloating(false));
          }} />
        <span>{text("external.floating_controller")}</span>
      </div>
      {floatingError && <Notice tone="error">{text("external.floating_error")}</Notice>}
      {recording && (
        <Notice tone="info" className="max-w-[52ch]">
          {text("external.shortcut_hint")}
        </Notice>
      )}
      {shortcutError && (
        <Notice tone="error" className="max-w-[52ch]">
          {text("external.shortcut_taken")}
        </Notice>
      )}
      {/* Reading status and the way back belong below the shared transport.
          Capture failures stay beside the shortcut that caused them. */}
      {statusMessage && (
        <Notice tone={translating ? "info" : "error"} className="max-w-[52ch]">
          {statusMessage}
        </Notice>
      )}
      {justGranted && (
        <Notice tone="ok" className="max-w-[52ch]">
          {text("external.permission_granted")}
        </Notice>
      )}
      {granted === false && (
        <Surface className="max-w-[60ch] p-4">
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
            <p className="m-0 mt-3 text-sm text-ink-mute">
              {text("external.permission_restart")}
            </p>
          )}
        </Surface>
      )}
      {granted !== true && (
        <p
          className={`m-0 max-w-[60ch] whitespace-pre-line text-xs leading-relaxed text-ink-mute ${
            bare ? "text-center" : ""
          }`}
        >
          {text("external.steps")}
        </p>
      )}
    </>
  );

  if (soloEntry) {
    return (
      <section className="flex min-h-0 flex-1 flex-col gap-2 pt-[var(--shell-top-h)]">
        {readingAction}
        <div className="mx-auto flex w-full max-w-[80ch] items-center gap-3">
          <IconButton
            aria-label={text("external.focus_back")}
            title={text("external.focus_back")}
            onClick={() => setAlone(null)}
          >
            <ArrowLeftIcon />
          </IconButton>
          {/* Truncated on purpose and owed no tooltip: unlike a clipped
              label on a card, the words it stands for are printed in full
              directly underneath. It names the passage; it does not stand
              in for it. */}
          <SectionTitle className="min-w-0 flex-1 truncate">
            {summarise(soloEntry.text, 60)}
          </SectionTitle>
          <IconButton
            aria-label={text("external.replay")}
            title={text("external.replay")}
            onClick={() => onReplay(soloEntry)}
          >
            <PlayIcon />
          </IconButton>
        </div>
        {/* The scroller spans the window and carries the side inset, so the
            bar sits at the window's edge and not against the passage's
            own buttons; the measure cap moves to the column inside. Same
            rule as the shelf (owner, 15/09). */}
        <div
          className="selection-scroll-mask -mx-6 min-h-0 flex-1 overflow-y-auto px-6 [scrollbar-gutter:stable_both-edges]"
          onWheel={byHand}
          onTouchMove={byHand}
          onKeyDown={byKey}
        >
          <div className="mx-auto w-full max-w-[80ch] pt-4 pb-[calc(var(--shell-bottom-h)+1rem)]">
            <ScanEntry
              playback={playback}
              onTogglePlayback={onTogglePlayback}
              entry={soloEntry}
              solo
              open
              following={following}
              jump={jump}
              current={currentPart(soloEntry.at, readingAt, position)}
              onToggle={() => undefined}
              onReplay={() => onReplay(soloEntry)}
              onReadPart={(segmentId) => onReadPart(soloEntry, segmentId)}
              onFocus={() => undefined}
            />
          </div>
        </div>
      </section>
    );
  }

  if (bare) {
    return (
      <section className="shell-inset flex min-h-0 flex-1 flex-col">
        {readingAction}
        <EmptyState
          icon={<CursorTextIcon className="h-8 w-8" />}
          actions={
            <div className="flex flex-col items-center gap-3">
              {setupBar}
              {asides}
            </div>
          }
          note={text("external.history_empty")}
        />
      </section>
    );
  }

  return (
    /* One column, not two. The left column used to give a one-time setup -
       a shortcut you learn once and three steps you read once - the same
       413 px the passages themselves got (measured at a 1060 px window,
       09/09). Scanning is what this screen DOES; the setup is what it
       needed once. So the setup is one bar across the top and the passages
       have the width (owner, 09/09). */
    <section className="flex min-h-0 flex-1 flex-col pt-[var(--shell-top-inner)]">
      {readingAction}
      {/* Keep shadow clearance inside the clipping container, not in a flex gap. */}
      <div className="-mx-6 shrink-0 overflow-y-auto px-6 py-4 [scrollbar-gutter:stable_both-edges]">
        <div className="mx-auto w-full max-w-[80ch]">
          <Surface className="scan-block flex flex-col gap-3 px-4 py-3">
            {setupBar}
            {asides}
          </Surface>
        </div>
      </div>
      {/* Capped at a readable measure rather than stretched: the passages
          are prose, and prose that runs the whole window is harder to
          follow than the narrow column this replaced.
          The scroller runs beneath the existing footer frost; bottom padding
          keeps the final capture above its controls at the end of the list.
          Separate surfaces and a consistent gap distinguish captures from
          the translation/source sections inside each capture. */}
      <div
        className="selection-scroll-mask -mx-6 -mt-4 min-h-0 flex-1 overflow-y-auto px-6 [scrollbar-gutter:stable_both-edges]"
        onWheel={byHand}
        onTouchMove={byHand}
        onKeyDown={byKey}
      >
       <div className="mx-auto flex w-full max-w-[80ch] flex-col gap-3 pt-4 pb-[calc(var(--shell-bottom-h)+1rem)]">
        {history.map((entry) => (
          <ScanEntry
            playback={playback}
            onTogglePlayback={onTogglePlayback}
            key={entry.at}
            entry={entry}
            open={isOpen(entry.at, readingAt, toggled)}
            following={following}
            jump={jump}
            current={currentPart(entry.at, readingAt, position)}
            onToggle={() =>
              setToggled((was) => ({
                ...was,
                [entry.at]: !isOpen(entry.at, readingAt, was),
              }))
            }
            onReplay={() => onReplay(entry)}
            onReadPart={(segmentId) => onReadPart(entry, segmentId)}
            onFocus={() => setAlone(entry.at)}
          />
        ))}
       </div>
      </div>
    </section>
  );
}
