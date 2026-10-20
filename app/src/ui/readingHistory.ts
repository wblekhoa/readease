/** Paste and scan history kept on this Mac (RE-HIST-001…004).
 *
 * The engine owns the store (`storage/history.py`) and both settings; this
 * module only asks it, and turns what it answers into what the screens
 * already show. Saving never blocks a reading: a failed save is dropped.
 */
import { invoke } from "@tauri-apps/api/core";
import type { ExternalEntry } from "./ScanEntry";

export type HistoryKind = "paste" | "scan";
export type HistoryEntry = {
  id: number; kind: HistoryKind; text: string;
  original: string | null; target: string | null; at: number;
};
export type HistoryState = { enabled: boolean; days: number; entries: HistoryEntry[] };

/** Retention choices, as the engine accepts them; 0 keeps until deleted. */
export const HISTORY_DAYS = [7, 30, 90, 365, 0] as const;
export const DEFAULT_HISTORY_DAYS = 30;

type Reply<T> = { result: T };
const ask = <T>(method: string, params: Record<string, unknown> = {}) =>
  invoke<Reply<T>>("engine_request", { method, params }).then(reply => reply.result);

export function loadHistory(): Promise<HistoryState> {
  // Shaped here, so an older engine or a partial answer can never take a
  // screen down: no list is an empty list, not an exception.
  return ask<Partial<HistoryState> | null | undefined>("history.list").then(reply => ({
    enabled: reply?.enabled !== false,
    days: typeof reply?.days === "number" ? reply.days : DEFAULT_HISTORY_DAYS,
    entries: Array.isArray(reply?.entries) ? reply.entries : [],
  }));
}

export function saveHistory(kind: HistoryKind, text: string, extra: { original?: string; target?: string } = {}): Promise<HistoryEntry | null> {
  if (!text.trim()) return Promise.resolve(null);
  return ask<{ saved: boolean; entry?: HistoryEntry }>("history.add", { kind, text, ...extra })
    .then(reply => (reply.saved && reply.entry ? reply.entry : null))
    .catch(() => null);
}

export function deleteHistory(id: number): Promise<boolean> {
  return ask<{ deleted: boolean }>("history.delete", { id }).then(reply => reply.deleted);
}

export function clearHistory(kind?: HistoryKind): Promise<number> {
  return ask<{ deleted: number }>("history.clear", kind ? { kind } : {}).then(reply => reply.deleted);
}

export function setHistorySetting(key: "history_enabled" | "history_days", value: boolean | number): Promise<unknown> {
  return invoke("engine_request", { method: "config.set", params: { key, value } });
}

/** A stored scan as the Scan screen's entry. */
export function toCapture(entry: HistoryEntry): ExternalEntry {
  return {
    at: entry.at, text: entry.text,
    ...(entry.original ? { original: entry.original } : {}),
    ...(entry.target ? { target: entry.target } : {}),
  };
}

/** This session's captures first, then stored ones not already among them
 * (the same passage read again this session is one entry, not two). */
export function mergeCaptures(session: readonly ExternalEntry[], stored: readonly HistoryEntry[] = [], limit = 50): ExternalEntry[] {
  const seen = new Set(session.map(entry => `${entry.original ?? ""}\u0000${entry.text}`));
  const older = stored
    .filter(entry => entry.kind === "scan")
    .map(toCapture)
    .filter(entry => !seen.has(`${entry.original ?? ""}\u0000${entry.text}`));
  return [...session, ...older].sort((a, b) => b.at - a.at).slice(0, limit);
}

/** The newest stored entry of a kind moved to the top, or added. */
export function withEntry(entries: readonly HistoryEntry[], entry: HistoryEntry): HistoryEntry[] {
  return [entry, ...entries.filter(other => other.id !== entry.id)];
}
