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
import { save as savePanel } from "@tauri-apps/plugin-dialog";
import { engineMessage } from "../i18n";
import { audiobookName, progressFor, type ExportPhase } from "./audiobook";
import { asWavPath, defaultExportName } from "./exportName";

type Result = {
  stopped?: boolean;
  path?: string;
  subtitles?: string;
  seconds?: number;
  /** Present on a finished export: its takes stay reviewable until closed. */
  session?: string;
  retake?: boolean;
  sentences?: { index: number; text: string }[];
};
type Finished = { id: number; ok: boolean; error?: string; result?: Result };

export type ExportJob =
  | { kind: "idle" }
  | { kind: "running"; done: number; total: number; phase?: ExportPhase; title?: string; startedAt?: number; cancelling?: boolean; cancelError?: string }
  | { kind: "done"; path: string; seconds: number; title?: string; book?: boolean }
  | { kind: "cancelled"; title?: string }
  | { kind: "failed"; message: string; title?: string };

export type ExportRequest = { content: string; voiceId: string; voiceLabel: string; rate: number };

/** The last export's takes, reviewable sentence by sentence. `changed` holds
 * the sentences said again since the file was last written. */
export type ExportReview = {
  session: string;
  sentences: { index: number; text: string }[];
  retake: boolean;
  changed: number[];
  /** The sentence being said again, while the voice works on it. */
  busy: number | null;
  error: string | null;
};

export function useExport() {
  const [job, setJob] = useState<ExportJob>({ kind: "idle" });
  const [review, setReview] = useState<ExportReview | null>(null);
  const active = useRef(false);
  const context = useRef<{ title?: string; book?: boolean }>({});
  const jobId = useRef<number | null>(null);
  // An answer can beat `invoke` home: a refusal (a folder that vanished)
  // comes back before the id does. Kept by id until the id is known.
  const early = useRef(new Map<number, Finished>());
  const listeners = useRef<Promise<unknown>>(Promise.resolve());

  const settle = useCallback((payload: Finished) => {
    jobId.current = null;
    active.current = false;
    const result = payload.result;
    if (!payload.ok) {
      setJob({ kind: "failed", message: engineMessage(payload.error ?? ""), title: context.current.title });
    } else if (result?.stopped || !result?.path) {
      setJob({ kind: "cancelled", title: context.current.title });
    } else {
      setJob({ kind: "done", path: result.path, seconds: result.seconds ?? 0, ...context.current });
      // A fresh export brings its sentences and a new review; a re-save of
      // the review's file keeps the list and clears what waited to be
      // written - whether or not the answer names the session.
      const session = result.session;
      const sentences = result.sentences;
      setReview((current) => session && sentences
        ? { session, sentences, retake: Boolean(result.retake), changed: [], busy: null, error: null }
        : current && { ...current, changed: [], error: null });
    }
  }, []);

  useEffect(() => {
    const progress = listen<{ id: number; done: number; total: number; phase?: string }>(
      "engine:export_progress",
      (event) => {
        if (event.payload.id !== jobId.current) return;
        setJob(current => progressFor(current, event.payload));
      },
    );
    const finished = listen<Finished>("engine:export_done", (event) => {
      if (event.payload.id !== jobId.current) {
        if (active.current && jobId.current === null) {
          if (early.current.size >= 4) early.current.clear();
          early.current.set(event.payload.id, event.payload);
        }
        return;
      }
      settle(event.payload);
    });
    listeners.current = Promise.all([progress, finished]);
    return () => {
      progress.then((unlisten) => unlisten());
      finished.then((unlisten) => unlisten());
    };
  }, [settle]);

  const start = useCallback(async (request: ExportRequest) => {
    if (active.current) return;
    active.current = true;
    context.current = {};
    try {
      const chosen = await savePanel({
        defaultPath: defaultExportName(),
        filters: [{ name: "WAV", extensions: ["wav"] }],
      });
      if (!chosen) { active.current = false; return; }
      setJob({ kind: "running", done: 0, total: 0, startedAt: Date.now() });
      setReview(null);
      await listeners.current;
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
      active.current = false;
      jobId.current = null;
      setJob({ kind: "failed", message: engineMessage(error), title: context.current.title });
    }
  }, [settle]);

  const startBook = useCallback(async (request: {
    bookId: string; title: string; fromChapter: number; chapters: number;
    voiceId: string; voiceLabel: string; rate: number;
  }) => {
    if (active.current) return;
    active.current = true;
    context.current = { title: request.title, book: true };
    try {
      const chosen = await savePanel({ defaultPath: audiobookName(request.title), filters: [{ name: "M4B", extensions: ["m4b"] }] });
      if (!chosen) { active.current = false; return; }
      setReview(null);
      setJob({ kind: "running", done: 0, total: 0, title: request.title, startedAt: Date.now() });
      await listeners.current;
      const id = await invoke<number>("export_book", { ...request, path: /\.m4b$/i.test(chosen) ? chosen : `${chosen}.m4b` });
      jobId.current = id;
      const already = early.current.get(id);
      early.current.clear();
      if (already) settle(already);
    } catch (error) {
      active.current = false;
      jobId.current = null;
      setJob({ kind: "failed", message: engineMessage(error), title: context.current.title });
    }
  }, [settle]);

  // The reading's own stop: the engine treats an export as a reading.
  const cancel = useCallback(() => {
    setJob(current => current.kind === "running" ? { ...current, cancelling: true } : current);
    void invoke("stop_reading").catch(error => {
      // A timeout is not proof of a dead engine. Keep its job/id until
      // the actual completion/EOF event, so another export cannot queue.
      setJob(current => current.kind === "running"
        ? { ...current, cancelling: false, cancelError: engineMessage(error) } : current);
    });
  }, []);

  /** Say one sentence again; the new take replaces it in the review, and
   * reaches the file at the next `save`. */
  const retake = useCallback(async (index: number) => {
    const session = review?.session;
    if (!session) return;
    setReview((current) => current && { ...current, busy: index, error: null });
    try {
      await invoke("engine_request", { method: "export.retake", params: { session, index } });
      setReview((current) => current && {
        ...current,
        busy: null,
        changed: current.changed.includes(index) ? current.changed : [...current.changed, index],
      });
    } catch (error) {
      setReview((current) => current && { ...current, busy: null, error: engineMessage(error) });
    }
  }, [review?.session]);

  /** Write the file again from the takes as they stand. */
  const save = useCallback(async () => {
    const session = review?.session;
    if (!session || active.current) return;
    active.current = true;
    context.current = {};
    setJob({ kind: "running", done: 0, total: 0, startedAt: Date.now() });
    try {
      await listeners.current;
      const id = await invoke<number>("save_export", { session });
      jobId.current = id;
      const already = early.current.get(id);
      early.current.clear();
      if (already) settle(already);
    } catch (error) {
      active.current = false;
      jobId.current = null;
      setJob({ kind: "failed", message: engineMessage(error), title: context.current.title });
    }
  }, [review?.session, settle]);

  /** End the review: the engine drops the takes it was keeping. */
  const close = useCallback(() => {
    setReview(null);
    void invoke("engine_request", { method: "export.close", params: {} }).catch(() => undefined);
  }, []);

  return { job, start, startBook, cancel, review, retake, save, close, dismiss: () => setJob({ kind: "idle" }) };
}
