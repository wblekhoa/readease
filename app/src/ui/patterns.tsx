/** The pattern layer - the HIG-shaped answer to "which element, arranged how".
 *
 * controls.tsx is the muscle (one button, one select); this file is the
 * skeleton: named screen patterns with their structure and rhythm decided
 * once. Building a screen means picking a pattern and pouring content in.
 * The written half lives in docs/readease-hig.md.
 */
import { useEffect, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent, type ReactNode, type RefObject } from "react";
import { hoverText } from "./format";
import { text } from "../i18n";
import { IconButton, ProgressBar, Surface } from "./controls";
import { BookClosedIcon, ChevronDownIcon, ChevronLeftIcon, ChevronRightIcon, SidebarIcon } from "./icons";
import { WINDOW_BUTTONS_IN_PAGE } from "./host";

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
  role,
  label,
  children,
}: {
  radius?: keyof typeof CLUSTER_RADIUS;
  className?: string;
  /** `group` when the cluster is a set of controls over one dimension. */
  role?: string;
  /** The set's name. Carries the naming when the visible label is dropped -
   * a row of filter chips reads "Tất cả" with nothing to say all of WHAT. */
  label?: string;
  children: ReactNode;
}) {
  return (
    <div
      role={role}
      aria-label={label}
      className={`flex items-center gap-2 ${className}`}
      style={{ "--ctl-radius": CLUSTER_RADIUS[radius] } as CSSProperties}
    >
      {children}
    </div>
  );
}

/** The window's top row, Mac-rhythm: navigation leads, actions trail,
 * one fixed-height line so nothing wobbles between screens.
 *
 * Since the title bar became an overlay (16/09) this row is also what a
 * person drags the window by: Tauri starts a drag on a mousedown whose
 * TARGET carries `data-tauri-drag-region`, so the row and its empty middle
 * both carry it - a control inside stays a control. */
export function Toolbar({
  leading,
  trailing,
}: {
  leading: ReactNode;
  trailing?: ReactNode;
}) {
  return (
    <header data-tauri-drag-region className="flex h-9 items-center gap-3">
      {leading}
      <div data-tauri-drag-region className="h-full flex-1" />
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
  rowRef,
  active = false,
  dense = false,
}: {
  leading?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  trailing?: ReactNode;
  onPress?: () => void;
  /** A handle on the row itself, for a list that has to bring one of its rows
   * into view. */
  rowRef?: RefObject<HTMLDivElement | null>;
  /** "You are here" - painted in `band`, the same token the reading line
   * uses, so the app only ever has one colour for current position. */
  active?: boolean;
  /** Navigation lists (a book's contents) trade padding for how many rows
   * fit on screen; content lists keep the roomier default. */
  dense?: boolean;
}) {
  const shape = dense
    ? "rounded-[var(--ctl-radius)] px-2.5 py-1.5"
    : "rounded-2xl px-3 py-2";
  return (
    <div
      ref={rowRef}
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
          <span className="flex items-baseline gap-2 min-w-0">{title}</span>
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
    /* A TITLED section starts a new subject, so it opens a wider gap above
       itself than the rows inside it ever have between them - 24px above the
       heading against 6px below it, which is what binds the heading to the
       rows it names rather than to the group before it (owner, 04/09:
       "phân cấp bằng spacing rõ hơn"). The margin lives here so six call
       sites cannot each pick their own. */
    <section className={`${title ? "mt-6" : ""} ${className}`}>
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
  icon,
  actions,
  note,
}: {
  /** Drawn above, faint and large. For a list whose way in is elsewhere
   * (a keyboard shortcut, a book you have not opened yet) there is no button
   * to offer, and one grey sentence alone in a corner reads as a bug rather
   * than as an empty shelf (owner, 09/09). */
  icon?: ReactNode;
  actions?: ReactNode;
  note?: ReactNode;
}) {
  return (
    <div className="flex h-full flex-1 flex-col items-center justify-center gap-3">
      {icon && <span className="text-ink-faint">{icon}</span>}
      {actions && <div className="flex gap-2">{actions}</div>}
      {note && (
        <p className="m-0 max-w-[42ch] text-center text-sm text-ink-mute">{note}</p>
      )}
    </div>
  );
}

/** The whole window as a target while something is dragged over it.
 *
 * Over everything and under the pointer's notice - `pointer-events-none`,
 * because the drop is the window's to receive (the webview hands it over as
 * paths) and this layer only says what will happen. It appears on drag-enter
 * and goes on leave or drop; a drop target that is always on screen would
 * be a second empty state under every shelf. */
