/** The reader's pronunciations as the app keeps them: how a written word is
 * said. Stored under the engine's `pronunciations` key; the engine applies
 * them (`domain/pronunciation.py`) and owns the matching rules. Pure. */

export type Pronunciation = { written: string; spoken: string };

/** The same bounds the engine keeps; a longer row would be skipped there. */
export const MAX_WRITTEN = 80;
export const MAX_SPOKEN = 200;
export const MAX_ENTRIES = 300;

const tidy = (value: string) => value.split(/\s+/).filter(Boolean).join(" ");

/** What a stored value holds, skipping anything malformed. */
export function readPronunciations(value: unknown): Pronunciation[] {
  let rows = value;
  if (typeof rows === "string") {
    try {
      rows = rows.trim() ? JSON.parse(rows) : [];
    } catch {
      return [];
    }
  }
  if (!Array.isArray(rows)) return [];
  return rows.flatMap((row) => {
    if (!row || typeof row !== "object") return [];
    const written = tidy(String((row as Pronunciation).written ?? ""));
    const spoken = tidy(String((row as Pronunciation).spoken ?? ""));
    return written && spoken ? [{ written, spoken }] : [];
  });
}

/** A new row, or a new spelling for a word already there (any case): the
 * word keeps its place in the list. Null when the row cannot be kept. */
export function withPronunciation(list: Pronunciation[], written: string, spoken: string): Pronunciation[] | null {
  const row = { written: tidy(written), spoken: tidy(spoken) };
  if (!row.written || !row.spoken || row.written.length > MAX_WRITTEN || row.spoken.length > MAX_SPOKEN) return null;
  const at = list.findIndex((entry) => entry.written.toLocaleLowerCase() === row.written.toLocaleLowerCase());
  if (at >= 0) return list.map((entry, index) => (index === at ? row : entry));
  if (list.length >= MAX_ENTRIES) return null;
  return [...list, row];
}

export function withoutPronunciation(list: Pronunciation[], written: string): Pronunciation[] {
  return list.filter((entry) => entry.written !== written);
}
