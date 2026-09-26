/** The Voice choice in the settings panel, with a sample and a star on every
 * row (HIG 3.13; owner, 26/09: "nâng cấp dropdown chọn giọng cũng có thể
 * preview voice và favorite luôn").
 *
 * A native <select> cannot hold a button - the system's menu is lines of
 * text - so this is a `SelectButton`, the select's own face, opening a
 * menu-tier layer: each row is the voice (pick it, and the layer closes),
 * then the voice list's two buttons, hear and star, with the same names and
 * shapes they have there.
 *
 * Drawn through a portal and placed from the button's measured box: the
 * panel clips what spills out of it and scrolls its own body - the trap the
 * tooltip goes around the same way. Below the button; above it when the
 * list does not fit below and there is more room above.
 *
 * Grouped as the select was (`voiceGroups`) and PINNED when it opens: a star
 * pressed here changes the star, not where the row stands - the rows
 * regroup the next time it opens, the voice list's rule. Closing it stops a
 * sample it started, the way closing the voice list does.
 *
 * Keyboard (HIG 4.2, point 3): Enter, Space, ↓ or ↑ on the button open it
 * with the focus on the voice in use; ↑ ↓ keep the column (voice, hear,
 * star), ← → move along the row, Home and End go to the first and last row;
 * Tab goes round inside - the layer sits at the end of the page, so leaving
 * it would land nowhere; Escape closes this layer only and gives the focus
 * back to the button. It is a named dialog holding buttons, not a listbox or
 * a menu: both of those forbid a button inside an item.
 */
import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { text, type TextKey } from "../i18n";
import { IconButton, LAYER_GAP, SelectButton, Surface } from "./controls";
import { CheckIcon, SpeakerIcon, StarIcon, StarOutlineIcon, StopIcon } from "./icons";
import { Presence } from "./motion";
import { pressedByPointer } from "./patterns";
import { isPaidVoice } from "./readingCost";
import { tidyName, voiceDescriptionShown, voiceGroups, type Voice } from "./voiceShortlist";

const GROUP_TITLE: Record<"starred" | "local" | "paid", TextKey> = {
  starred: "voices.group_favorites",
  local: "voices.group_local",
  paid: "voices.source_api",
};

/** What the button and a row call a voice: the name the voice list shows. */
const shown = (voice: Voice) => tidyName(voice.label) || voice.id;

/** Kept this far from the window's edges, like the tooltip. */
const MARGIN = 12;

