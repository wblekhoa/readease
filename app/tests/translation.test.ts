import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as translation from '../src/ui/translation.ts';
import { translationSettings, translationVoice, translationError } from '../src/ui/translation.ts';

test('translation is opt-in and malformed settings cannot enable it', () => {
  assert.equal(translationSettings(null).enabled, false);
  assert.equal(translationSettings({ enabled: true, provider: 'remote' }).enabled, false);
  assert.equal(translationSettings({ enabled: 'yes', provider: 'remote' }).enabled, false);
  assert.equal(translationSettings({ enabled: true, provider: 'ollama', target: 'vi', model: 'qwen3:4b' }).target, 'vi');
});
test('translation selects only an installed local voice for the target language', () => {
  const voices = [{ id: 'vi-local', label: 'VI', languages: ['vi'] }, { id: 'kokoro:af_heart', label: 'EN', languages: ['en'] }, { id: 'openai:alloy', label: 'API', languages: [] }];
  assert.equal(translationVoice(translationSettings(null), voices), 'kokoro:af_heart');
  assert.equal(translationVoice({ ...translationSettings(null), target: 'vi' }, voices), 'vi-local');
  assert.equal(translationVoice(translationSettings(null), [voices[0], voices[2]]), null);
});
test('provider errors never expose raw model output as an error', () => {
  assert.equal(translationError(new Error('translation:local_unavailable')), 'translation.local_unavailable');
  assert.equal(translationError('translation:packages_missing'), 'translation.packages_missing');
  assert.equal(translationError('private text echoed from provider'), 'translation.failed');
});

// RE-PLAY-025: the selection footer must describe the voice the next capture uses.
test('selection settings use the target voice without replacing the saved original voice', () => {
  const voices = [{ id: 'vi-local', label: 'VI', languages: ['vi'] }, { id: 'kokoro:af_heart', label: 'EN', languages: ['en-US'] }];
  const settings = { ...translationSettings(null), enabled: true };
  assert.equal(typeof translation.selectionVoice, 'function');
  const { selectionVoice } = translation;
  assert.equal(selectionVoice(settings, voices, 'vi-local'), 'kokoro:af_heart');
  assert.equal(selectionVoice({ ...settings, enabled: false }, voices, 'vi-local'), 'vi-local');
  assert.equal(selectionVoice({ ...settings, target: 'vi' }, voices, 'kokoro:af_heart'), 'vi-local');
  assert.equal(selectionVoice(settings, [voices[0]], 'vi-local'), null);
});

// RE-PLAY-029
test('a setting saved before sources existed stays Scan-only', async () => {
  const { translationSettings, translates } = await import('../src/ui/translation.ts');
  const legacy = translationSettings({ enabled: true, provider: 'apple', target: 'en' });
  assert.deepEqual(legacy.sources, { scan: true, paste: false, library: false });
  assert.equal(translates(legacy, 'scan'), true);
  assert.equal(translates(legacy, 'paste'), false);
});

test('each source has its own switch under the master one', async () => {
  const { translationSettings, translates, selectionVoice } = await import('../src/ui/translation.ts');
  const pasteOnly = translationSettings({ enabled: true, provider: 'apple', target: 'en', sources: { scan: false, paste: true } });
  assert.equal(translates(pasteOnly, 'paste'), true);
  assert.equal(translates(pasteOnly, 'scan'), false);
  assert.equal(selectionVoice(pasteOnly, [], 'vi-local'), 'vi-local');
  assert.equal(translates({ ...pasteOnly, enabled: false }, 'paste'), false);
  assert.deepEqual(translationSettings({ enabled: true, provider: 'apple', sources: { scan: 'yes' } }).sources, { scan: false, paste: false, library: false });
});

// RE-PLAY-030
test('the hub calls the chosen translator ready only when it can translate now', async () => {
  const { translationSettings, translatorReady } = await import('../src/ui/translation.ts');
  const apple = translationSettings({ enabled: true, provider: 'apple', sources: { scan: true, paste: false } });
  assert.equal(translatorReady(apple, { state: 'ready', models: [] }), true);
  assert.equal(translatorReady(apple, { state: 'missing', reason: 'hub.translate_apple_packs' }), false);
  assert.equal(translatorReady(apple, { state: 'checking' }), false);
  const ollama = translationSettings({ enabled: true, provider: 'ollama', model: 'qwen3:4b' });
  assert.equal(translatorReady(ollama, { state: 'ready', models: ['qwen3:4b'] }), true);
  assert.equal(translatorReady(ollama, { state: 'ready', models: ['gemma3:4b'] }), false);
});

// RE-PLAY-031
test('Automatic means ReadEase once downloaded, Apple until then; an old Apple default becomes Automatic', async () => {
  const { translationSettings, resolvedProvider } = await import('../src/ui/translation.ts');
  assert.equal(translationSettings(null).provider, 'auto');
  assert.equal(translationSettings({ enabled: true, provider: 'apple' }).provider, 'auto');
  assert.equal(translationSettings({ enabled: true, provider: 'apple', sources: { scan: true, paste: false } }).provider, 'apple');
  assert.equal(translationSettings({ enabled: true, provider: 'readease', sources: { scan: true, paste: true } }).enabled, true);
  const auto = translationSettings(null);
  assert.equal(resolvedProvider(auto, false), 'apple');
  assert.equal(resolvedProvider(auto, true), 'readease');
  assert.equal(resolvedProvider({ ...auto, provider: 'ollama' }, true), 'ollama');
});

// RE-PLAY-032
test('the Library reads through translation only on its own switch; old settings keep it off', async () => {
  const { translationSettings, translates } = await import('../src/ui/translation.ts');
  assert.equal(translates(translationSettings({ enabled: true, provider: 'apple', sources: { scan: true, paste: true } }), 'library'), false);
  assert.equal(translates(translationSettings({ enabled: true, provider: 'apple', sources: { library: true } }), 'library'), true);
});

// RE-PLAY-033
test('a paste export saves what was heard', async () => {
  const { pasteExport } = await import('../src/ui/translation.ts');
  assert.deepEqual(pasteExport('Xin chào.', 'vi-voice', { text: 'Hello.' }, 'af_heart'), { text: 'Hello.', voiceId: 'af_heart' });
  assert.deepEqual(pasteExport('Xin chào.', 'vi-voice', null, 'af_heart'), { text: 'Xin chào.', voiceId: 'vi-voice' });
  assert.deepEqual(pasteExport('Xin chào.', 'vi-voice', { text: 'Hello.' }, null), { text: 'Xin chào.', voiceId: 'vi-voice' });
});
