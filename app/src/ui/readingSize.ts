/** The reading size, shared by the screen that renders text and the bar that
 * changes it - they live in different components, so the steps and the
 * storage key have to be one thing, not two copies.
 *
 * Reading text is CONTENT, not UI chrome: it does not belong to the app's
 * 14px scale, and the reader picks its own size (HIG §3.9).
 */
export const READING_SIZES = [15, 16, 17, 19, 21];
const KEY = "readease.reading-size";

export function storedReadingSize(): number {
  try {
    const saved = Number(localStorage.getItem(KEY));
    return READING_SIZES.includes(saved) ? saved : 16;
  } catch {
    return 16;
  }
}

export function rememberReadingSize(size: number): void {
  try {
    localStorage.setItem(KEY, String(size));
  } catch {
    // A reader that cannot remember the size still reads fine.
  }
}