export function VoicePicker({
  labelledBy,
  voices,
  favorites,
  value,
  locked,
  previewing,
  className = "",
  onChoose,
  onPreview,
  onStopPreview,
  onFavorite,
}: {
  /** The row title that names the choice ("Giọng"); the button adds its value. */
  labelledBy: string;
  /** What is on offer, in order - the settings panel decides which. */
  voices: readonly Voice[];
  favorites: readonly string[];
  /** The voice in use when it is one of `voices`; "" when it is not. */
  value: string;
  /** No sample can play: something is being read (HIG 3.13). */
  locked: boolean;
  previewing: string | null;
  className?: string;
  onChoose: (id: string) => void;
  onPreview: (id: string) => void;
  onStopPreview: () => void;
  onFavorite: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  /* A fresh layer - and so a fresh pin of the groups - every time it opens,
     even when it opens again before the last one has faded out. */
  const [opens, setOpens] = useState(0);
  const [place, setPlace] = useState<{ left: number; top: number; maxHeight: number } | null>(null);
  const own = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const layer = useRef<HTMLDivElement>(null);
  const byKeys = useRef(false);
  const sample = useRef(previewing);
  sample.current = previewing;
  const current = voices.find((voice) => voice.id === value);

  const show = (keys: boolean) => {
    byKeys.current = keys;
    setPlace(null);
    setOpens((count) => count + 1);
    setOpen(true);
  };
  /** `giveBack`: the keyboard was inside, so it returns to the button. */
  const close = useCallback((giveBack: boolean) => {
    if (sample.current !== null) onStopPreview();
    setOpen(false);
    if (giveBack) trigger.current?.focus({ preventScroll: true });
  }, [onStopPreview]);

  useLayoutEffect(() => {
    if (!open) return;
    const measure = () => {
      const box = layer.current;
      const at = trigger.current?.getBoundingClientRect();
      if (!box || !at) return;
      const width = box.offsetWidth;
      const height = box.scrollHeight;
      const left = Math.min(Math.max(at.right - width, MARGIN), Math.max(MARGIN, window.innerWidth - width - MARGIN));
      const below = window.innerHeight - at.bottom - LAYER_GAP - MARGIN;
      const above = at.top - LAYER_GAP - MARGIN;
      if (height <= below) { setPlace({ left, top: at.bottom + LAYER_GAP, maxHeight: below }); return; }
      if (height <= above) { setPlace({ left, top: at.top - LAYER_GAP - height, maxHeight: above }); return; }
      // Neither side holds the whole list (a short window: the panel stands
      // on the footer). Over the button, then, the way the Mac's own pop-up
      // opens - the voice in use level with it - rather than a list that
      // scrolls in a sliver with its last rows out of sight.
      const full = window.innerHeight - 2 * MARGIN;
      const shownHeight = Math.min(height, full);
      const row = box.querySelector<HTMLElement>('[data-voice-row]:has(button[aria-current="true"])');
      const level = row ? row.offsetTop + row.offsetHeight / 2 : shownHeight / 2;
      const top = Math.min(Math.max(at.top + at.height / 2 - level, MARGIN), window.innerHeight - MARGIN - shownHeight);
      setPlace({ left, top, maxHeight: full });
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [open, opens]);

  // Opened from the keyboard: onto the voice in use, as the system's select
  // does - once the layer is where it will stay, so nothing scrolls twice.
  useEffect(() => {
    if (!open || !place || !byKeys.current) return;
    byKeys.current = false;
    const box = layer.current;
    const target = box?.querySelector<HTMLElement>('[data-voice-row] button[aria-current="true"]')
      ?? box?.querySelector<HTMLElement>("[data-voice-row] button");
    target?.focus({ preventScroll: true });
    target?.scrollIntoView({ block: "nearest" });
  }, [open, place]);

  useEffect(() => {
    if (!open) return;
    const inside = (node: EventTarget | null) => node instanceof Node && !!layer.current?.contains(node);
    const onDown = (event: MouseEvent) => {
      if (inside(event.target) || trigger.current?.contains(event.target as Node)) return;
      close(false);
    };
    // The layer is placed against the button; once what holds the button
    // scrolls, it would float beside nothing. Only that: in a scroll the page
    // follows the voice every paragraph, and changing voice mid-reading is an
    // ordinary thing to do - the page moving must not shut the list (26/09).
    const onScroll = (event: Event) => {
      const moved = event.target;
      if (moved instanceof Node && trigger.current && moved.contains(trigger.current)) close(false);
    };
    const onKey = (event: KeyboardEvent) => {
      const box = layer.current;
      if (!box) return;
      const at = document.activeElement;
      if (event.key === "Escape") {
        // One press closes this layer only: the panel under it closes on
        // Escape too, and would go with it.
        event.preventDefault();
        event.stopImmediatePropagation();
        close(inside(at));
        return;
      }
      if (!(at instanceof HTMLElement) || !box.contains(at)) return;
      if (event.key === "Tab") {
        const stops = [...box.querySelectorAll<HTMLButtonElement>("button:not([disabled])")];
        if (!stops.length) return;
        const index = stops.indexOf(at as HTMLButtonElement);
        const next = event.shiftKey ? (index <= 0 ? stops.length - 1 : index - 1) : (index + 1) % stops.length;
        event.preventDefault();
        event.stopPropagation();
        stops[next].focus({ preventScroll: true });
        stops[next].scrollIntoView({ block: "nearest" });
        return;
      }
      const rows = [...box.querySelectorAll<HTMLElement>("[data-voice-row]")];
      const row = at.closest<HTMLElement>("[data-voice-row]");
      if (!row || !rows.length) return;
      const cells = (of: HTMLElement) => [...of.querySelectorAll<HTMLButtonElement>("button")];
      const column = cells(row).indexOf(at as HTMLButtonElement);
      // Same column in another row; the voice itself when that row's button
      // there is locked (no sample while reading).
      const inRow = (of: HTMLElement) => {
        const here = cells(of)[column];
        return here && !here.disabled ? here : cells(of)[0];
      };
      const r = rows.indexOf(row);
      const along = (step: number) => {
        const enabled = cells(row).filter((cell) => !cell.disabled);
        return enabled[enabled.indexOf(at as HTMLButtonElement) + step];
      };
      const to = event.key === "ArrowDown" ? inRow(rows[(r + 1) % rows.length])
        : event.key === "ArrowUp" ? inRow(rows[(r - 1 + rows.length) % rows.length])
        : event.key === "Home" ? inRow(rows[0])
        : event.key === "End" ? inRow(rows[rows.length - 1])
        : event.key === "ArrowRight" ? along(1)
        : event.key === "ArrowLeft" ? along(-1)
        : null;
      if (to === null) return;
      // Handled here, whatever the page would have made of it (a turn).
      event.preventDefault();
      event.stopPropagation();
      to?.focus({ preventScroll: true });
      to?.scrollIntoView({ block: "nearest" });
    };
    document.addEventListener("mousedown", onDown);
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("mousedown", onDown);
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("keydown", onKey, true);
    };
  }, [open, close]);

  return (
    <>
      <SelectButton
        ref={trigger}
        id={own}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-labelledby={`${labelledBy} ${own}`}
        className={className}
        /* Like every opener (HIG 4.2): after a mouse press it lets go of the
           focus, so the next Space still pauses the reading. */
        onClick={(event) => {
          const pointer = pressedByPointer();
          if (pointer) event.currentTarget.blur();
          if (open) close(false);
          else show(!pointer);
        }}
        onKeyDown={(event) => {
          if (open || (event.key !== "ArrowDown" && event.key !== "ArrowUp")) return;
          event.preventDefault();
          show(true);
        }}
      >
        {current ? shown(current) : <span className="text-ink-mute">{text("voices.pick")}</span>}
      </SelectButton>
      {createPortal(
        <Presence open={open}>
          <div
            /* Outside the panel's DOM, so the panel's own "a click outside
               closes me" must be told this is part of it. */
            data-keeps-popover
            className="fixed z-40"
            style={{
              left: place?.left ?? 0,
              top: place?.top ?? 0,
              maxHeight: place?.maxHeight,
              // Hidden for the frame before it has been measured, so it
              // never shows in the wrong place first.
              visibility: place ? "visible" : "hidden",
            }}
          >
            <Surface
              key={opens}
              ref={layer}
              dialog={text("voices.picker")}
              edge="strong"
              material="glass"
              radius="menu"
              layer="menu"
              /* The panel's own width: "Nam · miền Nam · Phong cách kể chuyện" fits
                 on one line beside the two buttons. The style is what tells
                 two voices apart, and at 21rem it was the part the ellipsis
                 took; at 24rem it still broke before its last word. */
              className="max-h-[inherit] w-[26rem] max-w-[calc(100vw-2rem)] overflow-y-auto overscroll-contain p-2 shadow-lifted"
            >
              <PickerRows
                voices={voices}
                favorites={favorites}
                value={value}
                locked={locked}
                previewing={previewing}
                onChoose={(id) => {
                  const keys = !pressedByPointer();
                  close(keys);
                  onChoose(id);
                }}
                onPreview={onPreview}
                onStopPreview={onStopPreview}
                onFavorite={onFavorite}
              />
            </Surface>
          </div>
        </Presence>,
        document.body,
      )}
    </>
  );
}

function PickerRows({
  voices,
  favorites,
  value,
  locked,
  previewing,
  onChoose,
  onPreview,
  onStopPreview,
  onFavorite,
}: {
  voices: readonly Voice[];
  favorites: readonly string[];
  value: string;
  locked: boolean;
  previewing: string | null;
  onChoose: (id: string) => void;
  onPreview: (id: string) => void;
  onStopPreview: () => void;
  onFavorite: (id: string) => void;
}) {
  // The groups as they were when the layer opened (HIG 3.13): a row that
  // jumped to the top under the pointer would be a row lost.
  const [pinned] = useState(() => [...favorites]);
  const groups = voiceGroups(voices, pinned);
  return (
    <>
      {groups.map((group) => (
        <div key={group.key}>
          {group.key !== "all" && (
            <h3 className="m-0 px-3 pb-1 pt-2 text-xs font-semibold text-ink-mute">{text(GROUP_TITLE[group.key])}</h3>
          )}
          {group.voices.map((voice) => {
            const name = shown(voice);
            const about = voiceDescriptionShown(voice.label);
            const chosen = voice.id === value;
            const favorite = favorites.includes(voice.id);
            const playing = previewing === voice.id;
            return (
              <div key={voice.id} data-voice-row className="flex items-center gap-1">
                <button
                  type="button"
                  aria-current={chosen ? "true" : undefined}
                  onClick={() => onChoose(voice.id)}
                  /* The menu row's corner and inset (MenuButton): 12px,
                     concentric with the layer's 20 at an 8px inset. */
                  className="flex min-w-0 flex-1 items-center gap-2.5 rounded-xl px-3 py-2 text-left hover-wash"
                >
                  <span className="flex w-4 shrink-0 justify-center text-ink [&_svg]:h-4 [&_svg]:w-4">
                    {chosen && <CheckIcon />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-ink">{name}</span>
                    {/* Wraps rather than clips: a cloned voice's description is free text. */}
                    {about && <span className="block text-xs text-ink-mute">{about}</span>}
                  </span>
                </button>
                <IconButton
                  onClick={() => (playing ? onStopPreview() : onPreview(voice.id))}
                  disabled={locked}
                  aria-label={text(playing ? "voices.stop_preview" : "voices.preview")}
                  title={text(playing ? "voices.stop_preview" : "voices.preview")}
                  className={playing ? "text-brand-600" : ""}
                >
                  {playing ? <StopIcon /> : <SpeakerIcon />}
                </IconButton>
                {/* Two shapes for the two states, as in the voice list. */}
                <IconButton
                  onClick={() => onFavorite(voice.id)}
                  aria-pressed={favorite}
                  aria-label={text("voices.favorite", { name })}
                  title={text(favorite ? "voices.favorite_remove" : "voices.favorite_add")}
                >
                  {favorite ? <StarIcon className="text-favorite" /> : <StarOutlineIcon />}
                </IconButton>
              </div>
            );
          })}
        </div>
      ))}
      {/* A locked button shows no tooltip, so the reason is said here. */}
      {locked && <p className="m-0 px-3 pb-1 pt-2 text-xs text-ink-mute">{text("voices.preview_while_reading")}</p>}
      {voices.some((voice) => isPaidVoice(voice.id)) && (
        <p className="m-0 px-3 pb-1 pt-2 text-xs text-ink-mute">{text("voices.paid_preview")}</p>
      )}
    </>
  );
}
