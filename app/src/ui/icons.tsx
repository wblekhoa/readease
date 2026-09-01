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
