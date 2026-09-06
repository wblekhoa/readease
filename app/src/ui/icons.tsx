import { useId } from "react";

/** The product's icon set, drawn in the **bulk** manner (owner, 04/09).
 *
 * Bulk means two fills of the SAME colour: a mass at 40% that carries the
 * silhouette, and a detail at full strength on top. One colour, so every
 * icon still takes `currentColor` and follows the theme; two weights, so a
 * glyph reads as an object rather than as an outline.
 *
 * **24 grid, rendered at 20.** The old set was drawn on a 16 grid at 1.5
 * stroke and rendered at 16. Bulk is designed for 24 and a two-tone glyph
 * squeezed into 16 loses its lighter layer to a grey smudge - the owner
 * looked at both sizes side by side and chose 20 (04/09). Two places still
 * need 16 and force it themselves in controls.tsx: an icon inside a line of
 * text, which must not push the line apart, and a small button, which has
 * only 28px to put one in.
 *
 * Inlined rather than imported. DOL canon sources icons from DS Studio's
 * DsIcon, and that registry is not consumable outside the DS repo (same gap
 * as ToggleButtonGroup); no icon package is a dependency of this app. So the
 * glyphs are copied in, as drawn in their source, and only the ones the
 * source has no equivalent for are drawn here: the A pair that sets reading
 * size, and the half-lit disc for "follow the Mac". Redrawing a glyph the
 * source already has produced a lopsided book and an off-balance stop, and
 * cost two rounds each (owner, 06/09: "tìm đúng … chứ đừng tự vẽ").
 *
 * They are a SET, so weight and proportion are decided across the set and
 * not per glyph: reworking one in isolation is how a set stops looking like
 * one - which is the other half of the reason for copying rather than
 * drawing. `CloseIcon` is the one deliberate exception: the source's close
 * is a circled cross, and a panel closes with the bare mark Books uses.
 */

const bulk = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "currentColor",
  "aria-hidden": true,
};

/** The same attributes: the source's OUTLINE manner is also filled paths, so
 * only the path data differs.
 *
 * Eight glyphs are outline rather than bulk, each at the owner's word (06/09)
 * and each for its own reason. `ResetIcon` and the two that lead a slider,
 * `LineSpacingIcon` and `MarginsIcon`, because the reading settings form was
 * drawn from a line-drawn reference. `ArrowLeftIcon` because the owner asked
 * for a back arrow WITH A SHAFT and the source's bulk arrow is not one - it
 * is a rounded badge with an arrow cut out of it, a different object. And
 * the four that mark the voice filters - `MonitorIcon`, `CloudIcon`,
 * `ManIcon`, `WomanIcon` - because those chips draw their glyph at 16, where
 * bulk's lighter layer collapses into a grey smudge (the reason this file
 * renders at 20 in the first place). They are named exceptions, not a new
 * rule. */
const outline = bulk;

/** The 40% layer. A constant so no icon quietly picks its own weight. */
const MASS = 0.4;

export function BookIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M12 5.302v16.03c-.17 0-.35-.03-.49-.11l-.04-.02c-1.92-1.05-5.27-2.15-7.44-2.44l-.29-.04c-.96-.12-1.74-1.02-1.74-1.98V4.662c0-1.19.97-2.09 2.16-1.99 2.1.17 5.28 1.23 7.06 2.34l.25.15c.15.09.34.14.53.14Z" />
      <path d="M22 4.67v12.07c0 .96-.78 1.86-1.74 1.98l-.33.04c-2.18.29-5.54 1.4-7.46 2.46-.13.08-.29.11-.47.11V5.3c.19 0 .38-.05.53-.14l.17-.11c1.78-1.12 4.97-2.19 7.07-2.37h.06c1.19-.1 2.17.79 2.17 1.99ZM7.75 9.238H5.5c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h2.25c.41 0 .75.34.75.75s-.34.75-.75.75ZM8.5 12.238h-3c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h3c.41 0 .75.34.75.75s-.34.75-.75.75Z" />
    </svg>
  );
}

export function CloseIcon({ className }: { className?: string }) {
  /* Single layer on purpose. A bare mark has nothing to be the mass OF, and
     the filled square this started as read like a heavy chip sitting in a
     panel header rather than a way out of it. Bulk sets keep marks like this
     one-weight too. */
  return (
    <svg {...bulk} className={className}>
      <path d="M13.4 12l5-5a1 1 0 1 0-1.4-1.4l-5 5-5-5A1 1 0 0 0 5.6 7l5 5-5 5A1 1 0 1 0 7 18.4l5-5 5 5a1 1 0 0 0 1.4-1.4l-5-5Z" />
    </svg>
  );
}

export function TrashIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path d="M21.07 5.23c-1.61-.16-3.22-.28-4.84-.37v-.01l-.22-1.3c-.15-.92-.37-2.3-2.71-2.3h-2.62c-2.33 0-2.55 1.32-2.71 2.29l-.21 1.28c-.93.06-1.86.12-2.79.21l-2.04.2c-.42.04-.72.41-.68.82.04.41.4.71.82.67l2.04-.2c5.24-.52 10.52-.32 15.82.21h.08c.38 0 .71-.29.75-.68a.766.766 0 0 0-.69-.82Z" />
      <path d="M19.23 8.14c-.24-.25-.57-.39-.91-.39H5.68c-.34 0-.68.14-.91.39-.23.25-.36.59-.34.94l.62 10.26c.11 1.52.25 3.42 3.74 3.42h6.42c3.49 0 3.63-1.89 3.74-3.42l.62-10.25c.02-.36-.11-.7-.34-.95Z" />
      <path d="M9.58 17a.75.75 0 0 1 .75-.75h3.33a.75.75 0 0 1 0 1.5h-3.33a.75.75 0 0 1-.75-.75ZM8.75 13a.75.75 0 0 1 .75-.75h5a.75.75 0 0 1 0 1.5h-5a.75.75 0 0 1-.75-.75Z" />
    </svg>
  );
}

/** Going BACK: an arrowhead on a shaft. Distinct from `ChevronLeftIcon`,
 * which is a bare mark and stays where it belongs - turning a page, where
 * the pair of them point along the text. An arrow leaves; a chevron steps
 * (owner, 06/09: "arrow icon có line"). */
export function ArrowLeftIcon({ className }: { className?: string }) {
  return (
    <svg {...outline} className={className}>
      <path d="M9.57 18.82c-.19 0-.38-.07-.53-.22l-6.07-6.07a.754.754 0 010-1.06L9.04 5.4c.29-.29.77-.29 1.06 0 .29.29.29.77 0 1.06L4.56 12l5.54 5.54c.29.29.29.77 0 1.06-.14.15-.34.22-.53.22z" />
      <path d="M20.5 12.75H3.67c-.41 0-.75-.34-.75-.75s.34-.75.75-.75H20.5c.41 0 .75.34.75.75s-.34.75-.75.75z" />
    </svg>
  );
}

