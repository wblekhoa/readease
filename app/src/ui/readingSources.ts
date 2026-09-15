/** What this Mac can read, in which language, and with what.
 *
 * Two local models, one per language, each a download the reader chooses
 * (owner, 15/09: "cho user chọn tải theo yêu cầu"); and the paid providers,
 * whose voices read both. The settings panel asks first which LANGUAGE to
 * read in and then shows that language's voices and models (owner, 15/09:
 * "chọn trước là họ muốn đọc ở ngôn ngữ nào rồi mới hiển thị"); the hub
 * on the home screen sums it all up. Nothing here forbids anything - since
 * 15/09 any voice reads any text - it only says what fits, and suggests.
 * Pure, so the rules have tests without a shell.
 */
import { isPaidVoice } from "./readingCost.ts";
import { canSpeak, vouchedFor, type Voice } from "./voiceShortlist.ts";

export type Language = "vi" | "en";

export const LANGUAGES: readonly Language[] = ["vi", "en"];

export function isLanguage(value: unknown): value is Language {
  return value === "vi" || value === "en";
}

/** `model.status` as the engine answers it. */
export type ModelStatus = {
  ready: boolean;
  precision: string | null;
  installed: Record<string, number>;
  /** Absent on an engine without the English model at all. */
  english?: { ready: boolean; installed: number; download_bytes: number };
};

/** The voices that fit a language: its own model's, and every paid voice
 * the provider vouched for in it or said nothing about. */
export function voicesFor(voices: readonly Voice[], language: Language): Voice[] {
  return voices.filter((voice) => canSpeak(voice, language));
}

/** What the settings panel offers under a language's tab.
 *
 * The marked voices that fit, plus the one in use - the same list the
 * mid-reading switcher shows, narrowed to the language. When none of the
 * marked voices fits, EVERY voice that fits: the starting shortlist is five
 * Vietnamese voices, so a reader who has just downloaded the English model
 * would otherwise open its tab on an empty select with the six new voices
 * a visit to the voices panel away.
 */
export function offeredFor(
  voices: readonly Voice[],
  shortlist: readonly string[],
  currentId: string,
  language: Language,
): Voice[] {
  const fitting = voicesFor(voices, language);
  const marked = new Set(shortlist);
  if (currentId) marked.add(currentId);
  const picked = fitting.filter((voice) => marked.has(voice.id));
  return picked.length ? picked : fitting;
}

/** The voice to switch to when the reader picks a language.
 *
 * The one last used under that language if it is still offered; otherwise
 * the first offered voice on this Mac; otherwise the first offered at all -
 * a paid voice, but one the reader listed themselves. Null when nothing
 * fits, in which case the voice in use is left alone and the panel shows
 * how to get one.
 */
export function voiceForTab(
  remembered: string | null | undefined,
  offered: readonly Voice[],
): string | null {
  if (remembered && offered.some((voice) => voice.id === remembered)) return remembered;
  const local = offered.find((voice) => !isPaidVoice(voice.id));
  return (local ?? offered[0])?.id ?? null;
}

/** The language a voice was made for, when it names exactly one of the two
 * this app reads; null for a voice that names none (OpenAI) or both. */
export function languageOfVoice(voice: Pick<Voice, "languages"> | undefined): Language | null {
  if (!voice) return null;
  const named = LANGUAGES.filter((language) => vouchedFor(voice, language));
  return named.length === 1 ? named[0] : null;
}

/** Where to open the language tab the first time: what was stored, else
 * the language of the voice in use, else the interface's. */
export function initialReadingLanguage(
  stored: string | null | undefined,
  voice: Pick<Voice, "languages"> | undefined,
  interfaceLanguage: string,
): Language {
  if (isLanguage(stored)) return stored;
  return languageOfVoice(voice) ?? (interfaceLanguage === "en" ? "en" : "vi");
}

/** What can read a language on this Mac: the model made for it, and any
 * paid voice that fits. `keyed` says a provider's key is in but its voices
 * have not been listed (yet, or at all) - the hub names that state rather
 * than calling it "nothing". */
export type Readable = {
  local: boolean;
  api: number;
  keyed: boolean;
};

export function readable(
  language: Language,
  status: ModelStatus | null,
  voices: readonly Voice[],
  keysSet: Record<string, boolean>,
): Readable {
  const local = language === "vi"
    ? Boolean(status?.ready)
    : Boolean(status?.english?.ready);
  const api = voicesFor(voices, language).filter((voice) => isPaidVoice(voice.id)).length;
  return { local, api, keyed: Object.values(keysSet).some(Boolean) };
}

export function canRead(readable: Readable): boolean {
  return readable.local || readable.api > 0;
}

/** Whether the first-run screen is due: nothing on this Mac can read - no
 * model of either language, no provider key. Decided before any voice is
 * listed, so a key counts on its own: its voices arrive by event, and an
 * API-only reader must not see the setup screen flash on every launch. */
export function firstRunNeeded(
  status: ModelStatus | null,
  keysSet: Record<string, boolean>,
): boolean {
  if (status?.ready || status?.english?.ready) return false;
  return !Object.values(keysSet).some(Boolean);
}

/** Whether this Mac can read ANYTHING, voices counted. */
export function anythingReadable(
  status: ModelStatus | null,
  voices: readonly Voice[],
  keysSet: Record<string, boolean>,
): boolean {
  return LANGUAGES.some((language) => canRead(readable(language, status, voices, keysSet)));
}

/** The nudge the settings panel and the footer chip carry.
 *
 * Shown when the text in front of the reader is in a language the voice in
 * use was not made for - a Vietnamese voice on an English chapter, or the
 * other way round; a paid voice that names no language is never nudged, it
 * reads both after a fashion. `switch` when some offered voice fits the
 * text's language, `get` when none does and the download or a key is the
 * way. Never acted on by itself: the owner's decision (15/09) is a hint,
 * and the voice stays the reader's.
 */
export type LanguageHint = {
  content: Language;
  kind: "switch" | "get";
};

export function languageHint(
  content: string | null | undefined,
  voice: Pick<Voice, "languages"> | undefined,
  offeredForContent: readonly Voice[],
): LanguageHint | null {
  if (!isLanguage(content)) return null;
  if (voice && canSpeak(voice, content)) return null;
  return { content, kind: offeredForContent.length ? "switch" : "get" };
}
