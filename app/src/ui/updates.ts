/**
 * In-app updates (HIG 3.20): one hook over the updater plugin, with the
 * states the sheet draws and the behaviours a Mac expects of Sparkle -
 * skip a version, later, install when quitting, automatic download.
 * The quiet launch check is here too, so the page has one place that
 * knows whether a newer ReadEase exists and how far it has come.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { check, type Update } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { IN_WINDOW } from "./host";

export type UpdatePhase =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "none"; version: string }
  | { kind: "available"; version: string; date: string | null; notes: string | null }
  | { kind: "downloading"; version: string; percent: number | null }
  /** Downloaded, not yet installed: the person chooses when. */
  | { kind: "ready"; version: string; date: string | null; notes: string | null }
  | { kind: "installing"; version: string }
  | { kind: "installed"; version: string }
  | { kind: "failed"; message: string };

/** What the menu bar says beside "Kiểm tra bản mới…" (HIG 3.20): the
 * standing indicator that replaced the floating notice. */
export type UpdateSignal =
  | { kind: "none" }
  | { kind: "available"; version: string }
  | { kind: "ready"; version: string };

/** How long after launch the quiet check runs: after the engine and the
 * shelf, never in the way of the first thing the person came to do. */
const LAUNCH_CHECK_MS = 5000;
const SKIPPED_KEY = "readease.update.skipped";
const AUTO_KEY = "readease.update.auto";

function stored(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}
function remember(key: string, value: string | null) {
  try { value === null ? localStorage.removeItem(key) : localStorage.setItem(key, value); } catch { /* private window */ }
}

export function useUpdater(currentVersion: string) {
  const [phase, setPhase] = useState<UpdatePhase>({ kind: "idle" });
  const [open, setOpen] = useState(false);
  /** Automatic download, the person's choice; off until they say so. */
  const [auto, setAutoState] = useState(() => stored(AUTO_KEY) === "1");
  /** The update will be installed as the app quits. */
  const [onQuit, setOnQuitState] = useState(false);
  const pending = useRef<Update | null>(null);
  const downloaded = useRef(false);

  const forget = useCallback(() => {
    void pending.current?.close().catch(() => undefined);
    pending.current = null;
    downloaded.current = false;
  }, []);

  const found = useCallback((update: Update, ready: boolean) => {
    pending.current = update;
    downloaded.current = ready;
    const info = { version: update.version, date: update.date ?? null, notes: update.body ?? null };
    setPhase(ready ? { kind: "ready", ...info } : { kind: "available", ...info });
  }, []);

  const download = useCallback(async (): Promise<boolean> => {
    const update = pending.current;
    if (!update) return false;
    if (downloaded.current) return true;
    let total: number | null = null;
    let got = 0;
    setPhase({ kind: "downloading", version: update.version, percent: null });
    try {
      await update.download((event) => {
        if (event.event === "Started") total = event.data.contentLength ?? null;
        else if (event.event === "Progress") {
          got += event.data.chunkLength;
          setPhase({ kind: "downloading", version: update.version, percent: total ? Math.min(100, Math.round((got / total) * 100)) : null });
        }
      });
      downloaded.current = true;
      setPhase({ kind: "ready", version: update.version, date: update.date ?? null, notes: update.body ?? null });
      return true;
    } catch (error) {
      setPhase({ kind: "failed", message: describe(error) });
      return false;
    }
  }, []);

  /** The person asked (menu): every outcome is shown, errors too, and a
   * skipped version is offered again - they asked. */
  const checkNow = useCallback(async () => {
    setOpen(true);
    if (pending.current) return; // already known: the sheet shows its state
    setPhase({ kind: "checking" });
    try {
      const update = await check();
      if (!update) { setPhase({ kind: "none", version: currentVersion }); return; }
      found(update, false);
    } catch (error) {
      setPhase({ kind: "failed", message: describe(error) });
    }
  }, [currentVersion, found]);

  /** Download now, install now, then offer the relaunch - never relaunch
   * on the person's behalf while they may be mid-reading. */
  const installNow = useCallback(async () => {
    const update = pending.current;
    if (!update) return;
    if (!(await download())) return;
    setPhase({ kind: "installing", version: update.version });
    try {
      await update.install();
      setOnQuitState(false);
      void invoke("set_install_on_quit", { armed: false }).catch(() => undefined);
      setPhase({ kind: "installed", version: update.version });
    } catch (error) {
      setPhase({ kind: "failed", message: describe(error) });
    }
  }, [download]);

  /** Download now, install as the app quits: nothing interrupts a reading. */
  const installOnQuit = useCallback(async () => {
    if (!(await download())) return;
    setOnQuitState(true);
    void invoke("set_install_on_quit", { armed: true }).catch(() => undefined);
    setOpen(false);
  }, [download]);

  /** Sparkle's "Skip This Version": the quiet check stays silent about it. */
  const skip = useCallback(() => {
    const version = pending.current?.version;
    if (version) remember(SKIPPED_KEY, version);
    forget();
    setPhase({ kind: "idle" });
    setOpen(false);
  }, [forget]);

  const setAuto = useCallback((value: boolean) => {
    setAutoState(value);
    remember(AUTO_KEY, value ? "1" : null);
  }, []);

  const restart = useCallback(() => { void relaunch().catch(() => undefined); }, []);

  const dismiss = useCallback(() => {
    if (phase.kind === "downloading" || phase.kind === "installing") return; // work in flight is not hidden
    setOpen(false);
  }, [phase.kind]);

  // The quiet check: once, a while after launch; a skipped version is
  // passed over; with automatic download on, the archive comes down now
  // and is installed as the app quits - the sheet then says "ready".
  useEffect(() => {
    if (!IN_WINDOW) return;
    let live = true;
    const timer = window.setTimeout(() => {
      check().then(async (update) => {
        if (!live || !update) return;
        if (stored(SKIPPED_KEY) === update.version) { void update.close().catch(() => undefined); return; }
        found(update, false);
        if (stored(AUTO_KEY) === "1") {
          if (await download()) {
            setOnQuitState(true);
            void invoke("set_install_on_quit", { armed: true }).catch(() => undefined);
          }
        }
      }).catch(() => undefined);
    }, LAUNCH_CHECK_MS);
    return () => { live = false; window.clearTimeout(timer); };
  }, [download, found]);

  // The host is quitting with an install waiting (HIG 3.20): install, then
  // tell it to leave. The host's own 60 s net covers a page that cannot.
  useEffect(() => {
    if (!IN_WINDOW) return;
    const heard = listen("update:install-now", async () => {
      const update = pending.current;
      try { if (update && downloaded.current) await update.install(); } catch (error) { console.error("[update] install on quit", error); }
      void invoke("exit_now").catch(() => undefined);
    });
    return () => { heard.then((unlisten) => unlisten()).catch(() => undefined); };
  }, []);

  const signal: UpdateSignal =
    phase.kind === "ready" || onQuit
      ? { kind: "ready", version: pending.current?.version ?? "" }
      : phase.kind === "available" || phase.kind === "downloading" || phase.kind === "installed"
        ? { kind: "available", version: pending.current?.version ?? "" }
        : { kind: "none" };

  return { phase, open, auto, onQuit, signal, checkNow, installNow, installOnQuit, skip, setAuto, restart, dismiss, show: () => setOpen(true) };
}

function describe(error: unknown): string {
  if (typeof error === "string") return error;
  if (error && typeof error === "object" && "message" in error) return String((error as { message: unknown }).message);
  return String(error);
}
