/** Everything about the voice, in one panel above the footer.
 *
 * The footer itself carries one quiet chip ("Thu Hà · 1,25×"); the choices
 * live here, opened on request (owner, 02/09: "tối giản … setting sẽ có một
 * panel để chỉnh chi tiết"). Its inset is the sheets' 24, not its own 16:
 * every floating PANEL sets content in by the same amount (owner, 03/09).
 *
 * The first choice is the LANGUAGE to read in, and everything under it is
 * that language's: its voices, its speed, its model and keys (owner, 15/09:
 * "cho user chọn trước là họ muốn đọc ở ngôn ngữ nào rồi mới hiển thị các
 * nội dung liên quan đến ngôn ngữ đó"). Switching the language switches the
 * voice to the one last used for it - a tab that only filtered while the
 * other language's voice kept speaking would be a half-state nobody asked
 * for. Under the tab, a paid voice and a local one sit in the same select,
 * grouped by where they come from.
 *
 * Above the voices, when the text in front of the reader is in a language
 * the voice in use was not made for, one callout says so and offers the
 * switch. It never acts by itself: the voice is the reader's (owner, 15/09:
 * "cho user tự do chọn voice", with an alert that suggests).
 *
 * The voice can be changed while something is being read - the reading
 * restarts at the paragraph it had reached, in the new voice (owner, 03/09).
 * The select offers the voices SWITCHED ON in the voices panel, not the whole
 * catalogue (owner, 03/09): one list means one list everywhere, and the row
 * right below it is the way to add to it. Speed is still read once at the
 * start, so it stays disabled rather than promising what the engine will
 * not do.
 */
import { text } from "../i18n";
import { Button, IconButton, Notice, SegmentedControl, Select, SuggestionDot, Surface } from "./controls";
import { GroupedRow, GroupedSection, useDismiss } from "./patterns";
import { CloseIcon, VoiceSwitchIcon } from "./icons";
import { ReadingLimits } from "./CostPanel";
import { isPaidVoice, providerOf, PROVIDERS } from "./readingCost";
import { ModelProgress, ModelRows } from "./ModelPanel";
import { sourcesLine } from "./SourcesHub";
import {
  LANGUAGES,
  offeredFor,
  type Language as ReadingLanguage,
  type LanguageHint,
} from "./readingSources";
import type { Models } from "./useModels";
import {
  voiceDescription as describe,
  voiceName as name,
  type Voice,
} from "./voiceShortlist";

export type { Voice };

/** The sound between chapters and how much of a footnote is read - the
 * engine's `chapter_chime` and `note_reading` settings, listed here in
 * the order the select shows them (owner, 16/09; HIG 5.1). */
export const CHIMES = ["off", "marimba", "harp", "piano"] as const;
export type Chime = (typeof CHIMES)[number];
export const NOTE_READINGS = ["short", "full", "off"] as const;
export type NoteReading = (typeof NOTE_READINGS)[number];
export const DEFAULT_CHIME: Chime = "marimba";
export const DEFAULT_NOTE_READING: NoteReading = "short";

export function languageName(language: ReadingLanguage): string {
  return text(language === "vi" ? "language.vi" : "language.en");
}

