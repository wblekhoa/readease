/** One persistent export receipt on every screen, outside the reading bar. */
import { useEffect, useState } from "react";
import { revealItemInDir } from "@tauri-apps/plugin-opener";
import { text } from "../i18n";
import { Button, IconButton, ProgressBar, Surface } from "./controls";
import { CloseIcon } from "./icons";
import type { ExportJob } from "./useExport";

export function ExportStatus({ job, onCancel, onDismiss, onReview }: {
  job: ExportJob; onCancel: () => void; onDismiss: () => void; onReview: (() => void) | null;
}) {
  const [now, setNow] = useState(Date.now());
  const running = job.kind === "running";
  useEffect(() => {
    if (!running) return;
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [running]);
  if (job.kind === "idle") return null;
  const title = "title" in job ? job.title : null;
  const phase = job.kind === "running" ? job.phase : null;
  const label = job.kind === "running"
    ? job.cancelling ? text("audiobook.cancelling")
      : phase === "normalising" ? text("audiobook.normalising")
      : phase === "encoding" ? text("audiobook.encoding")
      : job.total ? text(job.title ? "audiobook.synthesising" : "export.progress", { done: job.done, total: job.total }) : text("export.starting")
    : job.kind === "failed" ? job.message : job.kind === "cancelled" ? text("audiobook.cancelled")
    : text(job.book ? "audiobook.done" : "export.done", { minutes: Math.max(1, Math.round(job.seconds / 60)) });
  const announcement = job.kind !== "running" ? label
    : job.cancelling ? text("audiobook.cancelling")
    : phase === "normalising" ? text("audiobook.normalising")
    : phase === "encoding" ? text("audiobook.encoding")
    : text("audiobook.generating");
  const seconds = job.kind === "running" ? Math.max(0, Math.floor((now - (job.startedAt ?? now)) / 1000)) : 0;
  return <div data-export-status=""><Surface edge="strong" className="mx-6 mb-3 shrink-0 px-4 py-3">
    <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2">
      <div className="min-w-0 flex-1" role={job.kind === "failed" ? "alert" : "status"}>
        {title && <div className="truncate text-sm font-semibold">{title}</div>}
        <div aria-hidden={running || undefined} className={`text-sm ${job.kind === "failed" ? "text-danger" : "text-ink-mute"}`}>{label}</div>
        {running && <span className="sr-only">{announcement}</span>}
      </div>
      {job.kind === "running" && <>
        <span className="text-xs tabular-nums text-ink-mute">{text("audiobook.elapsed", { time: `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}` })}</span>
        <Button size="sm" disabled={job.cancelling} onClick={onCancel}>{text("export.cancel")}</Button>
      </>}
      {job.kind === "done" && <>
        <Button size="sm" onClick={() => void revealItemInDir(job.path)}>{text("export.reveal")}</Button>
        {onReview && <Button size="sm" onClick={onReview}>{text("export.review")}</Button>}
      </>}
      {!running && <IconButton onClick={onDismiss} aria-label={text("aria.close")}><CloseIcon /></IconButton>}
    </div>
    {job.kind === "running" && <div className="mt-2">
      {phase !== "normalising" && phase !== "encoding" && job.total > 0
        ? <div role="progressbar" aria-label={announcement} aria-valuemin={0} aria-valuemax={job.total} aria-valuenow={job.done}><ProgressBar value={Math.min(.99, job.done / job.total)} /></div>
        : <span role="progressbar" aria-label={label} className="block h-1 rounded-full bg-wash" />}
      {job.cancelError && <p role="alert" className="mb-0 mt-2 text-sm text-danger">{job.cancelError}</p>}
      <p className="mb-0 mt-2 text-xs text-ink-mute">{text("audiobook.background_short")}</p>
    </div>}
  </Surface></div>;
}
