/** What this Mac can translate with, beside what it can read with (RE-PLAY-030).
 *
 * The hub sums up the voices; the owner asked whether it also sums up the
 * translators (20/10). ReadEase's own translator (RE-PLAY-031) is downloaded
 * and removed here like a voice model; Apple's packs are part of macOS and
 * Ollama/LM Studio models are the reader's own, so for those this group only
 * ASKS and says what it found, with the way to fix it.
 */
import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { text } from "../i18n";
import { Button, Notice } from "./controls";
import { ChevronDownIcon } from "./icons";
import type { Models } from "./useModels";
import { GroupedRow, GroupedSection } from "./patterns";
import { resolvedProvider, translatorReady, type TranslationSettings, type TranslatorFound as Found } from "./translation";

type Provider = "apple" | "ollama" | "lmstudio";
const NAMES: Record<Exclude<TranslationSettings["provider"], "auto">, string> = {
  readease: "ReadEase", apple: "Apple Translation", ollama: "Ollama", lmstudio: "LM Studio",
};
const PROVIDERS: readonly { id: Provider; name: string }[] = [
  { id: "apple", name: "Apple Translation" },
  { id: "ollama", name: "Ollama" },
  { id: "lmstudio", name: "LM Studio" },
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

export function TranslationSources({ settings, summary, onOpenSettings, disabled, models, reading }: {
  settings: TranslationSettings;
  summary: string;
  onOpenSettings: () => void;
  disabled: boolean;
  models: Models;
  reading: boolean;
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
  const own = models.status?.translator;
  const chosen = resolvedProvider(settings, own?.ready === true);
  const chosenFound: Found = chosen === "readease"
    ? (own?.ready ? { state: "ready", models: [] } : { state: "missing", reason: "translation.translator_missing" })
    : found[chosen];
  const ready = translatorReady({ ...settings, provider: chosen }, chosenFound);
  const checking = chosenFound.state === "checking";
  const busy = models.job !== null || reading;
  return (
    <>
    <GroupedSection title={text("hub.section_translation")}>
      <GroupedRow
        title={
          <span className="inline-flex items-center gap-2">
            <span aria-hidden="true" className={`h-2 w-2 shrink-0 rounded-full ${ready ? "bg-ok" : "bg-edge-strong"}`} />
            {text(checking ? "translation.checking" : ready ? "hub.translate_ready" : "hub.translate_unready")}
          </span>
        }
        subtitle={text(settings.provider === "auto" ? "hub.translate_using_auto" : "hub.translate_using", { provider: NAMES[chosen] })}
        trailing={<Button size="sm" disabled={disabled} aria-label={`${text("translation.open_settings")}: ${summary}`} onClick={onOpenSettings}>
          {summary}<ChevronDownIcon />
        </Button>}
      />
      {own && (
        <GroupedRow
          title={text("hub.translator_build")}
          subtitle={own.ready
            ? text("hub.translator_ready")
            : text("hub.translator_hint")}
          trailing={<>
            {chosen === "readease" && own.ready && <span className="text-xs text-ink-mute">{text("model.in_use")}</span>}
            {!own.ready && <Button variant="primary" size="sm" disabled={busy} onClick={() => void models.downloadTranslator()}>{text("model.download")}</Button>}
            {(own.ready || own.installed > 0) && <Button size="sm" disabled={busy} aria-label={`${text("model.english_remove")} ${text("hub.translator_build")}`} onClick={() => void models.removeTranslator()}>{text("model.english_remove")}</Button>}
          </>}
        />
      )}
      {PROVIDERS.map(provider => {
        const state = found[provider.id];
        // A local server is an expert's tool: listed when it is the chosen
        // translator or is actually open, never as a row of "not open"s.
        if (provider.id !== "apple" && provider.id !== chosen && !(state.state === "ready" || (state.state === "missing" && state.reason === "hub.translate_local_empty"))) return null;
        return (
          <GroupedRow
            key={provider.id}
            title={provider.name}
            subtitle={state.state === "checking" ? text("translation.checking")
              : state.state === "ready" ? (provider.id === "apple" ? text("hub.translate_apple_ready") : text("hub.translate_local_models", { count: state.models.length }))
                : text(state.reason)}
            trailing={provider.id === chosen
              ? <span className="text-xs text-ink-mute">{text("model.in_use")}</span>
              : undefined}
          />
        );
      })}
    </GroupedSection>
    {/* An aside about the whole group, not one more row: a small callout
        below the list, so it neither sits on a row divider nor reads as a
        translator (owner, 20/10). */}
    <Notice tone="info" compact className="mt-3 block">{text("hub.translate_note")}</Notice>
    </>
  );
}
