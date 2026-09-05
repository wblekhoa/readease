/** The product's control kit - every interactive surface, defined once.
 *
 * This file exists because the alternative was lived, twice: control styling
 * as repeated class strings drifted (a `shrink-0` in the middle broke two
 * radius sweeps; 13px spread to 38 call sites; the focus colour was wrong in
 * three places at once). Colours come only from the token bridge in
 * index.css; heights are the DS tiers the owner approved (control 30px, small
 * 28px, icon buttons 32 round, surfaces rounded-2xl) and the CORNER is not a
 * per-control decision at all - it comes from `--ctl-radius`, one value per
 * cluster (see `Cluster` in patterns.tsx).
 *
 * `npm run audit:ui` fails the build if a raw control signature appears
 * outside this folder - the gate that keeps this the single source.
 */
import { useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  Ref,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

/** `--layer-gap` in pixels, for the layers positioned by measurement rather
 * than by class. Kept in step with the token in index.css by hand: there is
 * one relationship here, and it should not read as three. */
export const LAYER_GAP = 12;
type Size = "lg" | "md" | "sm";

/* Hover/press come from the `hover-wash` utility in index.css: a wash painted
 * OVER the control's fill. Swapping the fill for the alpha wash (the old
 * `hover:bg-wash`) made any control floating over content go see-through.
 * Focus is drawn ONCE, by the `:focus-visible` ring in index.css. Controls
 * used to switch their border colour instead, which meant two competing
 * formulas - and on the borderless ones, adding a border on focus shifted
 * the label by a pixel every time it was tabbed to. */
const BUTTON_BASE =
  "inline-flex items-center justify-center gap-1.5 whitespace-nowrap font-medium transition-colors disabled:cursor-default";

/* Size changes the box, never the corner: radius comes from the cluster
 * variable so a row of controls shares one shape (DS radius §3.1). A 28px
 * button next to a 30px select used to differ by 4px of corner - visible,
 * and exactly what the owner flagged. */
const BUTTON_SIZE: Record<Size, string> = {
  /* The one button a screen is FOR - the one that starts a reading. Its own
     step rather than a bigger `md`, because `md` is every other button in
     the product and the point here is that this one is not one of them. */
  /* 12px, not the 16 the other tiers carry: the only `lg` in the product
     leads with an icon, and a glyph needs less air against the edge than a
     word does. The word gets its 16 back from a 4px inset on the label group
     at the call site, so the two sides of the button end up unequal on
     purpose (owner, 04/09). */
  lg: "h-9 rounded-[var(--ctl-radius-lg)] px-3 text-sm",
  md: "h-[30px] rounded-[var(--ctl-radius)] px-4 text-sm",
  sm: "h-7 rounded-[var(--ctl-radius)] px-2.5 text-sm [&_svg]:h-4 [&_svg]:w-4",
};

/* Disabled is always ink-faint, never opacity: fading a bordered control also
 * fades its border to a ghost line. A bordered control keeps its own stroke
 * (edge-strong) so the silhouette still says "a button belongs here" - the
 * quiet `edge` measured 1.00:1 against the light desk, i.e. invisible;
 * borderless variants stay borderless and only dim their label. */
const BUTTON_VARIANT: Record<Variant, string> = {
  primary:
    "border border-brand-600 bg-brand-600 font-semibold text-white hover:bg-brand-700 hover:border-brand-700 active:bg-brand-700 disabled:border-edge-strong disabled:bg-transparent disabled:text-ink-faint",
  secondary:
    "border border-edge-strong bg-paper text-ink hover-wash disabled:bg-transparent disabled:text-ink-faint",
  ghost:
    "border border-transparent bg-transparent text-ink-mute hover-wash hover:text-ink disabled:text-ink-faint",
  danger:
    "border border-transparent bg-transparent font-semibold text-danger hover-wash disabled:text-ink-faint",
};

export function Button({
  variant = "secondary",
  size = "md",
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
}) {
  return (
    <button
      type="button"
      className={`${BUTTON_BASE} ${BUTTON_SIZE[size]} ${BUTTON_VARIANT[variant]} ${className}`}
      {...rest}
    />
  );
}

/** A circular icon-only action. Pass aria-label always.
 *
 * A `title` becomes a real tooltip rather than the browser's: the native one
 * waits about a second, is drawn by the OS in a style nothing else here
 * shares, and cannot be seen at all on a touch screen. Every icon button in
 * the product gets it from this one place (owner, 03/09), so no screen has
 * to remember to add one.
 *
 * It is drawn through a PORTAL, and positioned from the button's measured
 * rectangle: an icon button can sit inside the reader's transformed columns
 * or a panel that clips, and `fixed` alone does not survive a transformed
 * ancestor. Measured, then clamped, because a button at the edge of the
 * window would otherwise centre its tooltip half off the screen.
 */
export function IconButton({
  className = "",
  title,
  onMouseEnter,
  onMouseLeave,
  onFocus,
  onBlur,
  ...rest
}: Omit<ButtonHTMLAttributes<HTMLButtonElement>, "title"> & {
  /* Wider than the DOM attribute on purpose: `title` never reaches the
     button - it is destructured out and drawn here - so it can be a whole
     line rather than a string. The reader's "where you are" is a page count,
     a chapter and a percentage set in three weights, and it had grown its own
     floating panel for want of this (App.tsx, owner 04/09). */
  title?: ReactNode;
}) {
  const [tip, setTip] = useState<
    { centre: number; above: number; below: number } | null
  >(null);
  const [box, setBox] = useState<{ left: number; top: number } | null>(null);
  const bubble = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (!tip || !bubble.current) { setBox(null); return; }
    const width = bubble.current.offsetWidth;
    const height = bubble.current.offsetHeight;
    const margin = 12;
    // Below by default, ABOVE when below would run off the bottom. Buttons in
    // the footer are the whole reason: their tooltip was drawn past the edge
    // of the window and cropped, so the one control that most needed naming
    // was the one whose name you could not read.
    const fitsBelow = tip.below + height + margin <= window.innerHeight;
    setBox({
      left: Math.min(
        Math.max(tip.centre - width / 2, margin),
        Math.max(margin, window.innerWidth - width - margin),
      ),
      top: fitsBelow ? tip.below : Math.max(margin, tip.above - height),
    });
  }, [tip]);

  const open = (element: HTMLElement) => {
    if (!title) return;
    const rect = element.getBoundingClientRect();
    // Both candidates are recorded here; which one is used needs the
    // bubble's own height, which only exists once it has rendered.
    setTip({
      centre: rect.left + rect.width / 2,
      above: rect.top - LAYER_GAP,
      below: rect.bottom + LAYER_GAP,
    });
  };

  return (
    <>
      <button
        type="button"
        className={`flex h-8 w-8 items-center justify-center rounded-full text-ink-mute transition-colors hover-wash disabled:text-ink-faint ${className}`}
        onMouseEnter={(event) => { open(event.currentTarget); onMouseEnter?.(event); }}
        onMouseLeave={(event) => { setTip(null); onMouseLeave?.(event); }}
        onFocus={(event) => { open(event.currentTarget); onFocus?.(event); }}
        onBlur={(event) => { setTip(null); onBlur?.(event); }}
        {...rest}
      />
      {tip && title && createPortal(
        <div
          ref={bubble}
          role="tooltip"
          /* The corner and the inset of a `Surface edge="strong"`, spelled out
             rather than composed: `Surface` forwards neither a ref nor a
             style, and this one is measured and placed. Matching it is not a
             preference - the note peek in Reader.tsx is the same kind of
             object, a small bubble that appears under the pointer, and it IS
             a Surface. This one had been left on an 8px corner and a 4px
             inset, tighter than anything else that floats (owner, 04/09:
             "radius còn tròn hơn và padding cần thoáng hơn"). */
          className="pointer-events-none fixed z-50 w-max max-w-[16rem] rounded-2xl border border-edge-strong bg-paper px-3 py-2 text-xs leading-snug text-ink shadow-lifted"
          /* Hidden for the one frame before it has been measured, so it
             never appears in the wrong place first. */
          style={{ left: box?.left ?? 0, top: box?.top ?? 0, visibility: box ? "visible" : "hidden" }}
        >
          {title}
        </div>,
        document.body,
      )}
    </>
  );
}

