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
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { text } from "../i18n";
import { Button, IconButton, InlineIconButton, LAYER_GAP, Notice, Surface, Textarea } from "../ui/controls";
import { ListRow } from "../ui/patterns";
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

type BookSegment = { id: string; text: string; kind: string };
type BookFigure = {
  id: string;
  anchor_segment_id: string;
  placement: string;
  alt: string | null;
  /** Per chapter - the same number the voice says in "Xem hình N". */
  number: number;
  /** "Image", "img_01" and friends: an alt that names nothing. Hidden. */
  alt_is_generic: boolean;
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
  book: { id: string; title: string; chapters: BookChapter[] };
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
    if (cued && !paged) holder.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [cued, paged]);

  const alt = figure.alt_is_generic ? "" : figure.alt ?? "";
  const label = text("reader.figure_label", { n: figure.number });

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

export function Reader({
  bookId,
  currentSegment,
  currentFigure,
  reading,
  mode,
  showToc,
  onHideToc,
  showNotes,
  notesFocus,
  onNotes,
  reveal,
  size,
  onSegments,
  onReadFrom,
  onSelection,
  onPageInfo,
}: {
  bookId: string;
  currentSegment: string | null;
  /** Figure whose spoken cue the ear just heard, or null. */
  currentFigure: string | null;
  reading: boolean;
  mode: ReadingMode;
  /** Both live in App: the window has ONE chrome row, and it is the toolbar,
   * so the controls that drive this screen are rendered up there. */
  showToc: boolean;
  onHideToc: () => void;
  showNotes: boolean;
  /** The annotation whose icon opened the panel, if it was opened that way. */
  notesFocus: string | null;
  /** Open (with an optional annotation to focus) or close the notes panel. */
  onNotes: (open: boolean, focusId?: string | null) => void;
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
  /** Why the book would not open, and why one that was deleted came back. */
  const [openError, setOpenError] = useState<string | null>(null);
  const [noteError, setNoteError] = useState<string | null>(null);
  const [seenChapter, setSeenChapter] = useState<string | null>(null);
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

  /* A failed delete explains itself only while the panel it happened in is
   * open. Clearing it in the panel's own onClose was not enough: the toolbar
   * button closes the panel without going through it, so reopening later
   * showed a complaint about something the person had not just done. */
  useEffect(() => {
    if (!showNotes) setNoteError(null);
  }, [showNotes]);

  const marker = currentSegment ?? opened?.progress.segment_id ?? null;
  const flat = useMemo(
    () => opened?.book.chapters.flatMap((chapter) => chapter.segments.map((s) => s.id)) ?? [],
    [opened],
  );
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
        setOpenError(String(error));
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId]);

  const jumpTo = useCallback((segmentId: string, smooth = true) => {
    column.current
      ?.querySelector(`[data-segment="${segmentId}"]`)
      ?.scrollIntoView({ block: "center", behavior: smooth ? "smooth" : "auto" });
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

  // The voice announced a picture: on pages, show the page it is anchored to.
  useEffect(() => {
    if (!paged || !currentFigure || !following || !opened) return;
    const figure = opened.book.chapters.flatMap((c) => c.figures).find((f) => f.id === currentFigure);
    if (figure && !shown.includes(figure.anchor_segment_id)) {
      showSegment(figure.anchor_segment_id, "figure");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentFigure, paged, following, opened, showSegment]);

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

  // The facts about where you are go up to the toolbar's ⓘ - the page
  // itself stays clear of them (owner, 02/09: "giảm bớt nội dung không
  // quan trọng").
  useEffect(() => {
    if (!opened) { onPageInfo(null); return; }
    const chapter = paged
      ? opened.book.chapters[chapterIndex]
      : opened.book.chapters.find((c) => c.id === seenChapter) ?? opened.book.chapters[0];
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
  }, [opened, paged, chapterIndex, seenChapter, shown, pageIndex, flat, marker, chapterOf, onPageInfo]);
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
  /** A paragraph's text with EVERY highlight it carries marked.
   *
   * A paragraph often holds more than one - two sentences marked on
   * different days, a phrase inside a sentence marked whole - and for a
   * while this showed only the first, so a note attached to the second had
   * no icon to open it by. `markParagraph` cuts the paragraph up instead;
   * each piece knows which highlight made it, and so which colour and which
   * note belong to it.
   */
  const marked = (segment: BookSegment) => {
    const items = highlightsBySegment.get(segment.id);
    if (!items) return segment.text;
    const pieces = markParagraph(segment.text, items.map((item) => item.selected_text));
    // Nothing found: hand back the plain string, not a wrapped one.
    if (pieces.every((piece) => piece.index === null)) return segment.text;
    return pieces.map((piece, at) => {
      if (piece.index === null) return <Fragment key={at}>{piece.text}</Fragment>;
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
          <mark data-style={item.style || undefined}>{piece.text}</mark>
        </Fragment>
      );
    });
  };

  const chapterBody = (chapter: BookChapter) =>
    chapter.segments.map((segment) => (
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
            "-mx-2 cursor-text rounded-lg px-2 py-1 transition-colors " +
            (segment.kind === "heading"
              ? (paged ? "mt-2 mb-2 " : "mt-10 mb-2 ") + "text-[1.35em] font-bold leading-snug "
              : "my-3 ") +
            (segment.id === marker ? "bg-band" : "hover:bg-wash")
          }
        >
          {marked(segment)}
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

  /* The contents float over the book in BOTH modes (owner, 02/09: the
   * overlay "quá tối ưu"): closed until asked for, a chapter jumps and
   * closes it. A fixed column would eat the page's own width. In the scroll
   * the panel starts under the header bar; on pages the section already
   * pads for it. */
  const contents = showToc && (
    <Surface
      edge="strong"
      /* Built like NotesPanel, its sibling over the same page: a heading that
         stays put, a way out that is not the toolbar, and only the list
         scrolling under them. It used to be a bare box of rows - the one
         panel in the app with no name on it and no close (owner, 04/09).
         288 rather than 256, because a chapter title is a sentence and this
         is the panel whose whole job is to show them. */
      className={`flex flex-col overflow-hidden absolute left-0 z-10 w-72 shadow-lifted ${
        paged
          ? "top-0 max-h-full"
          : "top-[calc(var(--shell-top-inner)+var(--layer-gap))] layer-capped"
      }`}
    >
      <div className="flex shrink-0 items-center gap-2 px-4 pb-1 pt-3">
        <h3 className="m-0 flex-1 text-sm font-bold">{text("reader.toc_title")}</h3>
        <IconButton onClick={onHideToc} aria-label={text("aria.close")} title={text("aria.close")}>
          <CloseIcon />
        </IconButton>
      </div>
      <nav className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
        {opened.book.chapters.map((chapter, index) => (
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
              onHideToc();
              if (reading) onReadFrom(chapter.segments[0].id);
            }}
            /* Two lines, not one truncated to nothing: a title long enough to
               be cut is the one carrying the most, and this list is read by
               scanning it rather than by width. */
            title={<span className="line-clamp-2 text-sm">{chapter.title}</span>}
          />
        ))}
      </nav>
    </Surface>
  );

  /* Beside the contents, and under the same rule: a row jumps to the place,
   * it never starts speaking. */
  const notes = showNotes && (
    <NotesPanel
      chapters={opened.book.chapters}
      annotations={opened.annotations ?? []}
      paged={paged}
      focusId={notesFocus}
      onNavigate={(segmentId) => {
        showSegment(segmentId, "contents");
        onNotes(false);
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
          setNoteError(String(error));
        });
      }}
      onClose={() => onNotes(false)}
    />
  );

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
      <Surface edge="strong" className="px-3 py-2 text-sm leading-relaxed shadow-lifted">
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
  const noteEditor = editing && (
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
        <Surface edge="strong" className="flex w-[22rem] max-w-full flex-col gap-2 p-3 shadow-lifted">
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
              onClick={() => { setEditing(null); onNotes(true, editing.id); }}
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
    <section className={`relative flex min-h-0 flex-1 flex-col ${paged ? "shell-inset" : ""}`}>
      {paged ? (
        <div ref={column} className="relative flex min-h-0 flex-1 flex-col">
          <PageFlow
            chapterIndex={chapterIndex}
            chapterCount={opened.book.chapters.length}
            size={size}
            target={target}
            onTargetReached={() => setTarget(null)}
            onChapterChange={onChapterChange}
            onPageShown={onPageShown}
          >
            {opened.book.chapters[chapterIndex] && chapterBody(opened.book.chapters[chapterIndex])}
          </PageFlow>
          {contents}
          {notes}
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
                className="shell-inset-content mx-auto max-w-[40em] select-text px-2"
                style={{ fontSize: `${size}px`, lineHeight: 1.75 }}
              >
                {opened.book.chapters.map((chapter) => (
                  <div key={chapter.id}>{chapterBody(chapter)}</div>
                ))}
              </div>
            </div>
            {contents}
            {notes}
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
