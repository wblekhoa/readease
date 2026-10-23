/** The small bar over a selection, or over a highlight that was pressed
 * (RE-NOTE-005 ... RE-NOTE-007): five colours, a note, and - on a highlight
 * already there - delete.
 *
 * It floats where the words are, like Books' and Preview's, and takes no
 * focus away from the page: pressing it must not drop the selection it acts
 * on, so the bar swallows its own mousedown. A highlight from Books shows no
 * colours - the next sync would paint it back.
 */
import type { CSSProperties } from "react";
import { text, type TextKey } from "../i18n";
import { Surface } from "./controls";
import { NoteIcon, TrashIcon } from "./icons";

export const HIGHLIGHT_STYLES = [3, 1, 2, 4, 5] as const;
const NAME: Record<(typeof HIGHLIGHT_STYLES)[number], TextKey> = {
  3: "highlight.style_3", 1: "highlight.style_1", 2: "highlight.style_2",
  4: "highlight.style_4", 5: "highlight.style_5",
};

export function HighlightBar({ position, current, colours, hasNote, removable, error, busy, onStyle, onNote, onRemove }: {
  position: CSSProperties;
  /** The colour of the highlight pressed; none while a selection is new. */
  current: number | null;
  colours: boolean;
  hasNote: boolean;
  removable: boolean;
  error: string | null;
  busy: boolean;
  onStyle: (style: number) => void;
  onNote: () => void;
  onRemove: () => void;
}) {
  return (
    /* z-10: over the page's words, UNDER every panel (z-20 and up) - a bar
       left from a selection sat on top of Reading settings opened after it
       (owner, 23/10: "panel setting nằm trên tooltip select"). */
    <div data-highlight-bar className="fixed z-10 w-max" style={position} onMouseDown={(event) => event.preventDefault()}>
      <Surface edge="strong" material="glass" className="peek-in flex flex-col gap-1.5 p-1.5 shadow-lifted">
        <div role="toolbar" aria-label={text("highlight.toolbar")} className="flex items-center gap-1">
          {colours && HIGHLIGHT_STYLES.map((style) => (
            <button key={style} type="button" disabled={busy}
              aria-label={text(NAME[style])} title={text(NAME[style])} aria-pressed={current === style}
              onClick={() => onStyle(style)}
              className="flex h-8 w-8 items-center justify-center rounded-full hover-wash disabled:opacity-50">
              <span data-style={style} className={`highlight-swatch h-5 w-5 rounded-full ${current === style ? "ring-2 ring-ink ring-offset-2 ring-offset-paper" : ""}`} />
            </button>
          ))}
          {colours && <span aria-hidden className="mx-0.5 h-5 w-px bg-edge-alpha" />}
          <button type="button" disabled={busy} onClick={onNote}
            className="flex h-8 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 text-sm text-ink hover-wash disabled:text-ink-faint">
            <NoteIcon className="h-4 w-4" />{text(hasNote ? "reader.note_edit" : "highlight.note")}
          </button>
          {removable && (
            <button type="button" disabled={busy} onClick={onRemove}
              aria-label={text("highlight.remove")} title={text("highlight.remove")}
              className="flex h-8 w-8 items-center justify-center rounded-full text-ink-mute hover-wash hover:text-danger disabled:text-ink-faint">
              <TrashIcon className="h-4 w-4" />
            </button>
          )}
        </div>
        {error && <p role="alert" className="m-0 max-w-[18rem] px-2 pb-1 text-xs text-danger">{error}</p>}
      </Surface>
    </div>
  );
}
