/** The contents as a reader sees them (HIG 3.25) - pure, for node:test.
 *
 * The engine hands the publisher's tree - every entry a title, a level (1 is
 * the outermost) and the passage it points at. This file decides what the
 * column shows for it: a number, the words beside the number, how deep the
 * row sits and how much weight it carries.
 *
 * Numbers follow the book. A chapter keeps the number its own title gives it
 * ("Chương 7" is 7, whatever came before); a part gets a Roman numeral; what
 * lies under a numbered chapter counts as N.1, N.2, N.1.1. What stands before
 * the first part or chapter and after the last one - a foreword, a prologue,
 * the notes - carries no number, and neither does anything under it. A book
 * whose titles carry no "Chương"/"Chapter" at all is numbered 1..N at its
 * top level, less the front and back matter its titles name.
 */
export type TocEntry = { title: string; level: number; segment_id: string };

export type ContentsRow = {
  entry: TocEntry;
  /** The number beside the title, or null. */
  number: string | null;
  /** The words shown: the title without the "Chương 1 " the number now says. */
  label: string;
  /** 0 for the outermost level of this book's tree. */
  depth: number;
  /** Levels below the chapter level: 0 for a chapter, 1 for its sections,
   * negative for a part above it - what the column indents by. */
  sub: number;
  /** A part opens a group; a chapter is a stop; the rest sits inside one. */
  role: "part" | "chapter" | "section";
};

const UNITS: Record<string, number> = {
  "một": 1, "mốt": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4, "năm": 5, "lăm": 5,
  "sáu": 6, "bảy": 7, "tám": 8, "chín": 9,
};
const ENGLISH: Record<string, number> = {
  one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16,
  seventeen: 17, eighteen: 18, nineteen: 19, twenty: 20,
};

/** "hai mươi mốt" = 21, "mười lăm" = 15, "tư" = 4 - or null. */
function vietnameseNumber(words: string[]): number | null {
  let value = 0;
  let seen = false;
  for (let i = 0; i < words.length; i++) {
    const word = words[i];
    if (word === "mười") { value += 10; seen = true; continue; }
    if (word in UNITS) {
      if (words[i + 1] === "mươi") { value += UNITS[word] * 10; i++; seen = true; continue; }
      value += UNITS[word];
      seen = true;
      continue;
    }
    return null;
  }
  return seen ? value : null;
}

function romanNumber(word: string): number | null {
  if (!/^[IVXLC]+$/.test(word)) return null;
  const values: Record<string, number> = { I: 1, V: 5, X: 10, L: 50, C: 100 };
  let total = 0;
  for (let i = 0; i < word.length; i++) {
    const here = values[word[i]];
    const next = values[word[i + 1]] ?? 0;
    total += here < next ? -here : here;
  }
  return total > 0 ? total : null;
}

const ROMAN = [["C", 100], ["XC", 90], ["L", 50], ["XL", 40], ["X", 10], ["IX", 9], ["V", 5], ["IV", 4], ["I", 1]] as const;
export function roman(n: number): string {
  let rest = n;
  let out = "";
  for (const [glyph, value] of ROMAN) while (rest >= value) { out += glyph; rest -= value; }
  return out;
}

type Marker = { kind: "chapter" | "part"; n: number; rest: string };

const MARKER = /^(chương|chapter|phần|part|quyển)\s+(.+)$/iu;

