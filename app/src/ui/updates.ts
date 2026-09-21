/**
 * In-app updates (HIG 3.20): one hook over the updater plugin, with the
 * states the sheet draws. The quiet launch check is here too, so the page
 * has one place that knows whether a newer ReadEase exists.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { check, type Update } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";
import { IN_WINDOW } from "./host";

export type UpdatePhase =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "none"; version: string }
  | { kind: "available"; version: string; date: string | null; notes: string | null }
  | { kind: "downloading"; version: string; percent: number | null }
  | { kind: "installed"; version: string }
  | { kind: "failed"; message: string };

/** How long after launch the quiet check runs: after the engine and the
 * shelf, never in the way of the first thing the person came to do. */
const LAUNCH_CHECK_MS = 5000;

export function useUpdater(currentVersion: string) {
  const [phase, setPhase] = useState<UpdatePhase>({ kind: "idle" });
  /** The newer release the quiet check found, for the small notice; the
   * sheet is only opened by the person. */
  const [found, setFound] = useState<{ version: string } | null>(null);
  const [open, setOpen] = useState(false);
  const pending = useRef<Update | null>(null);

  const forget = useCallback(() => {
    void pending.current?.close().catch(() => undefined);
    pending.current = null;
  }, []);

  /** The person asked (menu, notice): every outcome is shown, errors too. */
  const checkNow = useCallback(async () => {
    setOpen(true);
    setPhase({ kind: "checking" });
    forget();
    try {
      const update = await check();
      if (!update) {
        setPhase({ kind: "none", version: currentVersion });
        setFound(null);
        return;
      }
      pending.current = update;
      setFound({ version: update.version });
      setPhase({ kind: "available", version: update.version, date: update.date ?? null, notes: update.body ?? null });
    } catch (error) {
      setPhase({ kind: "failed", message: describe(error) });
    }
  }, [currentVersion, forget]);

  /** Download, install, then offer the relaunch - never relaunch on the
   * person's behalf while they may be mid-reading. */
  const install = useCallback(async () => {
    const update = pending.current;
    if (!update) return;
    let total: number | null = null;
    let got = 0;
    setPhase({ kind: "downloading", version: update.version, percent: null });
    try {
      await update.downloadAndInstall((event) => {
        if (event.event === "Started") total = event.data.contentLength ?? null;
        else if (event.event === "Progress") {
          got += event.data.chunkLength;
          setPhase({ kind: "downloading", version: update.version, percent: total ? Math.min(100, Math.round((got / total) * 100)) : null });
        }
      });
      setPhase({ kind: "installed", version: update.version });
    } catch (error) {
      setPhase({ kind: "failed", message: describe(error) });
    }
  }, []);

  const restart = useCallback(() => { void relaunch().catch(() => undefined); }, []);

  const dismiss = useCallback(() => {
    if (phase.kind === "downloading") return; // a download in flight is not hidden
    setOpen(false);
  }, [phase.kind]);

  // The quiet check: once, a while after launch; only a find is shown.
  useEffect(() => {
    if (!IN_WINDOW) return;
    const timer = window.setTimeout(() => {
      check().then((update) => {
        if (!update) return;
        pending.current = update;
        setFound({ version: update.version });
        setPhase({ kind: "available", version: update.version, date: update.date ?? null, notes: update.body ?? null });
      }).catch(() => undefined);
    }, LAUNCH_CHECK_MS);
    return () => window.clearTimeout(timer);
  }, []);

  return { phase, found, open, checkNow, install, restart, dismiss, show: () => setOpen(true) };
}

function describe(error: unknown): string {
  if (typeof error === "string") return error;
  if (error && typeof error === "object" && "message" in error) return String((error as { message: unknown }).message);
  return String(error);
}
