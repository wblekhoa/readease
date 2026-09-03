import { useEffect, useState } from "react";
import {
  checkAccessibilityPermission,
  requestAccessibilityPermission,
} from "tauri-plugin-macos-permissions-api";
import { openUrl } from "@tauri-apps/plugin-opener";
import { text, type TextKey } from "../i18n";
import { Button, Kbd, Notice, SectionTitle, Surface } from "../ui/controls";
import { ListRow } from "../ui/patterns";
import { comboFromEvent, displayShortcut } from "../ui/useShortcut";

export type ExternalEntry = { at: number; text: string };

const ACCESSIBILITY_PANE =
  "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility";

export function External({
  history,
  status,
  shortcut,
  onChangeShortcut,
  onReplay,
  onClearHistory,
}: {
  history: ExternalEntry[];
  status: string | null;
  shortcut: string;
  onChangeShortcut: (accelerator: string) => Promise<void>;
  onReplay: (entry: ExternalEntry) => void;
  onClearHistory: () => void;
}) {
  const [granted, setGranted] = useState<boolean | null>(null);
  const [asked, setAsked] = useState(false);
  const [recording, setRecording] = useState(false);
  const [shortcutError, setShortcutError] = useState(false);

  useEffect(() => {
    if (!recording) return;
    const onKey = (event: KeyboardEvent) => {
      event.preventDefault();
      event.stopPropagation();
      if (event.key === "Escape") {
        setRecording(false);
        return;
      }
      const combo = comboFromEvent(event);
      if (!combo) return;
      setRecording(false);
      setShortcutError(false);
      onChangeShortcut(combo).catch(() => setShortcutError(true));
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [recording, onChangeShortcut]);

  useEffect(() => {
    checkAccessibilityPermission().then(setGranted).catch(() => setGranted(null));
  }, []);

  const statusMessage =
    status && status !== "reading"
      ? text(`status.${status}` as TextKey)
      : status === "reading"
        ? text("external.reading")
        : null;

  return (
    <section className="shell-inset flex min-h-0 flex-1 gap-10">
      <div className="max-w-[52ch]">
        <SectionTitle>{text("external.title")}</SectionTitle>
        {granted === false && (
          <Surface className="mt-5 p-4">
            <p className="m-0 text-sm leading-relaxed text-ink-mute">
              {text("external.permission_note")}
            </p>
            <div className="mt-3 flex gap-2">
              <Button
                variant="primary"
                onClick={() => {
                  setAsked(true);
                  void requestAccessibilityPermission();
                }}
              >
                {text("external.open_settings")}
              </Button>
              <Button className="px-3" onClick={() => void openUrl(ACCESSIBILITY_PANE)}>
                {text("external.open_system_settings")}
              </Button>
            </div>
            {asked && (
              <p className="m-0 mt-3 text-sm font-medium">
                {text("external.permission_restart")}
              </p>
            )}
          </Surface>
        )}
        <div className="mt-4 flex items-center gap-3">
          <span className="text-sm font-semibold text-ink-mute">
            {text("external.shortcut")}
          </span>
          {recording ? (
            <span className="text-sm text-ink-mute">
              {text("external.shortcut_recording")}
            </span>
          ) : (
            <Kbd>{displayShortcut(shortcut)}</Kbd>
          )}
          <Button size="sm" onClick={() => setRecording((value) => !value)}>
            {text("external.shortcut_change")}
          </Button>
        </div>
        {recording && (
          <p className="m-0 mt-2 max-w-[48ch] text-sm text-ink-mute">
            {text("external.shortcut_hint")}
          </p>
        )}
        {shortcutError && (
          <Notice tone="error" className="mt-2 max-w-[48ch]">
            {text("external.shortcut_taken")}
          </Notice>
        )}

        <p className="m-0 mt-5 whitespace-pre-line text-xs leading-relaxed text-ink-mute">
          {text("external.steps")}
        </p>
        {granted === true && (
          <p className="m-0 mt-4 text-sm text-ink-mute">
            {text("external.permission_granted")}
          </p>
        )}

        {statusMessage && (
          <Notice tone="error" className="mt-4 max-w-[52ch]">
            {statusMessage}
          </Notice>
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-3">
          <h3 className="m-0 flex-1 text-sm font-bold">
            {text("external.recent_title")}
          </h3>
          {/* The Qt shell could empty this list; the rewrite dropped the
              action until the parity audit found it (2026-09-02). */}
          {history.length > 0 && (
            <Button variant="ghost" size="sm" onClick={onClearHistory}>
              {text("external.history_clear")}
            </Button>
          )}
        </div>
        {history.length === 0 ? (
          <p className="m-0 mt-2 text-sm text-ink-mute">
            {text("external.history_empty")}
          </p>
        ) : (
          <div className="mt-2 flex max-h-full flex-col gap-1 overflow-y-auto">
            {history.map((entry) => (
              <ListRow
                key={entry.at}
                onPress={() => onReplay(entry)}
                title={
                  <span
                    className="line-clamp-2 text-sm leading-snug"
                    title={text("external.replay")}
                  >
                    {entry.text}
                  </span>
                }
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