/** "Chương 1 THỜI GIAN…" → chapter 1, "THỜI GIAN…"; "Phần Hai: X" → part 2, "X". */
export function marker(title: string): Marker | null {
  const found = title.trim().match(MARKER);
  if (!found) return null;
  const kind = /^(chương|chapter)$/iu.test(found[1]) ? "chapter" : "part";
  const words = found[2].split(/\s+/);
  const first = words[0].replace(/[:.\-–—]+$/u, "");
  let n: number | null = null;
  let used = 1;
  if (/^\d+$/.test(first)) n = Number(first);
  else if (romanNumber(first) !== null) n = romanNumber(first);
  else if (ENGLISH[first.toLowerCase()] !== undefined) n = ENGLISH[first.toLowerCase()];
  else {
    // Vietnamese numbers run over several words: take the longest run that
    // still reads as one ("hai mươi mốt"), stopping at the title's first word.
    for (let take = Math.min(4, words.length); take >= 1; take--) {
      const run = words.slice(0, take).map((w) => w.replace(/[:.\-–—]+$/u, "").toLowerCase());
      const value = vietnameseNumber(run);
      if (value !== null) { n = value; used = take; break; }
    }
  }
  if (n === null || n <= 0) return null;
  const rest = words.slice(used).join(" ").replace(/^[\s:.\-–—]+/u, "").trim();
  return { kind, n, rest };
}

/** Front and back matter a book without numbered chapters names. */
const MATTER = /^(bìa|bìa sách|lời bạt|lời nói đầu|lời giới thiệu|lời tựa|lời mở đầu|phần mở đầu|mở đầu|dẫn nhập|lời kết|phần kết|lời cảm ơn|lời cám ơn|chú thích|ghi chú|phụ lục|tài liệu tham khảo|thư mục|mục lục|về tác giả|cover|title page|copyright|contents|table of contents|preface|foreword|prologue|epilogue|afterword|acknowledg(e)?ments|notes|endnotes|appendix|bibliography|index|glossary|about the author)(?![\p{L}\p{N}])/iu;

export function contentsRows(entries: readonly TocEntry[]): ContentsRow[] {
  if (!entries.length) return [];
  const top = Math.min(...entries.map((e) => e.level));
  const markers = entries.map((e) => marker(e.title));
  // The chapter level: where "Chương N" titles sit most often.
  const tally = new Map<number, number>();
  entries.forEach((e, i) => { if (markers[i]?.kind === "chapter") tally.set(e.level, (tally.get(e.level) ?? 0) + 1); });
  const chapterLevel = tally.size
    ? [...tally.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0][0]
    : null;
  const stops = chapterLevel ?? top;

  const rows: ContentsRow[] = [];
  const stack: { level: number; number: string | null; kids: number }[] = [];
  let sequence = 0;
  entries.forEach((entry, i) => {
    while (stack.length && stack[stack.length - 1].level >= entry.level) stack.pop();
    const parent = stack[stack.length - 1];
    const found = markers[i];
    let number: string | null = null;
    let label = entry.title;
    if (chapterLevel !== null && found?.kind === "chapter" && entry.level === chapterLevel) {
      number = String(found.n);
      if (found.rest) label = found.rest;
    } else if (found?.kind === "part" && entry.level < stops) {
      number = roman(found.n);
      if (found.rest) label = found.rest;
    } else if (chapterLevel === null && entry.level === top && !MATTER.test(entry.title.trim())) {
      sequence += 1;
      number = String(sequence);
    } else if (parent?.number && entry.level > stops) {
      parent.kids += 1;
      number = `${parent.number}.${parent.kids}`;
    }
    // Above the chapter level, only a real part - or a line with lines under
    // it - opens a group; a lone "Lời bạt" there is one stop like a chapter.
    const opensGroup = found?.kind === "part" || (entries[i + 1]?.level ?? 0) > entry.level;
    const role = entry.level < stops ? (opensGroup ? "part" : "chapter")
      : entry.level === stops ? "chapter" : "section";
    // A part's numeral does not number what lies under it: the chapters
    // carry their own numbers.
    stack.push({ level: entry.level, number: role === "part" ? null : number, kids: 0 });
    rows.push({ entry, number, label, depth: entry.level - top, sub: entry.level - stops, role });
  });
  return rows;
}

/** The entry the reader is at: the deepest one whose passage is at or before
 * `position` (an index into the book's reading order). -1 before the first. */
export function currentRow(rows: readonly ContentsRow[], orderOf: (segmentId: string) => number, position: number): number {
  let at = -1;
  rows.forEach((row, i) => {
    const place = orderOf(row.entry.segment_id);
    if (place >= 0 && place <= position) at = i;
  });
  return at;
}
