/** RE-UPDATE-001: dismissible detail popover, with no scrim or focus trap. */
import { currentLanguage, text } from "../i18n";
import { Button, IconButton, Surface, Switch } from "./controls";
import { CloseIcon } from "./icons";
import { useDismiss } from "./patterns";
import { openUrl } from "@tauri-apps/plugin-opener";
import type { UpdatePhase } from "./updates";
import { excerpt, releaseDate } from "./releaseNotes";

const RELEASES = "https://github.com/wblekhoa/readease/releases/latest";

export function UpdatePanel({
  phase,
  auto,
  onQuit,
  exportBlocked = false,
  onInstallNow,
  onInstallOnQuit,
  onAuto,
  onRestart,
  onDownload,
  onRetry,
  anchor,
  readingActive = false,
  onClose,
}: {
  phase: UpdatePhase;
  auto: boolean;
  onQuit: boolean;
  exportBlocked?: boolean;
  onInstallNow: () => void;
  onInstallOnQuit: () => void;
  onAuto: (value: boolean) => void;
  onRestart: () => void;
  onDownload: () => void;
  onRetry: () => void;
  anchor: { left: number; bottom: number };
  readingActive?: boolean;
  onClose: () => void;
}) {
  const sheet = useDismiss(onClose);
  const offer = phase.kind === "available" || phase.kind === "ready";
  return (
    <div id="update-details">
      <Surface
        edge="strong"
        radius="sheet"
        layer="popover"
        ref={sheet}
        dialog={text("update.title")}
        style={{ left: anchor.left, bottom: anchor.bottom }}
        className="fixed z-30 flex max-h-[calc(100dvh-2rem)] w-[26rem] max-w-[calc(100vw-2rem)] flex-col overflow-y-auto shadow-lifted"
      >
        <div className="flex items-start gap-3 px-6 pb-2 pt-5">
          <div className="min-w-0 flex-1">
            <h3 className="m-0 text-base font-bold">{text("update.title")}</h3>
            {/* Wraps anywhere: a failed check says the URL it could not reach,
                one unbroken word wider than the sheet (27/09). */}
            <p aria-live="polite" className="m-0 mt-1 break-words text-sm text-ink-mute">{headline(phase, onQuit)}</p>
            {offer && phase.date && (
              <p className="m-0 mt-0.5 text-xs text-ink-mute">{text("update.released", { date: releaseDate(phase.date, currentLanguage()) })}</p>
            )}
          </div>
          <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
              <CloseIcon />
          </IconButton>
        </div>
        {readingActive && (phase.kind === "ready" || phase.kind === "installed") && <p className="m-0 px-6 py-2 text-sm text-ink-mute">{text("update.reading_warning")}</p>}
        {phase.kind === "installed" && phase.error && <p role="alert" className="m-0 break-words px-6 py-2 text-sm text-danger">{phase.error}</p>}
        {exportBlocked && <p role="status" className="m-0 px-6 py-2 text-sm text-ink-mute">{text("audiobook.update_wait")}</p>}
        {offer && phase.notes && (
          // The release's notes as paragraphs: a note is a note, not a page;
          // the whole of it is on the release. The half in the reader's
          // language. It scrolls, so the keyboard can reach it - a region
          // with a name (axe, 27/09: scrollable-region-focusable).
          <p
            tabIndex={0}
            role="region"
            aria-label={text("update.notes")}
            className="m-0 max-h-48 overflow-y-auto whitespace-pre-line break-words px-6 py-2 text-sm leading-relaxed text-ink-mute"
          >
            {excerpt(phase.notes, currentLanguage())}
          </p>
        )}
        {phase.kind === "downloading" && (
          <div className="px-6 py-2">
            <div className="h-1.5 overflow-hidden rounded-full bg-track">
              <div className="h-full rounded-full bg-progress transition-[width]" style={{ width: `${phase.percent ?? 8}%` }} />
            </div>
          </div>
        )}
        {offer && (
          // Sparkle's checkbox, as a row of the sheet: the person's standing
          // choice about the NEXT releases, off until they say otherwise.
          <div className="flex items-center justify-between gap-3 px-6 py-2">
            <span className="text-sm text-ink">{text("update.auto")}</span>
            <Switch checked={auto} onChange={onAuto} label={text("update.auto")} />
          </div>
        )}
        <div className="flex flex-wrap items-center gap-2 px-6 pb-5 pt-3">
          {phase.kind !== "ready" && <span className="flex-1" />}
          {phase.kind === "available" && (
            <>
              <Button variant="ghost" onClick={onClose}>{text("update.later")}</Button>
              <Button variant="primary" onClick={onDownload}>{text("update.download")}</Button>
            </>
          )}
          {phase.kind === "ready" && (
            <div className="flex w-full items-center gap-2">
              {onQuit
                ? <Button className="min-w-0 flex-1" variant="ghost" onClick={onClose}>{text("aria.close")}</Button>
                : <Button className="min-w-0 flex-1" onClick={onInstallOnQuit}>{text("update.on_quit")}</Button>}
              <Button className="min-w-0 flex-1" variant="primary" disabled={exportBlocked} onClick={onInstallNow}>{text("update.install_now")}</Button>
            </div>
          )}
          {phase.kind === "installed" && (
            <Button variant="primary" disabled={exportBlocked} onClick={onRestart}>{text("update.relaunch")}</Button>
          )}
          {phase.kind === "failed" && (
            <>
              <Button variant="ghost" onClick={() => void openUrl(RELEASES).catch(() => undefined)}>{text("update.open_releases")}</Button>
              <Button variant="primary" disabled={phase.recovery === "install" && exportBlocked} onClick={onRetry}>{text(phase.recovery === "install" ? "update.install_now" : "update.retry")}</Button>
            </>
          )}
          {phase.kind === "downloading" && <Button onClick={onClose}>{text("update.continue")}</Button>}
          {(phase.kind === "none" || phase.kind === "checking" || phase.kind === "idle") && (
            <Button onClick={onClose}>{text("aria.close")}</Button>
          )}
        </div>
      </Surface>
    </div>
  );
}

function headline(phase: UpdatePhase, onQuit: boolean): string {
  switch (phase.kind) {
    case "checking": return text("update.checking");
    case "none": return text("update.latest", { version: phase.version });
    case "available": return text("update.available", { version: phase.version });
    case "downloading": return phase.percent === null
      ? text("update.downloading_start", { version: phase.version })
      : text("update.downloading", { version: phase.version, percent: phase.percent });
    case "ready": return onQuit
      ? text("update.on_quit_armed", { version: phase.version })
      : text("update.ready", { version: phase.version });
    case "installing": return text("update.installing", { version: phase.version });
    case "installed": return text("update.installed", { version: phase.version });
    case "failed": return text("update.failed", { error: phase.message });
    default: return text("update.latest_unknown");
  }
}
