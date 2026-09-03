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
import { Button, IconButton, Select, Surface } from "./controls";
import { GroupedRow, GroupedSection } from "./patterns";
import { CloseIcon, SpeakerIcon } from "./icons";
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
  onVoice: (voiceId: string) => void;
  onRate: (rate: number) => void;
  onManageVoices: () => void;
  onClose: () => void;
}) {
  const [busy, setBusy] = useState(false);

  // Esc closes any layer that sits above the screen - the keyboard contract
  // in docs/readease-hig.md §4. Not while a build is being fetched: leaving
  // then would hide a running download behind a chip.
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
      className="absolute bottom-[calc(var(--shell-bottom-h)+var(--layer-gap))] left-1/2 z-20 flex layer-capped w-[26rem] -translate-x-1/2 flex-col overflow-hidden shadow-lifted"
    >
      <div className="flex shrink-0 items-center px-6 pb-1 pt-5">
        <h3 className="m-0 flex-1 text-sm font-bold">{text("player.settings")}</h3>
        <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-5">
      <GroupedSection className="mt-3">
        {/* The control carries the voice's NAME only; what the voice is like
            (gender · region · style) is the row's own line - the full label
            in the select ran past the row and clipped its title (owner,
            02/09). */}
        <GroupedRow
          title={text("player.voice")}
          subtitle={describe(voices.find((voice) => voice.id === voiceId)?.label)}
          trailing={
            <Select value={voiceId} className="max-w-[11rem]" onChange={(event) => onVoice(event.target.value)}>
              {voices.map((voice) => (
                <option key={voice.id} value={voice.id}>{name(voice.label) || voice.id}</option>
              ))}
            </Select>
          }
        />
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
      <h4 className="m-0 mb-1.5 mt-4 text-xs font-semibold uppercase tracking-wide text-ink-mute">
        {text("model.quality")}
      </h4>
      <ModelChoices reading={reading} onBusy={setBusy} />
      </div>
    </Surface>
  );
}
