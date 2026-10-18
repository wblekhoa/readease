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