/** A small control that lives INSIDE a line of text.
 *
 * The round `IconButton` is 32px - a third of a line's height again - and
 * putting one mid-paragraph pushes the line apart. This one is sized to the
 * text it sits in and adds no vertical rhythm of its own; the touch target
 * stays honest through padding rather than height.
 *
 * It stops the click reaching the paragraph on purpose: a paragraph click
 * means "read from here", and pressing a note icon means the opposite. */
export function InlineIconButton({
  className = "",
  onClick,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      /* The set renders at 20 now; here it does not. A 20px glyph inside a
         paragraph pushes the line apart, which is the one thing this control
         exists to avoid. */
      className={`ml-0.5 inline-flex translate-y-[0.1em] items-center justify-center rounded p-0.5 align-baseline text-ink-mute transition-colors hover:text-ink [&_svg]:h-4 [&_svg]:w-4 ${className}`}
      onClick={(event) => {
        event.stopPropagation();
        onClick?.(event);
      }}
      {...rest}
    />
  );
}

/** The one styled <select>. The chevron and appearance reset live in
 * index.css, because WKWebView ignores radius on native selects. */
export function Select({
  className = "",
  pill = false,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement> & { pill?: boolean }) {
  return (
    <select
      className={`${pill ? "h-8 rounded-full px-3" : "h-[30px] rounded-[var(--ctl-radius)] px-2"} border border-edge-strong bg-paper text-sm text-ink hover:bg-wash disabled:text-ink-faint ${className}`}
      {...rest}
    />
  );
}

/** The one single-line input: a search or a filter box, control-height,
 * at the cluster radius like every other control in its row. */
export function Input({
  className = "",
  ...rest
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      data-raw
      className={`h-[30px] rounded-[var(--ctl-radius)] border border-edge-strong bg-paper px-3 text-sm text-ink placeholder:text-ink-faint ${className}`}
      {...rest}
    />
  );
}

/** The one multi-line input, at the surface radius tier. */
export function Textarea({
  className = "",
  ...rest
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      data-raw
      className={`resize-none rounded-2xl border border-edge-field bg-paper p-3 font-[inherit] text-sm leading-relaxed ${className}`}
      {...rest}
    />
  );
}

/** Label + control on one axis: "Giọng [ ... ]". */
export function Field({
  label,
  children,
  className = "",
}: {
  label: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={`flex items-center gap-2 text-sm text-ink-mute ${className}`}>
      {label}
      {children}
    </label>
  );
}

/** Screen title - the 16px tier the owner set. */
export function SectionTitle({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <h2 className={`m-0 text-base font-bold ${className}`}>{children}</h2>;
}

/** A paper card at the surface tier. Its stroke is `edge-field`: on the white
 * desk the card and the page are the same colour, so a line is the only thing
 * that says "card"; in dark the fill ladder already says it, so the line goes
 * away rather than sitting there as a second, redundant signal. */
export function Surface({
  children,
  className = "",
  edge = "field",
  radius = "surface",
  ref,
}: {
  children: ReactNode;
  className?: string;
  /** For a floating layer that has to know whether a click landed inside it. */
  ref?: Ref<HTMLDivElement>;
  /** `field`: the fallback hairline that disappears where the fill already
   * separates (dark). `strong`: a real stroke for a layer that floats over
   * content and must read as an object on both papers - a tooltip (owner
   * asked for a firmer edge, 02/09). */
  edge?: "field" | "strong";
  /** `surface` = the 16px card tier. `sheet` = 24px for a layer that stands
   * on its own in the middle of the window (owner, 02/09: a modal should be
   * rounder than a card). */
  radius?: "surface" | "sheet";
}) {
  return (
    <div
      ref={ref}
      className={`border bg-paper ${radius === "sheet" ? "rounded-3xl" : "rounded-2xl"} ${
        edge === "strong" ? "border-edge-strong" : "border-edge-field"
      } ${className}`}
    >
      {children}
    </div>
  );
}

/** One-line outcome: quiet when fine, danger-toned when not. */
export function Notice({
  tone = "ok",
  fine = false,
  children,
  className = "",
}: {
  tone?: "ok" | "error";
  /** Fine print: 12px and italic, for the aside that qualifies a control
   * rather than telling somebody something happened. A separate flag and not
   * a className, because `text-xs` handed in from outside would fight the
   * `text-sm` in here and the winner would depend on stylesheet order. */
  fine?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <p
      className={`m-0 leading-relaxed ${fine ? "text-xs italic" : "text-sm"} ${
        tone === "error" ? "font-medium text-danger" : "text-ink-mute"
      } ${className}`}
    >
      {children}
    </p>
  );
}

/** A keyboard shortcut, drawn as separate KEYCAPS.
 *
 * It used to be one bordered box on paper at the control radius - which in
 * this app is precisely the shape of a button, so it read as one (the owner
 * mistook it for a button standing next to the real "Đổi phím tắt", 2026-09-01).
 * Three things now say "not a button": several small caps instead of one box,
 * the recessed `panel` fill instead of `paper`, and a heavier bottom edge -
 * the thing you press on a keyboard, not on screen.
 */
export function Kbd({ children }: { children: string }) {
  const keys = children.split(" + ");
  return (
    <span className="inline-flex items-center gap-1">
      {keys.map((key, index) => (
        <span key={`${key}-${index}`} className="contents">
          {index > 0 && <span className="px-0.5 text-xs text-ink-faint">+</span>}
          <kbd className="rounded-lg border border-edge border-b-2 border-b-edge-strong bg-panel px-1.5 py-0.5 font-sans text-xs font-semibold text-ink">
            {key}
          </kbd>
        </span>
      ))}
    </span>
  );
}

/** An on/off switch: the control for "is this in the list or not".
 *
 * A checkbox would do the job, but this answers a different question - not
 * "did you tick this row" but "is this voice one of the ones you switch
 * between" - and the sliding thumb says on/off at a glance down a list of
 * twenty. Native `<input type=checkbox>` keeps the keyboard and the
 * accessibility tree honest; the box itself is drawn from the tokens.
 */
export function Switch({
  checked,
  onChange,
  disabled = false,
  label,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label: string;
}) {
  return (
    <label className={`relative inline-flex h-[22px] w-[38px] shrink-0 items-center ${disabled ? "" : "cursor-pointer"}`}>
      <input
        data-raw
        type="checkbox"
        role="switch"
        className="peer sr-only"
        checked={checked}
        disabled={disabled}
        aria-label={label}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span
        aria-hidden
        className={`h-full w-full rounded-full border transition-colors ${
          disabled
            ? "border-edge bg-band"
            : checked
              ? "border-brand-600 bg-brand-600"
              : "border-edge-strong bg-band"
        } peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-brand-600`}
      />
      <span
        aria-hidden
        className={`pointer-events-none absolute left-[3px] h-4 w-4 rounded-full bg-paper shadow-raised transition-transform ${
          checked ? "translate-x-4" : ""
        } ${disabled ? "opacity-60" : ""}`}
      />
    </label>
  );
}

/** How far something got, 0..1.
 *
 * Blue, from the DS's own `progress` role - not brand red, which is this
 * app's identity rather than a status, and made every started book shout
 * (owner, 03/09). */
export function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-1.5 overflow-hidden rounded-full bg-band">
      <div
        className="h-full rounded-full bg-progress transition-[width]"
        style={{ width: `${Math.round(Math.min(1, Math.max(0, value)) * 100)}%` }}
      />
    </div>
  );
}