export function SettingsPanel({
  voices,
  shortlist,
  favorites,
  voiceId,
  rate,
  rates,
  reading,
  shortlisted,
  voicesError,
  readingLanguage,
  contentLanguage,
  hint,
  models,
  keysSet,
  scope,
  budget,
  spent,
  onReadingLanguage,
  onScope,
  onBudget,
  onVoice,
  onRate,
  chime,
  noteReading,
  onChime,
  onNoteReading,
  onManageVoices,
  onOpenHub,
  output = null,
  onClose,
}: {
  /** The whole catalogue; what each tab offers is decided here. */
  voices: Voice[];
  shortlist: readonly string[];
  /** The voices starred ★: first in the select, under their own group
   * (HIG 3.13). Order only - the switch still decides what is offered. */
  favorites: readonly string[];
  voiceId: string;
  rate: number;
  rates: readonly number[];
  reading: boolean;
  /** How many voices are marked for the mid-reading switcher. */
  shortlisted: number;
  /** Why the list is empty, when it is empty for a reason worth saying. */
  voicesError?: string | null;
  readingLanguage: ReadingLanguage;
  /** What the text in front of the reader is in, when known - the dot on
   * the language option, the same device the voices panel uses. */
  contentLanguage: string | null;
  hint: LanguageHint | null;
  models: Models;
  /** Provider id → whether a key is stored. Never the key. */
  keysSet: Record<string, boolean>;
  /* The same two limits the cost panel by the read button carries. They are
     in both places on purpose (owner, 04/09): one is beside the price, the
     other beside the voice that bills, and a person adjusting either is
     already looking at the thing it governs. */
  scope: number | null;
  budget: number | null;
  spent: number;
  onReadingLanguage: (language: ReadingLanguage) => void;
  onScope: (chapters: number | null) => void;
  onBudget: (usd: number | null) => void;
  onVoice: (voiceId: string) => void;
  onRate: (rate: number) => void;
  chime: Chime;
  noteReading: NoteReading;
  onChime: (chime: Chime) => void;
  onNoteReading: (reading: NoteReading) => void;
  onManageVoices: () => void;
  onOpenHub: () => void;
  /** The device the voice plays through, from the host (HIG 3.21). */
  output?: { name: string; default: boolean } | null;
  onClose: () => void;
}) {
  const downloading = models.job !== null;
  // Escape and a click on the book both put it away; neither does while a
  // download runs, which is the one moment closing hides work in progress.
  const panel = useDismiss(onClose, !downloading);

  const offered = offeredFor(voices, shortlist, voiceId, readingLanguage);
  const current = voices.find((voice) => voice.id === voiceId);
  const chosen = offered.some((voice) => voice.id === voiceId) ? voiceId : "";
  const starred = offered.filter((voice) => favorites.includes(voice.id));
  const local = offered.filter((voice) => !isPaidVoice(voice.id) && !favorites.includes(voice.id));
  const paid = offered.filter((voice) => isPaidVoice(voice.id) && !favorites.includes(voice.id));
  const optionName = (voice: Voice) => (isPaidVoice(voice.id) ? voice.label : name(voice.label) || voice.id);
  const paidVoice = isPaidVoice(voiceId);

  return (
    /* Capped at the room between the bars, and only the BODY scrolls: with
       the quality section open this panel outgrew a short window and ran up
       under the header (owner, 03/09). Same shape as the notes panel - title
       pinned, list moving, scrollbar owned by the list. */
    <Surface
      edge="strong"
      material="glass"
      /* Sheet tier, not card: this floats over the book and stands on its
         own, which is what the guideline's 24 is for (owner, 03/09). */
      radius="sheet"
      ref={panel}
      dialog={text("player.settings")}
      /* Over its OWN button, not over the middle of the window. The button
         is the last thing in the footer's right-hand cluster, so the panel's
         right edge sits at the same 24px inset the row is padded by and the
         two line up without measuring anything (owner, 05/09: it used to
         open across the screen from the button that opened it). */
      layer="popover"
      className="absolute bottom-[calc(var(--shell-bottom-inner)+var(--layer-gap))] right-6 z-20 flex layer-capped w-[26rem] max-w-[calc(100vw-3rem)] origin-bottom-right flex-col overflow-hidden shadow-lifted"
    >
      <div className="flex shrink-0 items-center px-6 pb-1 pt-5">
        <h3 className="m-0 flex-1 text-sm font-bold">{text("player.settings")}</h3>
        <IconButton onClick={onClose} disabled={downloading} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>
      {/* Sideways never: a floating panel scrolls down when the window is
          shorter than it, and nothing else (HIG 3.5, 16/09). */}
      <div className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto px-6 pb-5">
        <div className="mt-3">
          <p className="m-0 mb-2 text-xs font-semibold text-ink-mute">{text("settings.language")}</p>
          <SegmentedControl
            value={readingLanguage}
            label={text("settings.language")}
            options={LANGUAGES.map((code) => {
              const label = text(code === "vi" ? "voices.language_vi" : "voices.language_en");
              /* The suggestion is a DOT on the option itself (owner, 07/09,
                 for the book's language): the text in front of the reader
                 is in this language and the tab is on the other one. Acting
                 on it is the same tap the option always was. */
              const marked = contentLanguage === code && code !== readingLanguage;
              return {
                value: code,
                label: marked ? (
                  <>
                    <SuggestionDot />
                    {label}
                  </>
                ) : label,
                ariaLabel: marked ? text("settings.language_content", { name: label }) : undefined,
                title: marked ? text("settings.language_content", { name: label }) : undefined,
              };
            })}
            onChange={onReadingLanguage}
          />
        </div>

        {/* Not over the empty tab of the same language: the rows under it
            already say there is no voice and offer the download, and a
            button that flips to the tab you are on is a button that does
            nothing. */}
        {hint && !(hint.kind === "get" && hint.content === readingLanguage) && (
          <Notice
            tone="info"
            className="mt-4 block"
            action={
              <Button
                size="sm"
                variant="primary"
                disabled={downloading}
                onClick={() => onReadingLanguage(hint.content)}
              >
                {text(hint.kind === "switch" ? "hint.switch" : "hint.get", { language: languageName(hint.content) })}
              </Button>
            }
          >
            {text(hint.kind === "switch" ? "hint.mismatch" : "hint.no_voice", { language: languageName(hint.content) })}
          </Notice>
        )}

        {offered.length === 0 ? (
          <>
            {/* Nothing reads this language yet. The model's own row is the
                shortest way to change that, and the hub is the other. */}
            <GroupedSection title={text("player.voice")}>
              <GroupedRow
                title={text("settings.no_voice", { language: languageName(readingLanguage) })}
                subtitle={voicesError ? `${text("voices.unavailable")} (${voicesError})` : text("settings.no_voice_hint")}
              />
            </GroupedSection>
            <ModelRows language={readingLanguage} models={models} reading={reading} />
            <div className="mt-4 flex justify-end">
              <Button size="sm" disabled={downloading} onClick={onOpenHub}>{text("hub.title")}…</Button>
            </div>
          </>
        ) : (
          <>
            {/* Two named groups instead of a flat run of rows: what you read
                WITH, then where it comes from. Unlabelled groups separated
                only by a dotted rule left a reader working out where one
                concern ended (owner, 04/09: "phân cấp tốt hơn"). */}
            <GroupedSection title={text("player.voice")}>
              {/* The control carries the voice's NAME only; what the voice
                  is like (gender · region · style) is the row's own line -
                  the full label in the select ran past the row and clipped
                  its title (owner, 02/09). A paid voice's line is its
                  provider's NAME: "openai" in a subtitle is an internal
                  token wearing a label's clothes. */}
              <GroupedRow
                title={text("player.voice")}
                subtitle={
                  paidVoice
                    ? PROVIDERS.find((item) => item.id === providerOf(voiceId))?.label
                    : describe(current?.label)
                }
                trailing={(titleId) => (
                  <Select
                    labelledBy={titleId}
                    value={chosen}
                    className="max-w-[11rem]"
                    onChange={(event) => onVoice(event.target.value)}
                  >
                    {/* The voice in use is not one of this language's, so
                        none is chosen here. The empty slot is NAMED rather
                        than blank: a select showing nothing reads as broken,
                        where "Chọn giọng…" reads as an invitation. */}
                    {!chosen && (
                      <option value="" disabled>{text("voices.pick")}</option>
                    )}
                    {/* Starred first, under their own name; the groups
                        below are the rest, as they were (HIG 3.13). */}
                    {starred.length > 0 ? (
                      <>
                        <optgroup label={text("voices.group_favorites")}>
                          {starred.map((voice) => (
                            <option key={voice.id} value={voice.id}>{optionName(voice)}</option>
                          ))}
                        </optgroup>
                        {local.length > 0 && (
                          <optgroup label={text("voices.group_local")}>
                            {local.map((voice) => (
                              <option key={voice.id} value={voice.id}>{optionName(voice)}</option>
                            ))}
                          </optgroup>
                        )}
                        {paid.length > 0 && (
                          <optgroup label={text("voices.source_api")}>
                            {paid.map((voice) => (
                              <option key={voice.id} value={voice.id}>{optionName(voice)}</option>
                            ))}
                          </optgroup>
                        )}
                      </>
                    ) : local.length > 0 && paid.length > 0 ? (
                      <>
                        <optgroup label={text("voices.group_local")}>
                          {local.map((voice) => (
                            <option key={voice.id} value={voice.id}>{name(voice.label) || voice.id}</option>
                          ))}
                        </optgroup>
                        <optgroup label={text("voices.source_api")}>
                          {paid.map((voice) => (
                            <option key={voice.id} value={voice.id}>{voice.label}</option>
                          ))}
                        </optgroup>
                      </>
                    ) : (
                      offered.map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {isPaidVoice(voice.id) ? voice.label : name(voice.label) || voice.id}
                        </option>
                      ))
                    )}
                  </Select>
                )}
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
                    {/* The same glyph the transport's switcher wears, so a
                        person reads as "voices" wherever it turns up. */}
                    <VoiceSwitchIcon />
                    {text("voices.manage")}
                  </Button>
                }
              />
              <GroupedRow
                title={text("player.speed")}
                trailing={(titleId) => (
                  <Select labelledBy={titleId} value={rate} disabled={reading} onChange={(event) => onRate(Number(event.target.value))}>
                    {rates.map((value) => (
                      <option key={value} value={value}>{value}×</option>
                    ))}
                  </Select>
                )}
              />
              {/* How the document SOUNDS beyond the voice and its speed:
                  the chime between chapters and how much of a footnote is
                  read. Each subtitle is the rule the choice sets, so the
                  row explains itself (HIG 5.1). Neither is locked while
                  reading: the engine reads both at the next press of
                  Read, which is when a change can take effect anyway. */}
              <GroupedRow
                title={text("settings.chime")}
                subtitle={text("settings.chime_hint")}
                trailing={(titleId) => (
                  <Select labelledBy={titleId} value={chime} onChange={(event) => onChime(event.target.value as Chime)}>
                    {CHIMES.map((value) => (
                      <option key={value} value={value}>{text(`settings.chime_${value}`)}</option>
                    ))}
                  </Select>
                )}
              />
              <GroupedRow
                title={text("settings.notes")}
                subtitle={text(`settings.notes_${noteReading}_hint`)}
                trailing={(titleId) => (
                  <Select labelledBy={titleId} value={noteReading} onChange={(event) => onNoteReading(event.target.value as NoteReading)}>
                    {NOTE_READINGS.map((value) => (
                      <option key={value} value={value}>{text(`settings.notes_${value}`)}</option>
                    ))}
                  </Select>
                )}
              />
              {/* How far a press reads and where the money stops - only
                  under a voice that bills. The same two controls the panel
                  beside the read button carries. */}
              {paidVoice && (
                <ReadingLimits
                  scope={scope}
                  budget={budget}
                  spent={spent}
                  onScope={onScope}
                  onBudget={onBudget}
                  bare
                />
              )}
            </GroupedSection>
            <GroupedSection title={text("settings.sources")}>
              <GroupedRow
                title={text(readingLanguage === "vi" ? "voices.language_vi" : "voices.language_en")}
                subtitle={sourcesLine(readingLanguage, models.status, voices, keysSet)}
                trailing={
                  <Button size="sm" disabled={downloading} onClick={onOpenHub}>{text("hub.manage")}</Button>
                }
              />
              {/* Where the voice goes (HIG 3.21): named, and honest when it
                  is not the Mac's default - the fact that makes a "silent"
                  Multi-Output setup diagnosable from the screen. */}
              <GroupedRow
                title={text("settings.output")}
                subtitle={
                  output === null
                    ? text("settings.output_unknown")
                    : `${output.name} · ${text(output.default ? "settings.output_default" : "settings.output_fallback")}`
                }
              />
            </GroupedSection>
          </>
        )}
        {/* A download started anywhere - the hub, the first-run screen - is
            visible here while this panel is the one open. */}
        <ModelProgress models={models} className="mt-4" />
      </div>
    </Surface>
  );
}
