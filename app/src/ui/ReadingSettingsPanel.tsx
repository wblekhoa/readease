/** How the book is set: the Books "Themes & Settings" popover, without the
 * theme grid (owner, 06/09: "không cần nhiều theme màu/text khác nhau").
 *
 * The quick row is what Books puts first - type size, appearance, pages or
 * scroll. "Tuỳ chỉnh" opens the finer choices in the SAME panel rather than
 * a second sheet (owner's pick, 06/09): line spacing, margins, columns,
 * justification, bold. Every choice applies as it is made; "reset" puts the
 * fine ones back, the quick ones are a click away anyway.
 */
import { useState } from "react";
import { text } from "../i18n";
import { Button, IconButton, SegmentedControl, Slider, Surface, Switch } from "./controls";
import {
  AutoAppearanceIcon, ChevronDownIcon, CloseIcon, MoonIcon, PagesIcon, ScrollIcon, SlidersIcon, SunIcon,
  TextLargerIcon, TextSmallerIcon,
} from "./icons";
import { useDismiss } from "./patterns";
import {
  DEFAULT_PREFS, LINE_HEIGHT, MARGIN, isDefaultPrefs, type Columns, type ReadingPrefs,
} from "./readingPrefs";
import type { ReadingMode } from "./readingMode";
import type { ThemePreference } from "./theme";