export function ChevronLeftIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M10.77 8.52l5.05 3.79v5.61c0 .96-1.16 1.44-1.84.76L8.8 13.51a2.13 2.13 0 010-3.01l1.97-1.98z" />
      <path d="M15.82 6.08v6.23l-5.05-3.79 3.21-3.21c.68-.67 1.84-.19 1.84.77z" />
    </svg>
  );
}

export function ChevronRightIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M13.23 8.52l-5.05 3.79v5.61c0 .96 1.16 1.44 1.84.76l5.18-5.18c.83-.83.83-2.18 0-3.01l-1.97-1.97z" />
      <path d="M8.18 6.08v6.23l5.05-3.79-3.21-3.21c-.68-.67-1.84-.19-1.84.77z" />
    </svg>
  );
}

export function ChevronDownIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M15.48 13.23l-3.79-5.05H6.08c-.96 0-1.44 1.16-.76 1.84l5.18 5.18c.83.83 2.18.83 3.01 0l1.97-1.97z" />
      <path d="M17.92 8.18h-6.23l3.79 5.05 3.21-3.21c.67-.68.19-1.84-.77-1.84z" />
    </svg>
  );
}

export function PlayIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path d="M18.7 8.98 4.14 17.71c-.09-.33-.14-.68-.14-1.04V7.33c0-3.08 3.33-5 6-3.46l4.04 2.33 4.05 2.34c.22.13.43.27.61.44Z" />
      <path opacity={MASS} d="m18.089 15.46-4.05 2.34-4.04 2.33c-1.91 1.1-4.16.44-5.28-1.17l.42-.25 14.44-8.66c1 1.8.51 4.26-1.49 5.41Z" />
    </svg>
  );
}

export function PauseIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path d="M10.65 19.11V4.89c0-1.35-.57-1.89-2.01-1.89H5.01C3.57 3 3 3.54 3 4.89v14.22C3 20.46 3.57 21 5.01 21h3.63c1.44 0 2.01-.54 2.01-1.89Z" />
      <path opacity={MASS} d="M21.002 19.11V4.89c0-1.35-.57-1.89-2.01-1.89h-3.63c-1.43 0-2.01.54-2.01 1.89v14.22c0 1.35.57 1.89 2.01 1.89h3.63c1.44 0 2.01-.54 2.01-1.89Z" />
    </svg>
  );
}

/** Stop: the set's own glyph, as drawn - a rounded square split on the
 * diagonal into the two weights. Two hand redrawings preceded it; the
 * owner asked for the source glyph instead (06/09). */
export function StopIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path d="m20.9 7.66-.78.47-.49.3-.93.55-13.94 8.36-.09.05-.53.32-.61.37C3.17 17.19 3 16.07 3 14.7V9.3C3 4.8 4.8 3 9.3 3h5.4c3.91 0 5.78 1.36 6.2 4.66Z" />
      <path opacity={MASS} d="M21 9.2v5.5c0 4.5-1.8 6.3-6.3 6.3H9.3c-2.44 0-4.09-.53-5.07-1.74l.3-.18.61-.37.53-.32.09-.05L19.7 9.98l.93-.55.37-.23Z" />
    </svg>
  );
}

/** Reading size, smaller and larger. These were the letter "A" set in the
 * interface font at two sizes - the one control in the bar drawn in a
 * different hand from every glyph beside it (owner, 06/09). The letter stays,
 * because Books uses it and the owner knows it, but it is drawn on the set's
 * grid in the set's weight: an A stroked at 1.7 with round joins. Stroked
 * rather than filled for the same reason as `CoinIcon`: a hand-filled
 * letterform at 20 closes up. Single-layer: the text line first drawn under
 * the letter as its mass read as an underline (owner, 06/09). */
function TextSizeIcon({ className, apex }: { className?: string; apex: number }) {
  // The legs meet the baseline at y=19.5; the bar sits two thirds down.
  const half = apex === 4.5 ? 6 : 4;
  const bar = apex + (19.5 - apex) * 0.66;
  const spread = half * ((bar - apex) / (19.5 - apex));
  return (
    <svg {...bulk} className={className}>
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
        d={`M${12 - half} 19.5 12 ${apex} ${12 + half} 19.5M${(12 - spread).toFixed(1)} ${bar.toFixed(1)}h${(spread * 2).toFixed(1)}`}
      />
    </svg>
  );
}

/** Search in the book: the lens whose handle is a straight stem (owner,
 * 06/09) - the set also has one drawn as a blob, which read as a smudge
 * beside the gear. Disc at 40%, handle at full. */
export function SearchIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M11.5 21a9.5 9.5 0 1 0 0-19 9.5 9.5 0 0 0 0 19Z" />
      <path d="M21.3 21.999c-.18 0-.36-.07-.49-.2l-1.86-1.86a.706.706 0 0 1 0-.99c.27-.27.71-.27.99 0l1.86 1.86c.27.27.27.71 0 .99-.14.13-.32.2-.5.2Z" />
    </svg>
  );
}

/** Reading settings: the gear from the source set, in bulk - body at 40%,
 * hub at full. A gear rather than a type glyph because the panel holds
 * appearance, layout, spacing and more (owner, 06/09); not the sliders,
 * which already mean the voice settings in the footer. Taken from the set
 * as drawn, not redrawn (owner, 06/09: "tìm đúng … chứ đừng tự vẽ"). */
export function ReadingSettingsIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M2 12.881v-1.76c0-1.04.85-1.9 1.9-1.9 1.81 0 2.55-1.28 1.64-2.85-.52-.9-.21-2.07.7-2.59l1.73-.99c.79-.47 1.81-.19 2.28.6l.11.19c.9 1.57 2.38 1.57 3.29 0l.11-.19c.47-.79 1.49-1.07 2.28-.6l1.73.99c.91.52 1.22 1.69.7 2.59-.91 1.57-.17 2.85 1.64 2.85 1.04 0 1.9.85 1.9 1.9v1.76c0 1.04-.85 1.9-1.9 1.9-1.81 0-2.55 1.28-1.64 2.85.52.91.21 2.07-.7 2.59l-1.73.99c-.79.47-1.81.19-2.28-.6l-.11-.19c-.9-1.57-2.38-1.57-3.29 0l-.11.19c-.47.79-1.49 1.07-2.28.6l-1.73-.99a1.899 1.899 0 0 1-.7-2.59c.91-1.57.17-2.85-1.64-2.85-1.05 0-1.9-.86-1.9-1.9Z" />
      <path d="M12 15.25a3.25 3.25 0 1 0 0-6.5 3.25 3.25 0 0 0 0 6.5Z" />
    </svg>
  );
}

export function TextSmallerIcon({ className }: { className?: string }) {
  return <TextSizeIcon className={className} apex={9.5} />;
}

