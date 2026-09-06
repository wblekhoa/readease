/** The reading size, shared by the screen that renders text and the bar that
 * changes it - they live in different components, so the steps and the
 * storage key have to be one thing, not two copies.
 *
 * Reading text is CONTENT, not UI chrome: it does not belong to the app's
 * 14px scale, and the reader picks its own size (HIG §3.9).
 */
/** Eight steps, not five (owner, 06/09: "thêm cấp"). The five were 15-21,
 * which gave a reader who wanted SMALL exactly one step down and a reader
 * who wanted LARGE exactly two. The ends are where a size control earns its
 * keep, so the scale reaches further in both directions; the middle keeps
 * its old spacing so the sizes people are already reading at are untouched.
 * `storedReadingSize` validates by `includes`, so widening the set cannot
 * invalidate anything already saved. */
export const READING_SIZES = [13, 14, 15, 16, 17, 19, 21, 24];
/** The size a reader lands on before touching anything. Named once: the
 * fallback below and the "you are at the default" test in the panel must
 * agree, and two literals do not stay agreed. */
export const DEFAULT_READING_SIZE = 16;
const KEY = "readease.reading-size";

export function storedReadingSize(): number {
  try {
    const saved = Number(localStorage.getItem(KEY));
    return READING_SIZES.includes(saved) ? saved : DEFAULT_READING_SIZE;
  } catch {
    return DEFAULT_READING_SIZE;
  }
}

export function rememberReadingSize(size: number): void {
  try {
    localStorage.setItem(KEY, String(size));
  } catch {
    // A reader that cannot remember the size still reads fine.
  }
}
