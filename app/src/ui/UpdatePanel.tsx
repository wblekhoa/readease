/** The "Bản mới" sheet (HIG 3.20): what the updater found, how far it has
 * come, and the choices a Mac expects - skip this version, later, install
 * when quitting, install and relaunch, automatic download. In the middle
 * of the window on the scrim like the other sheets; work in flight cannot
 * be dismissed. */
import { text } from "../i18n";
import { Button, IconButton, Surface, Switch } from "./controls";
import { CloseIcon } from "./icons";
import { Scrim, useDismiss } from "./patterns";
import { openUrl } from "@tauri-apps/plugin-opener";
import type { UpdatePhase } from "./updates";
import { excerpt, releaseDate } from "./releaseNotes";

const RELEASES = "https://github.com/wblekhoa/readease/releases/latest";

export function UpdatePanel({
  phase,
  auto,
  onQuit,
  onInstallNow,
  onInstallOnQuit,
  onSkip,
  onAuto,
  onRestart,
  onClose,
}: {
  phase: UpdatePhase;
  auto: boolean;
  onQuit: boolean;
  onInstallNow: () => void;
  onInstallOnQuit: () => void;
  onSkip: () => void;
  onAuto: (value: boolean) => void;
  onRestart: () => void;
  onClose: () => void;
}) {
  const busy = phase.kind === "downloading" || phase.kind === "installing";
  const sheet = useDismiss(onClose, !busy);
  const offer = phase.kind === "available" || phase.kind === "ready";
  return (
    <>
      <Scrim />
      <Surface
        edge="strong"
        radius="sheet"
        layer="sheet"
        ref={sheet}
        dialog={text("update.title")}
        modal
        className="fixed left-1/2 top-1/2 z-30 flex w-[28rem] max-w-[calc(100vw-3rem)] -translate-x-1/2 -translate-y-1/2 flex-col shadow-lifted"
      >
        <div className="flex items-start gap-3 px-6 pb-2 pt-5">
          <div className="min-w-0 flex-1">
            <h3 className="m-0 text-base font-bold">{text("update.title")}</h3>
            <p className="m-0 mt-1 text-sm text-ink-mute">{headline(phase, onQuit)}</p>
            {offer && phase.date && (
              <p className="m-0 mt-0.5 text-xs text-ink-mute">{text("update.released", { date: releaseDate(phase.date) })}</p>
            )}
          </div>
          {!busy && (
            <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
              <CloseIcon />
            </IconButton>
          )}
        </div>
        {offer && phase.notes && (
          // The release's notes as paragraphs: a note is a note, not a page;
          // the whole of it is on the release.
          <p className="m-0 max-h-48 overflow-y-auto whitespace-pre-line px-6 py-2 text-sm leading-relaxed text-ink-mute">
            {excerpt(phase.notes)}
          </p>
        )}
        {phase.kind === "downloading" && (
          <div className="px-6 py-2">
            <div className="h-1.5 overflow-hidden rounded-full bg-band">
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
          {offer && !onQuit && (
            <Button variant="ghost" onClick={onSkip}>{text("update.skip")}</Button>
          )}
          <span className="flex-1" />
          {phase.kind === "available" && (
            <>
              <Button variant="ghost" onClick={onClose}>{text("update.later")}</Button>
              <Button onClick={onInstallOnQuit}>{text("update.on_quit")}</Button>
              <Button variant="primary" onClick={onInstallNow}>{text("update.install")}</Button>
            </>
          )}
          {phase.kind === "ready" && (
            <>
              {onQuit
                ? <Button variant="ghost" onClick={onClose}>{text("aria.close")}</Button>
                : <Button onClick={onInstallOnQuit}>{text("update.on_quit")}</Button>}
              <Button variant="primary" onClick={onInstallNow}>{text("update.install_now")}</Button>
            </>
          )}
          {phase.kind === "installed" && (
            <Button variant="primary" onClick={onRestart}>{text("update.relaunch")}</Button>
          )}
          {phase.kind === "failed" && (
            <Button onClick={() => void openUrl(RELEASES).catch(() => undefined)}>{text("update.open_releases")}</Button>
          )}
          {(phase.kind === "none" || phase.kind === "checking" || phase.kind === "idle") && (
            <Button onClick={onClose}>{text("aria.close")}</Button>
          )}
        </div>
      </Surface>
    </>
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
