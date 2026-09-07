/** The voices a person switches between, and how a voice's label reads.
 *
 * The engine ships twenty voices. Twenty is too many to pick from mid-
 * sentence, and one is too few to be worth a menu, so the person marks the
 * handful they actually use and the reading UI offers only those (owner,
 * 03/09: "nơi để người dùng chọn để đưa voice vào danh sách muốn đổi khi
 * đọc"). Pure functions, so the rules are testable without a shell.
 */

export type VoiceGender = "male" | "female";

export type Voice = {
  id: string;
  label: string;
  /** Languages the provider verified this voice in (BCP-47: "vi", "en-us").
   * Absent or empty is "nobody said" - the local model and OpenAI both come
   * that way - and is never drawn as "cannot". */
  languages?: string[];
  /** Explicit provider metadata when available. Missing means unknown. */
  gender?: VoiceGender;
};

/** Has the provider itself vouched for this voice in Vietnamese?
 *
 * The primary subtag is what matters: "vi" and "vi-VN" are both yes. Only
 * ElevenLabs answers this at all today; for everything else the answer is
 * unknown, which reads as false here so that a badge is only ever a claim
 * somebody made.
 */
export function speaksVietnamese(voice: Pick<Voice, "languages">): boolean {
  return (voice.languages ?? []).some((tag) => tag.toLowerCase().split("-")[0] === "vi");
}

/** May this voice be offered for a book in `language`?
 *
 * Yes unless the voice NAMES its languages and this one is not among them.
 * The difference matters: the local model publishes `["vi"]` because the
 * engine enforces it, so it drops out of an English book's list; OpenAI
 * publishes nothing about any of its voices and they all read Vietnamese
 * after a fashion, so they stay. Hiding those would be a lie by filter -
 * a list quietly missing rows with nothing on screen to say why.
 */
export function canSpeak(
  voice: Pick<Voice, "languages">,
  language: string,
): boolean {
  const named = voice.languages ?? [];
  if (named.length === 0) return true;
  const wanted = language.toLowerCase().split("-")[0];
  return named.some((tag) => tag.toLowerCase().split("-")[0] === wanted);
}

/** The engine labels a voice "Tên — Nữ · Bắc · Phong cách kể chuyện": the
 * part before the dash is the name, the rest describes it. Lived in
 * SettingsPanel; two panels now read labels, so it lives here instead.
 *
 * The dash is the SDK's em dash (" — "); the mock and older fixtures wrote
 * " - ". Splitting on the hyphen alone let the whole label through to the
 * footer chip - "Phạm Tuyên — Nam · Bắc · Phong cách tự nhiên · 1×" across
 * the transport buttons (owner, 06/09). An en dash is NOT a separator: a
 * cloned voice is called "JM – Husky & Engaging", and that is its name. */
const NAME_DASH = /\s+[-—]\s+/;

export function voiceName(label: string | undefined): string {
  return (label ?? "").split(NAME_DASH)[0].trim();
}

export function voiceDescription(label: string | undefined): string | undefined {
  const value = label ?? "";
  const dash = value.match(NAME_DASH);
  if (!dash || dash.index === undefined) return undefined;
  const rest = value.slice(dash.index + dash[0].length).trim();
  return rest || undefined;
}

/** What the footer chip calls the voice in use: the shortest thing that
 * still tells it apart from the other voices on offer.
 *
 * The chip is a reminder, not a description - the description lives one
 * tap away in the settings panel. So: the name alone ("Phạm Tuyên",
 * "Alloy"); and only when another offered voice answers to the same name
 * does the first descriptor come along ("Nam · Bắc", or the provider). */
export function chipName(voice: Pick<Voice, "id" | "label">, offered: readonly Pick<Voice, "id" | "label">[]): string {
  const bare = (item: Pick<Voice, "id" | "label">) =>
    (tidyName(item.label) || item.id).split(" · ")[0].trim();
  const mine = bare(voice);
  const twin = offered.some((item) => item.id !== voice.id && bare(item) === mine);
  if (!twin) return mine;
  const detail =
    voiceDescription(voice.label)?.split(" · ")[0]?.trim()
    || tidyName(voice.label).split(" · ").slice(1).join(" · ").trim();
  return detail ? `${mine} · ${detail}` : mine;
}

/** A name without its diacritics, for matching what someone types.
 *
 * This is a Vietnamese app: a search that will not find "Hùng" when you
 * type "hung" is a search nobody uses. NFD splits the tone marks off as
 * combining characters and they are dropped; "đ" carries no combining mark
 * and has to be named.
 */
export function fold(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}

/** The name to SHOW: the studio's own, minus the timestamp it was saved with.
 *
 * A cloned voice comes back as "JM – Husky & Engaging (2025-01-25_1100)".
 * The date is filing, not description. Only a date-shaped tail goes -
 * "(Real Time AI Voice)" is what the voice IS and stays.
 */
export function tidyName(label: string | undefined): string {
  return voiceName(label).replace(/\s*\(\d{4}-\d{2}-\d{2}[^)]*\)\s*$/, "").trim();
}

/** Does this voice answer to what was typed? Empty query matches everything. */
export function matchesVoice(voice: Voice, query: string): boolean {
  const wanted = fold(query).trim();
  if (!wanted) return true;
  const haystack = fold(`${voice.label ?? ""} ${voice.id}`);
  return wanted.split(/\s+/).every((word) => haystack.includes(word));
}

/** Known gender without guessing from a provider voice's name.
 *
 * VieNeu's local catalogue owns a structured description whose first token
 * is exactly `Nam` or `Nữ`, so that field is safe to translate. External
 * voices only qualify when their provider supplied an explicit value.
 */
export function voiceGender(voice: Voice, local = true): VoiceGender | null {
  if (voice.gender === "male" || voice.gender === "female") return voice.gender;
  if (!local) return null;
  const localField = fold((voiceDescription(voice.label) ?? "").split("·")[0]).trim();
  if (localField === "nam") return "male";
  if (localField === "nu") return "female";
  return null;
}

/** One voice must satisfy every active shortcut filter. */
export function matchesVoiceFilters(
  voice: Voice,
  query: string,
  source: string,
  provider: string,
  gender: "all" | VoiceGender,
): boolean {
  return matchesVoice(voice, query)
    && (provider === "all" || provider === source)
    && (gender === "all" || voiceGender(voice, source === "local") === gender);
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
