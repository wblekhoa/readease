/** The two glyphs the library row needs.
 *
 * DOL canon sources icons from DS Studio's DsIcon; this app ships outside
 * that repo, so the registry is not consumable here (same gap note as
 * ToggleButtonGroup). These two are drawn to its geometry instead: 16px grid,
 * 1.5 stroke, round caps, currentColor.
 */

const base = {
  width: 16,
  height: 16,
  viewBox: "0 0 16 16",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export function BookIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M2.5 3.2c1.8-.9 3.6-.9 5.5.2 1.9-1.1 3.7-1.1 5.5-.2v9.3c-1.8-.9-3.6-.9-5.5.2-1.9-1.1-3.7-1.1-5.5-.2V3.2Z" />
      <path d="M8 3.4v9.3" />
    </svg>
  );
}

export function CloseIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M4 4l8 8M12 4l-8 8" />
    </svg>
  );
}

export function TrashIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M2.8 4.3h10.4M6.3 4.3V3c0-.4.3-.8.8-.8h1.8c.5 0 .8.4.8.8v1.3M4.2 4.3l.6 8.2c0 .7.6 1.2 1.2 1.2h4c.6 0 1.2-.5 1.2-1.2l.6-8.2" />
      <path d="M6.6 6.9v4.2M9.4 6.9v4.2" />
    </svg>
  );
}

export function ChevronLeftIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M10 3.5 5.5 8l4.5 4.5" />
    </svg>
  );
}

/** Two panes, the left one filled: the contents list toggling in and out. */
export function SidebarIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <rect x="2.2" y="3" width="11.6" height="10" rx="2" />
      <path d="M6.4 3v10" />
    </svg>
  );
}

/* Media glyphs read better filled than stroked - the transport is the one
 * place the app borrows a language everybody already knows. */
const solid = {
  width: 16,
  height: 16,
  viewBox: "0 0 16 16",
  fill: "currentColor",
  "aria-hidden": true,
};

export function PlayIcon() {
  return (
    <svg {...solid}>
      <path d="M4.8 3.3c0-.6.7-1 1.2-.6l6 4.1c.5.3.5 1 0 1.3l-6 4.2c-.5.4-1.2 0-1.2-.6V3.3Z" />
    </svg>
  );
}

export function PauseIcon() {
  return (
    <svg {...solid}>
      <rect x="4" y="3" width="3" height="10" rx="1.2" />
      <rect x="9" y="3" width="3" height="10" rx="1.2" />
    </svg>
  );
}

export function StopIcon() {
  return (
    <svg {...solid}>
      <rect x="3.6" y="3.6" width="8.8" height="8.8" rx="2" />
    </svg>
  );
}

export function PreviousIcon() {
  return (
    <svg {...solid}>
      <rect x="3" y="3.4" width="2.2" height="9.2" rx="1" />
      <path d="M12.6 4.1c0-.6-.7-.9-1.1-.5L6.7 7.4a.8.8 0 0 0 0 1.2l4.8 3.8c.4.4 1.1 0 1.1-.5V4.1Z" />
    </svg>
  );
}

export function NextIcon() {
  return (
    <svg {...solid}>
      <rect x="10.8" y="3.4" width="2.2" height="9.2" rx="1" />
      <path d="M3.4 4.1c0-.6.7-.9 1.1-.5l4.8 3.8a.8.8 0 0 1 0 1.2l-4.8 3.8c-.4.4-1.1 0-1.1-.5V4.1Z" />
    </svg>
  );
}

export function ChevronRightIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M6 3.5 10.5 8 6 12.5" />
    </svg>
  );
}

/** Two pages side by side: the paginated reading mode. */
export function PagesIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <rect x="2" y="3" width="5.2" height="10" rx="1.2" />
      <rect x="8.8" y="3" width="5.2" height="10" rx="1.2" />
    </svg>
  );
}

/** Lines running off the bottom: the continuous scroll mode. */
export function ScrollIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M3 3.5h10M3 6.5h10M3 9.5h10M3 12.5h6" />
    </svg>
  );
}

/** A small "i" in a ring: secondary information on request. */
export function InfoIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <circle cx="8" cy="8" r="5.8" />
      <path d="M8 7.2v3.6M8 5.2v.2" />
    </svg>
  );
}

