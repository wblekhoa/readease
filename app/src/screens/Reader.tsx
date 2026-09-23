/** The one screen where the content IS the product and chrome is the cost.
 *
 * Two positions are tracked here, not one: where the EYE is (the page or
 * scroll position you are at, which marks the chapter in the contents) and
 * where the VOICE is (the segment being spoken, painted in `band`). They
 * diverge the moment someone turns or scrolls ahead while listening, and the
 * screen must not fight that - it stops following, and offers a way back
 * instead. Written up in docs/readease-hig.md §3.9.
 *
 * Two ways to move through a book (owner, 02/09): PAGES, the default, the
 * shape every reading app converges on - one chapter at a time cut into
 * pages by the type size and the window, two pages when there is room; and
 * the continuous SCROLL, kept as a choice. Both address the book by segment
 * id, so the voice, the contents, the saved place and the engine are the
 * same underneath.
 *
 * The text is the one place selection is on (the shell disables it
 * everywhere else): drag to copy, or hand the selection to the voice through
 * the pill. A plain click on a paragraph still moves the voice.
 */
import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";
import { invoke } from "@tauri-apps/api/core";
import { engineMessage, text } from "../i18n";
import { continues, listLead, quoteRole, type Joint } from "../ui/blockStyle";
import { measureEm, type ReadingPrefs } from "../ui/readingPrefs";
import { SearchPanel, type SearchMarks } from "../ui/SearchPanel";
import { matchRanges } from "../ui/textSearch";
import { Button, IconButton, InlineIconButton, LAYER_GAP, Notice, Surface, Textarea } from "../ui/controls";
import { ListRow } from "../ui/patterns";
import { contentsRows, currentRow, type ContentsRow, type TocEntry } from "../ui/contents";
import { Presence, scrollBehavior } from "../ui/motion";
import type { SidebarTab } from "../ui/sidebarState";
import { CloseIcon, NoteIcon } from "../ui/icons";
import { NotesPanel } from "../ui/NotesPanel";
import { noteCount } from "../ui/annotationsList";
import { markParagraph } from "../ui/highlight";
import type { ReadingMode } from "../ui/readingMode";
import { PageFlow, type PageReason, type PageTarget } from "./PageFlow";

/** What the toolbar's ⓘ says about where you are. Pages carry a page count;
 * a scroll only knows its chapter. `percent` is the first segment on screen
 * against the whole book. */
export type PageInfo = {
  page?: number;
  pages?: number;
  chapterTitle: string;
  percent: number;
  /** What this book carries, so the toolbar can leave the notes button out
   * entirely rather than opening an empty panel. */
  annotations: number;
  notes: number;
  /** The chapter a "read" would resume in - null when the book is untouched
   * and reading would start from the beginning. */
  resumeChapterTitle: string | null;
  /** The segment a "read on" would start at, and its opening words - so the
   * footer can SHOW what is about to be read instead of naming the chapter,
   * and can offer to go there without reading it (owner, 04/09). */
  resumeSegmentId: string | null;
  resumeExcerpt: string | null;
};

type BookSegment = { id: string; text: string; kind: string; joint?: Joint };
type BookFigure = {
  id: string;
  anchor_segment_id: string;
  placement: string;
  alt: string | null;
  /** Per chapter - the same number the voice says in "Xem hình N". */
  number: number;
  /** "Image", "img_01" and friends: an alt that names nothing. Hidden. */
  alt_is_generic: boolean;
  /** The book's own label ("Hình 1.1") when it numbers its figures; then
   * the page shows that, not a second numbering of ours. */
  label?: string | null;
  /** The paragraph that captions this picture, when the book has one. Its
   * words are already on the page, so the figure does not repeat them. */
  caption_segment_id?: string | null;
  /** A translated copy of the picture just before it. Shown, so the two
   * can be compared; it shares that picture's number and label. */
  duplicate_of?: string | null;
};
type BookChapter = {
  id: string;
  title: string;
  figures: BookFigure[];
  segments: BookSegment[];
};
type BookAnnotation = {
  id: string;
  segment_id: string;
  selected_text: string;
  note: string | null;
  style: number;
};
type OpenedBook = {
  book: {
    id: string;
    title: string;
    chapters: BookChapter[];
    /** The publisher's contents tree (HIG 3.25); empty or absent when the
     * book has none, and the column lists the chapters instead. */
    toc?: TocEntry[];
  };
  /** Highlights brought over from Apple Books, pinned to segments. */
  annotations?: BookAnnotation[];
  progress: { segment_id: string | null };
};

/** One EPUB figure: modest in the flow of reading, full size on demand. */
function Figure({
  bookId,
  figure,
  cued,
  paged,
  onOpen,
}: {
  bookId: string;
  figure: BookFigure;
  /** The voice just said this picture's cue: bring it into view, mark it. */
  cued: boolean;
  /** On a page a picture must fit the page; in a scroll, the viewport. */
  paged: boolean;
  onOpen: (source: string, alt: string) => void;
}) {
  const [source, setSource] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const holder = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = holder.current;
    if (!element) return;
    const load = () =>
      invoke<{ result: { media_type: string; data: string } }>(
        "engine_request",
        { method: "book.figure", params: { book_id: bookId, figure_id: figure.id } },
      )
        .then((reply) =>
          setSource(`data:${reply.result.media_type};base64,${reply.result.data}`),
        )
        .catch(() => setFailed(true));
    // On pages a picture in an overflow column never "intersects" anything,
    // and a picture arriving mid-chapter repaginates under the reader - so
    // a chapter's figures load with its text. A scroll keeps loading lazily.
    if (paged) {
      void load();
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      void load();
    }, { rootMargin: "400px" });
    observer.observe(element);
    return () => observer.disconnect();
  }, [bookId, figure.id, paged]);

  useEffect(() => {
    if (cued && !paged) holder.current?.scrollIntoView({ block: "center", behavior: scrollBehavior() });
  }, [cued, paged]);

  // A caption on the page says it all; an alt that repeats it under the
  // picture is the same sentence twice (owner, 05/09).
  const alt = figure.alt_is_generic || figure.caption_segment_id ? "" : figure.alt ?? "";
  const label = figure.label ?? text("reader.figure_label", { n: figure.number });

  return (
    <figure
      ref={holder}
      data-figure={figure.id}
      className={`-mx-3 my-6 break-inside-avoid rounded-2xl px-3 py-2 transition-colors ${cued ? "bg-band" : ""}`}
    >
      {failed && (
        <p className="m-0 text-center text-xs text-ink-mute">
          {text("reader.figure_unavailable")}
        </p>
      )}
      {source && (
        <>
          <img
            src={source}
            alt={alt || label}
            title={text("reader.figure_open")}
            onClick={() => onOpen(source, alt || label)}
            onError={() => { setSource(null); setFailed(true); }}
            draggable={false}
            className={`mx-auto max-w-full cursor-zoom-in rounded-2xl ${
              paged ? "max-h-[calc(var(--page-h)-6rem)]" : "max-h-[46vh]"
            }`}
          />
          <figcaption className="mt-2 text-center text-xs text-ink-mute">
            <span className="font-semibold">{label}</span>
            {alt && <span> · {alt}</span>}
          </figcaption>
        </>
      )}
    </figure>
  );
}

