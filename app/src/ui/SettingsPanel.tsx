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
import { useState } from "react";
import { text } from "../i18n";
import { Button, IconButton, Notice, Select, Surface } from "./controls";
import { GroupedRow, GroupedSection, useDismiss } from "./patterns";
import { CloseIcon, SpeakerIcon } from "./icons";
import { AppTabs } from "./AppTabs";
import { ProviderKeys } from "./ProviderKeys";
import { ReadingLimits } from "./CostPanel";
import { isPaidVoice, providerOf, PROVIDERS } from "./readingCost";
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
  paidAvailable,
  keysSet,
  scope,
  budget,
  spent,
  onSaveKey,
  onScope,
  onBudget,
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
  /** The account offers paid voices, whether or not any is on the list. */
  paidAvailable: boolean;
  /** Provider id → whether a key is stored. Never the key. */
  keysSet: Record<string, boolean>;
  /* The same two limits the cost panel by the read button carries. They are
     in both places on purpose (owner, 04/09): one is beside the price, the
     other beside the key, and a person adjusting either is already looking
     at the thing it governs. */
  scope: number | null;
  budget: number | null;
  spent: number;
  onSaveKey: (provider: string, key: string) => Promise<{ ok: boolean; code: string | null }>;
  onScope: (chapters: number | null) => void;
  onBudget: (usd: number | null) => void;
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

  // Escape and a click on the book both put it away; neither does while a
  // key is being checked, which is the one moment closing loses work.
  const panel = useDismiss(onClose, !busy);

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
      ref={panel}
      /* Over its OWN button, not over the middle of the window. The button
         is the last thing in the footer's right-hand cluster, so the panel's
         right edge sits at the same 24px inset the row is padded by and the
         two line up without measuring anything (owner, 05/09: it used to
         open across the screen from the button that opened it). */
      className="absolute bottom-[calc(var(--shell-bottom-inner)+var(--layer-gap))] right-6 z-20 flex layer-capped w-[26rem] max-w-[calc(100vw-3rem)] flex-col overflow-hidden shadow-lifted"
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
          {/* Two named groups instead of a flat run of rows: what you read
              WITH, then what it costs to have it here. Unlabelled groups
              separated only by a dotted rule left a reader working out where
              one concern ended (owner, 04/09: "phân cấp tốt hơn"). */}
          <GroupedSection title={text("section.reading_local")}>
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
          <h4 className="m-0 mb-1.5 mt-6 text-xs font-semibold uppercase tracking-wide text-ink-mute">
            {text("model.quality")}
          </h4>
          <ModelChoices reading={reading} onBusy={setBusy} />
        </>
      ) : (
        <>
          {/* Two groups, and the split is the useful one: what you set up
              ONCE, and how it reads every time. Four unlabelled runs of rows
              separated by dotted rules made a reader work out where each
              concern ended (owner, 04/09: "phân cấp tốt hơn"). */}
          <ProviderKeys
            title={text("section.keys")}
            keysSet={keysSet}
            onSaveKey={onSaveKey}
          />
          {/* Said once, directly under the keys it is about - not on the
              outside of the app, and not on every screen that names a
              voice. */}
          <Notice fine className="mt-2 block">{text("key.local_only")}</Notice>

          {paidVoices.length > 0 || paidAvailable ? (
            <GroupedSection title={text("section.reading_api")}>
              <GroupedRow
                title={text("player.voice")}
                /* The provider's NAME, not its id: "openai" in a subtitle is
                   an internal token wearing a label's clothes. */
                subtitle={
                  PROVIDERS.find((item) => item.id === providerOf(voiceId))?.label
                }
                trailing={
                  <Select
                    value={isPaidVoice(voiceId) ? voiceId : ""}
                    className="max-w-[11rem]"
                    disabled={paidVoices.length === 0}
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
              {/* The same way in as the tab beside it. An empty list here is
                  not an error - it is a list nobody has chosen from yet, and
                  the row says so instead of the old "no key yet", which with
                  a working key was simply untrue. */}
              <GroupedRow
                title={paidVoices.length === 0 ? text("voices.none_api") : text("voices.title")}
                subtitle={
                  paidVoices.length === 0
                    ? text("voices.none_api_hint")
                    : text("voices.marked", { count: paidVoices.length })
                }
                trailing={
                  <Button size="sm" onClick={onManageVoices}>
                    <SpeakerIcon />
                    {text("voices.manage")}
                  </Button>
                }
              />
              {/* How far a press reads, where the money stops, and how fast -
                  the three things that describe one reading, in one group.
                  The first two are the same controls the panel beside the
                  read button carries: somebody setting a key up is exactly
                  somebody deciding how much of the book to spend on. */}
              <ReadingLimits
                scope={scope}
                budget={budget}
                spent={spent}
                onScope={onScope}
                onBudget={onBudget}
                bare
              />
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
          ) : (
            <Notice className="mt-4 block">{text("key.none_yet")}</Notice>
          )}
        </>
      )}

      </div>
    </Surface>
  );
}