/** Three sliders: the settings the reader may want to open. */
export function SlidersIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M3 4.5h6.2M11.8 4.5H13M3 8h1.6M7.2 8H13M3 11.5h8M13.6 11.5H13" />
      <circle cx="10.6" cy="4.5" r="1.4" />
      <circle cx="5.8" cy="8" r="1.4" />
      <circle cx="12.2" cy="11.5" r="1.4" />
    </svg>
  );
}

export function SunIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <circle cx="8" cy="8" r="3" />
      <path d="M8 1.8v1.6M8 12.6v1.6M1.8 8h1.6M12.6 8h1.6M3.6 3.6l1.1 1.1M11.3 11.3l1.1 1.1M3.6 12.4l1.1-1.1M11.3 4.7l1.1-1.1" />
    </svg>
  );
}

export function MoonIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M13.2 9.6A5.6 5.6 0 0 1 6.4 2.8a5.6 5.6 0 1 0 6.8 6.8Z" />
    </svg>
  );
}

/** A clipboard with lines: pasted text. */
export function ClipboardIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <rect x="3.5" y="3" width="9" height="11" rx="1.6" />
      <path d="M6 3V2.4h4V3M6 7.5h4M6 10h2.6" />
    </svg>
  );
}

/** An I-beam over a line of text: reading whatever is selected elsewhere. */
export function CursorTextIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M2.5 8h4M9.5 8h4" />
      <path d="M8 2.8v10.4M6.4 2.8h3.2M6.4 13.2h3.2" />
    </svg>
  );
}

/** Two pages with an arrow between: notes moving from one book to another. */
export function TransferIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <rect x="2" y="3" width="4.6" height="10" rx="1.2" />
      <rect x="9.4" y="3" width="4.6" height="10" rx="1.2" />
      <path d="M6.6 8h2.8M8.2 6.8 9.4 8l-1.2 1.2" />
    </svg>
  );
}

/** A small note card: a highlight that carries the person's own words. */
export function NoteIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M3 3.5h10v6.2L9.8 13H3V3.5Z" />
      <path d="M9.8 13V9.7H13M5.5 6.5h5M5.5 9h3" />
    </svg>
  );
}

/** Apple Books' shelf glyph: an open book with a bookmark. */
export function ShelfIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M2.5 3.5h4.2c.8 0 1.3.5 1.3 1.3v8.4c-.4-.6-.9-.9-1.6-.9H2.5V3.5ZM13.5 3.5H9.3c-.8 0-1.3.5-1.3 1.3v8.4c.4-.6.9-.9 1.6-.9h3.9V3.5Z" />
      <path d="M11 3.5v4l-1-.8-1 .8v-4" />
    </svg>
  );
}

export function CheckIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M3.2 8.4 6.5 11.6 12.8 4.6" />
    </svg>
  );
}

export function LockIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <rect x="3.2" y="7" width="9.6" height="6.6" rx="1.6" />
      <path d="M5.4 7V5.2a2.6 2.6 0 0 1 5.2 0V7" />
    </svg>
  );
}

/** An arrow down into a tray: bring the book in. */
export function ImportIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M8 2.5v7.4M5.2 7.2 8 10l2.8-2.8" />
      <path d="M2.8 10.4v1.8c0 .7.6 1.3 1.3 1.3h7.8c.7 0 1.3-.6 1.3-1.3v-1.8" />
    </svg>
  );
}

/** Two arrows chasing: bring the highlights over again. */
export function SyncIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M13 6.8A5.2 5.2 0 0 0 3.6 5.4M3 9.2a5.2 5.2 0 0 0 9.4 1.4" />
      <path d="M13 2.8v4h-4M3 13.2v-4h4" />
    </svg>
  );
}

export function ChevronDownIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M3.5 6 8 10.5 12.5 6" />
    </svg>
  );
}

/** A speaker with one wave: hear this voice. */
export function SpeakerIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M8.2 2.8 4.8 5.6H2.6v4.8h2.2l3.4 2.8z" />
      <path d="M11 5.8a3.2 3.2 0 0 1 0 4.4" />
    </svg>
  );
}

/** Two lines of text with a marker stroke under them: a highlight with no
 * note. Its pair is NoteIcon - together they say, at a glance down a list,
 * which rows carry something to read and which are just a passage kept. */
export function HighlightIcon({ className }: { className?: string }) {
  return (
    <svg {...base} className={className}>
      <path d="M3 4.2h10M3 7.4h6" />
      <path d="M3.2 11.2h7.6" strokeWidth={3} />
    </svg>
  );
}

