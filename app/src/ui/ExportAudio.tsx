/** Paste text read into a file: a WAV and its subtitles, where the person
 * chooses to keep them.
 *
 * The engine does the work (`export.text`): the same voice, rests and speed
 * as reading aloud, sent to a file instead of the speakers, its loudness
 * set for video and an AI-speech mark in the file's own metadata. The job
 * lives app-wide (`useExport`); this is only the door to it and the news of
 * how it went. Where the file goes next is the person's business, not the
 * app's.
 */
import { revealItemInDir } from "@tauri-apps/plugin-opener";
import { text } from "../i18n";
import { Button, ProgressBar } from "./controls";
import type { ExportJob } from "./useExport";

export function ExportAudio({
  job,
  disabled,
  cost,
  onStart,
  onCancel,
}: {
  job: ExportJob;
  /** Nothing to export, or a reading is under way. */
  disabled: boolean;
  /** A paid voice's price for this text, already phrased - the same figure
   * the read button carries, shown before anything is spent. */
  cost: string | null;
  onStart: () => void;
  onCancel: () => void;
}) {
  if (job.kind === "running") {
    const share = job.total > 0 ? job.done / job.total : 0;
    return (
      <div className="flex min-w-0 items-center gap-2" role="status">
        <span className="whitespace-nowrap">
          {job.total > 0
            ? text("export.progress", { done: job.done, total: job.total })
            : text("export.starting")}
        </span>
        <span className="w-24">
          <ProgressBar value={share} />
        </span>
        <Button size="sm" onClick={onCancel}>
          {text("export.cancel")}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex min-w-0 flex-wrap items-center gap-2">
      {job.kind === "done" && (
        <span role="status" className="flex items-center gap-2">
          <span>{text("export.done", { minutes: Math.max(1, Math.round(job.seconds / 60)) })}</span>
          <Button size="sm" variant="ghost" onClick={() => void revealItemInDir(job.path)}>
            {text("export.reveal")}
          </Button>
        </span>
      )}
      {job.kind === "failed" && (
        <span role="alert" className="text-danger">
          {job.message}
        </span>
      )}
      <Button size="sm" disabled={disabled} onClick={onStart}>
        {text("export.action")}
        {cost && <span className="font-normal">· {cost}</span>}
      </Button>
    </div>
  );
}