export function TextLargerIcon({ className }: { className?: string }) {
  return <TextSizeIcon className={className} apex={4.5} />;
}

export function PreviousIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M20.24 7.22v9.57c0 1.96-2.129 3.19-3.829 2.21l-4.15-2.39-4.15-2.4c-1.7-.98-1.7-3.43 0-4.41l4.15-2.4 4.15-2.39c1.7-.98 3.83.24 3.83 2.21Z" />
      <path d="M3.762 18.93c-.41 0-.75-.34-.75-.75V5.82c0-.41.34-.75.75-.75s.75.34.75.75v12.36c0 .41-.34.75-.75.75Z" />
    </svg>
  );
}

export function NextIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M3.762 7.22v9.57c0 1.96 2.13 3.19 3.83 2.21l4.15-2.39 4.15-2.4c1.7-.98 1.7-3.43 0-4.41l-4.15-2.4-4.15-2.39c-1.7-.98-3.83.24-3.83 2.21Z" />
      <path d="M20.238 18.93c-.41 0-.75-.34-.75-.75V5.82c0-.41.34-.75.75-.75s.75.34.75.75v12.36c0 .41-.33.75-.75.75Z" />
    </svg>
  );
}

/** The table of contents: a closed book, distinct from `BookIcon` - the
 * open book that names the library. One is a place to go, this one is what
 * a book has inside (owner picked it, 04/09). */
export function BookClosedIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M16.19 2H7.82C4.18 2 2.01 4.17 2.01 7.81v8.37c0 3.64 2.17 5.81 5.81 5.81h8.37c3.64 0 5.81-2.17 5.81-5.81V7.81C22 4.17 19.83 2 16.19 2Z" />
      <path d="M11.5 8.089v9.16c0 .36-.36.6-.69.46-1.21-.52-2.79-1-3.89-1.14l-.19-.02c-.61-.08-1.11-.65-1.11-1.27v-7.7c0-.76.62-1.33 1.38-1.27 1.25.1 3.1.7 4.26 1.36.15.07.24.24.24.42ZM18.38 7.7v7.57c0 .62-.5 1.19-1.11 1.27l-.21.02c-1.09.15-2.66.62-3.87 1.13-.33.14-.69-.1-.69-.46V8.08a.5.5 0 0 1 .25-.44c1.16-.65 2.97-1.23 4.2-1.34h.04c.77.01 1.39.63 1.39 1.4Z" />
    </svg>
  );
}

/** Pages: the set's open book, as drawn - two leaves of equal height either
 * side of the gutter, lines on the left leaf. Replaces a redrawn variant
 * whose left leaf sat lower and shorter (owner, 06/09: "icon trang đang bị
 * lệch"). */
export function PagesIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M12 5.302v16.03c-.17 0-.35-.03-.49-.11l-.04-.02c-1.92-1.05-5.27-2.15-7.44-2.44l-.29-.04c-.96-.12-1.74-1.02-1.74-1.98V4.662c0-1.19.97-2.09 2.16-1.99 2.1.17 5.28 1.23 7.06 2.34l.25.15c.15.09.34.14.53.14Z" />
      <path d="M22 4.67v12.07c0 .96-.78 1.86-1.74 1.98l-.33.04c-2.18.29-5.54 1.4-7.46 2.46-.13.08-.29.11-.47.11V5.3c.19 0 .38-.05.53-.14l.17-.11c1.78-1.12 4.97-2.19 7.07-2.37h.06c1.19-.1 2.17.79 2.17 1.99ZM7.75 9.238H5.5c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h2.25c.41 0 .75.34.75.75s-.34.75-.75.75ZM8.5 12.238h-3c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h3c.41 0 .75.34.75.75s-.34.75-.75.75Z" />
    </svg>
  );
}

export function ScrollIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M20.5 10.19h-2.89c-2.37 0-4.3-1.93-4.3-4.3V3c0-.55-.45-1-1-1H8.07C4.99 2 2.5 4 2.5 7.57v8.86C2.5 20 4.99 22 8.07 22h7.86c3.08 0 5.57-2 5.57-5.57v-5.24c0-.55-.45-1-1-1Z" />
      <path d="M15.8 2.21c-.41-.41-1.12-.13-1.12.44v3.49c0 1.46 1.24 2.67 2.75 2.67.95.01 2.27.01 3.4.01.57 0 .87-.67.47-1.07-1.44-1.45-4.02-4.06-5.5-5.54ZM13.5 13.75h-6c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h6c.41 0 .75.34.75.75s-.34.75-.75.75ZM11.5 17.75h-4c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h4c.41 0 .75.34.75.75s-.34.75-.75.75Z" />
    </svg>
  );
}

export function InfoIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10Z" />
      <path d="M12 13.75c.41 0 .75-.34.75-.75V8c0-.41-.34-.75-.75-.75s-.75.34-.75.75v5c0 .41.34.75.75.75ZM12.92 15.619c-.05-.12-.12-.23-.21-.33-.1-.09-.21-.16-.33-.21a1 1 0 0 0-.76 0c-.12.05-.23.12-.33.21-.09.1-.16.21-.21.33-.05.12-.08.25-.08.38s.03.26.08.38c.05.13.12.23.21.33.1.09.21.16.33.21.12.05.25.08.38.08s.26-.03.38-.08.23-.12.33-.21c.09-.1.16-.2.21-.33.05-.12.08-.25.08-.38s-.03-.26-.08-.38Z" />
    </svg>
  );
}

/** Voice settings. Sliders, not the gear: the gear opens how the PAGE is
 * set, and two panels must not share a glyph. */
export function SlidersIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M21.23 7.62h-5.54c-.38 0-.69-.31-.69-.7 0-.38.31-.69.69-.69h5.54c.38 0 .69.31.69.69 0 .39-.31.7-.69.7ZM6.46 7.618H2.77c-.38 0-.69-.31-.69-.69 0-.38.31-.69.69-.69h3.69c.38 0 .69.31.69.69 0 .38-.31.69-.69.69Z" />
      <path d="M10.15 10.84a3.92 3.92 0 1 0 0-7.84 3.92 3.92 0 0 0 0 7.84Z" />
      <path opacity={MASS} d="M21.23 17.77h-3.69c-.38 0-.69-.31-.69-.69 0-.38.31-.69.69-.69h3.69c.38 0 .69.31.69.69 0 .38-.31.69-.69.69ZM8.31 17.77H2.77c-.38 0-.69-.31-.69-.69 0-.38.31-.69.69-.69h5.54c.38 0 .69.31.69.69 0 .38-.31.69-.69.69Z" />
      <path d="M13.85 21a3.92 3.92 0 1 0 0-7.84 3.92 3.92 0 0 0 0 7.84Z" />
    </svg>
  );
}

