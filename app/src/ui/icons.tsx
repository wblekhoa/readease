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
 * Drawn here rather than imported. DOL canon sources icons from DS Studio's
 * DsIcon, and that registry is not consumable outside the DS repo (same gap
 * as ToggleButtonGroup); `@dol/icons-library` is not a dependency of this
 * app. Every glyph below is drawn in this file.
 *
 * They are a SET, so weight and proportion are decided across the set and
 * not per glyph: reworking one in isolation is how a set stops looking like
 * one. `CloseIcon` and `SlidersIcon` are the evidence - both had to be
 * redrawn after being looked at next to the others at the real size.
 */

const bulk = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "currentColor",
  "aria-hidden": true,
};

/** The 40% layer. A constant so no icon quietly picks its own weight. */
const MASS = 0.4;

export function BookIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M22 4.1v12.4c0 1-.8 1.9-1.8 2-2 .2-4.9 1.2-6.7 2.2-.3.2-.7-.1-.7-.5V4.5c0-.2.1-.4.3-.5 1.8-1 4.8-2 6.9-2.2C21.1 1.7 22 2.6 22 3.7v.4Z" />
      <path d="M11.2 4v16.2c0 .4-.4.7-.7.5-1.8-1-4.7-2-6.7-2.2-1-.1-1.8-1-1.8-2V3.7c0-1.1.9-2 2-1.9 2.1.2 5.1 1.2 6.9 2.2.2.1.3.3.3.5v-.5Z" />
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
      <path opacity={MASS} d="M20.4 6.4c-1.8-.2-3.6-.3-5.4-.4v-.6c0-1-.1-1.6-.4-2-.4-.5-1.1-.6-2.3-.6h-.6c-1.2 0-1.9.1-2.3.6-.3.4-.4 1-.4 2v.6c-1.8.1-3.6.2-5.4.4l-.5.1a.8.8 0 0 0 .1 1.5h.1c5.2-.5 10.4-.3 15.6.2h.1a.8.8 0 0 0 .1-1.5l-.7-.3Z" />
      <path d="M19.4 9.3a.9.9 0 0 0-.7-.3H5.3a.9.9 0 0 0-.9 1l.6 9.4c.1 1.7.3 3.6 3.9 3.6h6.2c3.6 0 3.8-1.9 3.9-3.6l.6-9.4a.9.9 0 0 0-.2-.7ZM14 18.2h-4a.8.8 0 0 1 0-1.5h4a.8.8 0 0 1 0 1.5Zm1-4H9a.8.8 0 0 1 0-1.5h6a.8.8 0 0 1 0 1.5Z" />
    </svg>
  );
}

export function ChevronLeftIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path d="M14.7 20.7c-.2 0-.4-.1-.6-.2l-6.5-6.5a2.8 2.8 0 0 1 0-4l6.5-6.5a.8.8 0 0 1 1.1 1.1l-6.5 6.5c-.5.5-.5 1.3 0 1.8l6.5 6.5a.8.8 0 0 1-.5 1.3Z" />
    </svg>
  );
}

export function ChevronRightIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path d="M9.3 20.7a.8.8 0 0 1-.5-1.3l6.5-6.5c.5-.5.5-1.3 0-1.8L8.8 4.6a.8.8 0 0 1 1.1-1.1l6.5 6.5c1.1 1.1 1.1 2.9 0 4l-6.5 6.5c-.2.1-.4.2-.6.2Z" />
    </svg>
  );
}

export function ChevronDownIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path d="M12 15.7c-.7 0-1.4-.3-2-.8l-5.6-5.6a.8.8 0 0 1 1.1-1.1l5.6 5.6c.5.5 1.3.5 1.8 0l5.6-5.6a.8.8 0 0 1 1.1 1.1L14 14.9c-.6.5-1.3.8-2 .8Z" />
    </svg>
  );
}

export function PlayIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M4.5 12V6.9c0-3.2 2.3-4.5 5-2.9l4.4 2.6 4.4 2.5c2.7 1.6 2.7 4.2 0 5.8l-4.4 2.5-4.4 2.6c-2.7 1.6-5 .3-5-2.9V12Z" />
      <path d="M18.3 8.6 13.9 6.1 9.5 3.5C7.6 2.4 6 3 5.5 4.6c1 .2 2 .7 3 1.3l4.4 2.6 4.4 2.5c1 .6 1.8 1.3 2.3 2.1.9-1.6.3-3.5-1.3-4.5Z" />
    </svg>
  );
}

