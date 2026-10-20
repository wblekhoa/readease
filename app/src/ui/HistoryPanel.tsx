/** Paste or scan history, and the two settings that govern it (RE-HIST-001…004).
 *
 * Opened from the screen whose history it is. The list is that screen's
 * kind; the switch, the days and "delete all" cover both, because they are
 * one setting in the engine and the reader should not have to set it twice.
 */
import { currentLanguage, text } from "../i18n";
import { Button, IconButton, Select, Surface, Switch } from "./controls";
import { CloseIcon, TrashIcon } from "./icons";
import { HISTORY_DAYS, type HistoryEntry, type HistoryKind } from "./readingHistory";
import { summarise } from "./scanHistory";

export function HistoryPanel({ kind, entries, enabled, days, onOpen, onDelete, onClearAll, onEnabled, onDays, onClose }: {
  kind: HistoryKind;
  entries: readonly HistoryEntry[];
  enabled: boolean;
  days: number;
  onOpen: (entry: HistoryEntry) => void;
  onDelete: (entry: HistoryEntry) => void;
  onClearAll: () => void;
  onEnabled: (enabled: boolean) => void;
  onDays: (days: number) => void;
  onClose: () => void;
}) {
  const mine = entries.filter(entry => entry.kind === kind);
  const date = new Intl.DateTimeFormat(currentLanguage(), { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  return (
    <Surface
      edge="strong"
      radius="sheet"
      dialog={text("history.title")}
      layer="popover"
      className="absolute bottom-[calc(var(--shell-bottom-inner)+var(--layer-gap))] left-6 z-30 flex layer-capped w-[30rem] max-w-[calc(100vw-3rem)] origin-bottom-left flex-col overflow-hidden shadow-lifted"
    >
      <div className="flex items-start gap-3 px-5 pb-3 pt-4">
        <div className="min-w-0 flex-1">
          <h3 className="m-0 text-base font-bold">{text(kind === "paste" ? "history.paste_title" : "history.scan_title")}</h3>
          <p className="m-0 mt-1 text-xs text-ink-mute">{text("history.caption")}</p>
        </div>
        <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}><CloseIcon /></IconButton>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-edge px-5 py-3 text-sm">
        <span className="flex items-center gap-2">
          <Switch checked={enabled} onChange={onEnabled} label={text("history.keep")} />
          <span aria-hidden="true">{text("history.keep")}</span>
        </span>
        <span className="ml-auto flex items-center gap-2 text-ink-mute">
          <span id="history-days-label">{text("history.days")}</span>
          <Select labelledBy="history-days-label" value={days} disabled={!enabled}
            onChange={event => onDays(Number(event.target.value))}>
            {HISTORY_DAYS.map(value => (
              <option key={value} value={value}>{value ? text("history.days_n", { days: value }) : text("history.days_forever")}</option>
            ))}
          </Select>
        </span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto border-t border-edge px-3 py-1">
        {mine.length === 0 && (
          <p className="m-0 px-2 py-4 text-sm text-ink-mute">{text(enabled ? "history.empty" : "history.off")}</p>
        )}
        <ul className="m-0 list-none p-0">
          {mine.map(entry => (
            <li key={entry.id} className="flex items-center gap-2 border-b border-edge last:border-b-0">
              <Button variant="ghost" onClick={() => onOpen(entry)}
                aria-label={text("history.open", { title: summarise(entry.text, 60) })}
                className="!h-auto min-w-0 flex-1 !justify-start !px-2 !py-2 text-left">
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm text-ink">{summarise(entry.text, 120)}</span>
                  <span className="mt-0.5 block truncate text-xs text-ink-mute">
                    {date.format(entry.at)}{entry.target ? ` · ${text("home.translated", { language: entry.target.toUpperCase() })}` : ""}
                  </span>
                </span>
              </Button>
              <IconButton onClick={() => onDelete(entry)}
                aria-label={text("history.delete", { title: summarise(entry.text, 40) })}
                title={text("history.delete", { title: summarise(entry.text, 40) })}>
                <TrashIcon />
              </IconButton>
            </li>
          ))}
        </ul>
      </div>
      <div className="flex items-center justify-end border-t border-edge px-5 py-2.5">
        <Button variant="ghost" size="sm" disabled={entries.length === 0} onClick={onClearAll}>{text("history.clear_all")}</Button>
      </div>
    </Surface>
  );
}