/** Where a bubble hangs beside the marker that opened it.
 *
 * Measured, not styled: the reader's text lives in CSS columns slid
 * sideways by a transform, so anything parented to a paragraph is clipped
 * or lands somewhere else. Both bubbles - the one you read and the one you
 * type in - are drawn `fixed` from these numbers instead. */
type Bubble = {
  left?: number;
  right?: number;
  maxWidth: number;
  top?: number;
  bottom?: number;
};

/** One line of the contents tree (HIG 3.25): its number in a gutter sized
 * for its level, its words in the weight of its role, stepped in 12 px for
 * each level below the chapters. A part opens a group, so it gets air above;
 * lines two levels below a chapter fall back to `ink-mute` - one size for the
 * whole tree (the type scale has no step between xs and sm), told apart by
 * weight, colour, number and step. */
function ContentsLine({
  row,
  first,
  gutter,
  active,
  rowRef,
  onPress,
}: {
  row: ContentsRow;
  first: boolean;
  /** Whether the tree numbers anything: then every line keeps the gutter,
   * numbered or not, so the words of one level start on one edge. */
  gutter: boolean;
  active: boolean;
  rowRef?: RefObject<HTMLDivElement | null>;
  onPress: () => void;
}) {
  const below = Math.max(0, row.sub);
  const width = below === 0 ? "w-7" : below === 1 ? "w-9" : below === 2 ? "w-11" : "w-12";
  // Spoken: the book's own words where the number replaced them on screen
  // ("Chương 1 …", "Phần Một: …" - better aloud than a Roman "I"), else the
  // number and the title with a pause between them.
  const name = row.label !== row.entry.title
    ? row.entry.title
    : row.number ? `${row.number}, ${row.label}` : undefined;
  // On the lit row everything is ink: `ink-mute` on the `tint` wash measured
  // under 4.5:1 in dark (axe, 23/09), and the wash already says "here".
  const words =
    row.role === "part" ? "text-sm font-semibold text-ink"
    : row.role === "chapter" ? "text-sm font-medium text-ink"
    : below === 1 ? "text-sm text-ink"
    : `text-sm ${active ? "text-ink" : "text-ink-mute"}`;
  return (
    <>
      {row.role === "part" && !first && <div aria-hidden="true" className="h-2 shrink-0" />}
      <ListRow
        dense
        active={active}
        current={active}
        rowRef={rowRef}
        inset={below * 12}
        name={name}
        leading={gutter
          ? <span className={`inline-block ${width} text-xs tabular-nums ${active ? "text-ink" : ""}`}>{row.number ?? ""}</span>
          : undefined}
        onPress={onPress}
        title={<span className={`line-clamp-2 leading-snug ${words}`}>{row.label}</span>}
      />
    </>
  );
}