export function PauseIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M10.7 4v16c0 1.1-.5 1.5-1.7 1.5H5.7C4.5 21.5 4 21.1 4 20V4c0-1.1.5-1.5 1.7-1.5H9c1.2 0 1.7.4 1.7 1.5Z" />
      <path d="M20 4v16c0 1.1-.5 1.5-1.7 1.5H15c-1.2 0-1.7-.4-1.7-1.5V4c0-1.1.5-1.5 1.7-1.5h3.3c1.2 0 1.7.4 1.7 1.5Z" />
    </svg>
  );
}

export function StopIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M16.2 2H7.8C4.2 2 2 4.2 2 7.8v8.4C2 19.8 4.2 22 7.8 22h8.4c3.6 0 5.8-2.2 5.8-5.8V7.8C22 4.2 19.8 2 16.2 2Z" />
      <path d="M15 8.3v7.4c0 .9-.4 1.3-1.3 1.3h-3.4c-.9 0-1.3-.4-1.3-1.3V8.3C9 7.4 9.4 7 10.3 7h3.4c.9 0 1.3.4 1.3 1.3Z" />
    </svg>
  );
}

export function PreviousIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M19.5 12v5.1c0 3.2-2.3 4.5-5 2.9l-4.4-2.6-4.4-2.5c-2.7-1.6-2.7-4.2 0-5.8l4.4-2.5 4.4-2.6c2.7-1.6 5-.3 5 2.9V12Z" />
      <path d="M4.7 20.4a.8.8 0 0 1-.8-.8V4.4a.8.8 0 0 1 1.6 0v15.2c0 .4-.4.8-.8.8Z" />
    </svg>
  );
}

export function NextIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M4.5 12V6.9c0-3.2 2.3-4.5 5-2.9l4.4 2.6 4.4 2.5c2.7 1.6 2.7 4.2 0 5.8l-4.4 2.5-4.4 2.6c-2.7 1.6-5 .3-5-2.9V12Z" />
      <path d="M19.3 20.4a.8.8 0 0 1-.8-.8V4.4a.8.8 0 0 1 1.6 0v15.2c0 .4-.4.8-.8.8Z" />
    </svg>
  );
}

/** The table of contents: a closed book, from the DOL icon library (owner
 * picked it, 04/09). Distinct from `BookIcon`, which is the OPEN book naming
 * the library tab - one is a place to go, this one is what a book has inside.
 * It replaced a sidebar glyph that described the PANEL rather than what the
 * panel holds.
 *
 * Also redrawn once against the library's geometry: the first pass ran the
 * cover to the full 24 box and butted the page block against it in a straight
 * line. The cover is inset (3.5 to 20.5) and the block NOTCHES into it on the
 * left, which is what gives the two parts a join instead of a seam.
 */
export function BookClosedIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path
        opacity={MASS}
        d="M20.5 7v8H6.4a2.9 2.9 0 0 0-2.9 2.9V7c0-4 1-5 5-5h7c4 0 5 1 5 5Z"
      />
      <path d="M20.5 15v3.5a3.5 3.5 0 0 1-3.5 3.5H7a3.5 3.5 0 0 1-3.5-3.5v-.6A2.9 2.9 0 0 1 6.4 15h14.1Z" />
      <path d="M16 7.75H8a.75.75 0 0 1 0-1.5h8a.75.75 0 0 1 0 1.5Zm-3 3.5H8a.75.75 0 0 1 0-1.5h5a.75.75 0 0 1 0 1.5Z" />
    </svg>
  );
}

export function PagesIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M10.8 3.5v17c0 1-.9 1.7-1.9 1.5-1.6-.2-3.2-.6-4.6-1.2-1-.4-1.6-1.4-1.6-2.5V5.2c0-1.6 1.4-2.7 3-2.5 1.1.1 2.2.4 3.3.7.9.3 1.8 1.1 1.8 2.1Z" />
      <path d="M21.3 5.2v13.1c0 1.1-.6 2.1-1.6 2.5-1.4.6-3 1-4.6 1.2-1 .2-1.9-.5-1.9-1.5v-17c0-1 .9-1.8 1.8-2.1 1.1-.3 2.2-.6 3.3-.7 1.6-.2 3 .9 3 2.5Z" />
    </svg>
  );
}

