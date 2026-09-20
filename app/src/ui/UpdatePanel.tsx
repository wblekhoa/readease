/** The "Bản mới" sheet (HIG 3.20): what the updater found, and the one
 * button the state allows. Sits in the middle of the window on the scrim,
 * like the other sheets; a download in flight cannot be dismissed. */
import { text } from "../i18n";
import { Button, IconButton, Surface } from "./controls";
import { CloseIcon } from "./icons";
import { Scrim, useDismiss } from "./patterns";
import { openUrl } from "@tauri-apps/plugin-opener";
import type { UpdatePhase } from "./updates";

const RELEASES = "https://github.com/wblekhoa/readease/releases/latest";

export function UpdatePanel({
  phase,
  onInstall,
  onRestart,
  onClose,
}: {
  phase: UpdatePhase;
  onInstall: () => void;
  onRestart: () => void;
  onClose: () => void;
}) {
  const busy = phase.kind === "downloading";
  const sheet = useDismiss(onClose, !busy);
  return (
    <>
      <Scrim />
      <Surface
        edge="strong"
        radius="sheet"
        layer="sheet"
        ref={sheet}
        className="fixed left-1/2 top-1/2 z-30 flex w-[26rem] max-w-[calc(100vw-3rem)] -translate-x-1/2 -translate-y-1/2 flex-col shadow-lifted"
      >
        <div className="flex items-start gap-3 px-6 pb-2 pt-5">
          <div className="min-w-0 flex-1">
            <h3 className="m-0 text-base font-bold">{text("update.title")}</h3>
            <p className="m-0 mt-1 text-sm text-ink-mute">{headline(phase)}</p>
          </div>
          {!busy && (
            <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
              <CloseIcon />
            </IconButton>
          )}
        </div>
        {phase.kind === "available" && phase.notes && (
          // The release's first lines, as written: a note is a note, not a
          // page; the whole of it is on the release.
          <p className="m-0 max-h-40 overflow-y-auto whitespace-pre-line px-6 py-2 text-sm leading-relaxed text-ink-mute">
            {excerpt(phase.notes)}
          </p>
        )}
        {phase.kind === "downloading" && (
          <div className="px-6 py-2">
            <div className="h-1.5 overflow-hidden rounded-full bg-band">
              <div
                className="h-full rounded-full bg-progress transition-[width]"
                style={{ width: `${phase.percent ?? 8}%` }}
              />
            </div>
          </div>
        )}
        <div className="flex justify-end gap-2 px-6 pb-5 pt-3">
          {phase.kind === "available" && (
            <>
              <Button variant="ghost" onClick={onClose}>{text("update.later")}</Button>
              <Button variant="primary" onClick={onInstall}>{text("update.install")}</Button>
            </>
          )}
          {phase.kind === "installed" && (
            <Button variant="primary" onClick={onRestart}>{text("update.relaunch")}</Button>
          )}
          {phase.kind === "failed" && (
            <Button onClick={() => void openUrl(RELEASES).catch(() => undefined)}>{text("update.open_releases")}</Button>
          )}
          {(phase.kind === "none" || phase.kind === "checking") && (
            <Button onClick={onClose}>{text("aria.close")}</Button>
          )}
        </div>
      </Surface>
    </>
  );
}

function headline(phase: UpdatePhase): string {
  switch (phase.kind) {
    case "checking": return text("update.checking");
    case "none": return text("update.latest", { version: phase.version });
    case "available": return text("update.available", { version: phase.version });
    case "downloading": return phase.percent === null
      ? text("update.downloading_start", { version: phase.version })
      : text("update.downloading", { version: phase.version, percent: phase.percent });
    case "installed": return text("update.installed", { version: phase.version });
    case "failed": return text("update.failed", { error: phase.message });
    default: return "";
  }
}

/** Markdown is what the release notes are written in; on this sheet the
 * headings and bullets are stripped to plain lines, ten at most. */
function excerpt(notes: string): string {
  return notes
    .split("\n")
    .map((line) => line.replace(/^#+\s*/, "").replace(/^\s*[-*]\s+/, "• ").replace(/\*\*/g, "").trim())
    .filter((line) => line.length > 0 && line !== "---")
    .slice(0, 10)
    .join("\n");
}
