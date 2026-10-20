/** RE-UPDATE-001: persistent, quiet status in both sidebar layouts. */
import { text } from "../i18n";
import { Button, IconButton } from "./controls";
import { ResetIcon } from "./icons";
import type { UpdatePhase } from "./updates";
export function UpdateNotice({ phase, onQuit, compact = false, open, onPress }: {
  phase: UpdatePhase; onQuit: boolean; compact?: boolean; open: boolean; onPress: () => void;
}) {
  if (phase.kind === "idle" || phase.kind === "none" || phase.kind === "checking") return null;
  const label = phase.kind === "failed" ? text("update.short_failed")
    : phase.kind === "downloading" ? (phase.percent === null ? text("update.short_preparing") : text("update.short_downloading", { percent: phase.percent }))
    : phase.kind === "ready" ? text(onQuit ? "update.short_scheduled" : "update.short_ready")
    : phase.kind === "installing" ? text("update.installing", { version: phase.version })
    : phase.kind === "installed" ? text("update.relaunch") : text("update.short_available");
  const icon = <ResetIcon />;
  if (compact) return <IconButton data-update-notice data-popover-trigger aria-label={label} title={label} aria-haspopup="dialog" aria-expanded={open} aria-controls="update-details" onClick={onPress} className="text-brand-600" tipSide="right">{icon}</IconButton>;
  return <div className="px-3 pb-3 pt-1">
    <Button variant="ghost" data-update-notice data-popover-trigger aria-label={label} aria-haspopup="dialog" aria-expanded={open} aria-controls="update-details" onClick={onPress}
      className="!h-auto w-full !justify-start gap-2.5 !bg-brand-600/10 !px-3 !py-2.5 text-left !text-ink">
      <span className="shrink-0 text-brand-600">{icon}</span>
      <span className="min-w-0 flex-1 truncate text-sm font-medium">{label}</span>
    </Button>
    {phase.kind === "downloading" && <div role="progressbar" aria-label={text("update.details")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={phase.percent ?? undefined} className="mx-3 mt-1 h-0.5 overflow-hidden rounded-full bg-track">
      <div className="h-full bg-progress" style={{ width: `${phase.percent ?? 8}%` }} />
    </div>}
  </div>;
}