export function ScrollIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M17 2H7C4.2 2 3 3.6 3 6v12c0 2.4 1.2 4 4 4h10c2.8 0 4-1.6 4-4V6c0-2.4-1.2-4-4-4Z" />
      <path d="M16.5 8.8h-9a.8.8 0 0 1 0-1.6h9a.8.8 0 0 1 0 1.6Zm0 4h-9a.8.8 0 0 1 0-1.6h9a.8.8 0 0 1 0 1.6Zm-4 4h-5a.8.8 0 0 1 0-1.6h5a.8.8 0 0 1 0 1.6Z" />
    </svg>
  );
}

export function InfoIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Z" />
      <path d="M12 13.4a.8.8 0 0 1-.8-.8V8a.8.8 0 0 1 1.6 0v4.6c0 .4-.4.8-.8.8Zm0 3.4a1.1 1.1 0 1 1 0-2.2 1.1 1.1 0 0 1 0 2.2Z" />
    </svg>
  );
}

export function SlidersIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M21 6.8H3a1 1 0 0 1 0-2h18a1 1 0 0 1 0 2Zm0 6.2H3a1 1 0 0 1 0-2h18a1 1 0 0 1 0 2Zm0 6.2H3a1 1 0 0 1 0-2h18a1 1 0 0 1 0 2Z" />
      <path d="M15.5 8.7a2.9 2.9 0 1 1 0-5.8 2.9 2.9 0 0 1 0 5.8Zm-7 6.2a2.9 2.9 0 1 1 0-5.8 2.9 2.9 0 0 1 0 5.8Zm8.5 6.2a2.9 2.9 0 1 1 0-5.8 2.9 2.9 0 0 1 0 5.8Z" />
    </svg>
  );
}

export function SunIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M12 18.2a6.2 6.2 0 1 0 0-12.4 6.2 6.2 0 0 0 0 12.4Z" />
      <path d="M12 4.3a.8.8 0 0 1-.8-.8V2a.8.8 0 0 1 1.6 0v1.5c0 .4-.4.8-.8.8Zm0 18a.8.8 0 0 1-.8-.8v-1.5a.8.8 0 0 1 1.6 0v1.5c0 .4-.4.8-.8.8ZM21.5 12.8H20a.8.8 0 0 1 0-1.6h1.5a.8.8 0 0 1 0 1.6Zm-17.5 0H2.5a.8.8 0 0 1 0-1.6H4a.8.8 0 0 1 0 1.6ZM18.4 6.4a.8.8 0 0 1-.6-1.4l1-1a.8.8 0 0 1 1.1 1.1l-1 1c-.1.2-.3.3-.5.3ZM4.6 20.2a.8.8 0 0 1-.6-1.4l1-1a.8.8 0 0 1 1.1 1.1l-1 1c-.1.2-.3.3-.5.3Zm14.8 0c-.2 0-.4-.1-.6-.2l-1-1a.8.8 0 0 1 1.1-1.1l1 1a.8.8 0 0 1-.5 1.3ZM5.6 6.4c-.2 0-.4-.1-.6-.2l-1-1a.8.8 0 0 1 1.1-1.1l1 1a.8.8 0 0 1-.5 1.3Z" />
    </svg>
  );
}

export function MoonIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M21.5 14.9a9.8 9.8 0 0 1-12.4-12 .9.9 0 0 0-1.2-1.1A10.9 10.9 0 0 0 12 22.9a10.9 10.9 0 0 0 10.6-6.8.9.9 0 0 0-1.1-1.2Z" />
      <path d="M18.2 6.3l1-.4-1-.4-.4-1-.4 1-1 .4 1 .4.4 1 .4-1Z" />
    </svg>
  );
}

export function ClipboardIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M17 4.2h-1.4c.1.3.1.6.1.9v1.1c0 1.1-.9 2-2 2h-3.4c-1.1 0-2-.9-2-2V5.1c0-.3 0-.6.1-.9H7c-2.2 0-4 1.8-4 4v9.7c0 2.2 1.8 4 4 4h10c2.2 0 4-1.8 4-4V8.2c0-2.2-1.8-4-4-4Z" />
      <path d="M14.2 5.1v1.1c0 .5-.4.9-.9.9h-3.4c-.5 0-.9-.4-.9-.9V5.1c0-1.1.9-2 2-2h1.2c1.1 0 2 .9 2 2Z" />
    </svg>
  );
}

export function CursorTextIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M12 21.5a.8.8 0 0 1-.8-.8V3.3a.8.8 0 0 1 1.6 0v17.4c0 .4-.4.8-.8.8Z" />
      <path d="M15 4.3h-6a.8.8 0 0 1 0-1.6h6a.8.8 0 0 1 0 1.6Zm0 17h-6a.8.8 0 0 1 0-1.6h6a.8.8 0 0 1 0 1.6Z" />
    </svg>
  );
}