export function ReadingSettingsPanel({
  size,
  sizes,
  onSize,
  mode,
  onMode,
  appearance,
  onAppearance,
  prefs,
  onPrefs,
  onClose,
}: {
  size: number;
  sizes: readonly number[];
  onSize: (step: number) => void;
  mode: ReadingMode;
  onMode: (mode: ReadingMode) => void;
  appearance: ThemePreference;
  onAppearance: (preference: ThemePreference) => void;
  prefs: ReadingPrefs;
  onPrefs: (prefs: ReadingPrefs) => void;
  onClose: () => void;
}) {
  const [more, setMore] = useState(!isDefaultPrefs(prefs));
  const step = Math.max(0, sizes.indexOf(size));
  const panel = useDismiss(onClose);
  const set = <K extends keyof ReadingPrefs>(key: K, value: ReadingPrefs[K]) =>
    onPrefs({ ...prefs, [key]: value });

  return (
    <Surface
      ref={panel}
      edge="strong"
      /* A floating panel sets its content in by the sheets' 24 and takes the
         sheet radius - the rule every panel over a page follows
         (SettingsPanel, owner 03/09; restated 06/09 for this one, which had
         shipped at 16 and the card radius: "tăng padding và tăng radius"). */
      radius="sheet"
      className="absolute right-6 top-[calc(var(--shell-top-inner)+var(--layer-gap))] z-20 flex layer-capped w-[25rem] max-w-[calc(100vw-3rem)] flex-col overflow-hidden shadow-lifted"
    >
      <div className="flex shrink-0 items-center px-6 pb-2 pt-5">
        <h3 className="m-0 flex-1 text-sm font-bold">{text("reader.settings")}</h3>
        <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-6">
        <div className="flex flex-col gap-2">
          {/* The Books row: two halves of one wide pill, a hairline between
              them, the letters drawn at the size they set. Plain buttons - two
              actions, not a choice - so neither half is ever "on". */}
          {/* The size control carries its own scale: two halves of one pill,
              and under them - INSIDE the pill, not floating below it (owner,
              06/09) - a mark per step, filled up to the one in use. The
              buttons say "smaller" and "larger" but not "of how many", and a
              reader pressing one wants to know how much further it goes. The
              marks are a read-out, so they are hidden from the screen reader
              and the level travels in the group's own name instead. */}
          <div
            role="group"
            aria-label={text("settings.text_size_level", { n: step + 1, total: sizes.length })}
            className="flex h-14 flex-col rounded-[1.75rem] bg-band p-1"
          >
            <div className="flex min-h-0 flex-1 items-stretch">
              <button
                type="button"
                onClick={() => onSize(-1)}
                disabled={size === sizes[0]}
                aria-label={text("reader.text_smaller")}
                title={text("reader.text_smaller")}
                className="flex flex-1 items-center justify-center rounded-[1.5rem] text-ink transition-colors hover-wash disabled:text-ink-faint"
              >
                <TextSmallerIcon className="h-5 w-5" />
              </button>
              <span aria-hidden className="my-1.5 w-px bg-edge-strong" />
              <button
                type="button"
                onClick={() => onSize(1)}
                disabled={size === sizes[sizes.length - 1]}
                aria-label={text("reader.text_larger")}
                title={text("reader.text_larger")}
                className="flex flex-1 items-center justify-center rounded-[1.5rem] text-ink transition-colors hover-wash disabled:text-ink-faint"
              >
                <TextLargerIcon className="h-6 w-6" />
              </button>
            </div>
            <div aria-hidden className="flex shrink-0 items-center justify-center gap-1.5 pb-1 pt-1.5">
              {sizes.map((value, index) => (
                <span
                  key={value}
                  className={`h-1.5 w-1.5 rounded-full transition-colors ${
                    index <= step ? "bg-ink-mute" : "bg-edge-strong"
                  }`}
                />
              ))}
            </div>
          </div>
          <SegmentedControl<ThemePreference>
            size="lg"
            label={text("settings.appearance")}
            value={appearance}
            onChange={onAppearance}
            options={[
              { value: "light", label: <><SunIcon />{text("settings.light")}</> },
              { value: "dark", label: <><MoonIcon />{text("settings.dark")}</> },
              { value: "system", label: <><AutoAppearanceIcon />{text("settings.system")}</> },
            ]}
          />
          <SegmentedControl<ReadingMode>
            size="lg"
            label={text("settings.layout")}
            value={mode}
            onChange={onMode}
            options={[
              { value: "pages", label: <><PagesIcon />{text("settings.pages")}</> },
              { value: "scroll", label: <><ScrollIcon />{text("settings.scroll")}</> },
            ]}
          />
          <button
            type="button"
            onClick={() => setMore((value) => !value)}
            aria-expanded={more}
            className="flex h-11 items-center justify-center gap-2 rounded-full bg-band px-4 text-sm font-semibold text-ink transition-colors hover-wash"
          >
            <SlidersIcon />
            {text("settings.customize")}
            <ChevronDownIcon className={`h-4 w-4 text-ink-mute transition-transform ${more ? "rotate-180" : ""}`} />
          </button>
        </div>

        {more && (
          /* No box around this. The quick rows above are pills BECAUSE they
             are controls; these are a form, and a grey field behind a form
             that already sits inside a panel is one container too many
             (owner, 06/09: "box xám ở đây cũng không cần thiết, nó bị
             thừa"). A dotted rule opens the section instead - it separates
             without drawing a second edge the way a solid hairline does
             (owner, 06/09) - and each setting is a labelled line at the
             panel's own inset. */
          <div className="mt-4 flex flex-col gap-5 border-t border-dotted border-edge-strong pt-4">
            <label className="flex flex-col gap-2">
              <span className="flex items-baseline justify-between">
                <span className="text-sm text-ink">{text("settings.line_spacing")}</span>
                <span className="text-sm tabular-nums text-ink-mute">{prefs.lineHeight.toFixed(2)}</span>
              </span>
              <Slider
                label={text("settings.line_spacing")}
                value={prefs.lineHeight}
                min={LINE_HEIGHT.min}
                max={LINE_HEIGHT.max}
                step={LINE_HEIGHT.step}
                onChange={(value) => set("lineHeight", value)}
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className="flex items-baseline justify-between">
                <span className="text-sm text-ink">{text("settings.margins")}</span>
                <span className="text-sm tabular-nums text-ink-mute">{`${prefs.margin}%`}</span>
              </span>
              <Slider
                label={text("settings.margins")}
                value={prefs.margin}
                min={MARGIN.min}
                max={MARGIN.max}
                step={MARGIN.step}
                onChange={(value) => set("margin", value)}
              />
            </label>
            <div className="flex flex-col gap-2">
              <span className="text-sm text-ink">{text("settings.columns")}</span>
              <SegmentedControl<Columns>
                label={text("settings.columns")}
                value={prefs.columns}
                onChange={(value) => set("columns", value)}
                options={[
                  { value: "auto", label: text("settings.columns_auto"), disabled: mode !== "pages" },
                  { value: 1, label: "1", disabled: mode !== "pages" },
                  { value: 2, label: "2", disabled: mode !== "pages" },
                ]}
              />
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm text-ink">{text("settings.justify")}</span>
              <Switch label={text("settings.justify")} checked={prefs.justify} onChange={(value) => set("justify", value)} />
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm text-ink">{text("settings.bold")}</span>
              <Switch label={text("settings.bold")} checked={prefs.bold} onChange={(value) => set("bold", value)} />
            </div>
            <Button
              variant="ghost"
              size="sm"
              disabled={isDefaultPrefs(prefs)}
              onClick={() => onPrefs(DEFAULT_PREFS)}
              className="-mt-1 self-start rounded-full px-0"
            >
              {text("settings.reset")}
            </Button>
          </div>
        )}
      </div>
    </Surface>
  );
}
