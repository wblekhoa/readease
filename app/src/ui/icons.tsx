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
