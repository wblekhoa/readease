/** Where a highlight's words sit inside a paragraph - pure, so node:test
 * can hold the awkward cases.
 *
 * The words came from Apple Books, which straightens or curls quotes, uses
 * non-breaking spaces and collapses runs differently from this reader's
 * import. Both sides are normalised the same way for the search, and the
 * match is then mapped back to the paragraph's own characters so the mark
 * lands on the text exactly as displayed. A highlight that runs past the
 * paragraph is marked to the paragraph's end.
 */
export type HighlightSplit = { before: string; mark: string; after: string };

const FOLD: Record<string, string> = { "“": '"', "”": '"', "‘": "'", "’": "'", " ": " " };

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

export function splitHighlight(text: string, selected: string): HighlightSplit | null {
  const needle = normalise(selected).folded.trim();
  if (!needle) return null;
  const { folded, origin } = normalise(text);
  const at = folded.indexOf(needle);
  if (at < 0) {
    // The highlight may start here and run on into the next paragraph:
    // then the paragraph's tail is a prefix of the selection.
    for (let length = Math.min(needle.length - 1, folded.length); length >= 12; length -= 1) {
      const tail = needle.slice(0, length);
      const start = folded.indexOf(tail);
      if (start >= 0 && start + length === folded.length) {
        return { before: text.slice(0, origin[start]), mark: text.slice(origin[start]), after: "" };
      }
    }
    return null;
  }
  const startIndex = origin[at];
  const lastIndex = origin[at + needle.length - 1];
  return {
    before: text.slice(0, startIndex),
    mark: text.slice(startIndex, lastIndex + 1),
    after: text.slice(lastIndex + 1),
  };
}
