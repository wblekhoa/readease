/** Where a paragraph's highlights sit inside it - pure, so node:test can
 * hold the awkward cases.
 *
 * The words came from Apple Books, which straightens or curls quotes, uses
 * non-breaking spaces and collapses runs differently from this reader's
 * import. Both sides are normalised the same way for the search, and the
 * match is then mapped back to the paragraph's own characters so the mark
 * lands on the text exactly as displayed. A highlight that runs past the
 * paragraph is marked to the paragraph's end.
 *
 * A paragraph usually carries MORE than one highlight - two sentences marked
 * on different days, or a phrase marked inside a sentence marked whole. So
 * the paragraph comes back cut into pieces rather than split once, and no
 * character is ever claimed by two marks: a highlight that would land on
 * characters an earlier one took is moved to its next free occurrence, and
 * dropped when it has none.
 */
export type HighlightPiece = {
  text: string;
  /** Which highlight made this piece - its position in the list handed in,
   * so the caller can pair it back with the annotation and use that one's
   * colour and note. `null` for the plain stretches between marks. */
  index: number | null;
};

const FOLD: Record<string, string> = { "“": '"', "”": '"', "‘": "'", "’": "'", " ": " " };

function fold(character: string): string {
  return FOLD[character] ?? character.toLowerCase();
}

/** Normalised text plus, for each normalised character, the index of the
 * original character it came from. Runs of whitespace fold to one space. */
function normalise(text: string): { folded: string; origin: number[] } {
  let folded = "";
  const origin: number[] = [];
  let lastWasSpace = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = fold(text[index]);
    const isSpace = /\s/.test(character);
    if (isSpace) {
      if (lastWasSpace) continue;
      folded += " ";
    } else {
      folded += character;
    }
    origin.push(index);
    lastWasSpace = isSpace;
  }
  return { folded, origin };
}

/** Half-open span in normalised coordinates. */
type Span = { start: number; end: number; index: number };

/** The first place `needle` sits in `folded` at or after `from`.
 *
 * A needle that is not there whole may still START here and run on into the
 * next paragraph - then the paragraph's tail is a prefix of the selection,
 * and the mark reaches the paragraph's end.
 */
function locate(folded: string, needle: string, from: number): Omit<Span, "index"> | null {
  const at = folded.indexOf(needle, from);
  if (at >= 0) return { start: at, end: at + needle.length };
  for (let length = Math.min(needle.length - 1, folded.length); length >= 12; length -= 1) {
    const tail = needle.slice(0, length);
    const start = folded.indexOf(tail, from);
    if (start >= 0 && start + length === folded.length) return { start, end: folded.length };
  }
  return null;
}

/** The paragraph in order: plain stretches and highlighted ones. Joining
 * every piece's text always gives the paragraph back unchanged. */
export function markParagraph(text: string, selections: string[]): HighlightPiece[] {
  const { folded, origin } = normalise(text);
  const found: Span[] = [];
  for (let index = 0; index < selections.length; index += 1) {
    const needle = normalise(selections[index]).folded.trim();
    if (!needle) continue;
    const span = locate(folded, needle, 0);
    if (span) found.push({ ...span, index });
  }
  // Read order, not the order the notes arrived in. Two highlights starting
  // together are laid out longer-first, so the bigger one keeps its start
  // and the shorter one is the one that has to move.
  found.sort((a, b) => a.start - b.start || b.end - a.end);

  const kept: Span[] = [];
  let cursor = 0;
  for (const span of found) {
    let { start, end } = span;
    if (end <= cursor) {
      // Every character of it is already marked: the same words highlighted
      // twice, or a phrase inside a longer highlight. If the paragraph says
      // them again further on, that later saying is the one this highlight
      // can have; if it does not, this highlight has nowhere to go.
      const again = locate(folded, folded.slice(start, end), cursor);
      if (!again) continue;
      start = again.start;
      end = again.end;
    }
    if (start < cursor) start = cursor;
    // A mark that begins on the space left by the mark before it renders as
    // a coloured gap, so the clipped one starts on its first word instead.
    while (start < end && folded[start] === " ") start += 1;
    if (start >= end) continue;
    kept.push({ start, end, index: span.index });
    cursor = end;
  }

  const pieces: HighlightPiece[] = [];
  let at = 0;
  for (const span of kept) {
    const start = origin[span.start];
    // The last original character the span covers is the one the last
    // normalised character came from - so a mark never swallows the
    // whitespace that was collapsed after it.
    const end = origin[span.end - 1] + 1;
    if (start > at) pieces.push({ text: text.slice(at, start), index: null });
    pieces.push({ text: text.slice(start, end), index: span.index });
    at = end;
  }
  if (at < text.length) pieces.push({ text: text.slice(at), index: null });
  return pieces;
}