export function SunIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M12 19a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z" />
      <path d="M12 22.96c-.55 0-1-.41-1-.96v-.08c0-.55.45-1 1-1s1 .45 1 1-.45 1.04-1 1.04Zm7.14-2.82c-.26 0-.51-.1-.71-.29l-.13-.13a.996.996 0 1 1 1.41-1.41l.13.13a.996.996 0 0 1-.7 1.7Zm-14.28 0c-.26 0-.51-.1-.71-.29a.996.996 0 0 1 0-1.41l.13-.13a.996.996 0 1 1 1.41 1.41l-.13.13c-.19.19-.45.29-.7.29ZM22 13h-.08c-.55 0-1-.45-1-1s.45-1 1-1 1.04.45 1.04 1-.41 1-.96 1ZM2.08 13H2c-.55 0-1-.45-1-1s.45-1 1-1 1.04.45 1.04 1-.41 1-.96 1Zm16.93-7.01c-.26 0-.51-.1-.71-.29a.996.996 0 0 1 0-1.41l.13-.13a.996.996 0 1 1 1.41 1.41l-.13.13c-.19.19-.44.29-.7.29Zm-14.02 0c-.26 0-.51-.1-.71-.29l-.13-.14a.996.996 0 1 1 1.41-1.41l.13.13c.39.39.39 1.02 0 1.41-.19.2-.45.3-.7.3ZM12 3.04c-.55 0-1-.41-1-.96V2c0-.55.45-1 1-1s1 .45 1 1-.45 1.04-1 1.04Z" />
    </svg>
  );
}

/** Appearance that follows the Mac: a disc half in light, half in shade -
 * the Books "◐". Mass is the whole disc, detail the shaded half. */
export function AutoAppearanceIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Z" />
      <path d="M12 3.5v17a8.5 8.5 0 0 0 0-17Z" />
    </svg>
  );
}

export function MoonIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path d="M8.999 19c0 .84.13 1.66.37 2.42-3.84-1.33-6.74-4.86-7.04-8.99-.3-4.39 2.23-8.49 6.32-10.21 1.06-.44 1.6-.12 1.83.11.22.22.53.75.09 1.76a8.192 8.192 0 0 0-.67 3.28c.01 2.04.81 3.93 2.11 5.38A7.985 7.985 0 0 0 8.999 19Z" />
      <path opacity={MASS} d="M21.21 17.72a10.501 10.501 0 0 1-8.47 4.27c-.16 0-.32-.01-.48-.02-1-.04-1.97-.23-2.89-.55C9.13 20.66 9 19.84 9 19c0-2.53 1.18-4.79 3.01-6.25a8.41 8.41 0 0 0 5.91 2.82c.63.03 1.26-.02 1.88-.13 1.12-.2 1.57.22 1.73.49.17.27.35.86-.32 1.79Z" />
    </svg>
  );
}

export function ClipboardIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="m13.89 2.878-4.69-.74c-3.91-.61-5.72.71-6.34 4.62l-.74 4.69c-.4 2.56.02 4.22 1.47 5.23.76.54 1.8.9 3.15 1.11l4.69.74c3.91.61 5.72-.71 6.34-4.62l.73-4.69c.12-.77.17-1.46.13-2.07-.13-2.5-1.6-3.78-4.74-4.27Zm-5.65 6.47c-1.17 0-2.12-.95-2.12-2.11 0-1.17.95-2.12 2.12-2.12 1.16 0 2.11.95 2.11 2.12 0 1.16-.95 2.11-2.11 2.11Z" />
      <path d="m20.5 13.468-1.5 4.51c-1.25 3.76-3.25 4.76-7.01 3.51l-4.51-1.5c-2.27-.75-3.53-1.79-3.89-3.31.76.54 1.8.9 3.15 1.11l4.69.74c3.91.61 5.72-.71 6.34-4.62l.73-4.69c.12-.77.17-1.46.13-2.07 2.39 1.27 2.91 3.19 1.87 6.32ZM10.351 7.241c0 1.16-.95 2.11-2.11 2.11-1.17 0-2.12-.95-2.12-2.11 0-1.17.95-2.12 2.12-2.12 1.16 0 2.11.95 2.11 2.12Z" />
    </svg>
  );
}

/** Reading a selection captured from another app - a scan frame, which is
 * what "Quét đọc" says. It replaced an I-beam that described the CURSOR
 * rather than the thing the feature does. */
export function CursorTextIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M2 9.75c-.41 0-.75-.34-.75-.75V6.5c0-2.9 2.36-5.25 5.25-5.25H9c.41 0 .75.34.75.75s-.34.75-.75.75H6.5c-2.07 0-3.75 1.68-3.75 3.75V9c0 .41-.34.75-.75.75Z" />
      <path d="M22 9.75c-.41 0-.75-.34-.75-.75V6.5c0-2.07-1.68-3.75-3.75-3.75H15c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h2.5c2.89 0 5.25 2.35 5.25 5.25V9c0 .41-.34.75-.75.75Z" />
      <path opacity={MASS} d="M17.5 22.75H16c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h1.5c2.07 0 3.75-1.68 3.75-3.75V16c0-.41.34-.75.75-.75s.75.34.75.75v1.5c0 2.9-2.36 5.25-5.25 5.25Z" />
      <path d="M9 22.75H6.5c-2.89 0-5.25-2.35-5.25-5.25V15c0-.41.34-.75.75-.75s.75.34.75.75v2.5c0 2.07 1.68 3.75 3.75 3.75H9c.41 0 .75.34.75.75s-.34.75-.75.75ZM8.501 11.381a2.88 2.88 0 1 0 0-5.76 2.88 2.88 0 0 0 0 5.76Z" />
      <path opacity={MASS} d="M7.501 18.381a1.88 1.88 0 1 0 0-3.76 1.88 1.88 0 0 0 0 3.76ZM16.501 9.381a1.88 1.88 0 1 0 0-3.76 1.88 1.88 0 0 0 0 3.76Z" />
      <path d="M15.501 18.381a2.88 2.88 0 1 0 0-5.76 2.88 2.88 0 0 0 0 5.76Z" />
    </svg>
  );
}

export function TransferIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M21.75 6.73c0-.2-.08-.39-.22-.53l-3.72-3.72a.754.754 0 00-1.06 0c-.29.29-.29.77 0 1.06l2.45 2.45H3c-.41 0-.75.34-.75.75s.34.75.75.75h16.19l-2.44 2.44c-.29.29-.29.77 0 1.06.15.15.34.22.53.22s.38-.07.53-.22l3.71-3.71c.07-.07.13-.16.17-.26 0-.01 0-.02.01-.03.03-.09.05-.17.05-.26z" />
      <path d="M21 16.52H4.81l2.44-2.44c.29-.29.29-.77 0-1.06a.754.754 0 00-1.06 0l-3.71 3.71c-.07.07-.13.16-.17.26 0 .01 0 .02-.01.03-.03.08-.05.17-.05.26 0 .2.08.39.22.53l3.72 3.72c.15.15.34.22.53.22s.38-.07.53-.22c.29-.29.29-.77 0-1.06L4.8 18.02H21c.41 0 .75-.34.75-.75s-.34-.75-.75-.75z" />
    </svg>
  );
}

