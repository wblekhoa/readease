/** Everything about the voice, in one panel above the footer.
 *
 * The footer itself carries one quiet chip ("Thu Hà · 1,25×"); the choices
 * live here, opened on request (owner, 02/09: "tối giản … setting sẽ có một
 * panel để chỉnh chi tiết"). Its inset is the sheets' 24, not its own 16:
 * every floating PANEL sets content in by the same amount (owner, 03/09).
 * Menus of rows - the contents popover, the voice switcher - keep a small
 * 8px frame instead, because there the ROWS carry the inset.
 *
 * The voice can now be changed while something is being read - the reading
 * restarts at the paragraph it had reached, in the new voice (owner, 03/09).
 * The select offers the voices SWITCHED ON in the voices panel, not the whole
 * catalogue of twenty (owner, 03/09): one list means one list everywhere, and
 * the row right below it is the way to add to it. Speed is still read once at
 * the start, so it stays disabled rather than promising what the engine will
 * not do.
 */
import { useEffect, useState } from "react";
import { text } from "../i18n";
import { Button, IconButton, Notice, Select, Surface } from "./controls";
import { GroupedRow, GroupedSection } from "./patterns";
import { CloseIcon, SpeakerIcon } from "./icons";
import { AppTabs } from "./AppTabs";
import { ProviderKeys } from "./ProviderKeys";
import { isPaidVoice, providerOf } from "./readingCost";
import { ModelChoices } from "./ModelPanel";
import {
  voiceDescription as describe,
  voiceName as name,
  type Voice,
} from "./voiceShortlist";

export type { Voice };

