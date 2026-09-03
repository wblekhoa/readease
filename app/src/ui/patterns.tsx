/** The pattern layer - the HIG-shaped answer to "which element, arranged how".
 *
 * controls.tsx is the muscle (one button, one select); this file is the
 * skeleton: named screen patterns with their structure and rhythm decided
 * once. Building a screen means picking a pattern and pouring content in.
 * The written half lives in docs/readease-hig.md.
 */
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { IconButton, ProgressBar, Surface } from "./controls";
import { ChevronLeftIcon, ChevronRightIcon } from "./icons";

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
  dense = false,
}: {
  leading?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  trailing?: ReactNode;
  onPress?: () => void;
  /** "You are here" - painted in `band`, the same token the reading line
   * uses, so the app only ever has one colour for current position. */
  active?: boolean;
  /** Navigation lists (a book's contents) trade padding for how many rows
   * fit on screen; content lists keep the roomier default. */
  dense?: boolean;
}) {
  const shape = dense
    ? "rounded-[var(--ctl-radius)] px-2.5 py-1"
    : "rounded-2xl px-3 py-2";
  return (
    <div
      className={`group flex items-center ${
        dense ? "rounded-[var(--ctl-radius)]" : "rounded-2xl pr-1.5"
      } transition-colors ${active ? "bg-band" : "hover:bg-wash"}`}
    >
      <button
        onClick={onPress}
        className={`flex min-w-0 flex-1 items-center gap-3 text-left ${shape}`}
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

/** A list: an optional header label, then rows told apart by a dot rule.
 *
 * It used to be the macOS inset shape - rows on a grey card with hairlines
 * between them. On a white sheet that reads as a box inside a box, which the
 * DS forbids outright ("card treatment max depth = 1"), and the grey fought
 * every panel it sat in. Now the rows sit on the paper they are already on,
 * separated by the DS dot divider and their own breathing room, and the rows
 * carry no side padding of their own - the panel around them already sets
 * the margin (owner, 03/09, asked for this list everywhere it appears). */
export function GroupedSection({
  title,
  children,
  className = "",
  roomy = false,
}: {
  title?: ReactNode;
  children: ReactNode;
  className?: string;
  /** A sheet that lists things to act on breathes more than a settings
   * group (owner, 02/09): wider header gap, the rows opt in themselves. */
  roomy?: boolean;
}) {
  return (
    <section className={className}>
      {title && (
        <h3 className={`m-0 text-xs font-semibold uppercase tracking-wide text-ink-mute ${roomy ? "mb-2.5" : "mb-1.5"}`}>
          {title}
        </h3>
      )}
      <div className="dot-divided flex flex-col">{children}</div>
    </section>
  );
}

/** One row inside a GroupedSection: label/description left, control right. */
export function GroupedRow({
  title,
  subtitle,
  trailing,
  roomy = false,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  trailing?: ReactNode;
  /** Taller row, wider gaps - for a list of items with actions on them. */
  roomy?: boolean;
}) {
  return (
    <div className={`flex items-center ${roomy ? "gap-4 py-4" : "gap-3 py-3.5"}`}>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium">{title}</div>
        {subtitle && <div className={`text-xs text-ink-mute ${roomy ? "mt-1" : ""}`}>{subtitle}</div>}
      </div>
      {trailing && <div className={`flex shrink-0 items-center ${roomy ? "gap-3" : "gap-2"}`}>{trailing}</div>}
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

/** A book's cover, the object a shelf is made of.
 *
 * Printed proportions (2:3) and a small corner, because a cover is a
 * photograph of a thing, not a control. Hover deepens the shadow and nothing
 * else - the owner cut the 2px lift (02/09): a shelf should not fidget.
 * `source` undefined = still loading,
 * null = the book has none: then the title stands in on a panel, the way
 * Apple Books and Kindle draw a placeholder - readable, never a broken icon.
 */
export function BookCover({
  source,
  title,
}: {
  source: string | null | undefined;
  title: string;
}) {
  return (
    <div className="aspect-[2/3] w-full overflow-hidden rounded-lg bg-panel shadow-raised transition-shadow group-hover:shadow-lifted">
      {source ? (
        <img src={source} alt="" className="h-full w-full object-cover" draggable={false} />
      ) : source === null ? (
        <div className="flex h-full">
          <div className="w-1.5 shrink-0 bg-band" />
          <div className="line-clamp-5 p-3 text-xs font-semibold leading-snug text-ink-mute">
            {title}
          </div>
        </div>
      ) : null}
    </div>
  );
}

/** One book on the shelf: cover, then title and one line of fact.
 *
 * The whole cover is the way in (one button, labelled by the title); the
 * accessory floats on the cover's corner and shows on hover, exactly the
 * ListRow contract moved onto a card. A book in progress carries a thin
 * brand bar under its cover - where the voice got to, at a glance, the
 * signal Kindle and Apple Books both put there. `caption` replaces the
 * text block for an inline confirmation.
 */
export function BookCard({
  cover,
  title,
  meta,
  progress = null,
  onOpen,
  openLabel,
  accessory,
  caption,
}: {
  cover: ReactNode;
  title: ReactNode;
  meta?: ReactNode;
  /** 0..1 while a book is being read; null when it has not been started. */
  progress?: number | null;
  onOpen: () => void;
  openLabel: string;
  accessory?: ReactNode;
  caption?: ReactNode;
}) {
  return (
    <div className="group relative flex min-w-0 flex-col gap-3">
      <button
        type="button"
        onClick={onOpen}
        aria-label={openLabel}
        className="block w-full rounded-lg text-left"
      >
        {cover}
      </button>
      {accessory && (
        <div className="absolute right-1.5 top-1.5 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
          {accessory}
        </div>
      )}
      {progress !== null && <ProgressBar value={progress} />}
      {caption ?? (
        <div className="min-w-0">
          <div className="line-clamp-2 text-sm font-semibold leading-snug">{title}</div>
          {meta && <div className="mt-1.5 truncate text-xs text-ink-mute">{meta}</div>}
        </div>
      )}
    </div>
  );
}

/** The shelf itself: as many covers per row as the width allows, one column
 * width for all so the row reads as a row. Air between books is generous on
 * purpose - covers are dense objects and read better apart (owner asked for
 * more room between books and between title, fact line and bar, 02/09). */
export function BookGrid({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(8.5rem,1fr))] gap-x-8 gap-y-10">
      {children}
    </div>
  );
}

/** The frosted ramp under a chrome bar - the DOL premium-blur engine.
 *
 * Eight real layers, because CSS stops at two pseudo-elements and eight
 * doubling radii need eight nodes (workspace recipe, verbatim). `edge` says
 * which way the ramp fades: a header fades downward into the page, a footer
 * upward. Never takes the pointer; the bar's own content sits above it.
 */
export function GradientBlur({ edge }: { edge: "top" | "bottom" }) {
  return (
    <div className={`gradient-blur ${edge === "top" ? "to-bottom" : "to-top"}`} aria-hidden="true">
      <div /><div /><div /><div /><div /><div /><div /><div />
    </div>
  );
}

/** The margin beside a page, made a control: the whole strip turns the page.
 *
 * Its width is the empty margin between the page box and the text - never
 * more (owner, 02/09: "cẩn thận quá lố width", a zone over the text would
 * steal clicks and drags from reading and selecting). The chevron is the
 * only mark; it fades when there is nowhere to go.
 */
export function EdgeZone({
  side,
  width,
  disabled = false,
  label,
  onPress,
}: {
  side: "left" | "right";
  width: number;
  disabled?: boolean;
  label: string;
  onPress: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onPress}
      style={{ width }}
      className={`absolute inset-y-0 flex items-center text-ink-faint transition-colors hover:text-ink disabled:cursor-default disabled:opacity-0 ${
        side === "left" ? "left-0 justify-start pl-2" : "right-0 justify-end pr-2"
      }`}
    >
      {side === "left" ? <ChevronLeftIcon /> : <ChevronRightIcon />}
    </button>
  );
}

/** A cover at list size (32×48): the real picture when the book is here,
 * a quiet panel with a glyph when it is not - so "already in the library"
 * and "not yet" read at a glance without a label. */
export function MiniCover({
  source,
  fallback,
  muted = false,
  size = "sm",
}: {
  source: string | null | undefined;
  fallback: ReactNode;
  muted?: boolean;
  /** `sm` 32×48 for a list row, `md` 44×66 for a tile. */
  size?: "sm" | "md";
}) {
  return (
    <span className={`flex shrink-0 items-center justify-center overflow-hidden rounded bg-band text-ink-faint ${size === "md" ? "h-[66px] w-11" : "h-12 w-8"} ${muted ? "opacity-60" : ""}`}>
      {source ? <img src={source} alt="" className="h-full w-full object-cover" draggable={false} /> : fallback}
    </span>
  );
}

/** A book as a compact tile, two to a row - Apple Books' "continue" shape
 * without its colour: a paper card with a quiet edge that firms up and
 * lifts under the cursor (owner, 02/09), the cover at the left, the title on
 * at most two lines, one line of fact, and the actions as icons at the
 * right. A tile that cannot be acted on stands back, muted. */
export function BookTile({
  cover,
  title,
  meta,
  action,
  muted = false,
}: {
  cover: ReactNode;
  title: ReactNode;
  meta?: ReactNode;
  action?: ReactNode;
  muted?: boolean;
}) {
  return (
    <div
      className={`flex min-w-0 items-center gap-3 rounded-2xl border border-edge bg-paper p-3 transition-[border-color,box-shadow] hover:border-edge-strong hover:shadow-lifted ${
        muted ? "opacity-70" : ""
      }`}
    >
      {cover}
      <div className="min-w-0 flex-1">
        <div className="line-clamp-2 text-sm font-semibold leading-snug">{title}</div>
        {meta && <div className="mt-0.5 truncate text-xs text-ink-mute">{meta}</div>}
      </div>
      {action && <div className="flex shrink-0 items-center gap-1">{action}</div>}
    </div>
  );
}

/** An icon button that opens a short list of choices under it.
 *
 * The first item is the default, marked as such; choosing anything closes
 * the menu, as do Escape and a click elsewhere. Small on purpose: this is
 * the "options behind an action" pattern, not a navigation menu. */
export function MenuButton({
  icon,
  label,
  items,
  disabled = false,
  align = "right",
}: {
  icon: ReactNode;
  label: string;
  items: readonly { label: string; hint?: string; onSelect: () => void }[];
  disabled?: boolean;
  align?: "left" | "right";
}) {
  const [open, setOpen] = useState(false);
  const holder = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (event: MouseEvent) => {
      if (!holder.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      // Swallow it entirely: the sheet under the menu also closes on
      // Escape, and one press should close only the menu.
      if (event.key === "Escape") { event.stopImmediatePropagation(); setOpen(false); }
    };
    document.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey, true);
    };
  }, [open]);
  return (
    <span ref={holder} className="relative inline-flex">
      <IconButton
        onClick={() => setOpen((value) => !value)}
        disabled={disabled}
        aria-label={label}
        title={label}
        aria-haspopup="menu"
        aria-expanded={open}
        className={open ? "text-ink" : ""}
      >
        {icon}
      </IconButton>
      {open && (
        <Surface
          edge="strong"
          className={`absolute top-full z-40 mt-[var(--layer-gap)] layer-capped min-w-[15rem] overflow-y-auto p-2 shadow-lifted ${align === "right" ? "right-0" : "left-0"}`}
        >
          <div role="menu" className="flex flex-col">
            {items.map((item, index) => (
              <button
                key={item.label}
                type="button"
                role="menuitem"
                onClick={() => { setOpen(false); item.onSelect(); }}
                /* 12px, not the 8px this started at: the menu's own corner is
                 * 16 and its padding is 4, so a nested row is only concentric
                 * with it at 12 - which is also the control tier (owner asked
                 * for a rounder item, 02/09). Hardcoded rather than
                 * `--ctl-radius`, because this layer can float above a `pill`
                 * cluster and would inherit its shape. */
                className="flex items-baseline gap-2 rounded-xl px-3 py-2 text-left text-sm text-ink hover-wash"
              >
                <span className="flex-1">{item.label}</span>
                {(item.hint || index === 0) && (
                  <span className="text-xs text-ink-faint">{item.hint ?? ""}</span>
                )}
              </button>
            ))}
          </div>
        </Surface>
      )}
    </span>
  );
}

