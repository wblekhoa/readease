/** Everything about the voice, in one panel above the footer.
 *
 * The footer itself carries one quiet chip ("Thu Hà · 1,25×"); the choices
 * live here, opened on request (owner, 02/09: "tối giản … setting sẽ có một
 * panel để chỉnh chi tiết"). Voice and speed are read once, when a reading
 * starts, so the panel says so while something is playing rather than
 * offering controls that would change nothing.
 */
import { useEffect, useState } from "react";
import { text } from "../i18n";
import { IconButton, Select, Surface } from "./controls";
import { GroupedRow, GroupedSection } from "./patterns";
import { CloseIcon } from "./icons";
import { ModelChoices } from "./ModelPanel";

export type Voice = { id: string; label: string };

/** The engine labels a voice "Tên - Nam · Bắc · Phong cách": the part before
 * the dash is the name, the rest describes it. */
function name(label: string | undefined): string {
  return (label ?? "").split(" - ")[0].trim();
}
function describe(label: string | undefined): string | undefined {
  const parts = (label ?? "").split(" - ");
  return parts.length > 1 ? parts.slice(1).join(" - ").trim() : undefined;
}

export function SettingsPanel({
  voices,
  voiceId,
  rate,
  rates,
  reading,
  onVoice,
  onRate,
  onClose,
}: {
  voices: Voice[];
  voiceId: string;
  rate: number;
  rates: readonly number[];
  reading: boolean;
  onVoice: (voiceId: string) => void;
  onRate: (rate: number) => void;
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
    <Surface edge="strong" className="absolute bottom-[calc(var(--shell-bottom-h)+0.5rem)] left-1/2 z-20 w-[26rem] -translate-x-1/2 p-4 shadow-lifted">
      <div className="flex items-center">
        <h3 className="m-0 flex-1 text-sm font-bold">{text("player.settings")}</h3>
        <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>
      <GroupedSection className="mt-3">
        {/* The control carries the voice's NAME only; what the voice is like
            (gender · region · style) is the row's own line - the full label
            in the select ran past the row and clipped its title (owner,
            02/09). */}
        <GroupedRow
          title={text("player.voice")}
          subtitle={describe(voices.find((voice) => voice.id === voiceId)?.label)}
          trailing={
            <Select value={voiceId} disabled={reading} className="max-w-[11rem]" onChange={(event) => onVoice(event.target.value)}>
              {voices.map((voice) => (
                <option key={voice.id} value={voice.id}>{name(voice.label) || voice.id}</option>
              ))}
            </Select>
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
      <h4 className="m-0 mb-1.5 mt-4 px-3 text-xs font-semibold uppercase tracking-wide text-ink-mute">
        {text("model.quality")}
      </h4>
      <ModelChoices reading={reading} onBusy={setBusy} />
    </Surface>
  );
}
