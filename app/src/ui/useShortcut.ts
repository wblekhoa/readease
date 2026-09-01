/** The selection shortcut: display form, recorder, persistence. */
import { useCallback, useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";

const CONFIG_KEY = "tauri_selection_shortcut";
export const DEFAULT_SHORTCUT = "alt+super+r";

/** "alt+super+r" -> "Option + Command + R" */
export function displayShortcut(accelerator: string): string {
  const NAMES: Record<string, string> = {
    control: "Control", ctrl: "Control",
    alt: "Option", option: "Option",
    super: "Command", cmd: "Command", command: "Command", meta: "Command",
    shift: "Shift",
  };
  return accelerator
    .split("+")
    .map((part) => NAMES[part.toLowerCase()] ?? part.toUpperCase())
    .join(" + ");
}

export function comboFromEvent(event: KeyboardEvent): string | null {
  if (!event.ctrlKey && !event.altKey && !event.metaKey) return null;
  const code = event.code;
  let key: string | null = null;
  if (/^Key[A-Z]$/.test(code)) key = code.slice(3).toLowerCase();
  else if (/^Digit[0-9]$/.test(code)) key = code.slice(5);
  else if (/^F[0-9]{1,2}$/.test(code)) key = code;
  if (!key) return null;
  const parts = [];
  if (event.ctrlKey) parts.push("control");
  if (event.altKey) parts.push("alt");
  if (event.shiftKey) parts.push("shift");
  if (event.metaKey) parts.push("super");
  parts.push(key);
  return parts.join("+");
}

export function useShortcut() {
  const [accelerator, setAccelerator] = useState(DEFAULT_SHORTCUT);

  useEffect(() => {
    invoke<{ result: { value: string | null } }>("engine_request", {
      method: "config.get",
      params: { key: CONFIG_KEY },
    })
      .then((reply) => {
        if (reply.result.value) setAccelerator(reply.result.value);
      })
      .catch(() => undefined);
  }, []);

  const change = useCallback(async (next: string) => {
    // Register first: a combination the OS refuses must never be saved as
    // the one the app will silently fail to register on next launch.
    await invoke("set_selection_shortcut", { accelerator: next });
    await invoke("engine_request", {
      method: "config.set",
      params: { key: CONFIG_KEY, value: next },
    });
    setAccelerator(next);
  }, []);

  return { accelerator, change };
}
