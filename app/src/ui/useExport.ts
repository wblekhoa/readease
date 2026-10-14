/** The one export in flight, owned by the whole app.
 *
 * An export outlives the Paste text screen: leave it mid-way and the engine
 * goes on writing. Kept in the screen, the job died with it - the progress
 * vanished, the read button stopped waiting, and the answer arrived for
 * nobody, so a second export could be queued behind the first. The same
 * shape `useModels` has for a download: listen once, for the whole app.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { save } from "@tauri-apps/plugin-dialog";
import { engineMessage } from "../i18n";
import { asWavPath, defaultExportName } from "./exportName";

type Result = { stopped?: boolean; path?: string; subtitles?: string; seconds?: number };
type Finished = { id: number; ok: boolean; error?: string; result?: Result };

export type ExportJob =
  | { kind: "idle" }
  | { kind: "running"; done: number; total: number }
  | { kind: "done"; path: string; seconds: number }
  | { kind: "failed"; message: string };

export type ExportRequest = { content: string; voiceId: string; voiceLabel: string; rate: number };

export function useExport() {
  const [job, setJob] = useState<ExportJob>({ kind: "idle" });
  const jobId = useRef<number | null>(null);
  // An answer can beat `invoke` home: a refusal (a folder that vanished)
  // comes back before the id does. Kept by id until the id is known.
  const early = useRef(new Map<number, Finished>());

  const settle = useCallback((payload: Finished) => {
    jobId.current = null;
    const result = payload.result;
    if (!payload.ok) {
      setJob({ kind: "failed", message: engineMessage(payload.error ?? "") });
    } else if (result?.stopped || !result?.path) {
      setJob({ kind: "idle" });
    } else {
      setJob({ kind: "done", path: result.path, seconds: result.seconds ?? 0 });
    }
  }, []);

  useEffect(() => {
    const progress = listen<{ id: number; done: number; total: number }>(
      "engine:export_progress",
      (event) => {
        if (event.payload.id !== jobId.current) return;
        setJob({ kind: "running", done: event.payload.done, total: event.payload.total });
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
  }, [settle]);

  const start = useCallback(async (request: ExportRequest) => {
    const chosen = await save({
      defaultPath: defaultExportName(),
      filters: [{ name: "WAV", extensions: ["wav"] }],
    });
    if (!chosen) return;
    setJob({ kind: "running", done: 0, total: 0 });
    try {
      const id = await invoke<number>("export_text", {
        text: request.content,
        voiceId: request.voiceId,
        voiceLabel: request.voiceLabel,
        rate: request.rate,
        path: asWavPath(chosen),
      });
      jobId.current = id;
      const already = early.current.get(id);
      early.current.clear();
      if (already) settle(already);
    } catch (error) {
      setJob({ kind: "failed", message: engineMessage(error) });
    }
  }, [settle]);

  // The reading's own stop: the engine treats an export as a reading.
  const cancel = useCallback(() => void invoke("stop_reading"), []);

  return { job, start, cancel };
}
