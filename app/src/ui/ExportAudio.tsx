/** Pasted text's export, beside Read in the bottom bar (21/10). The receipt
 * lives in the app-wide footer. */
import { text } from "../i18n";
import { Button } from "./controls";
import { ExportIcon } from "./icons";
import type { ExportJob } from "./useExport";

export function ExportAudio({ job, disabled, cost, onStart }: {
  job: ExportJob; disabled: boolean; cost: string | null; onStart: () => void;
  onCancel: () => void; onReview: (() => void) | null;
}) {
  const label = cost ? `${text("export.action")} · ${cost}` : text("export.action");
  /* A step below Read: `lg` is the one button a screen is for, and this is
     its second action. Where the bar is narrow the words step aside for the
     icon - the voice's name beside it was cut to one letter at 960 px with
     the column open - and stay its name and its tooltip. */
  return <Button disabled={disabled || job.kind === "running"} onClick={onStart}
    aria-label={label} title={label}>
    <ExportIcon />
    <span className="hidden items-center gap-1.5 @min-[52rem]:inline-flex">
      {text("export.action")}{cost && <span className="font-normal">· {cost}</span>}
    </span>
  </Button>;
}