export function SettingsPanel({
  voices,
  voiceId,
  rate,
  rates,
  reading,
  shortlisted,
  voicesError,
  paidVoices,
  keysSet,
  onSaveKey,
  onVoice,
  onRate,
  onManageVoices,
  onClose,
}: {
  voices: Voice[];
  voiceId: string;
  rate: number;
  rates: readonly number[];
  reading: boolean;
  /** How many voices are marked for the mid-reading switcher. */
  shortlisted: number;
  /** Why the list is empty, when it is empty for a reason worth saying. */
  voicesError?: string | null;
  /** Every voice a provider offers, whether or not it is in the shortlist -
   * the shortlist is about the mid-reading switcher, not about which voices
   * a person may choose from here. */
  paidVoices: Voice[];
  /** Provider id → whether a key is stored. Never the key. */
  keysSet: Record<string, boolean>;
  onSaveKey: (provider: string, key: string) => Promise<boolean>;
  onVoice: (voiceId: string) => void;
  onRate: (rate: number) => void;
  onManageVoices: () => void;
  onClose: () => void;
}) {
  const [busy, setBusy] = useState(false);

  // Esc closes any layer that sits above the screen - the keyboard contract
  // in docs/readease-hig.md §4. Not while a build is being fetched: leaving
  // then would hide a running download behind a chip.
  /* Two ways to be read to, and they are different enough to be different
     places: a model on this Mac, or somebody's API on the reader's own key
     (owner, 04/09). The panel opens on whichever the current voice belongs
     to, so it never argues with what is already speaking. */
  const [source, setSource] = useState(isPaidVoice(voiceId) ? "api" : "local");
  const localVoices = voices.filter((voice) => !isPaidVoice(voice.id));

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy, onClose]);

  return (
    /* Capped at the room between the bars, and only the BODY scrolls: with
       the quality section open this panel outgrew a short window and ran up
       under the header (owner, 03/09). Same shape as the notes panel - title
       pinned, list moving, scrollbar owned by the list. */
    <Surface
      edge="strong"
      /* Sheet tier, not card: this floats over the book and stands on its
         own, which is what the guideline's 24 is for (owner, 03/09). */
      radius="sheet"
      className="absolute bottom-[calc(var(--shell-bottom-inner)+var(--layer-gap))] left-1/2 z-20 flex layer-capped w-[26rem] -translate-x-1/2 flex-col overflow-hidden shadow-lifted"
    >
      <div className="flex shrink-0 items-center px-6 pb-1 pt-5">
        <h3 className="m-0 flex-1 text-sm font-bold">{text("player.settings")}</h3>
        <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-5">
      <div className="mt-3">
        <AppTabs
          items={[
            { value: "local", label: text("voices.source_local") },
            { value: "api", label: text("voices.source_api") },
          ]}
          value={source}
          onChange={setSource}
          ariaLabel={text("voices.source")}
        />
      </div>

      {source === "local" ? (
        <>
          <GroupedSection className="mt-3">
            {/* The control carries the voice's NAME only; what the voice is
                like (gender · region · style) is the row's own line - the
                full label in the select ran past the row and clipped its
                title (owner, 02/09). */}
            <GroupedRow
              title={text("player.voice")}
              subtitle={describe(localVoices.find((voice) => voice.id === voiceId)?.label)}
              trailing={
                <Select
                  value={isPaidVoice(voiceId) ? "" : voiceId}
                  className="max-w-[11rem]"
                  onChange={(event) => onVoice(event.target.value)}
                >
                  {/* A paid voice is speaking, so no local one is chosen.
                      The empty slot is NAMED rather than blank: a select
                      showing nothing reads as broken, where "Chọn giọng…"
                      reads as an invitation. */}
                  {isPaidVoice(voiceId) && (
                    <option value="" disabled>{text("voices.pick")}</option>
                  )}
                  {localVoices.map((voice) => (
                    <option key={voice.id} value={voice.id}>{name(voice.label) || voice.id}</option>
                  ))}
                </Select>
              }
            />
            {voicesError && (
              <Notice tone="error" className="py-2">
                {text("voices.unavailable")} ({voicesError})
              </Notice>
            )}
            <GroupedRow
              title={text("voices.title")}
              subtitle={text("voices.marked", { count: shortlisted })}
              trailing={
                <Button size="sm" onClick={onManageVoices}>
                  {/* The same glyph the transport's switcher wears, so the
                      speaker reads as "voices" wherever it turns up. */}
                  <SpeakerIcon />
                  {text("voices.manage")}
                </Button>
              }
            />
          </GroupedSection>
          <h4 className="m-0 mb-1.5 mt-4 text-xs font-semibold uppercase tracking-wide text-ink-mute">
            {text("model.quality")}
          </h4>
          <ModelChoices reading={reading} onBusy={setBusy} />
        </>
      ) : (
        <>
          <ProviderKeys keysSet={keysSet} onSaveKey={onSaveKey} />
          {paidVoices.length > 0 ? (
            <GroupedSection className="mt-3">
              <GroupedRow
                title={text("player.voice")}
                subtitle={providerOf(voiceId) ?? undefined}
                trailing={
                  <Select
                    value={isPaidVoice(voiceId) ? voiceId : ""}
                    className="max-w-[11rem]"
                    onChange={(event) => onVoice(event.target.value)}
                  >
                    {!isPaidVoice(voiceId) && (
                      <option value="" disabled>{text("voices.pick")}</option>
                    )}
                    {paidVoices.map((voice) => (
                      <option key={voice.id} value={voice.id}>{voice.label}</option>
                    ))}
                  </Select>
                }
              />
            </GroupedSection>
          ) : (
            <Notice className="mt-3 block">{text("key.none_yet")}</Notice>
          )}
          {/* Said once, where the key is typed - not on the outside of the
              app, and not repeated on every screen that mentions a voice. */}
          <Notice className="mt-3 block">{text("key.local_only")}</Notice>
        </>
      )}

      {/* Speed belongs to the reading, not to whichever engine performs it,
          so it sits under both tabs rather than being written twice. */}
      <GroupedSection className="mt-4">
        <GroupedRow
          title={text("player.speed")}
          trailing={
            <Select value={rate} disabled={reading} onChange={(event) => onRate(Number(event.target.value))}>
              {rates.map((value) => (
                <option key={value} value={value}>{value}×</option>
              ))}
            </Select>
          }
        />
      </GroupedSection>
      </div>
    </Surface>
  );
}
