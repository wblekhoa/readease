/** What this Mac can translate with, beside what it can read with (RE-PLAY-030).
 *
 * The hub sums up the voices; the owner asked whether it also sums up the
 * translators (20/10). ReadEase downloads none of them - Apple's packs are
 * part of macOS, Ollama and LM Studio models are the reader's own - so this
 * group only ASKS each one and says what it found, with the way to fix it.
 * Nothing here changes a setting: the one button opens Translation settings.
 */
import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { text } from "../i18n";
import { Button, Notice } from "./controls";
import { ChevronDownIcon } from "./icons";
import { GroupedRow, GroupedSection } from "./patterns";
import { translatorReady, type TranslationSettings, type TranslatorFound as Found } from "./translation";

type Provider = TranslationSettings["provider"];
const PROVIDERS: readonly { id: Provider; name: string; port?: number }[] = [
  { id: "apple", name: "Apple Translation" },
  { id: "ollama", name: "Ollama", port: 11434 },
  { id: "lmstudio", name: "LM Studio", port: 1234 },
];

function askApple(): Promise<Found> {
  // Both directions: a reader who only has English → Vietnamese installed
  // can scan English pages but not hear a Vietnamese paste in English.
  const pair = (source: string, target: string) =>
    invoke<{ available: boolean; installed: boolean }>("translation_status", { source, target });
  return Promise.all([pair("en", "vi"), pair("vi", "en")]).then(([toVi, toEn]): Found =>
    !toVi.available || !toEn.available ? { state: "missing", reason: "translation.apple_requires_26" }
      : toVi.installed && toEn.installed ? { state: "ready", models: [] }
        : { state: "missing", reason: "hub.translate_apple_packs" });
}

function askLocal(provider: Provider): Promise<Found> {
  return invoke<{ models: string[] }>("translation_models", { provider }).then(({ models }): Found =>
    models.length ? { state: "ready", models } : { state: "missing", reason: "hub.translate_local_empty" });
}

export function TranslationSources({ settings, summary, onOpenSettings, disabled }: {
  settings: TranslationSettings;
  summary: string;
  onOpenSettings: () => void;
  disabled: boolean;
}) {
  const [found, setFound] = useState<Record<Provider, Found>>({
    apple: { state: "checking" }, ollama: { state: "checking" }, lmstudio: { state: "checking" },
  });
  useEffect(() => {
    let alive = true;
    for (const { id } of PROVIDERS) {
      (id === "apple" ? askApple() : askLocal(id))
        .catch((): Found => ({ state: "missing", reason: id === "apple" ? "translation.failed" : "hub.translate_local_off" }))
        .then(result => { if (alive) setFound(current => ({ ...current, [id]: result })); });
    }
    return () => { alive = false; };
  }, []);
  const chosen = PROVIDERS.find(provider => provider.id === settings.provider) ?? PROVIDERS[0];
  const ready = translatorReady(settings, found[chosen.id]);
  const checking = found[chosen.id].state === "checking";
  return (
    <GroupedSection title={text("hub.section_translation")}>
      <GroupedRow
        title={
          <span className="inline-flex items-center gap-2">
            <span aria-hidden="true" className={`h-2 w-2 shrink-0 rounded-full ${ready ? "bg-ok" : "bg-edge-strong"}`} />
            {text(checking ? "translation.checking" : ready ? "hub.translate_ready" : "hub.translate_unready")}
          </span>
        }
        subtitle={text("hub.translate_using", { provider: chosen.name })}
        trailing={<Button size="sm" disabled={disabled} aria-label={`${text("translation.open_settings")}: ${summary}`} onClick={onOpenSettings}>
          {summary}<ChevronDownIcon />
        </Button>}
      />
      {PROVIDERS.map(provider => {
        const state = found[provider.id];
        return (
          <GroupedRow
            key={provider.id}
            title={provider.name}
            subtitle={state.state === "checking" ? text("translation.checking")
              : state.state === "ready" ? (provider.id === "apple" ? text("hub.translate_apple_ready") : text("hub.translate_local_models", { count: state.models.length }))
                : text(state.reason, { port: String(provider.port ?? "") })}
            trailing={provider.id === settings.provider
              ? <span className="text-xs text-ink-mute">{text("model.in_use")}</span>
              : undefined}
          />
        );
      })}
      <Notice fine className="mt-2 block">{text("hub.translate_note")}</Notice>
    </GroupedSection>
  );
}