/** Notes and highlights: the sticky note (owner picked it, 04/09). */
export function NoteIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M20 8.25V18c0 3-1.79 4-4 4H8c-2.21 0-4-1-4-4V8.25c0-3.25 1.79-4 4-4 0 .62.25 1.18.66 1.59.41.41.97.66 1.59.66h3.5C14.99 6.5 16 5.49 16 4.25c2.21 0 4 .75 4 4Z" />
      <path d="M16 4.25c0 1.24-1.01 2.25-2.25 2.25h-3.5c-.62 0-1.18-.25-1.59-.66C8.25 5.43 8 4.87 8 4.25 8 3.01 9.01 2 10.25 2h3.5c.62 0 1.18.25 1.59.66.41.41.66.97.66 1.59ZM12 13.75H8c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h4c.41 0 .75.34.75.75s-.34.75-.75.75ZM16 17.75H8c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h8c.41 0 .75.34.75.75s-.34.75-.75.75Z" />
    </svg>
  );
}

/** What a reading will cost and how much of the book to spend it on
 * (owner, 04/09). A coin: a gauge would be read as the reading SPEED, and
 * a wallet's silhouette does not survive 20px. */
export function CoinIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M12 21.898c5.523 0 10-4.477 10-10 0-5.522-4.477-10-10-10s-10 4.478-10 10c0 5.523 4.477 10 10 10Z" />
      <path d="m14.26 12-1.51-.53V8.08h.36c.81 0 1.47.71 1.47 1.58 0 .41.34.75.75.75s.75-.34.75-.75c0-1.7-1.33-3.08-2.97-3.08h-.36V6c0-.41-.34-.75-.75-.75s-.75.34-.75.75v.58h-.65c-1.48 0-2.69 1.25-2.69 2.78 0 1.79 1.04 2.36 1.83 2.64l1.51.53v3.38h-.36c-.81 0-1.47-.71-1.47-1.58 0-.41-.34-.75-.75-.75s-.75.34-.75.75c0 1.7 1.33 3.08 2.97 3.08h.36V18c0 .41.34.75.75.75s.75-.34.75-.75v-.58h.65c1.48 0 2.69-1.25 2.69-2.78-.01-1.8-1.05-2.37-1.83-2.64Zm-4.02-1.41c-.51-.18-.82-.35-.82-1.22 0-.71.53-1.28 1.19-1.28h.65v2.86l-1.02-.36Zm3.16 5.33h-.65v-2.86l1.01.35c.51.18.82.35.82 1.22 0 .71-.53 1.29-1.18 1.29Z" />
    </svg>
  );
}

/** What Apple Books already holds - the other way into the library. */
export function ShelfIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M20.5 7v8H6.35c-1.57 0-2.85 1.28-2.85 2.85V7c0-4 1-5 5-5h7c4 0 5 1 5 5Z" />
      <path d="M20.5 15v3.5c0 1.93-1.57 3.5-3.5 3.5H7c-1.93 0-3.5-1.57-3.5-3.5v-.65C3.5 16.28 4.78 15 6.35 15H20.5ZM16 7.75H8c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h8c.41 0 .75.34.75.75s-.34.75-.75.75ZM13 11.25H8c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h5c.41 0 .75.34.75.75s-.34.75-.75.75Z" />
    </svg>
  );
}

export function CheckIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10Z" />
      <path d="M10.58 15.582a.75.75 0 0 1-.53-.22l-2.83-2.83a.754.754 0 0 1 0-1.06c.29-.29.77-.29 1.06 0l2.3 2.3 5.14-5.14c.29-.29.77-.29 1.06 0 .29.29.29.77 0 1.06l-5.67 5.67a.75.75 0 0 1-.53.22Z" />
    </svg>
  );
}

/** Two stacked bars parted by a dashed line: the space BETWEEN lines, which
 * is what the slider beside it sets. Its horizontal twin is `MarginsIcon`;
 * they sit one under the other in the same form, so they are one pair from
 * one family rather than two glyphs that happen to mean spacing. */
export function LineSpacingIcon({ className }: { className?: string }) {
  return (
    <svg {...outline} className={className}>
      <path d="M17.4 20H6.6c-1.92 0-2.85-.98-2.85-2.98v-1.04c0-2 .93-2.98 2.85-2.98h10.8c1.92 0 2.85.98 2.85 2.98v1.04c0 2-.93 2.98-2.85 2.98ZM6.6 14.5c-1.01 0-1.35.21-1.35 1.48v1.04c0 1.27.34 1.48 1.35 1.48h10.8c1.01 0 1.35-.21 1.35-1.48v-1.04c0-1.27-.34-1.48-1.35-1.48H6.6ZM15.4 11.5H8.6c-1.92 0-2.85-.98-2.85-2.98V7.48c0-2.01.93-2.98 2.85-2.98h6.8c1.92 0 2.85.98 2.85 2.98v1.04c0 2-.93 2.98-2.85 2.98ZM8.6 6c-1.01 0-1.35.21-1.35 1.48v1.04c0 1.27.34 1.48 1.35 1.48h6.8c1.01 0 1.35-.21 1.35-1.48V7.48c0-1.27-.34-1.48-1.35-1.48H8.6Z" />
      <path d="M12 22.752c-.41 0-.75-.34-.75-.75v-2.4c0-.41.34-.75.75-.75s.75.34.75.75v2.4c0 .41-.34.75-.75.75ZM12 13.75c-.41 0-.75-.34-.75-.75v-2c0-.41.34-.75.75-.75s.75.34.75.75v2c0 .41-.34.75-.75.75ZM12 5.44c-.41 0-.75-.34-.75-.75V2a.749.749 0 1 1 1.5 0v2.69c0 .42-.34.75-.75.75Z" />
    </svg>
  );
}

/** The same glyph turned on its side: two bars parted horizontally, which is
 * what a margin is - the room left at the sides of the text. */