export function DropZone({
  icon,
  headline,
  detail,
  tone = "ok",
}: {
  icon: ReactNode;
  headline: ReactNode;
  detail?: ReactNode;
  /** `error`: nothing in hand can be dropped here. The frame, the icon and
   * the headline go to the danger colour, so the refusal is seen before it
   * is read - the words alone looked like an invitation (owner, 14/09). */
  tone?: "ok" | "error";
}) {
  const refusing = tone === "error";
  return (
    <div className="pointer-events-none fixed inset-0 z-50 bg-paper/80 p-6" role={refusing ? "alert" : "status"}>
      {/* The same dimming either way - the shelf steps back the same amount -
          and the red rides on top of it, inside the frame, so the two states
          differ in colour and in nothing else. */}
      <div
        className={`flex h-full flex-col items-center justify-center rounded-3xl border-2 border-dashed ${
          refusing ? "border-danger bg-danger-wash" : "border-edge-strong"
        }`}
      >
        {/* The words on their own sheet: the shelf shows through the wash,
            and a headline laid straight over a cover was read against
            whatever picture happened to be under it (measured 14/09). */}
        <div
          className={`flex max-w-[28rem] flex-col items-center gap-3 rounded-3xl border bg-paper px-8 py-6 text-center shadow-lifted ${
            refusing ? "border-danger-edge" : "border-edge-field"
          }`}
        >
          <span className={refusing ? "text-danger" : "text-ink-mute"}>{icon}</span>
          <p
            className={`m-0 text-lg font-semibold ${refusing ? "text-danger" : "text-ink"}`}
            style={{ textWrap: "balance" }}
          >
            {headline}
          </p>
          {detail && <p className="m-0 text-sm text-ink-mute">{detail}</p>}
        </div>
      </div>
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
  tag,
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
  /** Where the book came from, if that is worth saying - a small mark on the
   * cover's corner. Unlike `accessory` it is not an action and does not wait
   * for a hover: it is a fact about the book, and a fact that only appears
   * under the cursor is a fact nobody finds. */
  tag?: ReactNode;
  caption?: ReactNode;
}) {
  return (
    <div className="group relative flex min-w-0 flex-col gap-3">
      {/* Both corner marks hang off the COVER, not off the card. The card is
          cover plus title plus bar, so a card-relative `bottom` lands the tag
          next to the progress bar instead of on the picture - measured, not
          guessed (03/09). The accessory was card-relative too and only looked
          right because the cover happens to be at the top. */}
      <div className="relative">
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
        {/* Bottom-left, because top-right is where the remove button appears
            on hover and a fact must not sit where an action is about to. */}
        {tag && <div className="pointer-events-none absolute bottom-1.5 left-1.5">{tag}</div>}
      </div>
      {caption ?? (
        <div className="min-w-0">
          {/* Clamped to two lines, so a long title loses its end. Measured
              09/09 at the app's narrowest window: 96px of title shown in
              39px, with nothing to recover it - a reader could not read the
              name of their own book. The tooltip says the TEXT, which is
              what was taken away; it is not an action. */}
          <div className="line-clamp-2 text-sm font-semibold leading-snug" title={hoverText(title)}>
            {title}
          </div>
          {meta && <div className="mt-1.5 truncate text-xs text-ink-mute">{meta}</div>}
        </div>
      )}
      {/* Last, not under the cover: the bar is the card's footing, so a row
          of shelves shows one straight line of progress across it instead of
          a stripe interrupting each cover from its own title (owner,
          03/09). `mt-auto` pins it to the bottom when a neighbouring card is
          taller, which happens as soon as one title wraps to two lines. */}
      {progress !== null && (
        <div className="mt-auto">
          <ProgressBar value={progress} />
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

/** Choosing ONE book, drawn as the book rather than as a row in a menu.
 *
 * A `<select>` collapses a book to a line of text and throws away the fact
 * that decides the choice: which copy you have actually been reading. Three
 * entries called "Universal Principles of UX" are indistinguishable in a
 * menu and obvious as cards, once each carries how far it got.
 *
 * The picker itself is still a native `<select>`, laid transparent over the
 * card: clicking anywhere opens the system menu, Tab reaches it, a screen
 * reader reads it, and the card draws the focus ring through `focus-within`.
 * A hand-built listbox would have been a second implementation of all four.
 */
export function BookChoice({
  label,
  value,
  placeholder,
  books,
  onChange,
}: {
  label: string;
  value: string;
  placeholder: string;
  books: readonly { id: string; title: string; note?: string | null }[];
  onChange: (id: string) => void;
}) {
  const chosen = books.find((book) => book.id === value) ?? null;
  return (
    <label className="flex min-w-0 flex-col gap-1.5">
      <span className="text-xs font-semibold uppercase tracking-wide text-ink-mute">
        {label}
      </span>
      <span className="relative flex min-w-0 flex-1 items-center gap-3 rounded-2xl border border-edge bg-paper px-3.5 py-4 transition-[border-color,box-shadow] hover:border-edge-strong hover:shadow-lifted focus-within:border-edge-strong focus-within:shadow-lifted">
        <MiniCover source={null} fallback={<BookClosedIcon />} size="md" muted={!chosen} />
        <span className="min-w-0 flex-1">
          <span
            className={`line-clamp-2 text-sm leading-snug ${
              chosen ? "font-semibold" : "text-ink-faint"
            }`}
            title={chosen ? chosen.title : undefined}
          >
            {chosen ? chosen.title : placeholder}
          </span>
          {chosen?.note && (
            <span className="mt-1 block truncate text-xs text-ink-mute">
              {chosen.note}
            </span>
          )}
        </span>
        <ChevronDownIcon className="shrink-0 text-ink-mute" />
        <select
          data-raw
          data-overlay
          aria-label={label}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="absolute inset-0 opacity-0"
        >
          <option value="">{placeholder}</option>
          {books.map((book) => (
            <option key={book.id} value={book.id}>
              {book.title}
            </option>
          ))}
        </select>
      </span>
    </label>
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
        <div className="line-clamp-2 text-sm font-semibold leading-snug" title={hoverText(title)}>
          {title}
        </div>
        {meta && <div className="mt-0.5 truncate text-xs text-ink-mute">{meta}</div>}
      </div>
      {action && <div className="flex shrink-0 items-center gap-1">{action}</div>}
    </div>
  );
}

/** Escape, or a click anywhere outside, closes a floating panel.
 *
 * Every panel here already closed on Escape and on its own ✕. Neither is
 * where a hand goes: the reader clicks back onto the book and expects the
 * panel to get out of the way (owner, 05/09). Returns the ref to put on the
 * panel - a click inside it is not a click outside.
 *
 * The button that OPENED the panel is exempt, because it toggles: closing on
 * its mousedown and reopening on its click would leave the panel stuck open
 * and the button apparently dead. Mark such a button `data-popover-trigger`.
 *
 * The transport is exempt too, for a different reason (owner, 10/09). Pause,
 * stop, skip and the speaker do not move the reader's attention anywhere -
 * they act on the reading the open panel is ABOUT. Closing the voice list
 * because somebody paused to hear a voice more clearly means reopening it and
 * finding their place again, every time. Mark such a control
 * `data-keeps-popover`; it is deliberately not the same mark as the trigger,
 * which is exempt because it toggles rather than because it belongs.
 */
export function useDismiss(onClose: () => void, enabled = true) {
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!enabled) return;
    const onDown = (event: MouseEvent) => {
      const target = event.target as HTMLElement | null;
      if (!target || panel.current?.contains(target)) return;
      if (target.closest("[data-popover-trigger]")) return;
      if (target.closest("[data-keeps-popover]")) return;
      onClose();
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [enabled, onClose]);
  return panel;
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
        /* The tooltip follows focus, and a click leaves the button focused
           - so the tip sat over the menu's first row (16/09). Let it go. */
        onClick={(event) => { event.currentTarget.blur(); setOpen((value) => !value); }}
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


/** The side column: a real column of the layout, beside the content, not
 * a layer over it (HIG 3.16; owner, 16/09: "một sidebar riêng nằm một bên
 * của layout luôn chứ không phải là popover... giống như cách codex làm").
 *
 * Three tiers: a 52px head that is the window's drag region and holds the
 * macOS window buttons (the title bar is an overlay, so the lights sit
 * inside the column - `trafficLightPosition` in tauri.conf.json) with the
 * collapse switch at its right; a body the caller fills (navigation at
 * home, a book's lists inside one); a foot for what the app carries
 * everywhere. Closed is `width: 0` with the inner column kept at its full
 * width, so the text does not rewrap while the column slides; no
 * `@starting-style` - in a hidden WKWebView the timeline stands still and
 * an element stays at its starting style (measured 16/09).
 *
 * Whether it is open is not decided here: `ui/sidebarState.ts` holds the
 * rules (a hand beats the width, context changes the content), and the
 * caller passes the answer. */
export function SideColumn({
  open,
  width,
  onResize,
  onToggle,
  toggleLabel,
  resizeLabel,
  children,
  foot,
}: {
  open: boolean;
  /** How wide it stands when open, in px - the person's to drag. */
  width: number;
  /** The edge being dragged: a width per move, then `null` when the hand
   * lets go (the moment to remember it). */
  onResize: (width: number | null) => void;
  onToggle: () => void;
  /** The switch's accessible name, for the state it would move to. */
  toggleLabel: string;
  resizeLabel: string;
  children: ReactNode;
  foot?: ReactNode;
}) {
  /* The edge as a handle (owner, 16/09: "sidebar có thể nắm kéo để
     resize"): a strip over the hairline, pointer-captured so the drag
     survives leaving it, the width reported per move and the transition
     held off while a hand is on it - a column that eases after the cursor
     is a column that lags. Double-click puts the default back. */
  const [dragging, setDragging] = useState(false);
  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    const handle = event.currentTarget;
    const start = event.clientX;
    const from = width;
    handle.setPointerCapture(event.pointerId);
    setDragging(true);
    const move = (moved: PointerEvent) => onResize(from + moved.clientX - start);
    const stop = () => {
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", stop);
      handle.removeEventListener("pointercancel", stop);
      setDragging(false);
      onResize(null);
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", stop);
    handle.addEventListener("pointercancel", stop);
  };
  return (
    <aside
      aria-label={text("sidebar.label")}
      // Folded, the column is off the page for the keyboard and the screen
      // reader too, not only for the eye: `inert` takes its controls out of
      // the tab order (WebKit has had it since 16.4).
      inert={!open || undefined}
      style={{ width: open ? width : 0 }}
      className={`relative shrink-0 overflow-hidden bg-column ${
        dragging ? "" : "transition-[width] duration-200 ease-out motion-reduce:transition-none"
      } ${open ? "border-r border-edge" : ""}`}
    >
      {open && (
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label={resizeLabel}
          title={resizeLabel}
          onPointerDown={onPointerDown}
          onDoubleClick={() => { onResize(Number.NaN); onResize(null); }}
          className="absolute inset-y-0 right-0 z-10 w-1.5 cursor-col-resize"
        />
      )}
      <div className="flex h-full flex-col" style={{ width }}>
        {/* The lights live in the first 76px of this strip (x 20-72) - in
            the window; a browser has none, and leaves no hole for them. The
            switch takes the far end, where Codex puts it. */}
        <div
          data-tauri-drag-region
          className={`flex h-[52px] shrink-0 items-center justify-end pr-2.5 ${WINDOW_BUTTONS_IN_PAGE ? "pl-[76px]" : "pl-3"}`}
        >
          <IconButton onClick={onToggle} aria-label={toggleLabel} title={toggleLabel}>
            <SidebarIcon />
          </IconButton>
        </div>
        <div className="flex min-h-0 flex-1 flex-col">{children}</div>
        {foot && (
          <div className="flex shrink-0 items-center gap-1 border-t border-edge px-3 py-2">{foot}</div>
        )}
      </div>
    </aside>
  );
}

/** One entry of the column's navigation: a glyph and a name, painted `wash`
 * + `ink` when it is the screen on show (the state layer of HIG §2). */
export function RailItem({
  icon,
  label,
  active = false,
  onPress,
  trailing,
}: {
  icon?: ReactNode;
  label: ReactNode;
  active?: boolean;
  onPress: () => void;
  trailing?: ReactNode;
}) {
  return (
    <button
      onClick={onPress}
      aria-current={active ? "page" : undefined}
      className={`flex w-full items-center gap-3 rounded-[var(--ctl-radius)] px-2.5 py-1.5 text-left text-sm transition-colors ${
        active ? "bg-wash text-ink" : "text-ink-mute hover:bg-wash hover:text-ink"
      }`}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {trailing}
    </button>
  );
}

/** A named group of rail items - "Đang đọc" - with the heading Codex gives
 * its Pinned and Recents: small, quiet, above the rows. */
export function RailGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="pt-4">
      <p className="m-0 px-2.5 pb-1 text-xs font-semibold text-ink-mute">{title}</p>
      {children}
    </div>
  );
}
