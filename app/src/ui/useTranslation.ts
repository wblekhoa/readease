import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { translationSettings, type TranslationSettings } from './translation';

export function useTranslation() {
  const [settings, setSettings] = useState(() => translationSettings(null));
  const [ready, setReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);
  useEffect(() => {
    let alive = true;
    invoke<{ result: { value: unknown } }>('engine_request', { method: 'config.get', params: { key: 'selection_translation' } })
      .then(reply => { if (alive) { setSettings(translationSettings(reply.result.value)); setReady(true); } })
      .catch(() => { if (alive) setError(true); });
    return () => { alive = false; };
  }, []);
  const save = async (value: TranslationSettings) => {
    setSaving(true); setError(false);
    try {
      await invoke('engine_request', { method: 'config.set', params: { key: 'selection_translation', value } });
      setSettings(value);
    } catch { setError(true); }
    finally { setSaving(false); }
  };
  const retry = async () => {
    setSaving(true);
    try {
      const reply = await invoke<{ result: { value: unknown } }>('engine_request', { method: 'config.get', params: { key: 'selection_translation' } });
      setSettings(translationSettings(reply.result.value)); setReady(true); setError(false);
    } catch { setError(true); }
    finally { setSaving(false); }
  };
  return { settings, ready, saving, error, save, retry };
}
export type TranslationPreference = ReturnType<typeof useTranslation>;
