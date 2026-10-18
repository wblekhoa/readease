import { text } from "../i18n";
import { IconButton } from "./controls";
import { PauseIcon, PlayIcon } from "./icons";

/** RE-PLAY-026: shared, out-of-flow transport at the voice's current sentence. */
export function ReadingPositionControl({ playback, onToggle }: {
  playback: "reading" | "paused";
  onToggle: () => void;
}) {
  const label = text(playback === "paused" ? "player.resume" : "player.pause");
  return (
    <IconButton
      data-reading-control
      className="absolute right-full mr-1 top-2.5 text-white"
      frame="flex h-4.5 w-4.5 items-center justify-center rounded-full bg-brand-600 hover:bg-brand-700 active:bg-brand-700"
      aria-label={label}
      title={label}
      onKeyDown={event => event.stopPropagation()}
      onDoubleClick={event => event.stopPropagation()}
      onClick={event => { event.stopPropagation(); onToggle(); }}
    >
      {playback === "paused" ? <PlayIcon className="h-[9px] w-[9px]" /> : <PauseIcon className="h-[9px] w-[9px]" />}
    </IconButton>
  );
}
