/** How a written word is said: the reader's own list.
 *
 * A voice reads a brand, an acronym or an English word inside Vietnamese by
 * its own guess; this is where the reader writes the word and how it should
 * sound. The engine applies the list to every reading - books, pasted text,
 * a selection, an export - at the next press of Read; what is shown on the
 * page and in subtitles stays as written. Each change is saved at once.
 */
import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { text } from "../i18n";
import { Button, IconButton, Input, Surface } from "./controls";
import { CloseIcon, TrashIcon } from "./icons";
import { Scrim, SettingsPage, useDismiss } from "./patterns";
import {
  MAX_SPOKEN,
  MAX_WRITTEN,
  readPronunciations,
  withPronunciation,
  withoutPronunciation,
  type Pronunciation,
} from "./pronunciations";

const KEY = "pronunciations";

export function PronunciationsPanel({
  onChanged,
  onClose,
  presentation = "popover",
}: {
  /** Over its footer button, centred over a scrim, or a page of its own
   * from the side column (owner, 22/10). */
  presentation?: "popover" | "sheet" | "page";
  /** The list changed: a price that counted the old words is stale. */
  onChanged: () => void;
  onClose: () => void;
}) {
  // Centred, it is a dialog: Esc or a click outside closes it.
  const centered = presentation === "sheet";
  const layer = useDismiss(onClose, centered);
  const [list, setList] = useState<Pronunciation[] | null>(null);
  const [written, setWritten] = useState("");
  const [spoken, setSpoken] = useState("");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    invoke<{ result: { value: unknown } }>("engine_request", { method: "config.get", params: { key: KEY } })
      .then((reply) => setList(readPronunciations(reply.result.value)))
      .catch(() => setList([]));
  }, []);

  const store = (next: Pronunciation[]) => {
    setList(next);
    invoke("engine_request", { method: "config.set", params: { key: KEY, value: next } })
      .then(() => {
        setFailed(false);
        onChanged();
      })
      .catch(() => setFailed(true));
  };

  const next = list === null ? null : withPronunciation(list, written, spoken);
  const add = () => {
    if (next === null) return;
    store(next);
    setWritten("");
    setSpoken("");
  };

  const form = (<>
      <form
        className="flex items-center gap-2 pb-3"
        onSubmit={(event) => {
          event.preventDefault();
          add();
        }}
      >
        <Input
          className="min-w-0 flex-1"
          value={written}
          maxLength={MAX_WRITTEN}
          placeholder={text("pronounce.written")}
          aria-label={text("pronounce.written")}
          onChange={(event) => setWritten(event.target.value)}
        />
        <span aria-hidden="true" className="text-ink-mute">→</span>
        <Input
          className="min-w-0 flex-1"
          value={spoken}
          maxLength={MAX_SPOKEN}
          placeholder={text("pronounce.spoken")}
          aria-label={text("pronounce.spoken")}
          onChange={(event) => setSpoken(event.target.value)}
        />
        <Button type="submit" size="sm" disabled={next === null}>
          {text("pronounce.add")}
        </Button>
      </form>
      {failed && (
        <p role="alert" className="m-0 pb-2 text-xs text-danger">{text("pronounce.failed")}</p>
      )}
  </>);
  const entries = (<>
        {list !== null && list.length === 0 && (
          <p className="m-0 py-3 text-sm text-ink-mute">{text("pronounce.empty")}</p>
        )}
        <ul className="m-0 list-none p-0">
          {(list ?? []).map((entry) => (
            <li key={entry.written} className="flex items-center gap-3 border-b border-edge py-2 last:border-b-0">
              <span className="min-w-0 flex-1 truncate text-sm font-semibold">{entry.written}</span>
              <span aria-hidden="true" className="text-ink-mute">→</span>
              <span className="min-w-0 flex-1 truncate text-sm">{entry.spoken}</span>
              <IconButton
                onClick={() => list && store(withoutPronunciation(list, entry.written))}
                aria-label={text("pronounce.remove", { word: entry.written })}
                title={text("pronounce.remove", { word: entry.written })}
              >
                <TrashIcon />
              </IconButton>
            </li>
          ))}
        </ul>
  </>);

  if (presentation === "page") return (
    <SettingsPage caption={text("pronounce.caption")}>
      {form}
      {/* The list as a card, like the other settings pages' groups. */}
      <div className="mt-2 rounded-2xl border border-edge-alpha bg-[var(--app-card)] px-4 py-1">{entries}</div>
    </SettingsPage>
  );

  return (<>
    {centered && <Scrim />}
    <Surface
      ref={layer}
      edge="strong"
      radius="sheet"
      dialog={text("pronounce.title")}
      layer="popover"
      modal={centered}
      className={centered
        ? "fixed left-1/2 top-1/2 z-40 flex max-h-[84%] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden shadow-lifted w-[32rem] max-w-[calc(100vw-3rem)]"
        : "absolute bottom-[calc(var(--shell-bottom-inner)+var(--layer-gap))] right-6 z-30 flex layer-capped w-[32rem] max-w-[calc(100vw-3rem)] origin-bottom-right flex-col overflow-hidden shadow-lifted"}
    >
      <div className="flex items-start gap-3 px-6 pb-3 pt-5">
        <div className="min-w-0 flex-1">
          <h2 className="m-0 text-base font-bold">{text("pronounce.title")}</h2>
          <p className="m-0 mt-1 text-xs text-ink-mute">{text("pronounce.caption")}</p>
        </div>
        <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>
      <div className="px-6">{form}</div>
      <div className="min-h-0 flex-1 overflow-y-auto border-t border-edge px-6 py-2">
        {entries}
      </div>
    </Surface>
  </>);
}
