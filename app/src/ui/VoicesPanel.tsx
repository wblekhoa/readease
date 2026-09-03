/** The place where the list of voices is decided.
 *
 * The engine offers twenty. Picking one out of twenty in the middle of a
 * chapter is not a thing anyone wants to do, so this panel is where the
 * choosing happens ONCE - listen, mark the ones worth keeping - and the
 * reading UI then offers only those (owner, 03/09).
 *
 * Preview is not offered while something is being read, and that is a fact
 * about the engine rather than a decision here: it speaks one thing at a
 * time, so a preview would cancel the reading it was meant to help you
 * change. The two halves are meant for different moments - listen here when
 * idle, switch from the footer when reading.
 */
import { useEffect } from "react";
import { text } from "../i18n";
import { IconButton, Notice, Surface, Switch } from "./controls";
import { GroupedSection } from "./patterns";
import { CloseIcon, SpeakerIcon, StopIcon } from "./icons";
import { voiceDescription, voiceName, type Voice } from "./voiceShortlist";

export function VoicesPanel({
  voices,
  shortlist,
  voiceId,
  reading,
  previewing,
  onToggle,
  onPreview,
  onStopPreview,
  onClose,
}: {
  voices: Voice[];
  shortlist: string[];
  voiceId: string;
  /** Something is being read, so the engine cannot also speak a sample. */
  reading: boolean;
  /** The voice whose sample is playing right now, if any. */
  previewing: string | null;
  onToggle: (id: string) => void;
  onPreview: (id: string) => void;
  onStopPreview: () => void;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <Surface
      edge="strong"
      radius="sheet"
      className="absolute left-1/2 top-1/2 z-30 flex max-h-[84%] w-[32rem] -translate-x-1/2 -translate-y-1/2 flex-col shadow-lifted"
    >
      <div className="flex items-start gap-3 px-6 pb-4 pt-5">
        <div className="min-w-0 flex-1">
          <h3 className="m-0 text-base font-bold">{text("voices.title")}</h3>
          <p className="m-0 mt-1 text-xs text-ink-mute">{text("voices.caption")}</p>
        </div>
        <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-6">
        <GroupedSection>
          {voices.map((voice) => {
            const inList = shortlist.includes(voice.id);
            const playing = previewing === voice.id;
            return (
              <div key={voice.id} className="flex items-center gap-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2 text-sm font-medium">
                    {voiceName(voice.label) || voice.id}
                    {voice.id === voiceId && (
                      <span className="text-xs font-normal text-ink-faint">{text("voices.in_use")}</span>
                    )}
                  </div>
                  <div className="mt-0.5 text-xs text-ink-mute">{voiceDescription(voice.label)}</div>
                </div>
                <IconButton
                  onClick={() => (playing ? onStopPreview() : onPreview(voice.id))}
                  disabled={reading}
                  aria-label={text(playing ? "voices.stop_preview" : "voices.preview")}
                  title={text(reading ? "voices.preview_while_reading" : playing ? "voices.stop_preview" : "voices.preview")}
                  className={playing ? "text-brand-600" : ""}
                >
                  {playing ? <StopIcon /> : <SpeakerIcon />}
                </IconButton>
                <Switch
                  checked={inList}
                  onChange={() => onToggle(voice.id)}
                  label={text("voices.in_switcher", { name: voiceName(voice.label) || voice.id })}
                />
              </div>
            );
          })}
        </GroupedSection>
      </div>

      <div className="border-t border-edge px-6 py-4">
        <Notice>
          {reading
            ? text("voices.preview_while_reading")
            : text("voices.marked", { count: shortlist.length })}
        </Notice>
      </div>
    </Surface>
  );
}