export function TransferIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M20.5 8.5H6.2a.8.8 0 0 1 0-1.6h14.3a.8.8 0 0 1 0 1.6Zm-2.7 8.6H3.5a.8.8 0 0 1 0-1.6h14.3a.8.8 0 0 1 0 1.6Z" />
      <path d="M8.4 11.6a.8.8 0 0 1-.6-.2L4.2 7.8a.8.8 0 0 1 0-1.1l3.6-3.6a.8.8 0 0 1 1.1 1.1L5.9 7.2l3 3a.8.8 0 0 1-.5 1.4Zm7.2 9.3a.8.8 0 0 1-.6-1.4l3-3-3-3a.8.8 0 0 1 1.1-1.1l3.6 3.6a.8.8 0 0 1 0 1.1l-3.6 3.6c-.1.1-.3.2-.5.2Z" />
    </svg>
  );
}

/** Notes and highlights: the sticky note from the DOL icon library, in bulk
 * (owner picked it, 04/09).
 *
 * Two earlier drawings were thrown away. Bulk with two lines on a rounded
 * rectangle was `ScrollIcon` minus one line, and the two stand a few pixels
 * apart in the same header. Line weight fixed that by leaving the manner of
 * the set - and cost something in NotesPanel, where an outline note read
 * quieter beside the filled highlight pen, backwards for the row that carries
 * more.
 *
 * A third was thrown away for being WRONG: the peel was drawn as a square
 * corner filling a mid-point notch. Measured against the library's own
 * geometry, the note's outer corner turns on a radius nearly twice the
 * square's own (8.9 against 5) and the notch sits at 13.1, not the middle -
 * that big outer arc is the whole reason it reads as paper lifting rather
 * than as a tile with a bite out of it (owner, 04/09: "tôi thấy nó sai sai").
 * Body and fold share the notch exactly, reversed, so they nest with no seam.
 */
export function NoteIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path
        opacity={MASS}
        d="M22 7v3.9a2.2 2.2 0 0 1-2.2 2.2h-2.2a4.5 4.5 0 0 0-4.5 4.5v2.2a2.2 2.2 0 0 1-2.2 2.2H7a5 5 0 0 1-5-5V7a5 5 0 0 1 5-5h10a5 5 0 0 1 5 5Z"
      />
      <path d="M22 10.9v2.2a8.9 8.9 0 0 1-8.9 8.9h-2.2a2.2 2.2 0 0 0 2.2-2.2v-2.2a4.5 4.5 0 0 1 4.5-4.5h2.2a2.2 2.2 0 0 0 2.2-2.2Z" />
    </svg>
  );
}

/** What a reading will cost and how much of the book to spend it on (owner,
 * 04/09: "tìm một icon chi phí/phạm vi khác liên quan đến lưu lượng hoặc
 * cost").
 *
 * A coin. Three other readings were weighed first: a gauge, which
 * this app cannot use because it HAS a reading speed and a dial beside a play
 * button is read as that one; a wallet, whose silhouette at 20 is a grey
 * rounded square - the flap that makes a wallet a wallet does not survive the
 * size, and the clasp turned it into a price tag (both were drawn and looked
 * at, at 20, before being thrown away); and `SlidersIcon`, which is
 * already the settings opener standing in the same bar. A disc with a figure
 * on it is the one money glyph that still reads at 16.
 *
 * The mark is stroked rather than filled, on purpose: bulk is a rule about
 * COLOUR - one, at two weights - not about paint mode, and a hand-filled "S"
 * at this size closes up into a blob.
 */
export function CoinIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Z" />
      <path d="M12 5.2a.9.9 0 0 1 .9.9v11.8a.9.9 0 0 1-1.8 0V6.1a.9.9 0 0 1 .9-.9Z" />
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        d="M15 9.4c0-1.3-1.3-2.3-3-2.3s-3 1-3 2.3 1.3 2.1 3 2.3 3 1 3 2.3-1.3 2.3-3 2.3-3-1-3-2.3"
      />
    </svg>
  );
}

export function ShelfIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M8.4 2H5.6C4 2 3.2 2.8 3.2 4.4v15.2c0 1.6.8 2.4 2.4 2.4h2.8c1.6 0 2.4-.8 2.4-2.4V4.4C10.8 2.8 10 2 8.4 2Z" />
      <path d="M18 2h-2.4c-1.6 0-2.4.8-2.4 2.4v15.2c0 1.6.8 2.4 2.4 2.4H18c1.6 0 2.4-.8 2.4-2.4V4.4C20.4 2.8 19.6 2 18 2Zm-.2 8.5h-2a.8.8 0 0 1 0-1.6h2a.8.8 0 0 1 0 1.6Z" />
    </svg>
  );
}

