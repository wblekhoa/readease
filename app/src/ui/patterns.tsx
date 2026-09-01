/** The pattern layer - the HIG-shaped answer to "which element, arranged how".
 *
 * controls.tsx is the muscle (one button, one select); this file is the
 * skeleton: named screen patterns with their structure and rhythm decided
 * once. Building a screen means picking a pattern and pouring content in.
 * The written half lives in docs/readease-hig.md.
 */
import type { CSSProperties, ReactNode } from "react";

/** A row of controls that must share one corner.
 *
 * DS radius guideline §3.1: the eye reads a row of controls as ONE unit, so
 * every member takes the cluster's radius tier - not the tier its own height
 * would suggest. This component is where that tier is set; controls read it
 * from `--ctl-radius` and never carry a radius class of their own.
 *
 * `control` is the app's default 12px. `pill` is the navigation shape (tabs,
 * language) . `sharp` exists for a future toolbar that wants tighter corners.
 */
const CLUSTER_RADIUS = {
  control: "0.75rem",
  pill: "9999px",
  sharp: "0.5rem",
} as const;

export function Cluster({
  radius = "control",
  className = "",
  children,
}: {
  radius?: keyof typeof CLUSTER_RADIUS;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={`flex items-center gap-2 ${className}`}
      style={{ "--ctl-radius": CLUSTER_RADIUS[radius] } as CSSProperties}
    >
      {children}
    </div>
  );
}

/** The window's top row, Mac-rhythm: navigation leads, actions trail,
 * one fixed-height line so nothing wobbles between screens. */
export function Toolbar({
  leading,
  trailing,
}: {
  leading: ReactNode;
  trailing?: ReactNode;
}) {
  return (
    <header className="flex h-9 items-center gap-3">
      {leading}
      <div className="flex-1" />
      {trailing && <Cluster radius="pill">{trailing}</Cluster>}
    </header>
  );
}

/** One row of a list: leading glyph, a two-line body, trailing accessory.
 * The whole row is one hover surface; the accessory sits INSIDE it. */
export function ListRow({
  leading,
  title,
  subtitle,
  trailing,
  onPress,
  active = false,
}: {
  leading?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  trailing?: ReactNode;
  onPress?: () => void;
  /** "You are here" - painted in `band`, the same token the reading line
   * uses, so the app only ever has one colour for current position. */
  active?: boolean;
}) {
  return (
    <div
      className={`group flex items-center rounded-2xl pr-1.5 transition-colors ${
        active ? "bg-band" : "hover:bg-wash"
      }`}
    >
      <button
        onClick={onPress}
        className="flex min-w-0 flex-1 items-center gap-3 rounded-2xl px-3 py-2 text-left"
      >
        {leading && <span className="shrink-0 text-ink-mute">{leading}</span>}
        <span className="min-w-0 flex-1">
          <span className="flex items-baseline gap-2">{title}</span>
          {subtitle && (
            <span className="mt-0.5 block truncate text-xs text-ink-mute">
              {subtitle}
            </span>
          )}
        </span>
      </button>
      {trailing}
    </div>
  );
}

/** Inset grouped section, the macOS Settings shape: an optional header
 * label, then rows on one paper surface separated by hairlines. */
export function GroupedSection({
  title,
  children,
  className = "",
}: {
  title?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={className}>
      {title && (
        <h3 className="m-0 mb-1.5 px-3 text-xs font-semibold uppercase tracking-wide text-ink-mute">
          {title}
        </h3>
      )}
      <div className="overflow-hidden rounded-2xl bg-panel [&>*+*]:border-t [&>*+*]:border-edge">
        {children}
      </div>
    </section>
  );
}

/** One row inside a GroupedSection: label/description left, control right. */
export function GroupedRow({
  title,
  subtitle,
  trailing,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  trailing?: ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium">{title}</div>
        {subtitle && <div className="text-xs text-ink-mute">{subtitle}</div>}
      </div>
      {trailing && <div className="flex shrink-0 items-center gap-2">{trailing}</div>}
    </div>
  );
}

/** Nothing here yet: the way in stands where the content will be, and the
 * constraint sits under the choice it constrains. */
export function EmptyState({
  actions,
  note,
}: {
  actions: ReactNode;
  note?: ReactNode;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3">
      <div className="flex gap-2">{actions}</div>
      {note && (
        <p className="m-0 max-w-[42ch] text-center text-sm text-ink-mute">{note}</p>
      )}
    </div>
  );
}
