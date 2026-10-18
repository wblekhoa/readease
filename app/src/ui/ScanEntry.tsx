import { useEffect, useId, useMemo, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { currentLanguage, text } from "../i18n";
import { IconButton, Surface } from "./controls";
import { ChevronDownIcon, PlayIcon, ScrollIcon } from "./icons";
import { ReadingPositionControl } from "./ReadingPositionControl";
import { scrollBehavior } from "./motion";
import { summarise } from "./scanHistory";

export type ExternalEntry = { at: number; text: string; original?: string; target?: string; voiceId?: string };

type ScanPart = { segment_id: string; text: string };

/** One captured passage, openable, with the voice's place marked in it.
 *
 * The list used to clamp each passage to two lines and hang the replay
 * tooltip on the text, so hovering the words offered to read them again
 * instead of showing them. Scanning is how this app is USED - the passage
 * is the content, not a label for it (owner, 09/09). */
export function ScanEntry({
  entry,
  open,
  current,
  solo = false,
  following = true,
  jump = 0,
  onToggle,
  onReplay,
  onReadPart,
  onFocus,
  playback,
  onTogglePlayback,
}: {
  entry: ExternalEntry;
  open: boolean;
  current: string | null;
  playback: "reading" | "paused" | null;
  onTogglePlayback: () => void;
  /** Alone on the screen: the row of controls moved up to the screen's own
   * bar, so the passage is all that is left here. */
  solo?: boolean;
  /** Whether the page still follows the voice: it stops the moment the
   * reader scrolls by hand, and starts again from the button (owner,
   * 19/09) - the reader's own rule (HIG 3.9). */
  following?: boolean;
  /** Bumped by the "back to the reading position" button: bring the part
   * being read to the middle, whatever `following` says. */
  jump?: number;
  onToggle: () => void;
  onReplay: () => void;
  onReadPart: (segmentId: string) => void;
  onFocus: () => void;
}) {
  /* Split by the ENGINE, never here. The ids painted below arrive in
   * `reading:position`, and the engine's `text.parts` answers from the same
   * builder the reading speaks from - a second splitting rule in the shell
   * would drift and put the marker on the wrong paragraph. */
  const [parts, setParts] = useState<ScanPart[] | null>(null);
  const here = useRef<HTMLButtonElement>(null);
  const contentId = useId();
  const language = currentLanguage();
  const capturedAt = useMemo(() => {
    const date = new Date(entry.at);
    return { iso: date.toISOString(), label: date.toLocaleTimeString(language === "vi" ? "vi-VN" : "en-GB", { hour: "2-digit", minute: "2-digit" }) };
  }, [entry.at, language]);

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
    if (current && following) here.current?.scrollIntoView({ block: "nearest" });
  }, [current, following]);
  useEffect(() => {
    // The person asked to be taken there: a scroll, not a cut (HIG 3.17).
    // Following the voice, above, stays a cut - it moves by the sentence.
    if (jump > 0) here.current?.scrollIntoView({ block: "center", behavior: scrollBehavior() });
    // Only the button bumps `jump`; the part it lands on is whichever is
    // current at that moment, so `current` is read, not depended on.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jump]);

  return (
    // RE-PLAY-025: one capture per surface; the spoken translation precedes its source.
    <Surface className="scan-block">
      {!solo && (
        <div className="relative isolate flex items-center gap-3 px-4 py-4">
          <button
            onClick={onToggle}
            /* Open or shut, said as well as drawn: the chevron turns for the
               eye only (HIG 4.2, point 1). */
            aria-expanded={open}
            aria-controls={contentId}
            aria-labelledby={`${contentId}-summary`}
            className={`scan-block-toggle absolute inset-0 hover-wash ${open ? "rounded-t-2xl" : "rounded-2xl"}`}
          />
          <div className="pointer-events-none relative flex min-w-0 flex-1 items-center gap-3">
            <ChevronDownIcon
              className={`shrink-0 text-ink-mute transition-transform ${
                open ? "" : "-rotate-90"
              }`}
            />
            <span className="min-w-0 flex-1">
              <span id={`${contentId}-summary`} className="block truncate text-sm font-semibold leading-snug">{summarise(entry.text)}</span>
              <time dateTime={capturedAt.iso} className="mt-1 block text-xs font-normal text-ink-mute">{capturedAt.label}</time>
            </span>
          </div>
          {/* A long capture pushes everything else off the screen when it
              opens in place. This hands it the whole panel instead, which is
              what a passage worth re-reading needs (owner, 09/09). */}
          <IconButton
            className="relative shrink-0"
            aria-label={text("external.focus_one")}
            title={text("external.focus_one")}
            onClick={onFocus}
          >
            <ScrollIcon />
          </IconButton>
          <IconButton
            className="relative shrink-0"
            aria-label={text("external.replay")}
            title={text("external.replay")}
            onClick={onReplay}
          >
            <PlayIcon />
          </IconButton>
        </div>
      )}
      {open && (
        <div id={contentId} className={solo ? "p-4" : "mx-4 border-t border-edge pb-4 pt-4"}>
          {entry.original && <p className="m-0 mb-3 text-xs font-semibold text-ink-mute">
            {text('translation.translated', { language: text(entry.target === 'vi' ? 'language.vi' : 'language.en') })}
          </p>}
          <div className="-mx-2 flex flex-col gap-1">
          {parts === null ? (
            <p className="m-0 px-2 py-1 text-sm text-ink-mute">
              {text("external.parts_loading")}
            </p>
          ) : (
            parts.map((part, index) => (
              <div key={part.segment_id || index} className="relative flex">
              <button
                ref={part.segment_id === current ? here : undefined}
                onClick={() => part.segment_id && onReadPart(part.segment_id)}
                /* The fallback block (the engine could not be asked) has no
                   id, so it cannot be read from. It must not offer to be:
                   a tooltip promising something the click will not do is
                   the same lie the old replay tooltip told. */
                title={part.segment_id ? text("external.read_from_here") : undefined}
                className={`scan-sentence w-full px-2 py-1.5 text-left text-sm leading-relaxed whitespace-pre-line break-words ${
                  part.segment_id === current ? "voice-here" : ""
                } ${part.segment_id ? "read-from-here" : "cursor-default"}`}
              >
                {part.text}
              </button>
              {part.segment_id && part.segment_id === current && playback && (
                <ReadingPositionControl playback={playback} onToggle={onTogglePlayback} />
              )}
              </div>
            ))
          )}
          </div>
          {entry.original && <details className="group mt-4 border-t border-edge pt-3">
            <summary className="flex cursor-pointer list-none items-center gap-2 rounded-xl px-2 py-2 text-sm font-medium text-ink-mute hover-wash [&::-webkit-details-marker]:hidden">
              <ChevronDownIcon className="h-4 w-4 shrink-0 -rotate-90 group-open:rotate-0" />
              {text('translation.original')}
            </summary>
            <p className="m-0 whitespace-pre-wrap break-words px-2 pb-1 pt-3 text-sm leading-relaxed text-ink-mute">{entry.original}</p>
          </details>}
        </div>
      )}
    </Surface>
  );
}
