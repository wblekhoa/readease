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
import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "md" | "sm";

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
  md: "h-[30px] rounded-[var(--ctl-radius)] px-4 text-sm",
  sm: "h-7 rounded-[var(--ctl-radius)] px-2.5 text-sm",
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

/** A circular icon-only action. Pass aria-label always. */
export function IconButton({
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={`flex h-8 w-8 items-center justify-center rounded-full text-ink-mute transition-colors hover-wash disabled:text-ink-faint ${className}`}
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
}: {
  children: ReactNode;
  className?: string;
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
  children,
  className = "",
}: {
  tone?: "ok" | "error";
  children: ReactNode;
  className?: string;
}) {
  return (
    <p
      className={`m-0 text-sm leading-relaxed ${
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

/** Brand progress, 0..1. */
export function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-1.5 overflow-hidden rounded-full bg-band">
      <div
        className="h-full rounded-full bg-brand-600 transition-[width]"
        style={{ width: `${Math.round(Math.min(1, Math.max(0, value)) * 100)}%` }}
      />
    </div>
  );
}
