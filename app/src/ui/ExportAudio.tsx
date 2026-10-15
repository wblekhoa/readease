/** The Paste-text entry point. The receipt lives in the app-wide footer. */
import { text } from "../i18n";
import { Button } from "./controls";
import type { ExportJob } from "./useExport";

export function ExportAudio({ job, disabled, cost, onStart }: {
  job: ExportJob; disabled: boolean; cost: string | null; onStart: () => void;
  onCancel: () => void; onReview: (() => void) | null;
}) {
  return <Button size="sm" disabled={disabled || job.kind === "running"} onClick={onStart}>
    {text("export.action")}{cost && <span className="font-normal">· {cost}</span>}
  </Button>;
}
