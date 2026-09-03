import { useId } from "react";

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
