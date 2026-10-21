import { isPaidVoice } from './readingCost.ts';
import type { Voice } from './voiceShortlist.ts';

export type TranslationSettings = {
  enabled: boolean;
  /** RE-PLAY-031: 'auto' = ReadEase's own translator once downloaded, else Apple. */
  provider: 'auto' | 'readease' | 'apple' | 'ollama' | 'lmstudio';
  source: 'auto' | 'vi' | 'en';
  target: 'vi' | 'en';
  model: string;
  voice: string;
  /** RE-PLAY-029: where translation applies. A setting saved before sources
   * existed was Scan-only, and reads back that way. */
  sources: { scan: boolean; paste: boolean; library: boolean };
};
export type TranslationSource = keyof TranslationSettings['sources'];
export type TranslationResult = { text: string; voice_id: string; target: string | null };
const PROVIDERS = ['auto', 'readease', 'apple', 'ollama', 'lmstudio'];
export function translationSettings(value: unknown): TranslationSettings {
  const v = (value && typeof value === 'object' ? value : {}) as Record<string, unknown>;
  return {
    enabled: v.enabled === true && PROVIDERS.includes(String(v.provider ?? 'auto')),
    // RE-PLAY-031: Apple was the only on-device choice before ReadEase had
    // its own translator, so an 'apple' saved then (no `sources` yet) was a
    // default, not a choice - it becomes Automatic, which still uses Apple
    // until the ReadEase translator is downloaded. Nothing saved: Automatic.
    provider: v.provider === 'apple' && v.sources === undefined ? 'auto'
      : PROVIDERS.includes(String(v.provider)) ? v.provider as TranslationSettings['provider'] : 'auto',
    source: v.source === 'vi' || v.source === 'en' ? v.source : 'auto',
    target: v.target === 'vi' ? 'vi' : 'en',
    model: typeof v.model === 'string' ? v.model.slice(0, 200) : '',
    voice: typeof v.voice === 'string' ? v.voice : '',
    sources: translationSources(v.sources),
  };
}
function translationSources(value: unknown): TranslationSettings['sources'] {
  const v = (value && typeof value === 'object' ? value : null) as Record<string, unknown> | null;
  if (!v) return { scan: true, paste: false, library: false };
  // RE-PLAY-032: a setting saved before the Library could translate reads
  // back with it off.
  return { scan: v.scan === true, paste: v.paste === true, library: v.library === true };
}
/** RE-PLAY-029: does this source read through translation? */
export function translates(settings: TranslationSettings, source: TranslationSource): boolean {
  return settings.enabled && settings.sources[source];
}
export function translationVoices(settings: TranslationSettings, voices: readonly Voice[]): Voice[] {
  return voices.filter(v => !isPaidVoice(v.id) && v.languages?.some(tag => tag.split('-')[0] === settings.target));
}
export function translationVoice(settings: TranslationSettings, voices: readonly Voice[]): string | null {
  const local = translationVoices(settings, voices);
  return (local.find(v => v.id === settings.voice) ?? local[0])?.id ?? null;
}
/** RE-PLAY-025: describe the next capture, without changing the book voice. */
export function selectionVoice(settings: TranslationSettings, voices: readonly Voice[], originalVoice: string): string | null {
  return translates(settings, 'scan') ? translationVoice(settings, voices) : originalVoice;
}
const ERRORS = ['translator_missing', 'packages_missing', 'apple_requires_26', 'model_missing', 'voice_missing', 'local_unavailable', 'language_unknown', 'language', 'invalid_output', 'text_limit', 'timeout', 'export_busy'] as const;
export function translationError(error: unknown) {
  const code = (error instanceof Error ? error.message : String(error)).replace(/^translation:/, '');
  return ERRORS.includes(code as typeof ERRORS[number]) ? `translation.${code}` as `translation.${typeof ERRORS[number]}` : 'translation.failed' as const;
}

/** RE-PLAY-030: one translator's answer in the hub - still asking, ready
 * (with the local models it has), or the reason it cannot translate. */
export type TranslatorFound =
  | { state: 'checking' }
  | { state: 'ready'; models: string[] }
  | { state: 'missing'; reason: 'translation.translator_missing' | 'translation.apple_requires_26' | 'translation.failed' | 'hub.translate_apple_packs' | 'hub.translate_local_empty' | 'hub.translate_local_off' };
/** Whether the translator chosen in settings can translate right now: Apple
 * with both packs, or a local server that has the chosen model. */
export function translatorReady(settings: TranslationSettings, found: TranslatorFound): boolean {
  if (found.state !== 'ready') return false;
  return settings.provider === 'apple' || settings.provider === 'readease' || found.models.includes(settings.model);
}
/** RE-PLAY-031: which translator 'auto' means right now - the host resolves
 * it the same way just before translating. */
export function resolvedProvider(settings: TranslationSettings, translatorDownloaded: boolean): Exclude<TranslationSettings['provider'], 'auto'> {
  return settings.provider !== 'auto' ? settings.provider : translatorDownloaded ? 'readease' : 'apple';
}
