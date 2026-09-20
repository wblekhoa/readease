/** What this Mac reads, by language, and how to add to it.
 *
 * The owner asked for one place that sums it up - which languages the app
 * can read, with which models, which keys are in - and where the download
 * or the key happens (15/09: "một nơi thống kê để user quản lý và tải model
 * hoặc nhập API"). Two frames share the body: the sheet opened from the
 * gear on the home screen, and the first-run screen, which is this body
 * before anything can read.
 *
 * Rows, not cards (HIG §1): each language is a titled group whose first row
 * is the statistic - can it be read, by what - and whose next rows are the
 * model's; the providers are a third group. Nothing here is required:
 * every row is an offer.
 */
import { text } from "../i18n";
import { Button, IconButton, Notice, Surface } from "./controls";
import { CloseIcon } from "./icons";
import { GroupedRow, GroupedSection, Scrim, useDismiss } from "./patterns";
import { ModelProgress, ModelRows } from "./ModelPanel";
import { ProviderKeys } from "./ProviderKeys";
import { isPaidVoice, providerOf } from "./readingCost";
import {
  canRead,
  LANGUAGES,
  readable,
  voicesFor,
  type Language,
  type ModelStatus,
} from "./readingSources";
import type { Models } from "./useModels";
import type { Voice } from "./voiceShortlist";

export type SourcesProps = {
  models: Models;
  voices: readonly Voice[];
  /** Provider id → whether a key is stored. Never the key. */
  keysSet: Record<string, boolean>;
  onSaveKey: (provider: string, key: string) => Promise<{ ok: boolean; code: string | null }>;
  /** Something is being read: nothing is fetched or removed under it. */
  reading: boolean;
};

/** What reads a language, in one line: the model on this Mac and how many
 * voices it brings, the paid voices that fit, or the two ways to get one. */
export function sourcesLine(
  language: Language,
  status: ModelStatus | null,
  voices: readonly Voice[],
  keysSet: Record<string, boolean>,
): string {
  const found = readable(language, status, voices, keysSet);
  const parts: string[] = [];
  if (found.local) {
    const count = voicesFor(voices, language).filter((voice) => !isPaidVoice(voice.id)).length;
    parts.push(text(language === "vi" ? "hub.local_vi" : "hub.local_en", { count }));
  }
  if (found.api > 0) parts.push(text("hub.api_voices", { count: found.api }));
  return parts.length ? parts.join(" · ") : text("hub.how_to_read");
}

export function ReadingSources({ models, voices, keysSet, onSaveKey, reading }: SourcesProps) {
  const { status } = models;
  const voicesOf = Object.fromEntries(
    voices.filter((voice) => isPaidVoice(voice.id)).reduce((counts, voice) => {
      const provider = providerOf(voice.id);
      if (provider) counts.set(provider, (counts.get(provider) ?? 0) + 1);
      return counts;
    }, new Map<string, number>()),
  );
  return (
    <>
      {LANGUAGES.map((language) => {
        const found = readable(language, status, voices, keysSet);
        return (
          <GroupedSection
            key={language}
            title={text(language === "vi" ? "voices.language_vi" : "voices.language_en")}
          >
            {/* The statistic first: the question the owner asked this place
                to answer, before any row that changes the answer. */}
            <GroupedRow
              title={
                <span className="inline-flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className={`h-2 w-2 shrink-0 rounded-full ${canRead(found) ? "bg-ok" : "bg-edge-strong"}`}
                  />
                  {text(canRead(found) ? "hub.readable" : "hub.unreadable")}
                </span>
              }
              subtitle={sourcesLine(language, status, voices, keysSet)}
            />
            <ModelRows language={language} models={models} reading={reading} />
            {/* The Vietnamese model's builds load at construction: using the
                other one restarts the engine, and the rows say so once. */}
            {language === "vi" && (
              <Notice fine className="mt-2 block">{text("model.switch_restart")}</Notice>
            )}
          </GroupedSection>
        );
      })}
      <ProviderKeys
        title={text("hub.section_api")}
        keysSet={keysSet}
        voicesOf={voicesOf}
        onSaveKey={onSaveKey}
      />
      <Notice fine className="mt-2 block">{text("hub.api_note")} {text("key.local_only")}</Notice>
      <ModelProgress models={models} className="mt-4" />
    </>
  );
}

/** The sheet the gear on the home screen opens. */
export function SourcesHub({ onClose, ...sources }: SourcesProps & { onClose: () => void }) {
  const downloading = sources.models.job !== null;
  // Esc and a click outside close it - not over a running download, which
  // would go on behind a closed sheet with nothing on screen to say so.
  const sheet = useDismiss(onClose, !downloading);
  return (
    <>
    <Scrim />
    <Surface
      edge="strong"
      radius="sheet"
      ref={sheet}
      /* The Apple Books sheet's frame: a layer that stands on its own in the
         middle of the window, capped so a short window scrolls the body. */
      layer="sheet"
      className="fixed left-1/2 top-1/2 z-30 flex max-h-[84%] w-[36rem] max-w-[calc(100vw-3rem)] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden shadow-lifted"
    >
      <div className="flex shrink-0 items-start gap-3 px-6 pb-2 pt-5">
        <div className="min-w-0 flex-1">
          <h3 className="m-0 text-base font-bold">{text("hub.title")}</h3>
          <p className="m-0 mt-1 text-xs text-ink-mute">{text("hub.caption")}</p>
        </div>
        <IconButton
          onClick={onClose}
          disabled={downloading}
          aria-label={text("aria.close")}
          title={text("aria.close")}
        >
          <CloseIcon />
        </IconButton>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-6">
        <ReadingSources {...sources} />
      </div>
      {/* Nothing to confirm: every row acts on its own. The one button is
          the way out, for a person who came from the settings panel. */}
      <div className="flex shrink-0 justify-end border-t border-edge px-6 py-3">
        <Button size="sm" disabled={downloading} onClick={onClose}>{text("aria.close")}</Button>
      </div>
    </Surface>
    </>
  );
}