export function Reader({
  bookId,
  language,
  currentSegment,
  currentFigure,
  reading,
  mode,
  sidebarTab,
  sidebarSlot,
  prefs,
  notesFocus,
  onShowNotes,
  reveal,
  size,
  onSegments,
  onReadFrom,
  onSelection,
  onPageInfo,
}: {
  bookId: string;
  /** The language the document is written in ("vi" / "en"), for its words
   * only - the interface around them speaks the app's (WCAG 3.1.2). */
  language?: string;
  currentSegment: string | null;
  /** Figure whose spoken cue the ear just heard, or null. */
  currentFigure: string | null;
  reading: boolean;
  mode: ReadingMode;
  /** Which of this book's lists the side column shows, or null when the
   * column is folded or showing something else. The column is App's: the
   * chrome has one place for the switches (the toolbar) and one for the
   * lists (the column); this screen owns the lists' state and renders
   * them into the column's slot through a portal (HIG 3.16). */
  sidebarTab: SidebarTab | null;
  sidebarSlot: HTMLElement | null;
  /** Line spacing, margins, columns, justification, weight - the reader's
   * own setting of the page (ui/readingPrefs). */
  prefs: ReadingPrefs;
  /** The annotation whose icon opened the notes, if they were opened that way. */
  notesFocus: string | null;
  /** Show the notes tab with one annotation brought into view. */
  onShowNotes: (focusId: string) => void;
  /** Bring a place into view without speaking it. The `at` stamp is what
   * makes asking twice for the SAME place work - a plain id would look
   * unchanged to an effect and do nothing the second time. */
  reveal: { segmentId: string; at: number } | null;
  size: number;
  onSegments: (ids: string[]) => void;
  onReadFrom: (segmentId: string) => void;
  /** The words currently selected in the book, "" when none - the footer
   * turns them into a button (owner, 02/09: the pill left the page). */
  onSelection: (text: string) => void;
  onPageInfo: (info: PageInfo | null) => void;
}) {
  const [opened, setOpened] = useState<OpenedBook | null>(null);
  /** What the Tìm tab is looking for, so the page can mark it (HIG 3.16). */
  const [searchMarks, setSearchMarks] = useState<SearchMarks>({ query: "", current: null });
  /** Why the book would not open, and why one that was deleted came back. */
  const [openError, setOpenError] = useState<string | null>(null);
  const [noteError, setNoteError] = useState<string | null>(null);
  const [seenChapter, setSeenChapter] = useState<string | null>(null);
  /** The last passage of the contents tree the scroll has carried past the
   * reading line - the section the eye is in, finer than the chapter. */
  const [seenEntry, setSeenEntry] = useState<string | null>(null);
  /** The contents line last pressed: on pages it stays lit while its passage
   * is on the page - the jump often lands mid-page, under the tail of the
   * section before it. */
  const [pickedRow, setPickedRow] = useState<number | null>(null);
  const [following, setFollowing] = useState(true);
  const [zoomed, setZoomed] = useState<{ source: string; alt: string } | null>(null);
  /* A note read where it sits, without opening anything.
   *
   * The coordinates are computed from the icon and the bubble is drawn with
   * `fixed` at the top of the reader, NOT inside the paragraph: in pages mode
   * the text lives in CSS columns slid sideways by a transform, inside a
   * frame that clips - a popover parented to the paragraph would be cut off
   * or land somewhere else entirely. Fixed positioning is measured against
   * the window, so neither the columns nor the transform can reach it. */
  const [peek, setPeek] = useState<({ note: string } & Bubble) | null>(null);
  /* The same bubble, with a cursor in it. Separate state rather than a mode
     on `peek`, because they answer to opposite things: the peek follows the
     pointer and vanishes when it leaves, the editor stays until the person
     is done with it. Both are open at once for one frame while the pointer
     is still over the marker, so the peek is cleared when this opens. */
  const [editing, setEditing] = useState<
    ({ id: string; draft: string; error?: string } & Bubble) | null
  >(null);
  const [saving, setSaving] = useState(false);
  /* The contents row for the chapter being read, so opening the panel can put
     it in front of the person instead of at the top of a long book. */
  const here = useRef<HTMLDivElement>(null);
  const column = useRef<HTMLDivElement>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const paged = mode === "pages";

  // Pages: which chapter is open, where it should open, what is on screen.
  const [chapterIndex, setChapterIndex] = useState(0);
  const [target, setTarget] = useState<PageTarget | null>(null);
  const [shown, setShown] = useState<string[]>([]);

  /* A double-click selects a word, and its first click arrives while the
   * caret is still collapsed - so a plain click waits a beat, and a second
   * click cancels it. 220 ms is invisible for a seek; a voice jumping away
   * from the word you were about to copy is not. */
  const pendingRead = useRef<number | null>(null);
  const readFromSoon = useCallback((segmentId: string) => {
    if (pendingRead.current !== null) window.clearTimeout(pendingRead.current);
    pendingRead.current = window.setTimeout(() => {
      pendingRead.current = null;
      onReadFrom(segmentId);
    }, 220);
  }, [onReadFrom]);
  const cancelPendingRead = useCallback(() => {
    if (pendingRead.current !== null) window.clearTimeout(pendingRead.current);
    pendingRead.current = null;
  }, []);
  useEffect(() => cancelPendingRead, [cancelPendingRead]);

  /* A failed delete explains itself only while the notes are on show.
   * Clearing it on a close callback was not enough: the toolbar folds the
   * column without going through the panel, so reopening later showed a
   * complaint about something the person had not just done. */
  const showNotes = sidebarTab === "notes";
  const showToc = sidebarTab === "contents";
  useEffect(() => {
    if (!showNotes) setNoteError(null);
  }, [showNotes]);

  const marker = currentSegment ?? opened?.progress.segment_id ?? null;
  const flat = useMemo(
    () => opened?.book.chapters.flatMap((chapter) => chapter.segments.map((s) => s.id)) ?? [],
    [opened],
  );
  const flatIndex = useMemo(() => new Map(flat.map((id, index) => [id, index])), [flat]);
  // The contents as numbered rows (HIG 3.25), and the passages they lead to -
  // marked on the page so the scroll can tell which line the eye is under.
  const tocRows = useMemo(() => contentsRows(opened?.book.toc ?? []), [opened]);
  const tocTargets = useMemo(() => new Set(tocRows.map((row) => row.entry.segment_id)), [tocRows]);
  const tocNumbered = useMemo(() => tocRows.some((row) => row.number !== null), [tocRows]);
  // A pressed line belongs to the tree it was pressed in.
  useEffect(() => { setPickedRow(null); }, [tocRows]);
  const chapterOf = useCallback((segmentId: string): number => {
    const index = opened?.book.chapters.findIndex((chapter) =>
      chapter.segments.some((segment) => segment.id === segmentId),
    ) ?? -1;
    return index < 0 ? 0 : index;
  }, [opened]);

  useEffect(() => {
    const onSelectionChange = () => {
      const active = window.getSelection();
      const inside =
        active &&
        !active.isCollapsed &&
        column.current?.contains(active.anchorNode) &&
        column.current?.contains(active.focusNode);
      onSelection(inside ? active.toString().trim() : "");
    };
    document.addEventListener("selectionchange", onSelectionChange);
    return () => {
      document.removeEventListener("selectionchange", onSelectionChange);
      onSelection("");
    };
  }, [onSelection]);

  useEffect(() => {
    invoke<{ result: OpenedBook }>("engine_request", {
      method: "book.open",
      params: { book_id: bookId },
    })
      .then((reply) => {
        setOpened(reply.result);
        onSegments(
          reply.result.book.chapters.flatMap((chapter) =>
            chapter.segments.map((segment) => segment.id),
          ),
        );
        // A book opens where it was left - on the page, not at the top.
        const start = reply.result.progress.segment_id
          ?? reply.result.book.chapters[0]?.segments[0]?.id;
        if (start) {
          const index = reply.result.book.chapters.findIndex((chapter) =>
            chapter.segments.some((segment) => segment.id === start),
          );
          setChapterIndex(index < 0 ? 0 : index);
          setTarget({ segmentId: start, source: "open" });
        }
      })
      .catch((error) => {
        console.error(error);
        setOpenError(engineMessage(error));
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId]);

  const jumpTo = useCallback((segmentId: string, smooth = true) => {
    column.current
      ?.querySelector(`[data-segment="${segmentId}"]`)
      ?.scrollIntoView({ block: "center", behavior: smooth ? scrollBehavior() : "auto" });
  }, []);

  /** Put the bubble beside an icon: as wide as the note needs, never wider
   *  than the room it has.
   *
   * The width is the note's own - a five-word note in a 20rem box is mostly
   * empty box (owner, 03/09). What is computed here is the CEILING, and it
   * is the real room to the right of the icon rather than a guess, because a
   * note icon can sit anywhere on a line. When that room would leave a
   * column of two words per line, the bubble stops following the icon and
   * lines up with the window's right margin instead. Above the line when the
   * icon is low, so a long note is not cut off by the bottom of the window.
   */
  const place = useCallback((anchor: HTMLElement): Bubble => {
    const rect = anchor.getBoundingClientRect();
    const margin = 24;
    /** Under this, following the icon makes a column, not a bubble. */
    const narrowest = 260;
    /** Past this a note stops being a glance and wants the panel. */
    const widest = 448;
    const room = window.innerWidth - rect.left - margin;
    const low = rect.bottom > window.innerHeight * 0.6;
    const across = room >= narrowest
      ? { left: Math.max(margin, rect.left - 8), maxWidth: Math.min(widest, room + 8) }
      : { right: margin, maxWidth: Math.min(widest, window.innerWidth - margin * 2) };
    return {
      ...across,
      top: low ? undefined : rect.bottom + LAYER_GAP,
      bottom: low ? window.innerHeight - rect.top + LAYER_GAP : undefined,
    };
  }, []);

  const showPeek = useCallback((anchor: HTMLElement, note: string) => {
    setPeek({ note, ...place(anchor) });
  }, [place]);

  /** Open the note for writing, where it sits.
   *
   * The peek goes first: the pointer is still on the marker that opened
   * this, so both bubbles would otherwise be on screen at once, one of them
   * unreachable behind the other. */
  const editNote = useCallback((anchor: HTMLElement, id: string, note: string) => {
    setPeek(null);
    setNoteError(null);
    setEditing({ id, draft: note, ...place(anchor) });
  }, [place]);

  /** Write one note down, and mean it.
   *
   * Optimistic, like the delete beside it and for the same reason: the
   * words appear on the page at once. But the ENGINE is what makes it true
   * - it keeps a record of the edit so the next Apple Books sync cannot
   * overwrite the person's own words with the ones the highlight arrived
   * with - and when it refuses, the page goes back to what is actually on
   * disk and the box stays open, still holding what was typed, saying why.
   * A note that only LOOKS saved is the outcome to avoid: the person closes
   * the book believing they wrote something down.
   *
   * Up here, far from the box it serves, because it is a hook: written down
   * beside the editor it crashed the reader the moment a book opened - the
   * `!opened` return below comes first, so the hook count changed between
   * renders. Same trap as the contents-panel effect further down.
   */
  const saveNote = useCallback((id: string, draft: string) => {
    const note = draft.trim();
    const before = (opened?.annotations ?? []).find((item) => item.id === id);
    // Gone from under the box - deleted in the panel while this was open.
    // Returning quietly would leave the button doing nothing at all, which
    // is the one thing a save must never look like.
    if (!before) {
      setEditing((open) => open && { ...open, error: text("reader.note_gone") });
      return;
    }
    if ((before.note ?? "") === note) { setEditing(null); return; }
    const put = (value: string | null) => setOpened((book) => book && {
      ...book,
      annotations: (book.annotations ?? []).map((item) =>
        item.id === id ? { ...item, note: value } : item),
    });
    const refuse = (message: string) => {
      put(before.note ?? null);
      setEditing((open) => open && { ...open, error: message });
    };
    setSaving(true);
    put(note || null);
    void invoke<{ result: { updated: boolean } }>("engine_request", {
      method: "annotations.update",
      params: { book_id: bookId, annotation_id: id, note },
    }).then((reply) => {
      // `updated: false` is not an error - it is this highlight being gone,
      // removed in another window or by a sync while the box was open.
      if (reply?.result?.updated) setEditing(null);
      else refuse(text("reader.note_gone"));
    }).catch((error) => {
      console.error(error);
      refuse(text("reader.note_save_failed"));
    }).finally(() => setSaving(false));
  }, [bookId, opened]);

  /** Show a place, in whichever mode is on. */
  const showSegment = useCallback((segmentId: string, source: PageReason) => {
    if (paged) {
      setChapterIndex(chapterOf(segmentId));
      setTarget({ segmentId, source });
    } else {
      jumpTo(segmentId);
    }
  }, [paged, chapterOf, jumpTo]);

  /* Placed AFTER showSegment on purpose: a dependency array is evaluated
     during render, so an effect written above the `const` would read it in
     the temporal dead zone and throw before the first paint. */
  useEffect(() => {
    if (!reveal) return;
    showSegment(reveal.segmentId, "contents");
  }, [reveal, showSegment]);

  // The voice moved. Follow it only while the reader is still watching the
  // spoken line; if they have turned or scrolled away, leave them be.
  useEffect(() => {
    if (!currentSegment || !following) return;
    if (paged && shown.includes(currentSegment)) return;
    showSegment(currentSegment, "voice");
    // `shown` is deliberately not a dependency: a page coming on screen must
    // not re-trigger a jump to the segment already on it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSegment, following, paged, showSegment]);

  // The voice announced a picture: on pages, show the page the PICTURE is
  // on. Its anchor paragraph can be on this page while the picture opens
  // the next - aiming at the paragraph left the reader hearing "Xem hình"
  // with no picture in sight (owner, 05/09).
  useEffect(() => {
    if (!paged || !currentFigure || !following || !opened) return;
    const figure = opened.book.chapters.flatMap((c) => c.figures).find((f) => f.id === currentFigure);
    if (!figure) return;
    setChapterIndex(chapterOf(figure.anchor_segment_id));
    setTarget({ segmentId: figure.anchor_segment_id, source: "figure", figureId: figure.id });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentFigure, paged, following, opened, chapterOf]);

  const [pageIndex, setPageIndex] = useState<{ page: number; pages: number } | null>(null);
  const onPageShown = useCallback((ids: string[], reason: PageReason, page: number, pages: number) => {
    // A page that is only a picture has no segment to stand for it: keep
    // the last known place for the percentage and the anchor.
    if (ids.length) setShown(ids);
    setPageIndex({ page, pages });
    if (opened) setSeenChapter(opened.book.chapters[chapterIndex]?.id ?? null);
    // Only the reader's own hand counts as wandering off from the voice.
    if (reason === "turn" && currentSegment) setFollowing(ids.includes(currentSegment));
  }, [opened, chapterIndex, currentSegment]);

  // The chapter in front of the reader - the page's own on pages, the one
  // scrolled into in a scroll: what the ⓘ below reports, and the page's
  // name to a screen reader (HIG 4.2, point 4).
  const chapterInView = !opened ? undefined : paged
    ? opened.book.chapters[chapterIndex]
    : opened.book.chapters.find((c) => c.id === seenChapter) ?? opened.book.chapters[0];

  // The facts about where you are go up to the toolbar's ⓘ - the page
  // itself stays clear of them (owner, 02/09: "giảm bớt nội dung không
  // quan trọng").
  useEffect(() => {
    if (!opened) { onPageInfo(null); return; }
    const chapter = chapterInView;
    const first = paged ? shown[0] : chapter?.segments[0]?.id;
    const percent = flat.length && first ? Math.round((Math.max(0, flat.indexOf(first)) / flat.length) * 100) : 0;
    const resume = marker ? opened.book.chapters[chapterOf(marker)] : null;
    const resumeSegment = marker
      ? resume?.segments.find((segment) => segment.id === marker) ?? null
      : null;
    onPageInfo({
      page: paged ? pageIndex?.page : undefined,
      pages: paged ? pageIndex?.pages : undefined,
      chapterTitle: chapter?.title ?? "",
      percent,
      annotations: opened.annotations?.length ?? 0,
      notes: noteCount(opened.annotations ?? []),
      resumeChapterTitle: resume?.title ?? null,
      resumeSegmentId: marker,
      resumeExcerpt: resumeSegment?.text ?? null,
    });
  }, [opened, paged, chapterInView, shown, pageIndex, flat, marker, chapterOf, onPageInfo]);
  useEffect(() => () => onPageInfo(null), [onPageInfo]);

  const onChapterChange = useCallback((index: number, edge: "start" | "end") => {
    const chapter = opened?.book.chapters[index];
    if (!chapter) return;
    setChapterIndex(index);
    setTarget({ segmentId: edge === "start" ? chapter.segments[0].id : "__end__", source: "turn" });
  }, [opened]);

  // Scroll-spy (scroll mode): the topmost chapter heading at or above the
  // reading line is the one the eye is in. Cheap enough to run on scroll.
  useEffect(() => {
    if (paged) return;
    const root = scroller.current;
    if (!root || !opened) return;
    let frame = 0;
    const measure = () => {
      frame = 0;
      // The chrome bars float over the scroller, so "the top of the page"
      // is the named inset down, not the scroller's own edge.
      const style = getComputedStyle(root);
      const insetTop = parseFloat(style.getPropertyValue("--shell-top-h")) || 0;
      const insetBottom = parseFloat(style.getPropertyValue("--shell-bottom-h")) || 0;
      const line = root.getBoundingClientRect().top + insetTop + 40;
      let current: string | null = null;
      for (const chapter of opened.book.chapters) {
        const heading = column.current?.querySelector(
          `[data-chapter="${chapter.id}"]`,
        );
        if (!heading) continue;
        if (heading.getBoundingClientRect().top <= line) current = chapter.id;
      }
      setSeenChapter(current ?? opened.book.chapters[0]?.id ?? null);
      // The contents' own lines: the last one whose passage has reached the
      // MIDDLE of the page - where a jump from the contents puts it
      // (`jumpTo`, block "center"). In document order: the first one below
      // the middle ends the search.
      const middle = root.getBoundingClientRect().top + insetTop
        + (root.clientHeight - insetTop - insetBottom) / 2;
      let entry: string | null = null;
      for (const element of column.current?.querySelectorAll<HTMLElement>("[data-toc]") ?? []) {
        if (element.getBoundingClientRect().top > middle) break;
        entry = element.dataset.segment ?? null;
      }
      setSeenEntry(entry);
      if (currentSegment) {
        const spoken = column.current?.querySelector(
          `[data-segment="${currentSegment}"]`,
        );
        if (spoken) {
          const box = spoken.getBoundingClientRect();
          const view = root.getBoundingClientRect();
          setFollowing(
            box.bottom > view.top + insetTop && box.top < view.bottom - insetBottom,
          );
        }
      }
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(measure);
    };
    measure();
    root.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      root.removeEventListener("scroll", onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [paged, opened, currentSegment]);

  useEffect(() => {
    if (!zoomed) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setZoomed(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [zoomed]);

  useEffect(() => {
    if (!editing) return;
    const onKey = (event: KeyboardEvent) => {
      // Escape abandons the edit. The note on disk is untouched, which is
      // why this needs no confirmation: nothing has been written yet.
      if (event.key === "Escape") setEditing(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [editing]);

  const highlightsBySegment = useMemo(() => {
    const map = new Map<string, BookAnnotation[]>();
    for (const item of opened?.annotations ?? []) {
      map.set(item.segment_id, [...(map.get(item.segment_id) ?? []), item]);
    }
    return map;
  }, [opened]);

  /* ABOVE the early return below, where every hook in this component has to
     live: this one was written down beside the panel it serves and crashed
     the reader the moment a book opened - `!opened` returns before it, so the
     hook count changed between renders.

     `block: "center"` and not `nearest`: "nearest" leaves the row wherever it
     happens to fall, including flush under the heading. Instant, not smooth -
     the panel is not on screen yet when this runs, so there is nothing for an
     animation to be seen doing. */
  useEffect(() => {
    if (!showToc) return;
    here.current?.scrollIntoView({ block: "center" });
  }, [showToc]);

  if (!opened) {
    // A book that will not open has to SAY so. Returning null whatever the
    // reason left the reader permanently blank - a screen indistinguishable
    // from a book still loading and from a book with no words in it, and the
    // one thing it never showed was the reason. Loading still renders
    // nothing, because it is over in a moment; a failure does not end.
    if (!openError) return null;
    return (
      <section className="shell-inset flex min-h-0 flex-1 items-center justify-center">
        <Notice tone="error" className="max-w-[28em] text-center">
          {text("reader.open_failed")} ({openError})
        </Notice>
      </section>
    );
  }
  // The contents mark where the EYE is; `marker` marks where the voice is.
  const activeChapter =
    seenChapter ??
    opened.book.chapters.find((chapter) =>
      chapter.segments.some((segment) => segment.id === marker),
    )?.id;
  // The same in the tree's own terms (HIG 3.25). On pages: the line last
  // pressed while its passage is on the page, else the first line that
  // starts on this page, else the line the page opens inside. In a scroll:
  // the last line whose passage has reached the middle (the top of the book
  // before any) - the pressed one while it is that line's passage. Where
  // several lines share a passage and none was pressed, the deepest is lit.
  const orderOf = (id: string) => flatIndex.get(id) ?? -1;
  let activeRow = -1;
  if (tocRows.length && paged) {
    const onPage = new Set(shown);
    const picked = pickedRow !== null ? tocRows[pickedRow] : undefined;
    const starts = tocRows
      .filter((row) => onPage.has(row.entry.segment_id))
      .map((row) => orderOf(row.entry.segment_id));
    if (picked && onPage.has(picked.entry.segment_id)) activeRow = pickedRow!;
    else if (starts.length) activeRow = currentRow(tocRows, orderOf, Math.min(...starts));
    else if (shown[0] ?? marker) activeRow = currentRow(tocRows, orderOf, orderOf((shown[0] ?? marker)!));
  } else if (tocRows.length) {
    const at = seenEntry ?? flat[0] ?? marker;
    const picked = pickedRow !== null ? tocRows[pickedRow] : undefined;
    if (picked && picked.entry.segment_id === at) activeRow = pickedRow!;
    else if (at) activeRow = currentRow(tocRows, orderOf, orderOf(at));
  }
  const goToPassage = (segmentId: string) => {
    if (paged) {
      setChapterIndex(chapterOf(segmentId));
      setTarget({ segmentId, source: "contents" });
    } else {
      jumpTo(segmentId);
    }
    if (reading) onReadFrom(segmentId);
  };
  /** A paragraph's text with EVERY highlight it carries marked.
   *
   * A paragraph often holds more than one - two sentences marked on
   * different days, a phrase inside a sentence marked whole - and for a
   * while this showed only the first, so a note attached to the second had
   * no icon to open it by. `markParagraph` cuts the paragraph up instead;
   * each piece knows which highlight made it, and so which colour and which
   * note belong to it.
   */
  /** The search's marks on a stretch of a paragraph: the stretch cut at
   *  every match that falls inside it, the matches wrapped. `offset` is
   *  where the stretch starts in the printed paragraph, so a match found
   *  on the whole paragraph lands on the right characters of a piece cut
   *  out of it by a highlight. The match the list chose is the k-th of its
   *  paragraph, which is how the page counts them too. */
  const searched = (
    piece: string, offset: number, ranges: Array<[number, number]>, currentOccurrence: number | null,
  ): ReactNode => {
    const end = offset + piece.length;
    const inside = ranges
      .map((range, occurrence) => ({ range, occurrence }))
      .filter(({ range }) => range[0] < end && range[1] > offset);
    if (inside.length === 0) return piece;
    const out: ReactNode[] = [];
    let cursor = offset;
    inside.forEach(({ range, occurrence }) => {
      const from = Math.max(range[0], cursor);
      const to = Math.min(range[1], end);
      if (from > cursor) out.push(<Fragment key={`t${cursor}`}>{piece.slice(cursor - offset, from - offset)}</Fragment>);
      out.push(
        <mark key={`m${from}`} data-search={occurrence === currentOccurrence ? "current" : "match"}>
          {piece.slice(from - offset, to - offset)}
        </mark>,
      );
      cursor = to;
    });
    if (cursor < end) out.push(<Fragment key={`t${cursor}`}>{piece.slice(cursor - offset)}</Fragment>);
    return <>{out}</>;
  };

  /** `shown` is the text as the page prints it - a list item minus the
   *  marker the book typed into it. Highlights match by their own words, so
   *  a shorter string still finds them. */
  const marked = (segment: BookSegment, shown = segment.text) => {
    const items = highlightsBySegment.get(segment.id);
    const ranges = searchMarks.query ? matchRanges(shown, searchMarks.query) : [];
    const currentOccurrence =
      searchMarks.current?.segmentId === segment.id ? searchMarks.current.occurrence : null;
    if (!items) return ranges.length ? searched(shown, 0, ranges, currentOccurrence) : shown;
    const pieces = markParagraph(shown, items.map((item) => item.selected_text));
    // Nothing found: hand back the plain string, not a wrapped one.
    if (pieces.every((piece) => piece.index === null)) {
      return ranges.length ? searched(shown, 0, ranges, currentOccurrence) : shown;
    }
    let offset = 0;
    return pieces.map((piece, at) => {
      const start = offset;
      offset += piece.text.length;
      const body = searched(piece.text, start, ranges, currentOccurrence);
      if (piece.index === null) return <Fragment key={at}>{body}</Fragment>;
      const item = items[piece.index];
      return (
        <Fragment key={at}>
          {/* The colour Books drew it in - the stylesheet turns the number
              into the wash. An unknown or absent number falls through to the
              yellow every highlight used to get. */}
          {item.note && (
            /* The note icon, wearing the colour of the highlight it
               belongs to and outlined in the page's own colour so it reads
               as sitting ON the wash rather than smudged into it. It sits
               at the HEAD of the highlight, where a margin mark would be.
               The colours are in index.css: `.note-nudge` takes the hue
               from the same token the wash uses, at full strength. */
            <InlineIconButton
              className="note-nudge"
              data-style={item.style || undefined}
              onClick={(event) => editNote(event.currentTarget, item.id, item.note ?? "")}
              onMouseEnter={(event) => showPeek(event.currentTarget, item.note!)}
              onFocus={(event) => showPeek(event.currentTarget, item.note!)}
              onMouseLeave={() => setPeek(null)}
              onBlur={() => setPeek(null)}
              aria-label={text("reader.note_edit")}
            >
              <NoteIcon />
            </InlineIconButton>
          )}
          <mark data-style={item.style || undefined}>{body}</mark>
        </Fragment>
      );
    });
  };

  /* One look per kind of block, decided by what the book says it is and by
   * what it typed into the text (helpers in ui/blockStyle.ts, measured over
   * the owner's library before they were written):
   * - a `split` tail of a cut paragraph opens no gap above it;
   * - a list item hangs from a gutter with a dot, or the book's own number;
   * - a quotation is set in from the left; a one-word "quote" is a label.
   * The heading keeps its old shape. */
  const blockClasses = (segment: BookSegment, onPages: boolean, first = false): string => {
    // Spacing is TOP margin only, so a block decides its own distance from
    // the one above and a cut paragraph can close that distance to nothing.
    // Each block carries `py-1` for its hover band; the split's negative
    // margin swallows both paddings, so the tail sits one line-height under
    // the head exactly as the next line of the same paragraph would.
    const split = continues(segment.joint);
    switch (segment.kind) {
      case "heading":
        // On pages the chapter's opening heading sits at the top of the
        // first page and needs no room; a section heading further down
        // needs air from the paragraph above it (owner, 17/09: at 8 px it
        // clung to the body). A heading that lands at a column's top has
        // its margin truncated at the break, so the air never opens a
        // hole at the head of a page.
        return (onPages ? (first ? "mt-2 " : "mt-6 ") : "mt-10 ") + "text-[1.35em] font-bold leading-snug ";
      case "list_item":
        // One gutter for dotted and numbered items alike (32 px, room for
        // "99."), so the text edge is the same down a chapter whatever the
        // list's marker (owner, 17/09: "padding left của bullet bằng với
        // number"; HIG 3.9e).
        return (split ? "-mt-2 " : "mt-1 ") + "relative pl-8 ";
      case "quote":
        return quoteRole(segment.text) === "label"
          // `ink-faint` is the DISABLED colour. It was painting real words
          // of the book - "Trải nghiệm", "Phần cứng" - in the shade that
          // means "you cannot use this", at about 2:1 against the paper
          // (owner, 06/09: "nó bị mờ quá vậy?"). A label is SMALL and
          // quiet, not unavailable: size and weight say label, colour stays
          // legible.
          ? (split ? "-mt-2 " : "mt-2 ") + "text-sm font-semibold text-ink-mute "
          : (split ? "-mt-2 " : "mt-3 ") + "border-l-2 border-edge pl-4 italic text-ink-mute ";
      default:
        return split ? "-mt-2 " : "mt-3 ";
    }
  };

  const blockBody = (segment: BookSegment) => {
    if (segment.kind !== "list_item") return marked(segment);
    if (continues(segment.joint)) return marked(segment);
    const { marker, rest } = listLead(segment.text);
    return (
      <>
        {/* The gutter mark shares the first line's baseline: `top-1` is the
            block's own `py-1`, and the line-height is inherited rather than
            re-typed, so a dot or "1." sits where the eye expects a bullet -
            level with the first line, not perched above it. Two ranks
            (owner, 17/09): the dot in the brand colour - a mark of the
            app's, the one accent on a page of text - and the number, an
            ordinal at the text's size in tabular figures, a shade lighter
            than the words so it ranks below them, right-aligned in a
            gutter that holds "99." (the 0.9em number read as a footnote
            mark, and "10." overran a 20 px gutter). */}
        <span
          aria-hidden
          className={`absolute left-0 top-1 w-8 text-right tabular-nums ${
            // The dot sits under the DIGIT of a number, not under its
            // period: a number is right-aligned to 8 px from the text, so
            // its figure's centre is about 15 px in, and a 5 px dot set
            // 14 px from the text lands there (owner, 17/09: "xa ra bên
            // trái một xíu để align với number").
            marker.kind === "dot" ? "list-dot pr-3.5" : "text-ink-mute pr-2"
          }`}
        >
          {marker.kind === "dot"
            ? <span className="inline-block h-[5px] w-[5px] rounded-full bg-current align-middle" />
            : marker.label}
        </span>
        {marked(segment, rest)}
      </>
    );
  };

  const chapterBody = (chapter: BookChapter) =>
    chapter.segments.map((segment, index) => (
      <div key={segment.id}>
        {chapter.figures
          .filter((figure) =>
            figure.anchor_segment_id === segment.id &&
            figure.placement === "before")
          .map((figure) => (
            <Figure key={figure.id} bookId={bookId} figure={figure} paged={paged} cued={figure.id === currentFigure} onOpen={(source, alt) => setZoomed({ source, alt })} />
          ))}
        <p
          data-segment={segment.id}
          data-chapter={segment.kind === "heading" ? chapter.id : undefined}
          data-toc={tocTargets.has(segment.id) ? "" : undefined}
          /* Where the voice is, said to the screen reader as well as drawn
             (HIG 4.2, point 4): the dotted line is for the eye only. */
          aria-current={segment.id === marker ? "true" : undefined}
          /* The document's own language, so VoiceOver reads an English book
             in an English voice under a Vietnamese interface (HIG 4.2). */
          lang={language}
          onClick={() => {
            // A drag that selected text ends in a click on the same
            // paragraph; that click means "I am copying", not "read
            // from here". Only a plain click moves the voice - and
            // only once it is clear no second click is coming.
            if (window.getSelection()?.isCollapsed === false) return;
            readFromSoon(segment.id);
          }}
          onDoubleClick={cancelPendingRead}
          className={
            // No fill, ever: the block being READ carries a light dotted
            // line under its words (`.voice-here`), and the block under the
            // pointer the same line in neutral ink (`.read-from-here`) to
            // say "read from here". The padded, rounded wash both used to
            // wear boxed the paragraph like a selection (owner, 15/09). The
            // padding stays, invisible, because the split rule below counts
            // on it: a cut paragraph's negative margin swallows exactly
            // these two paddings to sit one line-height under its head.
            "-mx-2 cursor-text px-2 py-1 read-from-here " +
            blockClasses(segment, paged, index === 0) +
            (segment.id === marker ? "voice-here" : "")
          }
        >
          {blockBody(segment)}
        </p>
        {chapter.figures
          .filter((figure) =>
            figure.anchor_segment_id === segment.id &&
            figure.placement === "after")
          .map((figure) => (
            <Figure key={figure.id} bookId={bookId} figure={figure} paged={paged} cued={figure.id === currentFigure} onOpen={(source, alt) => setZoomed({ source, alt })} />
          ))}
      </div>
    ));

  /* The contents, in the side column (HIG 3.16; owner, 16/09: a real
   * column of the layout, "giống như cách codex làm" - reversing 02/09's
   * floating layer, since a column that folds itself when the window is
   * narrow no longer eats the page's width). A chapter jumps; the column
   * stays, because a column is not a thing that disappears when used. */
  const contents = showToc && (
    <nav aria-label={text("reader.toc_title")} className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto px-1.5 pb-6">
        {tocRows.length > 0 && tocRows.map((row, index) => (
          <ContentsLine
            key={`${index}-${row.entry.segment_id}`}
            row={row}
            first={index === 0}
            gutter={tocNumbered}
            active={index === activeRow}
            rowRef={index === activeRow ? here : undefined}
            onPress={() => { setPickedRow(index); goToPassage(row.entry.segment_id); }}
          />
        ))}
        {tocRows.length === 0 && opened.book.chapters.map((chapter, index) => (
          <ListRow
            key={chapter.id}
            dense
            active={chapter.id === activeChapter}
            /* Where you are, brought to you. A book of eighty chapters opened
               its contents at chapter one however deep you had read, and the
               row that says "you are here" was the one off the bottom of the
               panel. */
            rowRef={chapter.id === activeChapter ? here : undefined}
            onPress={() => {
              if (paged) {
                setChapterIndex(index);
                setTarget({ segmentId: chapter.segments[0].id, source: "contents" });
              } else {
                jumpTo(chapter.segments[0].id);
              }
              if (reading) onReadFrom(chapter.segments[0].id);
            }}
            /* Two lines, not one truncated to nothing: a title long enough to
               be cut is the one carrying the most, and this list is read by
               scanning it rather than by width. */
            title={<span className="line-clamp-2 text-sm leading-snug">{chapter.title}</span>}
          />
        ))}
    </nav>
  );

  /* Search, the column's third tab. A hit shows its place the way a
   * contents row does; the column stays so the next hit is one click away,
   * and the reading is not disturbed - looking something up mid-listen is
   * the whole point of having it here. */
  const search = sidebarTab === "search" && (
    <SearchPanel
      chapters={opened.book.chapters}
      onMarks={setSearchMarks}
      onJump={(hit) => {
        if (paged) {
          setChapterIndex(hit.chapterIndex);
          setTarget({ segmentId: hit.segmentId, source: "contents" });
        } else {
          jumpTo(hit.segmentId);
        }
      }}
    />
  );

  /* Beside the contents, and under the same rule: a row jumps to the place,
   * it never starts speaking. */
  const notes = showNotes && (
    <NotesPanel
      chapters={opened.book.chapters}
      annotations={opened.annotations ?? []}
      focusId={notesFocus}
      onNavigate={(segmentId) => {
        showSegment(segmentId, "contents");
      }}
      error={noteError}
      onDelete={(annotationId) => {
        // Off the page at once, because the finger deserves an answer now -
        // but the ENGINE is what makes a delete true, and it keeps a
        // tombstone so the next Apple Books sync cannot hand the note back.
        // If it refuses, the note is still on disk, so it goes back on the
        // page and says why. A note that only LOOKS deleted is the one
        // outcome this must never produce: the person walks away believing
        // something private is gone.
        const removed = (opened.annotations ?? []).find((item) => item.id === annotationId);
        setNoteError(null);
        setOpened((book) => book && {
          ...book,
          annotations: (book.annotations ?? []).filter((item) => item.id !== annotationId),
        });
        void invoke("engine_request", {
          method: "annotations.delete",
          params: { book_id: bookId, annotation_id: annotationId },
        }).catch((error) => {
          console.error(error);
          // `groupAnnotations` orders by where a note falls in the book, so
          // putting it back on the end puts it back in its place.
          if (removed) {
            setOpened((book) => book && {
              ...book,
              annotations: [...(book.annotations ?? []), removed],
            });
          }
          setNoteError(engineMessage(error));
        });
      }}
    />
  );

  /* Into the column's slot, not beside the page: the lists are this
   * screen's (their state lives here) but their place is App's column. */
  const lists = sidebarSlot
    ? createPortal(<>{contents}{search}{notes}</>, sidebarSlot)
    : null;

  /* Wrapped rather than styled through `Surface`: the kit's card takes a
     className, not a style, and a measured position is not a class. */
  const notePeek = peek && (
    <div
      className="pointer-events-none fixed z-30 w-max"
      style={{
        left: peek.left, right: peek.right,
        top: peek.top, bottom: peek.bottom,
        maxWidth: peek.maxWidth,
      }}
    >
      {/* Three lines and no more: this is a glance, not the note. A long
          note that unrolled here covered the paragraph it belongs to, and
          the whole of it is one click away in the box that opens. */}
      <Surface edge="strong" className="peek-in px-3 py-2 text-sm leading-relaxed shadow-lifted">
        {/* On a span of its own: `line-clamp` works by switching the
            element to -webkit-box, and the card has a display of its own
            that wins - on the card the rule was set and did nothing. */}
        <span className="line-clamp-3">{peek.note}</span>
      </Surface>
    </div>
  );

  /* The note, open for writing, where the marker is.
   *
   * Not a dialog: the sentence it belongs to has to stay readable while the
   * note about it is being written. The backdrop is there only to catch a
   * click outside - it paints nothing, so the page underneath is entirely
   * visible.
   */
  const noteEditor = (
    <Presence open={editing !== null}>
      {editing && (
    <>
      <div
        className="fixed inset-0 z-40"
        onClick={() => setEditing(null)}
        aria-hidden
      />
      <div
        className="fixed z-50 w-max"
        style={{
          left: editing.left, right: editing.right,
          top: editing.top, bottom: editing.bottom,
          maxWidth: editing.maxWidth,
        }}
      >
        <Surface edge="strong" layer="popover" className="flex w-[22rem] max-w-full flex-col gap-2 p-3 shadow-lifted">
          <Textarea
            autoFocus
            rows={3}
            value={editing.draft}
            placeholder={text("reader.note_placeholder")}
            aria-label={text("reader.note_edit")}
            onChange={(event) => setEditing((open) => open && {
              ...open, draft: event.target.value,
            })}
            onKeyDown={(event) => {
              // Enter alone makes a paragraph - a note is prose. The
              // shortcut is the one every macOS text box uses to send.
              if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                event.preventDefault();
                saveNote(editing.id, editing.draft);
              }
            }}
          />
          {editing.error && <Notice tone="error">{editing.error}</Notice>}
          <div className="flex items-center justify-between gap-2">
            {/* The panel is still the place to see every note at once, and
                this was the only way in that knew WHICH note to show. */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setEditing(null); onShowNotes(editing.id); }}
            >
              {text("notes.open")}
            </Button>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => setEditing(null)}>
                {text("reader.note_cancel")}
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={saving}
                onClick={() => saveNote(editing.id, editing.draft)}
              >
                {text("reader.note_save")}
              </Button>
            </div>
          </div>
        </Surface>
      </div>
    </>
      )}
    </Presence>
  );

  const pills = (
    <>
      {/* The eye wandered off from the voice: offer the way back, never drag. */}
      {marker && !following && reading && (
        <div className={`pointer-events-none absolute inset-x-0 flex justify-center ${paged ? "bottom-8" : "bottom-[calc(var(--shell-bottom-h)+1rem)]"}`}>
          <Button
            className="pointer-events-auto rounded-full shadow-raised"
            onClick={() => {
              setFollowing(true);
              showSegment(marker, "voice");
            }}
          >
            {text("reader.follow")}
          </Button>
        </div>
      )}
    </>
  );

  return (
    <section
      aria-label={chapterInView?.title || undefined}
      className={`relative flex min-h-0 flex-1 flex-col ${paged ? "shell-inset" : ""}`}
    >
      {paged ? (
        <div ref={column} className="relative flex min-h-0 flex-1 flex-col">
          <PageFlow
            chapterIndex={chapterIndex}
            chapterCount={opened.book.chapters.length}
            size={size}
            columns={prefs.columns}
            measureEm={measureEm(prefs.margin)}
            lineHeight={prefs.lineHeight}
            justify={prefs.justify}
            bold={prefs.bold}
            target={target}
            onTargetReached={() => setTarget(null)}
            onChapterChange={onChapterChange}
            onPageShown={onPageShown}
          >
            {opened.book.chapters[chapterIndex] && chapterBody(opened.book.chapters[chapterIndex])}
          </PageFlow>
          {lists}
          {notePeek}
          {noteEditor}
          {pills}
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 gap-5">
          <div className="relative flex min-h-0 flex-1 flex-col">
            <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto">
              <div
                ref={column}
                className="shell-inset-content mx-auto select-text px-2"
                style={{
                  fontSize: `${size}px`,
                  lineHeight: prefs.lineHeight,
                  maxWidth: `${measureEm(prefs.margin)}em`,
                  textAlign: prefs.justify ? "justify" : undefined,
                  fontWeight: prefs.bold ? 600 : undefined,
                }}
              >
                {opened.book.chapters.map((chapter) => (
                  <div key={chapter.id}>{chapterBody(chapter)}</div>
                ))}
              </div>
            </div>
            {lists}
            {notePeek}
            {noteEditor}
            {pills}
          </div>
        </div>
      )}

      {zoomed && (
        <div
          data-lightbox
          className="fixed inset-0 z-30 flex items-center justify-center bg-black/70 p-8"
          onClick={() => setZoomed(null)}
        >
          <img
            src={zoomed.source}
            alt={zoomed.alt}
            onClick={(event) => event.stopPropagation()}
            className="max-h-full max-w-full rounded-2xl"
          />
          <div className="absolute right-4 top-4">
            <IconButton
              onClick={() => setZoomed(null)}
              aria-label={text("reader.figure_close")}
              title={text("reader.figure_close")}
              className="bg-paper"
            >
              <CloseIcon />
            </IconButton>
          </div>
        </div>
      )}
    </section>
  );
}
