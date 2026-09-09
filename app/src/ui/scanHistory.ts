/* Two rules the scan history gets wrong if they are written inline.
 *
 * `position` is ONE value for the whole app - the part the voice is on. The
 * history shows many passages at once, and every one of them has a `part-2`.
 * Painting the marker wherever the id matches would light up a paragraph in
 * every open entry, including passages read an hour ago. Which entry the
 * voice is IN has to decide first, and that is what `readingAt` is.
 */

/** Whether an entry shows its full text, split as the voice will speak it.
 *
 * The entry being read opens itself: following along is the whole point, and
 * a reader should not have to click to see where the voice has got to. A
 * click after that still wins, in both directions - closing the noisy one,
 * opening an older one - so the choice is remembered per entry rather than
 * derived. */
export function isOpen(
  at: number,
  readingAt: number | null,
  toggled: Record<number, boolean>,
): boolean {
  const chosen = toggled[at];
  return chosen === undefined ? at === readingAt : chosen;
}

/** The part to paint inside THIS entry, or null when the voice is elsewhere. */
export function currentPart(
  at: number,
  readingAt: number | null,
  position: string | null,
): string | null {
  if (readingAt === null || at !== readingAt) return null;
  return position;
}

/** The first line of a collapsed entry: enough to recognise the passage. */
export function summarise(text: string, limit = 90): string {
  const tidy = text.replace(/\s+/g, " ").trim();
  return tidy.length <= limit ? tidy : `${tidy.slice(0, limit).trimEnd()}…`;
}
