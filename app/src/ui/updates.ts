/** RE-UPDATE-001: one session shared by the sidebar, menu and non-modal detail popover. */
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { check } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { UpdateFlow } from "./updateFlow";
export type { UpdatePhase } from "./updateFlow";
export type UpdateSignal = { kind: "none" } | { kind: "available" | "ready"; version: string };
const SKIPPED_KEY = "readease.update.skipped";
const AUTO_KEY = "readease.update.auto";
function stored(key: string): string | null { try { return localStorage.getItem(key); } catch { return null; } }
function remember(key: string, value: string | null) {
  try { value === null ? localStorage.removeItem(key) : localStorage.setItem(key, value); } catch { /* private window */ }
}
export function useUpdater(currentVersion: string, canApply: () => boolean) {
  const guard = useRef(canApply); guard.current = canApply;
  const [flow] = useState(() => new UpdateFlow({ check, relaunch, arm: armed => invoke("set_install_on_quit", { armed }), canApply: () => guard.current() }));
  const { phase, onQuit } = useSyncExternalStore(flow.subscribe, flow.snapshot);
  const [open, setOpen] = useState(false);
  const [auto, setAutoState] = useState(() => stored(AUTO_KEY) === "1");
  const checkNow = useCallback(async () => { setOpen(true); await flow.check(currentVersion); }, [flow, currentVersion]);
  const dismiss = useCallback(() => { setOpen(false); }, []);
  const skip = useCallback(async () => {
    const skipped = await flow.skip();
    if (skipped) { remember(SKIPPED_KEY, skipped); setOpen(false); }
  }, [flow]);
  const setAuto = useCallback((value: boolean) => { setAutoState(value); remember(AUTO_KEY, value ? "1" : null); }, []);
  const retry = useCallback(async () => {
    if (phase.kind !== "failed") return;
    if (phase.recovery === "check") await flow.check(currentVersion);
    else if (phase.recovery === "download") await flow.download();
    else if (phase.recovery === "schedule") await flow.installOnQuit();
    else await flow.installAndRestart();
  }, [flow, currentVersion, phase]);
  useEffect(() => {
    if (!("__TAURI_INTERNALS__" in window) || (window.__READEASE_MOCK__ && !new URLSearchParams(location.search).has("update"))) return;
    const timer = window.setTimeout(async () => {
      await flow.check(currentVersion, stored(SKIPPED_KEY));
      if (flow.snapshot().phase.kind === "available" && stored(AUTO_KEY) === "1") await flow.installOnQuit();
    }, 5000);
    return () => window.clearTimeout(timer);
  }, [flow, currentVersion]);
  useEffect(() => {
    if (!("__TAURI_INTERNALS__" in window)) return;
    const heard = listen("update:install-now", async () => {
      try { if (await flow.applyOnQuit()) await invoke("exit_now"); }
      catch (cause) { console.error("[update] quit", cause); }
    });
    return () => { heard.then(unlisten => unlisten()).catch(() => undefined); };
  }, [flow]);
  const signal: UpdateSignal = phase.kind === "ready" || onQuit
    ? { kind: "ready", version: "version" in phase ? phase.version : "" }
    : ["available", "downloading", "installing", "installed"].includes(phase.kind)
      ? { kind: "available", version: "version" in phase ? phase.version : "" } : { kind: "none" };
  return { phase, open, auto, onQuit, signal, checkNow, skip, setAuto, retry, dismiss,
    download: () => flow.download(), installNow: () => flow.installAndRestart(),
    installOnQuit: () => flow.installOnQuit(), restart: () => flow.installAndRestart(),
    show: () => setOpen(value => !value) };
}