export function MarginsIcon({ className }: { className?: string }) {
  return (
    <svg {...outline} className={className}>
      <path d="M8.02 20.25H6.98C4.97 20.25 4 19.32 4 17.4V6.6c0-1.92.98-2.85 2.98-2.85h1.04c2 0 2.98.93 2.98 2.85v10.8c0 1.92-.98 2.85-2.98 2.85Zm-1.04-15c-1.27 0-1.48.34-1.48 1.35v10.8c0 1.01.21 1.35 1.48 1.35h1.04c1.27 0 1.48-.34 1.48-1.35V6.6c0-1.01-.21-1.35-1.48-1.35H6.98ZM16.52 18.25h-1.04c-2.01 0-2.98-.93-2.98-2.85V8.6c0-1.92.98-2.85 2.98-2.85h1.04c2.01 0 2.98.93 2.98 2.85v6.8c0 1.92-.98 2.85-2.98 2.85Zm-1.04-11c-1.27 0-1.48.34-1.48 1.35v6.8c0 1.01.21 1.35 1.48 1.35h1.04c1.27 0 1.48-.34 1.48-1.35V8.6c0-1.01-.21-1.35-1.48-1.35h-1.04Z" />
      <path d="M4.4 12.75H2a.749.749 0 1 1 0-1.5h2.4a.749.749 0 1 1 0 1.5ZM13 12.75h-2c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h2c.41 0 .75.34.75.75s-.34.75-.75.75ZM22 12.75h-2.7c-.41 0-.75-.34-.75-.75s.34-.75.75-.75H22a.749.749 0 1 1 0 1.5Z" />
    </svg>
  );
}

/** A screen: this Mac. On the voice filters it marks the voices that run
 * HERE - the distinction the icon carries is not which company made a voice
 * but where it is spoken, which is what decides whether the words leave the
 * machine and whether they cost money. Its opposite is `CloudIcon`. */
export function MonitorIcon({ className }: { className?: string }) {
  return (
    <svg {...outline} className={className}>
      <path d="M17.56 17.97H6.44c-3.98 0-5.19-1.21-5.19-5.19V6.44c0-3.98 1.21-5.19 5.19-5.19h11.11c3.98 0 5.19 1.21 5.19 5.19v6.33c.01 3.99-1.2 5.2-5.18 5.2ZM6.44 2.75c-3.14 0-3.69.55-3.69 3.69v6.33c0 3.14.55 3.69 3.69 3.69h11.11c3.14 0 3.69-.55 3.69-3.69V6.44c0-3.14-.55-3.69-3.69-3.69H6.44Z" />
      <path d="M12 22.749c-.41 0-.75-.34-.75-.75v-4.78c0-.41.34-.75.75-.75s.75.34.75.75v4.78c0 .41-.34.75-.75.75ZM22 13.75H2c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h20c.41 0 .75.34.75.75s-.34.75-.75.75Z" />
      <path d="M16.5 22.75h-9c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h9c.41 0 .75.34.75.75s-.34.75-.75.75Z" />
    </svg>
  );
}

/** Spoken somewhere else, over the network, on your key. Deliberately the
 * SAME glyph for every paid provider: the word beside it already says which
 * company, and an icon invented to tell OpenAI from ElevenLabs would carry
 * no meaning at all. What it does carry is the thing they have in common and
 * the reader needs to know. */
export function CloudIcon({ className }: { className?: string }) {
  return (
    <svg {...outline} className={className}>
      <path d="M16.68 20.831H5.55c-2.94-.21-4.26-2.47-4.26-4.49 0-1.8 1.05-3.8 3.34-4.35-.64-2.5-.1-4.85 1.53-6.55 1.85-1.94 4.82-2.71 7.37-1.92 2.34.72 3.99 2.65 4.59 5.33 2.05.46 3.68 2.01 4.34 4.15.71 2.33.07 4.72-1.68 6.25a6.128 6.128 0 0 1-4.1 1.58Zm-11.11-7.48h-.02c-1.9.14-2.77 1.6-2.77 2.99 0 1.39.87 2.85 2.81 2.99h11.04c1.16-.02 2.27-.42 3.13-1.2 1.56-1.37 1.67-3.32 1.25-4.69-.42-1.38-1.59-2.94-3.63-3.2a.753.753 0 0 1-.65-.62c-.4-2.4-1.7-4.06-3.65-4.66-2.03-.62-4.37-.01-5.84 1.52-1.33 1.39-1.71 3.31-1.09 5.42.51.07 1 .22 1.45.45.37.19.52.64.33 1.01a.75.75 0 0 1-1.01.33 2.88 2.88 0 0 0-1.31-.32c-.01-.02-.02-.02-.04-.02Z" />
      <path d="M15.848 10.67c-.28 0-.54-.15-.67-.42a.754.754 0 0 1 .34-1.01c.62-.31 1.31-.48 1.99-.49.4-.01.76.32.76.74.01.41-.32.76-.74.76-.46.01-.93.12-1.35.33-.11.06-.22.09-.33.09Z" />
    </svg>
  );
}

/** The two the source set draws as a PAIR - one symbol turned two ways -
 * which is what a filter over one dimension needs. Picking two unrelated
 * glyphs for male and female would have read as two different questions. */
export function ManIcon({ className }: { className?: string }) {
  return (
    <svg {...outline} className={className}>
      <path d="M10.25 22.25c-4.69 0-8.5-3.81-8.5-8.5 0-4.69 3.81-8.5 8.5-8.5 4.69 0 8.5 3.81 8.5 8.5 0 4.69-3.81 8.5-8.5 8.5Zm0-15.5c-3.86 0-7 3.14-7 7s3.14 7 7 7 7-3.14 7-7-3.14-7-7-7Z" />
      <path d="M16 8.751c-.19 0-.38-.07-.53-.22a.754.754 0 0 1 0-1.06l5.5-5.5c.29-.29.77-.29 1.06 0 .29.29.29.77 0 1.06l-5.5 5.5c-.15.15-.34.22-.53.22Z" />
      <path d="M21.5 9.75c-.41 0-.75-.34-.75-.75V3.25H15c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h6.5c.41 0 .75.34.75.75V9c0 .41-.34.75-.75.75Z" />
    </svg>
  );
}

export function WomanIcon({ className }: { className?: string }) {
  return (
    <svg {...outline} className={className}>
      <path d="M12 16.75c-4.27 0-7.75-3.48-7.75-7.75S7.73 1.25 12 1.25 19.75 4.73 19.75 9s-3.48 7.75-7.75 7.75Zm0-14c-3.45 0-6.25 2.8-6.25 6.25s2.8 6.25 6.25 6.25 6.25-2.8 6.25-6.25-2.8-6.25-6.25-6.25Z" />
      <path d="M12 22.75c-.41 0-.75-.34-.75-.75v-6c0-.41.34-.75.75-.75s.75.34.75.75v6c0 .41-.34.75-.75.75Z" />
      <path d="M15 19.75H9c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h6c.41 0 .75.34.75.75s-.34.75-.75.75Z" />
    </svg>
  );
}

/** Undo, in the source's outline manner (owner, 06/09: an outline glyph
 * here). A counter-clockwise arrow says "put it back the way it was", which
 * is what this button does; the circular refresh in the same set means
 * "load it again", which is a different promise. */
