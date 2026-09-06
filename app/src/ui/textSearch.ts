/** Find words in the open book, the way a Vietnamese reader types them.
 *
 * Diacritics-insensitive: "hung" finds "Hùng" and "trai nghiem" finds
 * "trải nghiệm" (the same `fold` the voice list uses). The fold changes
 * string length, so every folded character remembers where it came from and
 * the hit is cut out of the ORIGINAL text - the snippet shows the book's own
 * spelling, and the match is marked exactly.
 *
 * Pure: the shell holds the book's text once it is open, so a search costs
 * no round trip and works with the engine busy reading.
 */
import { fold } from "./voiceShortlist.ts";

export type SearchChapter = {
  id: string;
  title: string;
  segments: { id: string; text: string }[];
};

export type SearchHit = {
  chapterIndex: number;
  chapterId: string;
  chapterTitle: string;
  segmentId: string;
  /** The words around the match, from the original text. */
  before: string;
  match: string;
  after: string;
};

export const MIN_QUERY = 2;
export const MAX_HITS = 200;
const CONTEXT = { before: 36, after: 56 };

/** The folded text, and for each folded character the index of the
 * original character it came from. */
export function foldMap(text: string): { folded: string; map: number[] } {
  let folded = "";
  const map: number[] = [];
  for (let index = 0; index < text.length; index += 1) {
    const piece = fold(text[index]);
    for (const character of piece) {
      folded += character;
      map.push(index);
    }
  }
  return { folded, map };
}

/** The query as the book is folded: trimmed, spaces collapsed. */
export function foldQuery(query: string): string {
  return fold(query).replace(/\s+/g, " ").trim();
}

function cutBefore(text: string, end: number): string {
  const start = Math.max(0, end - CONTEXT.before);
  let piece = text.slice(start, end);
  if (start > 0) {
    const space = piece.indexOf(" ");
    piece = (space >= 0 && space < piece.length - 1 ? piece.slice(space + 1) : piece);
    piece = "…" + piece;
  }
  return piece;
}

function cutAfter(text: string, start: number): string {
  const end = Math.min(text.length, start + CONTEXT.after);
  let piece = text.slice(start, end);
  if (end < text.length) {
    const space = piece.lastIndexOf(" ");
    piece = (space > 0 ? piece.slice(0, space) : piece) + "…";
  }
  return piece;
}

export function searchBook(chapters: readonly SearchChapter[], query: string, limit = MAX_HITS): SearchHit[] {
  const needle = foldQuery(query);
  if (needle.length < MIN_QUERY) return [];
  const hits: SearchHit[] = [];
  chapters.forEach((chapter, chapterIndex) => {
    for (const segment of chapter.segments) {
      if (hits.length >= limit) return;
      const { folded, map } = foldMap(segment.text);
      let at = folded.indexOf(needle);
      while (at >= 0 && hits.length < limit) {
        const start = map[at];
        const end = map[at + needle.length - 1] + 1;
        hits.push({
          chapterIndex,
          chapterId: chapter.id,
          chapterTitle: chapter.title,
          segmentId: segment.id,
          before: cutBefore(segment.text, start),
          match: segment.text.slice(start, end),
          after: cutAfter(segment.text, end),
        });
        at = folded.indexOf(needle, at + needle.length);
      }
    }
  });
  return hits;
}
