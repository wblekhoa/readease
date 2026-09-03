/** The voices a person switches between, and how a voice's label reads.
 *
 * The engine ships twenty voices. Twenty is too many to pick from mid-
 * sentence, and one is too few to be worth a menu, so the person marks the
 * handful they actually use and the reading UI offers only those (owner,
 * 03/09: "nơi để người dùng chọn để đưa voice vào danh sách muốn đổi khi
 * đọc"). Pure functions, so the rules are testable without a shell.
 */

export type Voice = { id: string; label: string };

/** The engine labels a voice "Tên - Nữ · Bắc · Phong cách kể chuyện": the
 * part before the dash is the name, the rest describes it. Lived in
 * SettingsPanel; two panels now read labels, so it lives here instead. */
export function voiceName(label: string | undefined): string {
  return (label ?? "").split(" - ")[0].trim();
}

export function voiceDescription(label: string | undefined): string | undefined {
  const parts = (label ?? "").split(" - ");
  return parts.length > 1 ? parts.slice(1).join(" - ").trim() : undefined;
}

/** The five the app starts with.
 *
 * Nobody arrives wanting to audition twenty voices before they can read a
 * book, so the switcher is not empty on a fresh install (owner, 03/09).
 * These are a SPREAD, not a ranking - there is no usage data to rank by:
 * the engine's own default, a natural voice of each gender, and a
 * storytelling voice of each, which is what a book most often wants.
 * Anything not in this build's catalogue is dropped rather than offered.
 */
export const STARTING_VOICES = [
  "Adam",
  "Trúc Ly",
  "Phạm Tuyên",
  "Ngọc Linh",
  "Thái Sơn",
] as const;

/** The list to start from: the stored one, or the starting five.
 *
 * "Never chosen" and "chosen to be empty" are different, and only the first
 * gets seeded - otherwise a person who switched every voice off would find
 * them all back the next time they opened the app.
 */
export function initialShortlist(
  stored: string | null | undefined,
  catalogue: readonly Voice[],
): string[] {
  if (stored === null || stored === undefined || stored === "") {
    return catalogue
      .filter((voice) => (STARTING_VOICES as readonly string[]).includes(voice.id))
      .map((voice) => voice.id);
  }
  return parseShortlist(stored);
}

/** Read the stored list. Anything unreadable is an empty list, never a
 * throw: a settings value is not worth a broken window. */
export function parseShortlist(stored: string | null | undefined): string[] {
  if (!stored) return [];
  try {
    const value: unknown = JSON.parse(stored);
    if (!Array.isArray(value)) return [];
    return value.filter((item): item is string => typeof item === "string");
  } catch {
    return [];
  }
}

export function serializeShortlist(ids: readonly string[]): string {
  return JSON.stringify(ids);
}

export function toggleShortlist(ids: readonly string[], id: string): string[] {
  return ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id];
}

/** What the reading UI offers: the marked voices, in the catalogue's own
 * order, plus the one being used.
 *
 * The current voice is always in the list even when it is not marked -
 * otherwise the menu would show a set that does not contain what you are
 * listening to, and there would be no way back to it. An empty shortlist is
 * left empty rather than seeded with everything: "I have not chosen yet" is
 * a real state, and it should offer the one voice in use, not twenty.
 */
export function offeredVoices(
  catalogue: readonly Voice[],
  shortlist: readonly string[],
  currentId: string,
): Voice[] {
  const wanted = new Set(shortlist);
  if (currentId) wanted.add(currentId);
  return catalogue.filter((voice) => wanted.has(voice.id));
}