export function ResetIcon({ className }: { className?: string }) {
  return (
    <svg {...outline} className={className}>
      <path d="M12 22.75c-5.2 0-9.42-4.23-9.42-9.42 0-1.87.55-3.68 1.59-5.24.23-.34.7-.44 1.04-.21.34.23.44.7.21 1.04a7.925 7.925 0 006.59 12.32c4.37 0 7.92-3.55 7.92-7.92S16.37 5.4 12 5.4c-.92 0-1.82.13-2.67.39a.75.75 0 01-.94-.5c-.12-.4.1-.82.5-.94 1-.3 2.04-.46 3.11-.46 5.2 0 9.42 4.23 9.42 9.42 0 5.19-4.22 9.44-9.42 9.44z" />
      <path d="M7.87 6.07a.748.748 0 01-.57-1.24l2.89-3.32c.27-.31.75-.35 1.06-.07.31.27.34.75.07 1.06L8.43 5.81c-.15.17-.36.26-.56.26z" />
      <path d="M11.24 8.53c-.15 0-.31-.05-.44-.14L7.42 5.92a.751.751 0 01.89-1.21l3.37 2.46c.33.24.41.71.16 1.05a.71.71 0 01-.6.31z" />
    </svg>
  );
}

export function LockIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path d="M18.75 8v2.1c-.44-.06-.94-.09-1.5-.1V8c0-3.15-.89-5.25-5.25-5.25S6.75 4.85 6.75 8v2c-.56.01-1.06.04-1.5.1V8c0-2.9.7-6.75 6.75-6.75S18.75 5.1 18.75 8Z" />
      <path opacity={MASS} d="M22 15v2c0 4-1 5-5 5H7c-4 0-5-1-5-5v-2c0-3.34.7-4.59 3.25-4.9.44-.06.94-.09 1.5-.1h10.5c.56.01 1.06.04 1.5.1C21.3 10.41 22 11.66 22 15Z" />
      <path d="M8 16.999c-.13 0-.26-.03-.38-.08-.13-.05-.23-.12-.33-.21-.18-.19-.29-.45-.29-.71 0-.13.03-.26.08-.38s.12-.23.21-.33c.1-.09.2-.16.33-.21.37-.16.81-.07 1.09.21.09.1.16.21.21.33.05.12.08.25.08.38 0 .26-.11.52-.29.71-.19.18-.45.29-.71.29ZM12 17c-.27 0-.52-.11-.71-.29-.09-.1-.16-.21-.21-.33A.995.995 0 0 1 11 16c0-.27.11-.52.29-.71.37-.37 1.04-.37 1.42 0 .18.19.29.44.29.71 0 .13-.03.26-.08.38s-.12.23-.21.33c-.19.18-.45.29-.71.29ZM16 17c-.26 0-.52-.11-.71-.29-.18-.19-.29-.44-.29-.71 0-.27.11-.52.29-.71.38-.37 1.05-.37 1.42 0 .04.05.08.1.12.16.04.05.07.11.09.17.03.06.05.12.06.18.01.07.02.14.02.2 0 .26-.11.52-.29.71-.19.18-.45.29-.71.29Z" />
    </svg>
  );
}

export function ImportIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M20.5 10.19h-2.89c-2.37 0-4.3-1.93-4.3-4.3V3c0-.55-.45-1-1-1H8.07C4.99 2 2.5 4 2.5 7.57v8.86C2.5 20 4.99 22 8.07 22h7.86c3.08 0 5.57-2 5.57-5.57v-5.24c0-.55-.45-1-1-1Z" />
      <path d="M15.8 2.21c-.41-.41-1.12-.13-1.12.44v3.49c0 1.46 1.24 2.67 2.75 2.67.95.01 2.27.01 3.4.01.57 0 .87-.67.47-1.07-1.44-1.45-4.02-4.06-5.5-5.54ZM12.28 14.72a.754.754 0 0 0-1.06 0l-.72.72v-4.19c0-.41-.34-.75-.75-.75s-.75.34-.75.75v4.19l-.72-.72a.754.754 0 0 0-1.06 0c-.29.29-.29.77 0 1.06l2 2c.01.01.02.01.02.02.06.06.14.11.22.15.1.03.19.05.29.05.1 0 .19-.02.28-.06.09-.04.17-.09.25-.16l2-2c.29-.29.29-.77 0-1.06Z" />
    </svg>
  );
}

export function SyncIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M22 7.81v8.37c0 3.64-2.17 5.81-5.81 5.81H7.81C4.17 22 2 19.83 2 16.19V7.81C2 4.17 4.17 2 7.81 2h8.37C19.83 2 22 4.17 22 7.81z" />
      <path d="M12 18.25c-1.79 0-3.19-.89-4.14-1.77v.71c0 .41-.34.75-.75.75s-.75-.34-.75-.75v-2.75c0-.41.34-.75.75-.75h2.48c.41 0 .75.34.75.75s-.34.75-.75.75h-.9c.74.74 1.89 1.56 3.31 1.56 2.62 0 4.75-2.13 4.75-4.75 0-.41.34-.75.75-.75s.75.34.75.75c0 3.45-2.8 6.25-6.25 6.25zm-5.5-5.5c-.41 0-.75-.34-.75-.75 0-3.45 2.8-6.25 6.25-6.25 2.15 0 3.73.93 4.75 1.82v-.76c0-.41.34-.75.75-.75s.75.34.75.75V9.63a.75.75 0 01-.3.54c-.07.05-.15.09-.24.12-.07.02-.14.03-.21.03h-2.43c-.41 0-.75-.34-.75-.75s.34-.75.75-.75h.83c-.8-.74-2.09-1.56-3.88-1.56-2.62 0-4.75 2.13-4.75 4.75-.02.4-.36.74-.77.74z" />
    </svg>
  );
}

export function SpeakerIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path d="M18 16.75a.75.75 0 0 1-.6-1.2 5.94 5.94 0 0 0 0-7.1.75.75 0 0 1 1.2-.9c1.96 2.62 1.96 6.28 0 8.9-.15.2-.37.3-.6.3Z" />
      <path d="M19.828 19.25a.75.75 0 0 1-.6-1.2c2.67-3.56 2.67-8.54 0-12.1a.75.75 0 0 1 1.2-.9c3.07 4.09 3.07 9.81 0 13.9-.14.2-.37.3-.6.3Z" />
      <path opacity={MASS} d="M15.75 7.412v9.18c0 1.72-.62 3.01-1.73 3.63a3 3 0 0 1-1.47.37c-.8 0-1.66-.27-2.54-.82l-2.92-1.83c-.2-.12-.43-.19-.66-.19H5.5v-11.5h.93c.23 0 .46-.07.66-.19l2.92-1.83c1.46-.91 2.89-1.07 4.01-.45 1.11.62 1.73 1.91 1.73 3.63Z" />
      <path d="M5.5 6.25v11.5H5c-2.42 0-3.75-1.33-3.75-3.75v-4c0-2.42 1.33-3.75 3.75-3.75h.5Z" />
    </svg>
  );
}

