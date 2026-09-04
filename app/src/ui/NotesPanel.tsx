/** Everything marked in this book, in one place.
 *
 * A highlight in the text says only that something was marked; the note
 * behind it lived in a native `title` tooltip, which is slow to appear,
 * truncates, and cannot be read on a touch screen. So the note is shown in
 * full here, and this doubles as the list of what the book carries (owner,
 * 03/09: "xem được note của user, có nơi để quản lý danh sách highlight,
 * note").
 *
 * It opens on the LEFT, under the button that opens it, exactly where the
 * contents open (owner, 03/09) - the two never share the screen, so they can
 * share the corner. And it follows the contents' rule: clicking a row
 * NAVIGATES, it does not start reading. Browsing what you marked should not
 * read at you.
 */
import { useEffect, useRef, useState } from "react";
import { text } from "../i18n";
import { Button, IconButton, Notice, Surface } from "./controls";
import { GroupedSection } from "./patterns";
import { CloseIcon, HighlightIcon, NoteIcon, TrashIcon } from "./icons";
import { groupAnnotations, type Annotation } from "./annotationsList";

export function NotesPanel({
  chapters,
  annotations,
  paged,
  focusId,
  error,
  onNavigate,
  onDelete,
  onClose,
}: {
  chapters: { id: string; title: string; segments: { id: string }[] }[];
  annotations: Annotation[];
  paged: boolean;
  /** The note whose icon was pressed: brought into view and marked. */
  focusId: string | null;
  /** Why a note that was asked to go is still here. */
  error?: string | null;
  onNavigate: (segmentId: string) => void;
  /** Remove one for good - a tombstone in the engine keeps the next Apple
   * Books sync from handing it back. */
  onDelete: (annotationId: string) => void;
  onClose: () => void;
}) {
  const groups = groupAnnotations(chapters, annotations);
  const focused = useRef<HTMLButtonElement>(null);
  /* Deleting is permanent by the owner's own decision (03/09), so it asks -
   * in the row, the way removing a book from the library asks. */
  const [confirming, setConfirming] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    focused.current?.scrollIntoView({ block: "center" });
  }, [focusId]);

  return (
    <Surface
      edge="strong"
      /* Sheet tier: a titled panel floating over the book, like the settings
         panel it sits opposite. Menus of rows - the contents, the voice
         switcher - stay at the card tier, where their 12px items are
         concentric with a 16px frame. */
      radius="sheet"
      /* The title stays put and only the list moves, so the scrollbar belongs
         to the list and not to the whole panel; `overflow-hidden` on the
         frame keeps it inside the rounded corner instead of running past it
         (owner, 03/09). */
      className={`mark-sample absolute left-0 z-10 flex w-[23rem] flex-col overflow-hidden shadow-lifted ${
        paged
          ? "top-0 max-h-full"
          : "top-[calc(var(--shell-top-inner)+var(--layer-gap))] layer-capped"
      }`}
    >
      <div className="flex shrink-0 items-center gap-2 px-4 pb-1 pt-3">
        <h3 className="m-0 flex-1 text-sm font-bold">{text("notes.title")}</h3>
        <IconButton onClick={onClose} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>

      {error && (
        <Notice tone="error" className="shrink-0 px-4 pb-2">
          {text("notes.remove_failed")} ({error})
        </Notice>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-3">
      {groups.length === 0 ? (
        <p className="m-0 mt-2 text-sm text-ink-mute">{text("notes.empty")}</p>
      ) : (
        groups.map((group) => (
          /* Rows outdent by 8 so the hover wash reaches past the text; the
             rule is pushed back in by the same 8 to line up with it. */
          <GroupedSection
            key={group.chapterId}
            title={group.chapterTitle}
            className="[--dot-inset:0.5rem]"
          >
            {group.items.map((item) => (
              confirming === item.id ? (
                <div key={item.id} className="-mx-2 flex items-center gap-2 px-2 py-3">
                  <span className="min-w-0 flex-1 truncate text-sm text-ink-mute">
                    {text("notes.remove_confirm")}
                  </span>
                  <Button size="sm" variant="danger" onClick={() => { setConfirming(null); onDelete(item.id); }}>
                    {text("notes.remove")}
                  </Button>
                  <Button size="sm" onClick={() => setConfirming(null)}>
                    {text("library.remove_keep")}
                  </Button>
                </div>
              ) : (
              <button
                key={item.id}
                type="button"
                ref={item.id === focusId ? focused : undefined}
                onClick={() => onNavigate(item.segment_id)}
                className={`group -mx-2 flex gap-2.5 rounded-[var(--ctl-radius)] px-2 py-3 text-left hover-wash ${
                  item.id === focusId ? "bg-wash" : ""
                }`}
              >
                {/* Which kind of thing this row is, said once on the left
                    (owner, 03/09): a passage kept, or a passage with
                    something written about it. Aligned to the first line,
                    not centred on the row - a three-line note would drag a
                    centred icon away from the text it belongs to. */}
                <span className="mt-0.5 shrink-0 text-ink-faint" aria-hidden>
                  {item.note ? <NoteIcon /> : <HighlightIcon />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm leading-relaxed">
                    <mark data-style={item.style || undefined}>{item.selected_text}</mark>
                  </span>
                  {item.note && (
                    <span className="mt-1.5 block text-sm leading-relaxed text-ink-mute">
                      {item.note}
                    </span>
                  )}
                </span>
                <span className="sr-only">
                  {text(item.note ? "notes.kind_note" : "notes.kind_highlight")}
                </span>
                {/* Quiet until the row is under the cursor, but always
                    reachable by keyboard - a destructive action should not
                    be the first thing the eye lands on. */}
                <span
                  role="button"
                  tabIndex={0}
                  aria-label={text("notes.remove")}
                  title={text("notes.remove")}
                  className="mt-0.5 shrink-0 rounded p-0.5 text-ink-faint opacity-0 transition-opacity hover:text-danger focus-visible:opacity-100 group-hover:opacity-100"
                  onClick={(event) => { event.stopPropagation(); setConfirming(item.id); }}
                  onKeyDown={(event) => {
                    if (event.key !== "Enter" && event.key !== " ") return;
                    event.preventDefault();
                    event.stopPropagation();
                    setConfirming(item.id);
                  }}
                >
                  <TrashIcon />
                </span>
              </button>
              )
            ))}
          </GroupedSection>
        ))
      )}
      </div>
    </Surface>
  );
}
