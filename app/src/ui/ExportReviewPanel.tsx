/** The last export, sentence by sentence: listen to each as it is in the
 * file, say the ones that came out wrong again, then write the file anew.
 *
 * A voice model never says a sentence the same way twice - which is the
 * trouble with a short title, and here the remedy: a person keeps the take
 * they like. Takes wait in the engine (a nameless temporary file) until the
 * file is written again; nothing reaches the WAV before "Save file".
 */
import { text } from "../i18n";
import { Button, IconButton, Surface } from "./controls";
import { CloseIcon, PlayIcon, ResetIcon, StopIcon } from "./icons";
import type { ExportReview } from "./useExport";

export function ExportReviewPanel({
  review,
  playing,
  busy,
  saving,
  onPlay,
  onStop,
  onRetake,
  onSave,
  onDone,
  onClose,
}: {
  review: ExportReview;
  /** The sentence playing now, if one is. */
  playing: number | null;
  /** Something else holds the voice (a reading): takes wait for it. */
  busy: boolean;
  saving: boolean;
  onPlay: (index: number) => void;
  onStop: () => void;
  onRetake: (index: number) => void;
  onSave: () => void;
  /** End the review: the takes are let go. */
  onDone: () => void;
  /** Hide the panel; the review stays. */
  onClose: () => void;
}) {
  const working = review.busy !== null || saving;
  return (
    <Surface
      edge="strong"
      radius="sheet"
      dialog={text("review.title")}
      layer="popover"
      className="absolute bottom-[calc(var(--shell-bottom-inner)+var(--layer-gap))] right-6 z-30 flex layer-capped w-[34rem] max-w-[calc(100vw-3rem)] origin-bottom-right flex-col overflow-hidden shadow-lifted"
    >
      <div className="flex items-start gap-3 px-6 pb-3 pt-5">
        <div className="min-w-0 flex-1">
          <h3 className="m-0 text-base font-bold">{text("review.title")}</h3>
          <p className="m-0 mt-1 text-xs text-ink-mute">
            {text(review.retake ? "review.caption" : "review.caption_fixed")}
          </p>
        </div>
        <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>
      <ol className="m-0 min-h-0 flex-1 list-none overflow-y-auto border-t border-edge px-6 py-1">
        {review.sentences.map(({ index, text: said }) => {
          const here = playing === index;
          const changed = review.changed.includes(index);
          return (
            <li key={index} className="flex items-center gap-3 border-b border-edge py-2 last:border-b-0">
              <span className="w-6 shrink-0 text-right text-xs tabular-nums text-ink-mute">{index + 1}</span>
              <span className="min-w-0 flex-1 text-sm">
                {said}
                {changed && (
                  <span className="ml-2 whitespace-nowrap text-xs font-semibold text-brand-600">
                    {text("review.changed")}
                  </span>
                )}
              </span>
              <IconButton
                onClick={() => (here ? onStop() : onPlay(index))}
                disabled={(busy && !here) || working}
                aria-label={text(here ? "review.stop" : "review.play", { number: index + 1 })}
                title={text(here ? "review.stop" : "review.play", { number: index + 1 })}
              >
                {here ? <StopIcon /> : <PlayIcon />}
              </IconButton>
              {review.retake && (
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy || working}
                  onClick={() => onRetake(index)}
                  aria-label={text("review.retake_aria", { number: index + 1 })}
                >
                  <ResetIcon />
                  {review.busy === index ? text("review.retaking") : text("review.retake")}
                </Button>
              )}
            </li>
          );
        })}
      </ol>
      <div className="flex items-center gap-2 border-t border-edge px-6 py-3">
        {review.error ? (
          <span role="alert" className="min-w-0 flex-1 text-xs text-danger">{review.error}</span>
        ) : (
          <span className="min-w-0 flex-1 text-xs text-ink-mute">
            {review.changed.length > 0
              ? text("review.pending", { count: review.changed.length })
              : text("review.saved")}
          </span>
        )}
        <Button size="sm" variant="ghost" disabled={working} onClick={onDone}>
          {text("review.done")}
        </Button>
        <Button
          size="sm"
          variant="primary"
          disabled={review.changed.length === 0 || working || busy}
          onClick={onSave}
        >
          {saving ? text("review.saving") : text("review.save")}
        </Button>
      </div>
    </Surface>
  );
}
