/** How the reading text is set - the Books "Customize" choices, minus the
 * ones the owner does not want (06/09: no colour themes, no font picker).
 *
 * Text size and pages-or-scroll have their own stores and predate this one;
 * these are the finer choices, kept together because a person changes them
 * together and a "reset" has to put all of them back at once. Stored
 * locally like the others: they are about this screen, not about the book.
 */
import { MEASURE_EM, type Columns } from "./pageLayout.ts";

export type { Columns };

export type ReadingPrefs = {
  /** Line height as a multiple of the type size. */
  lineHeight: number;
  /** 0-100: how much of the measure is given back to the margins. */
  margin: number;
  columns: Columns;
  justify: boolean;
  bold: boolean;
};

export const DEFAULT_PREFS: ReadingPrefs = {
  lineHeight: 1.75,
  margin: 0,
  columns: "auto",
  justify: false,
  bold: false,
};

export const LINE_HEIGHT = { min: 1.4, max: 2.1, step: 0.05 };
export const MARGIN = { min: 0, max: 100, step: 10 };
/** At 100% margin the measure narrows from 40em to 30em - narrower than
 * that and a page is a strip of a few words per line. */
const MARGIN_EM = 10;

const KEY = "readease.reading-prefs";

/** The reading measure in em for a margin setting. */
export function measureEm(margin: number): number {
  return MEASURE_EM - (clamp(margin, MARGIN.min, MARGIN.max) / 100) * MARGIN_EM;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function snap(value: number, { min, max, step }: { min: number; max: number; step: number }): number {
  const stepped = Math.round((clamp(value, min, max) - min) / step) * step + min;
  return Number(stepped.toFixed(2));
}

/** Whatever was stored, made sane: every field clamped to its scale, every
 * unknown value replaced by the default - so a hand-edited or stale record
 * can never draw an unreadable page. */
export function normalizePrefs(raw: unknown): ReadingPrefs {
  const given = (raw && typeof raw === "object" ? raw : {}) as Partial<Record<keyof ReadingPrefs, unknown>>;
  const lineHeight = typeof given.lineHeight === "number" && Number.isFinite(given.lineHeight)
    ? snap(given.lineHeight, LINE_HEIGHT)
    : DEFAULT_PREFS.lineHeight;
  const margin = typeof given.margin === "number" && Number.isFinite(given.margin)
    ? snap(given.margin, MARGIN)
    : DEFAULT_PREFS.margin;
  const columns: Columns = given.columns === 1 || given.columns === 2 ? given.columns : "auto";
  return {
    lineHeight,
    margin,
    columns,
    justify: given.justify === true,
    bold: given.bold === true,
  };
}

export function isDefaultPrefs(prefs: ReadingPrefs): boolean {
  return (Object.keys(DEFAULT_PREFS) as (keyof ReadingPrefs)[]).every(
    (key) => prefs[key] === DEFAULT_PREFS[key],
  );
}

export function storedReadingPrefs(): ReadingPrefs {
  try {
    const saved = localStorage.getItem(KEY);
    return saved ? normalizePrefs(JSON.parse(saved)) : DEFAULT_PREFS;
  } catch {
    return DEFAULT_PREFS;
  }
}

export function rememberReadingPrefs(prefs: ReadingPrefs): void {
  try {
    if (isDefaultPrefs(prefs)) localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, JSON.stringify(prefs));
  } catch {
    // The page still sets the way it was asked to, for this session.
  }
}
