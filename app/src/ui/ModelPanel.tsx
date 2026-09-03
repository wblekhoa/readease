/** The voice-build manager, now a section of the settings panel.
 *
 * A switch restarts the engine process - the build loads at construction -
 * so this panel is loud about that, downloads what is missing first
 * (streaming the engine's own progress), and only offers to delete the
 * build that is NOT in use (the engine refuses anything else anyway).
 */
import { useCallback, useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { text } from "../i18n";
import { Button, ProgressBar } from "./controls";
import { GroupedRow, GroupedSection } from "./patterns";

type Status = {
  ready: boolean;
  precision: string | null;
  installed: Record<string, number>;
};

const BUILDS = [
  { id: "int8", label: () => text("model.build_standard") },
  { id: "fp32", label: () => text("model.build_maximum") },
] as const;

export function ModelChoices({
  reading,
  onBusy,
}: {
  reading: boolean;
  /** The settings panel must not close over a running download. */
  onBusy?: (busy: boolean) => void;
}) {
  const [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const refresh = useCallback(() => {
    invoke<{ result: Status }>("engine_request", {
      method: "model.status",
      params: {},
    })
      .then((reply) => setStatus(reply.result))
      .catch((error) => setNote(String(error)));
  }, []);

  useEffect(refresh, [refresh]);

  useEffect(() => { onBusy?.(busy !== null); }, [busy, onBusy]);

  useEffect(() => {
    const progressEvents = listen<{ progress: number; message: string }>(
      "engine:model_progress",
      (event) => {
        setProgress(event.payload.progress);
        setNote(event.payload.message);
      },
    );
    // A model download outlives any sane request timeout, so its completion
    // arrives as an event rather than a reply (advisor finding #2).
    const finished = listen<{
      ok: boolean;
      error?: string;
      result?: { cancelled?: boolean };
    }>("engine:orphan_reply", (event) => {
      setBusy(null);
      setProgress(null);
      setNote(
        event.payload.result?.cancelled
          ? text("model.cancelled")
          : event.payload.ok
            ? null
            : event.payload.error ?? null,
      );
      refresh();
    });
    return () => {
      progressEvents.then((unlisten) => unlisten());
      finished.then((unlisten) => unlisten());
    };
  }, [refresh]);

  const switchTo = useCallback(async (precision: string) => {
    setBusy(precision);
    setNote(null);
    try {
      await invoke("engine_request", {
        method: "model.set_precision",
        params: { precision },
      });
      setNote(text("model.restarting"));
      await invoke("restart_engine");
      // The fresh engine may still miss files; download inside the new
      // process so the bytes land where it will look for them. Fire and
      // listen: completion comes back as engine:orphan_reply.
      setNote(text("model.preparing"));
      await invoke("prepare_model");
    } catch (error) {
      setNote(String(error));
      setBusy(null);
    }
  }, [refresh]);

  const removeSpare = useCallback(async (precision: string) => {
    setBusy(precision);
    try {
      await invoke("engine_request", {
        method: "model.remove_build",
        params: { precision },
      });
      refresh();
    } catch (error) {
      setNote(String(error));
    } finally {
      setBusy(null);
    }
  }, [refresh]);

  return (
    <>
      <p className="m-0 text-xs leading-relaxed text-ink-mute">
        {text("model.switch_restart")}
      </p>
      <GroupedSection className="mt-3">
        {BUILDS.map((build) => {
          const active = status?.precision === build.id;
          const installed = (status?.installed[build.id] ?? 0) > 0;
          return (
            <GroupedRow
              key={build.id}
              title={build.label()}
              subtitle={
                active
                  ? text("model.in_use")
                  : installed
                    ? undefined
                    : text("model.not_downloaded")
              }
              trailing={
                !active && (
                  <>
                    <Button
                      variant="primary"
                      size="sm"
                      disabled={busy !== null || reading}
                      onClick={() => void switchTo(build.id)}
                    >
                      {text("model.use_build")}
                    </Button>
                    {installed && (
                      <Button
                        size="sm"
                        disabled={busy !== null || reading}
                        onClick={() => void removeSpare(build.id)}
                      >
                        {text("model.spare_remove")}
                      </Button>
                    )}
                  </>
                )
              }
            />
          );
        })}
      </GroupedSection>
      {progress !== null && (
        <div className="mt-3 flex items-center gap-3">
          <div className="min-w-0 flex-1">
            <ProgressBar value={progress} />
          </div>
          <Button size="sm" onClick={() => void invoke("stop_reading")}>
            {text("model.cancel")}
          </Button>
        </div>
      )}
      {note && (
        <p className="m-0 mt-2 text-xs leading-relaxed text-ink-mute">{note}</p>
      )}
    </>
  );
}
