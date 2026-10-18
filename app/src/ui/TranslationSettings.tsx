import { useEffect, useId, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { text, type TextKey } from '../i18n';
import { Button, Notice, SegmentedControl, Select, Switch } from './controls';
import { GroupedRow, GroupedSection } from './patterns';
import { ChevronDownIcon } from './icons';
import { translationError, translationVoice, translationVoices, type TranslationSettings as Settings } from './translation';
import type { TranslationPreference } from './useTranslation';
import type { Voice } from './voiceShortlist';
import { VoicePicker } from './VoicePicker';

export function TranslationSettings({ preference, voices, locked, rate, rates, onRate, onOpenHub, downloading, mode, favorites, previewing, onPreview, onStopPreview, onFavorite }: {
  preference: TranslationPreference;
  favorites: readonly string[];
  previewing: string | null;
  onPreview: (id: string) => void;
  onStopPreview: () => void;
  onFavorite: (id: string) => void;
  mode: "voice" | "translation";
  voices: Voice[];
  locked: boolean;
  rate: number;
  rates: readonly number[];
  onRate: (rate: number) => void;
  onOpenHub: () => void;
  downloading: boolean;
}) {
  const { settings, ready, saving, error, save } = preference;
  const [models, setModels] = useState<string[]>([]);
  const [checking, setChecking] = useState(false);
  const [status, setStatus] = useState<TextKey | null>(null);
  const [revision, setRevision] = useState(0);
  const [optionsOpen, setOptionsOpen] = useState(false);
  const optionsId = useId();
  const disabled = (locked && previewing === null) || saving || !ready;
  const change = (patch: Partial<Settings>) => void save({ ...settings, ...patch });
  useEffect(() => {
    if (!settings.enabled || mode !== "translation") return;
    let alive = true;
    setChecking(true); setStatus(null); setModels([]);
    const check = settings.provider === 'apple'
      ? invoke<{ available: boolean; installed: boolean }>('translation_status', { source: settings.source === 'auto' ? (settings.target === 'en' ? 'vi' : 'en') : settings.source, target: settings.target })
          .then(result => { if (alive) setStatus(result.available ? (result.installed ? null : 'translation.packages_missing') : 'translation.apple_requires_26'); })
      : invoke<{ models: string[] }>('translation_models', { provider: settings.provider })
          .then(result => { if (alive) { setModels(result.models); if (!result.models.length) setStatus('translation.model_missing'); } });
    check.catch(error => { if (alive) setStatus(translationError(error)); })
      .finally(() => { if (alive) setChecking(false); });
    return () => { alive = false; };
  }, [settings.enabled, settings.provider, settings.source, settings.target, revision, mode]);
  const local = translationVoices(settings, voices);
  const providerName = settings.provider === 'apple' ? 'Apple Translation' : settings.provider === 'ollama' ? 'Ollama' : 'LM Studio';
  const needsModel = !checking && settings.provider !== 'apple' && !models.includes(settings.model);

  // RE-PLAY-025: one task, one voice. Provider setup is secondary to the target and voice.
  return <>
    {mode === "translation" && <GroupedSection>
      <GroupedRow title={text('translation.title')} subtitle={text('translation.mode_hint')}
        trailing={() => <Switch checked={settings.enabled} onChange={enabled => change({ enabled })} disabled={disabled} label={text('translation.enable')} />} />
    </GroupedSection>}
    {settings.enabled && <div className="flex min-w-0 flex-col gap-4 pt-3">
      {mode === "translation" && <div>
        <p className="m-0 mb-2 text-xs font-semibold text-ink-mute">{text('translation.to')}</p>
        <SegmentedControl label={text('translation.to')} value={settings.target}
          options={[{ value: 'en', label: text('language.en'), disabled }, { value: 'vi', label: text('language.vi'), disabled }]}
          onChange={target => change({ target, voice: translationVoice({ ...settings, target, voice: '' }, voices) ?? '' })} />
      </div>}
      <div className="flex min-w-0 flex-col gap-2">
        <p id={`${optionsId}-voice`} className="m-0 text-xs font-semibold text-ink-mute">{text('translation.voice')}</p>
        <VoicePicker labelledBy={`${optionsId}-voice`} className="w-full" voices={local}
          favorites={favorites} value={translationVoice(settings, voices) ?? ''}
          disabled={disabled || !local.length} locked={locked && previewing === null} previewing={previewing}
          onChoose={voice => change({ voice })} onPreview={onPreview}
          onStopPreview={onStopPreview} onFavorite={onFavorite} />
        <p className="m-0 text-xs leading-relaxed text-ink-mute">{text('translation.voice_hint', { language: text(settings.target === 'en' ? 'language.en' : 'language.vi') })}</p>
        {!local.length && <Notice tone="info" action={<Button size="sm" disabled={downloading} onClick={onOpenHub}>{text('hub.title')}…</Button>}>{text('translation.voice_missing')}</Notice>}
      </div>
      {mode === "voice" && <GroupedSection>
        <GroupedRow title={text('player.speed')} trailing={titleId => <Select labelledBy={titleId} value={rate} disabled={locked} onChange={e => onRate(Number(e.target.value))}>
          {rates.map(value => <option key={value} value={value}>{value}×</option>)}
        </Select>} />
      </GroupedSection>}
      {mode === "translation" && <>
      {(status || needsModel) && <Notice tone="info" action={!optionsOpen ? <Button size="sm" onClick={() => setOptionsOpen(true)}>{text('translation.options')}</Button> : undefined}>
        {text(status ?? (settings.model ? 'translation.model_missing' : 'translation.choose_model'))}
      </Notice>}
      <div>
        {/* RE-PLAY-025: a two-line disclosure sizes to content, not the 30px action button. */}
        <button type="button"
          className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left hover-wash"
          aria-expanded={optionsOpen} aria-controls={optionsId} onClick={() => setOptionsOpen(value => !value)}>
          <span className="flex min-w-0 flex-1 flex-col gap-1">
            <span className="text-sm font-medium leading-5 text-ink">{text('translation.options')}</span>
            <span className="text-xs leading-4 text-ink-mute">{providerName}</span>
          </span>
          <ChevronDownIcon className={`h-4 w-4 shrink-0 text-ink-mute ${optionsOpen ? 'rotate-180' : ''}`} />
        </button>
        <div id={optionsId} hidden={!optionsOpen} className="px-3 pt-4">
          <div className="flex min-w-0 flex-col gap-4">
            <label className="flex min-w-0 flex-col gap-2 text-sm">{text('translation.from')}
              <Select className="w-full" label={text('translation.from')} value={settings.source} disabled={disabled} onChange={e => change({ source: e.target.value as Settings['source'] })}>
                <option value="auto">{text('translation.auto')}</option><option value="vi">{text('language.vi')}</option><option value="en">{text('language.en')}</option>
              </Select>
            </label>
            <label className="flex min-w-0 flex-col gap-2 text-sm">{text('translation.provider')}
              <Select className="w-full" label={text('translation.provider')} value={settings.provider} disabled={disabled} onChange={e => change({ provider: e.target.value as Settings['provider'], model: '' })}>
                <option value="apple">Apple Translation</option><option value="ollama">Ollama</option><option value="lmstudio">LM Studio</option>
              </Select>
            </label>
            {settings.provider !== 'apple' && <>
              <label className="flex min-w-0 flex-col gap-2 text-sm">{text('translation.model')}
                <Select className="w-full" label={text('translation.model')} value={settings.model} disabled={disabled || checking} onChange={e => change({ model: e.target.value })}>
                  <option value="">{text('translation.choose_model')}</option>
                  {settings.model && !models.includes(settings.model) && <option value={settings.model}>{settings.model}</option>}
                  {models.map(model => <option key={model} value={model}>{model}</option>)}
                </Select>
              </label>
              <p className="m-0 text-xs leading-relaxed text-ink-mute">{text(settings.provider === 'ollama' ? 'translation.ollama_hint' : 'translation.lmstudio_hint')}</p>
            </>}
            <p className="m-0 text-xs leading-relaxed text-ink-mute">{text('translation.private')}</p>
            <p className="m-0 text-xs leading-relaxed text-ink-mute">{text('translation.next_selection')}</p>
            <div className="flex justify-end"><Button size="sm" disabled={checking || saving} onClick={() => setRevision(v => v + 1)}>{text(checking ? 'translation.checking' : 'translation.refresh')}</Button></div>
          </div>
        </div>
      </div>
      </>}
    </div>}
    {error && <div className="mt-4 flex flex-col items-start gap-2">
      <Notice tone="error">{text('translation.save_failed')}</Notice>
      <Button size="sm" disabled={saving} onClick={() => void preference.retry()}>{text('translation.refresh')}</Button>
    </div>}
  </>;
}
