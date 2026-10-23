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
      className="absolute right-full mr-1 top-2.5 text-on-brand"
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

/** Read from this block - shown only while the pointer is on it (owner,
 * 23/10: "click cụm sẽ không tự động đọc liền… hover vào cụm sẽ hiện icon
 * đọc bên trái, khi user nhấn vào thì mới đọc"). A plain click on the words
 * now only places the caret or starts a selection; reading is this one
 * deliberate press. Same spot and size as the voice's own control, which
 * takes its place on the block being read. Out of the Tab order: a book
 * has hundreds of blocks, and the keyboard reads from the transport. */
export function ReadFromHereButton({ onRead }: { onRead: () => void }) {
  const label = text("external.read_from_here");
  return (
    <IconButton
      data-read-from-here
      tabIndex={-1}
      className="absolute right-full mr-1 top-2.5 text-ink-mute opacity-0 transition-opacity group-hover:opacity-100 hover:text-on-brand"
      frame="flex h-4.5 w-4.5 items-center justify-center rounded-full bg-wash hover:bg-brand-600"
      aria-label={label}
      title={label}
      onMouseDown={event => event.preventDefault()}
      onDoubleClick={event => event.stopPropagation()}
      onClick={event => { event.stopPropagation(); onRead(); }}
    >
      <PlayIcon className="h-[9px] w-[9px]" />
    </IconButton>
  );
}
