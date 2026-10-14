/** Paste text read into a file: a WAV and its subtitles, where the person
 * chooses to keep them.
 *
 * The engine does the work (`export.text`): the same voice, rests and speed
 * as reading aloud, sent to a file instead of the speakers, its loudness
 * set for video and an AI-speech mark in the file's own metadata. This is
 * only the door to it and the news of how it went. Where the file goes next
 * is the person's business, not the app's.
 */
import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { save } from "@tauri-apps/plugin-dialog";
import { revealItemInDir } from "@tauri-apps/plugin-opener";
import { engineMessage, text } from "../i18n";
import { Button, ProgressBar } from "./controls";
import { asWavPath, defaultExportName } from "./exportName";

type Result = {
  stopped?: boolean;
  path?: string;
  subtitles?: string;
  seconds?: number;
};

type Finished = { id: number; ok: boolean; error?: string; result?: Result };

type Job =
  | { kind: "idle" }
  | { kind: "running"; id: number | null; done: number; total: number }
  | { kind: "done"; path: string; seconds: number }
  | { kind: "failed"; message: string };

export function ExportAudio({
  content,
  voiceId,
  voiceLabel,
  rate,
  disabled,
  cost,
  onBusyChange,
}: {
  content: string;
  voiceId: string;
  voiceLabel: string;
  rate: number;
  /** Nothing to export, or a reading is under way. */
  disabled: boolean;
  /** A paid voice's price for this text, already phrased - the same figure
   * the read button carries, shown before anything is spent. */
  cost: string | null;
  onBusyChange: (busy: boolean) => void;
}) {
  const [job, setJob] = useState<Job>({ kind: "idle" });
  const jobId = useRef<number | null>(null);
  // An answer can beat `invoke` home: a refusal (a folder that vanished)
  // comes back before the id does. Kept by id until the id is known.
  const early = useRef(new Map<number, Finished>());

  const settle = (payload: Finished) => {
    jobId.current = null;
    const result = payload.result;
    if (!payload.ok) {
      setJob({ kind: "failed", message: engineMessage(payload.error ?? "") });
    } else if (result?.stopped || !result?.path) {
      setJob({ kind: "idle" });
    } else {
      setJob({ kind: "done", path: result.path, seconds: result.seconds ?? 0 });
    }
  };

  useEffect(() => {
    onBusyChange(job.kind === "running");
  }, [job.kind, onBusyChange]);

  useEffect(() => {
    const progress = listen<{ id: number; done: number; total: number }>(
      "engine:export_progress",
      (event) => {
        if (event.payload.id !== jobId.current) return;
        setJob({ kind: "running", id: event.payload.id, done: event.payload.done, total: event.payload.total });
      },
    );
    const finished = listen<Finished>("engine:export_done", (event) => {
      if (event.payload.id !== jobId.current) {
        early.current.set(event.payload.id, event.payload);
        return;
      }
      settle(event.payload);
    });
    return () => {
      progress.then((unlisten) => unlisten());
      finished.then((unlisten) => unlisten());
    };
  }, []);

  const start = async () => {
    const chosen = await save({
      defaultPath: defaultExportName(),
      filters: [{ name: "WAV", extensions: ["wav"] }],
    });
    if (!chosen) return;
    setJob({ kind: "running", id: null, done: 0, total: 0 });
    try {
      const id = await invoke<number>("export_text", {
        text: content,
        voiceId,
        voiceLabel,
        rate,
        path: asWavPath(chosen),
      });
      jobId.current = id;
      const already = early.current.get(id);
      early.current.clear();
      if (already) settle(already);
    } catch (error) {
      setJob({ kind: "failed", message: engineMessage(error) });
    }
  };

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
        <Button size="sm" onClick={() => void invoke("stop_reading")}>
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
      <Button size="sm" disabled={disabled} onClick={() => void start()}>
        {text("export.action")}
        {cost && <span className="font-normal">· {cost}</span>}
      </Button>
    </div>
  );
}
