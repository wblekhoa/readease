/**
 * The release notes as the update sheet shows them (HIG 3.20). Pure, so
 * the node tests can read it without React or the Tauri plugins.
 */
import { formatDay } from "./format.ts";

/** Markdown is what the release notes are written in, hard-wrapped at 72
 * columns; on this sheet the wraps are undone (a line that is not a bullet
 * continues the one before it), headings are dropped and emphasis stripped, and a
 * bullet becomes a paragraph of its own - eight at most. */
export function excerpt(notes: string, language?: "vi" | "en"): string {
  const paragraphs: string[] = [];
  for (const raw of half(notes, language).split("\n")) {
    // A heading is the version, which the sheet already says.
    if (/^#+\s/.test(raw)) { paragraphs.push(""); continue; }
    // Emphasis, code marks and link syntax are markdown, not words: the
    // sheet said "`.dmg`" with its backticks (27/09).
    const line = raw
      .replace(/\*\*/g, "")
      .replace(/`([^`]*)`/g, "$1")
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
      .trim();
    if (line.length === 0 || line === "---") { paragraphs.push(""); continue; }
    const bullet = /^[-*]\s+/.test(line);
    const text = bullet ? "• " + line.replace(/^[-*]\s+/, "") : line;
    const last = paragraphs.length - 1;
    if (!bullet && last >= 0 && paragraphs[last].length > 0) paragraphs[last] += " " + text;
    else paragraphs.push(text);
  }
  return paragraphs.filter((p) => p.length > 0).slice(0, 8).join("\n");
}

/* The letters only Vietnamese writes with - the mark of the Vietnamese half. */
const VIETNAMESE_LETTER = /[ăâđêôơưàáạảãằắặẳẵầấậẩẫèéẹẻẽềếệểễìíịỉĩòóọỏõồốộổỗờớợởỡùúụủũừứựửữỳýỵỷỹ]/giu;

/** A release's notes are written twice - Vietnamese, a rule, English - and
 * the sheet shows the half in the reader's language (27/09: the English
 * interface showed the Vietnamese half). Which half is which is RELATIVE:
 * the Vietnamese one is the half whose letters most often carry Vietnamese
 * marks (measured on 0.1.18/0.1.19: 20-25 % against 0-0.3 %) - the English
 * half quotes a button by its Vietnamese name, so "has any" would not do.
 * Only when one half is plainly Vietnamese (over 10 %) are they halves at
 * all; one part, no language: the notes as they are. */
function half(notes: string, language?: "vi" | "en"): string {
  if (!language) return notes;
  const parts = notes.split(/\n-{3,}\n/);
  if (parts.length < 2) return notes;
  const marked = (part: string) => {
    const letters = part.match(/\p{L}/gu)?.length ?? 0;
    return letters ? (part.match(VIETNAMESE_LETTER)?.length ?? 0) / letters : 0;
  };
  const ranked = [...parts].sort((a, b) => marked(b) - marked(a));
  if (marked(ranked[0]) < 0.1) return notes;
  return language === "vi" ? ranked[0] : ranked[ranked.length - 1];
}

/** The manifest's `pub_date` (RFC 3339) as a short local date; the raw
 * string when it will not parse. */
export function releaseDate(iso: string, locale = "vi"): string {
  return formatDay(iso, locale === "vi" ? "vi" : "en") ?? iso;
}