export function HighlightIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path d="M6 2h12c1.1 0 2 .9 2 2v4.32H4V4c0-1.1.9-2 2-2Z" />
      <path opacity={MASS} d="M4 8.32v3.56c0 1.08.58 2.08 1.53 2.61l2.96 1.67c.63.35 1.02 1.02 1.02 1.74V20c0 1.1.9 2 2 2h1c1.1 0 2-.9 2-2v-2.1c0-.72.39-1.39 1.02-1.74l2.96-1.67c.94-.53 1.53-1.53 1.53-2.61V8.32H4Z" />
    </svg>
  );
}


/** The Apple Books app mark.
 *
 * The app's ICON, not the Apple logo: it names the product rather than the
 * company, and its colour makes it legible at 20px where a monochrome
 * silhouette turned to a smudge. Owner supplied the asset (03/09).
 *
 * The only icon here that is neither 16px nor `currentColor` - a product mark
 * is a picture of a thing, so it keeps its own geometry and its own colours,
 * the way a book cover does. Paths are Apple's, carried verbatim; the mask in
 * the original only clipped the gradient to the squircle, which filling the
 * squircle path directly does without the extra nodes.
 *
 * The gradient id comes from `useId`: two cards on one shelf mean two copies
 * of this svg in one document, and a hardcoded id would be duplicated - both
 * would then resolve to whichever came first.
 */
export function AppleBooksIcon({ className }: { className?: string }) {
  const gradient = `${useId()}-books`;
  return (
    <svg viewBox="0 0 240 240" className={className} aria-hidden="true">
      <defs>
        <linearGradient x1="50%" y1="0%" x2="50%" y2="100%" id={gradient}>
          <stop stopColor="#FFA800" offset="0%" />
          <stop stopColor="#F9671E" offset="100%" />
        </linearGradient>
      </defs>
      <path
        fill={`url(#${gradient})`}
        d="M240,75.0750762 C240,72.208641 240,69.3422058 239.983807,66.4757706 C239.969158,64.061215 239.941267,61.6472453 239.875993,59.2332756 C239.733843,53.9754881 239.42423,48.6715283 238.490002,43.4719837 C237.541476,38.1921647 235.99271,33.2782089 233.550614,28.4814417 C231.15176,23.7697535 228.018251,19.458499 224.27993,15.7200629 C220.541023,11.9811579 216.229063,8.84729816 211.516553,6.44844581 C206.722244,4.0078743 201.810864,2.45957742 196.53409,1.51105222 C191.33255,0.576120903 186.026713,0.266156836 180.766814,0.124006964 C178.352843,0.0588500558 175.938872,0.0309591493 173.524198,0.0161933752 C170.657762,0 167.791325,0 164.924889,0 L75.0751113,0 C72.2085576,0 69.3421211,0 66.4756845,0.0161933752 C64.0611278,0.0309591493 61.647157,0.0588500558 59.2331862,0.124006964 C53.9732868,0.266156836 48.6674495,0.576120903 43.4659102,1.51105222 C38.1890185,2.45957742 33.2777557,4.0078743 28.4834472,6.44844581 C23.7709365,8.84729816 19.4588597,11.9811579 15.7200702,15.7200629 C11.9817495,19.458499 8.84812262,23.7697535 6.44938635,28.4814417 C4.00729023,33.2782089 2.45852387,38.1921647 1.50999823,43.4719837 C0.575769607,48.6715283 0.266039772,53.9754881 0.124007022,59.2332756 C0.0587328947,61.6472453 0.030841975,64.061215 0.0161933828,66.4757706 C0,69.3422058 0,72.208641 0,75.0750762 L0,164.924929 C0,167.791364 0,170.657799 0.0161933828,173.524234 C0.030841975,175.93879 0.0587328947,178.352759 0.124007022,180.766729 C0.266039772,186.024517 0.575769607,191.328476 1.50999823,196.528138 C2.45852387,201.80784 4.00729023,206.721679 6.44938635,211.518563 C8.84812262,216.230368 11.9817495,220.541506 15.7200702,224.279825 C19.4588597,228.01873 23.7709365,231.152707 28.4834472,233.551559 C33.2777557,235.992248 38.1890185,237.54031 43.4659102,238.488835 C48.6674495,239.423884 53.9732868,239.733848 59.2331862,239.875998 C61.647157,239.941155 64.0611278,239.969046 66.4756845,239.983811 C69.3421211,240 72.2085576,240 75.0751113,240 L164.924889,240 C167.791325,240 170.657762,240 173.524198,239.983811 C175.938872,239.969046 178.352843,239.941155 180.766814,239.875998 C186.026713,239.733848 191.33255,239.423884 196.53409,238.488835 C201.810864,237.54031 206.722244,235.992248 211.516553,233.551559 C216.229063,231.152707 220.541023,228.01873 224.27993,224.279825 C228.018251,220.541506 231.15176,216.230368 233.550614,211.518563 C235.99271,206.721679 237.541476,201.80784 238.490002,196.528138 C239.42423,191.328476 239.733843,186.024517 239.875993,180.766729 C239.941267,178.352759 239.969158,175.93879 239.983807,173.524234 C240,170.657799 240,167.791364 240,164.924929 L240,75.0750762 Z"
      />
      <path
        fill="#FFFFFF"
        fillRule="nonzero"
        d="M195.58388,181.640625 C198.361762,181.640625 200,179.930321 200,177.364865 L200,78.3810177 C200,76.171875 199.928772,75.316723 199.145267,74.0339949 C191.80881,61.9193412 175.497657,55.078125 160.041237,55.078125 C146.009372,55.078125 132.903468,60.4940878 125.353327,70.3283361 C124.142455,71.9673775 124,72.4662162 124,74.1765203 L124,177.151077 C124,178.790118 125.139644,179.859058 126.564199,179.859058 C127.347704,179.859058 128.202437,179.574008 128.914714,178.932644 C135.752577,173.017842 146.009372,168.243243 158.118088,168.243243 C170.582943,168.243243 182.97657,172.16269 191.666354,180.072846 C192.805998,181.070524 194.01687,181.640625 195.58388,181.640625 Z M44.41612,181.640625 C41.6382381,181.640625 40,179.930321 40,177.364865 L40,78.3810177 C40,76.171875 40.0712277,75.316723 40.8547329,74.0339949 C48.1911903,61.9193412 64.502343,55.078125 79.9587629,55.078125 C93.9906279,55.078125 107.096532,60.4940878 114.646673,70.3283361 C115.857545,71.9673775 116,72.4662162 116,74.1765203 L116,177.151077 C116,178.790118 114.860356,179.859058 113.435801,179.859058 C112.652296,179.859058 111.797563,179.574008 111.085286,178.932644 C104.247423,173.017842 93.9906279,168.243243 81.8819119,168.243243 C69.4170572,168.243243 57.0234302,172.16269 48.3336457,180.072846 C47.1940019,181.070524 45.9831303,181.640625 44.41612,181.640625 Z"
      />
    </svg>
  );
}
