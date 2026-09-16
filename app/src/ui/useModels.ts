/** The two models on this Mac, and any download in flight - one owner.
 *
 * Three places show the same facts (the first-run screen, the hub on the
 * home screen, the settings panel's empty tab) and any of them can start a
 * download; each used to keep its own copy of "what is installed" and
 * "what is being fetched", so a download started in one was invisible from
 * the others and a panel closed over a running download forgot it. The
 * engine's progress arrives as events, and the completion as an orphan
 * reply (a download outlives any sane request timeout), so this listens
 * once for the whole app.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { engineMessage, text } from "../i18n";
import type { Language, ModelStatus } from "./readingSources";

export type ModelJob = {
  /** Which language's model, when this app started the download; null for
   * one already running when the app looked (the message says which). */
  target: Language | null;
  progress: number | null;
  message: string | null;
};

export type Models = {
  status: ModelStatus | null;
  setStatus: (status: ModelStatus) => void;
  refresh: () => void;
  job: ModelJob | null;
  /** The last outcome worth a sentence - a cancellation, a failure - until
   * the next action clears it. */
  note: string | null;
  downloadVietnamese: (precision: string) => Promise<void>;
  downloadEnglish: () => Promise<void>;
  cancel: () => void;
  removeVietnamese: (precision: string) => Promise<void>;
  removeEnglish: () => Promise<void>;
};

export function useModels(): Models {
  const [status, setStatus] = useState<ModelStatus | null>(null);
  const [job, setJob] = useState<ModelJob | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const refresh = useCallback(() => {
    invoke<{ result: ModelStatus }>("engine_request", { method: "model.status", params: {} })
      .then((reply) => setStatus(reply.result))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const progress = listen<{ progress: number; message: string }>(
      "engine:model_progress",
      (event) => {
        setJob((current) => ({
          target: current?.target ?? null,
          progress: event.payload.progress,
          message: event.payload.message,
        }));
      },
    );
    const finished = listen<{ ok: boolean; error?: string; result?: { cancelled?: boolean } }>(
      "engine:orphan_reply",
      (event) => {
        setJob(null);
        setNote(
          event.payload.result?.cancelled
            ? text("model.cancelled")
            : event.payload.ok
              ? null
              : event.payload.error ?? null,
        );
        refresh();
      },
    );
    return () => {
      progress.then((unlisten) => unlisten());
      finished.then((unlisten) => unlisten());
    };
  }, [refresh]);

  const downloadVietnamese = useCallback(async (precision: string) => {
    setNote(null);
    setJob({ target: "vi", progress: null, message: text("model.preparing") });
    try {
      // The build loads at construction, so another build means another
      // engine process; the download then runs INSIDE the new process, so
      // the bytes land where it will look for them.
      if (precision !== status?.precision) {
        await invoke("engine_request", {
          method: "model.set_precision",
          params: { precision },
        });
        setJob({ target: "vi", progress: null, message: text("model.restarting") });
        await invoke("restart_engine");
        setJob({ target: "vi", progress: null, message: text("model.preparing") });
      }
      await invoke("prepare_model");
    } catch (error) {
      setNote(engineMessage(error));
      setJob(null);
    }
  }, [status?.precision]);

  const downloadEnglish = useCallback(async () => {
    setNote(null);
    setJob({ target: "en", progress: null, message: text("model.english_downloading") });
    try {
      await invoke("prepare_model", { model: "english" });
    } catch (error) {
      setNote(engineMessage(error));
      setJob(null);
    }
  }, []);

  // The download's own word (16/09). It used to be the reading's stop,
  // which also served a Dừng pressed while a download ran - and cancelled
  // the download nobody meant to cancel. The engine answers from inside
  // the download, and the orphan reply then says "cancelled".
  const cancel = useCallback(() => {
    void invoke("engine_request", { method: "model.cancel", params: {} }).catch(() => undefined);
  }, []);

  const removeVietnamese = useCallback(async (precision: string) => {
    setNote(null);
    try {
      await invoke("engine_request", { method: "model.remove_build", params: { precision } });
    } catch (error) {
      setNote(engineMessage(error));
    }
    refresh();
  }, [refresh]);

  const removeEnglish = useCallback(async () => {
    setNote(null);
    try {
      await invoke("engine_request", { method: "model.remove_build", params: { engine: "english" } });
    } catch (error) {
      setNote(engineMessage(error));
    }
    refresh();
  }, [refresh]);

  return useMemo(() => ({
    status, setStatus, refresh, job, note,
    downloadVietnamese, downloadEnglish, cancel, removeVietnamese, removeEnglish,
  }), [status, refresh, job, note, downloadVietnamese, downloadEnglish, cancel, removeVietnamese, removeEnglish]);
}