export function CheckIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Z" />
      <path d="M10.6 15.6c-.2 0-.4-.1-.6-.2l-2.4-2.4a.8.8 0 0 1 1.1-1.1l1.9 1.9 4.7-4.7a.8.8 0 0 1 1.1 1.1l-5.2 5.2c-.2.1-.4.2-.6.2Z" />
    </svg>
  );
}

export function LockIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M17.5 9.6h-11c-2 0-3.5 1.5-3.5 3.5v5.4c0 2 1.5 3.5 3.5 3.5h11c2 0 3.5-1.5 3.5-3.5v-5.4c0-2-1.5-3.5-3.5-3.5Z" />
      <path d="M7 9.1V7.7C7 4.6 7.9 2 12 2c3.7 0 5 1.8 5 4.6v2.5h-1.6V6.5c0-2-.9-2.9-3.4-2.9-2.7 0-3.4 1.3-3.4 4.1v1.4H7Zm5 8.9a1.6 1.6 0 1 1 0-3.2 1.6 1.6 0 0 1 0 3.2Z" />
    </svg>
  );
}

export function ImportIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M20.5 14.7v2.2c0 2.8-1.6 4-4 4h-9c-2.4 0-4-1.2-4-4v-2.2a.8.8 0 0 1 1.6 0v2.2c0 1.9.8 2.4 2.4 2.4h9c1.6 0 2.4-.5 2.4-2.4v-2.2a.8.8 0 0 1 1.6 0Z" />
      <path d="M12 16.1c-.2 0-.4-.1-.6-.2l-3.5-3.5a.8.8 0 0 1 1.1-1.1l2.2 2.2V3.3a.8.8 0 0 1 1.6 0v10.2l2.2-2.2a.8.8 0 0 1 1.1 1.1l-3.5 3.5c-.2.1-.4.2-.6.2Z" />
    </svg>
  );
}

export function SyncIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M21 12a9 9 0 0 1-14.9 6.8.8.8 0 0 1 1-1.2A7.4 7.4 0 0 0 19.4 12a.8.8 0 0 1 1.6 0ZM3 12a9 9 0 0 1 14.9-6.8.8.8 0 0 1-1 1.2A7.4 7.4 0 0 0 4.6 12a.8.8 0 0 1-1.6 0Z" />
      <path d="M18.6 2.6a.8.8 0 0 1 .8.8v3.3h-3.3a.8.8 0 0 1 0-1.6h1.7V3.4c0-.4.4-.8.8-.8ZM5.4 21.4a.8.8 0 0 1-.8-.8v-3.3h3.3a.8.8 0 0 1 0 1.6H6.2v1.7c0 .4-.4.8-.8.8Z" />
    </svg>
  );
}

export function SpeakerIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M14.5 4.1v15.8c0 1.9-1.4 2.7-3.1 1.8l-4.4-2.5c-.3-.2-.7-.3-1-.3H4c-2 0-3-1-3-3v-3.8c0-2 1-3 3-3h2c.3 0 .7-.1 1-.3l4.4-2.5c1.7-.9 3.1-.1 3.1 1.8Z" />
      <path d="M18.4 16.9a.8.8 0 0 1-.6-1.3c1.7-2 1.7-5.2 0-7.2a.8.8 0 0 1 1.2-1c2.1 2.6 2.1 6.6 0 9.2-.2.2-.4.3-.6.3Zm2.5 2.9a.8.8 0 0 1-.6-1.3c3-3.6 3-9.4 0-13a.8.8 0 0 1 1.2-1c3.4 4.1 3.4 10.9 0 15-.2.2-.4.3-.6.3Z" />
    </svg>
  );
}

export function HighlightIcon({ className }: { className?: string }) {
  return (
    <svg {...bulk} className={className}>
      <path opacity={MASS} d="M20.2 3.8a3.9 3.9 0 0 0-5.5 0l-8.5 8.5c-.3.3-.5.7-.6 1.1l-.9 4.4c-.1.6.4 1.1 1 1l4.4-.9c.4-.1.8-.3 1.1-.6l8.5-8.5a3.9 3.9 0 0 0 0-5.5Z" />
      <path d="M20 22H4a.8.8 0 0 1 0-1.6h16a.8.8 0 0 1 0 1.6Z" />
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
