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
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { text } from "../i18n";
import { Button, IconButton, Surface } from "../ui/controls";
import { ListRow } from "../ui/patterns";
import { CloseIcon, NoteIcon } from "../ui/icons";
import { splitHighlight } from "../ui/highlight";
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
  /** The chapter a "read" would resume in - null when the book is untouched
   * and reading would start from the beginning. */
  resumeChapterTitle: string | null;
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

export function Reader({
  bookId,
  currentSegment,
  currentFigure,
  reading,
  mode,
  showToc,
  onHideToc,
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
  size: number;
  onSegments: (ids: string[]) => void;
  onReadFrom: (segmentId: string) => void;
  /** The words currently selected in the book, "" when none - the footer
   * turns them into a button (owner, 02/09: the pill left the page). */
  onSelection: (text: string) => void;
  onPageInfo: (info: PageInfo | null) => void;
}) {
  const [opened, setOpened] = useState<OpenedBook | null>(null);
  const [seenChapter, setSeenChapter] = useState<string | null>(null);
  const [following, setFollowing] = useState(true);
  const [zoomed, setZoomed] = useState<{ source: string; alt: string } | null>(null);
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
      .catch(console.error);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId]);

  const jumpTo = useCallback((segmentId: string, smooth = true) => {
    column.current
      ?.querySelector(`[data-segment="${segmentId}"]`)
      ?.scrollIntoView({ block: "center", behavior: smooth ? "smooth" : "auto" });
  }, []);

  /** Show a place, in whichever mode is on. */
  const showSegment = useCallback((segmentId: string, source: PageReason) => {
    if (paged) {
      setChapterIndex(chapterOf(segmentId));
      setTarget({ segmentId, source });
    } else {
      jumpTo(segmentId);
    }
  }, [paged, chapterOf, jumpTo]);

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
    onPageInfo({
      page: paged ? pageIndex?.page : undefined,
      pages: paged ? pageIndex?.pages : undefined,
      chapterTitle: chapter?.title ?? "",
      percent,
      resumeChapterTitle: resume?.title ?? null,
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

  const highlightsBySegment = useMemo(() => {
    const map = new Map<string, BookAnnotation[]>();
    for (const item of opened?.annotations ?? []) {
      map.set(item.segment_id, [...(map.get(item.segment_id) ?? []), item]);
    }
    return map;
  }, [opened]);

  if (!opened) return null;
  // The contents mark where the EYE is; `marker` marks where the voice is.
  const activeChapter =
    seenChapter ??
    opened.book.chapters.find((chapter) =>
      chapter.segments.some((segment) => segment.id === marker),
    )?.id;
  /** A paragraph's text with its highlights marked - the first highlight
   * whose words are found; the rest of the paragraph stays plain. */
  const marked = (segment: BookSegment) => {
    const items = highlightsBySegment.get(segment.id);
    if (!items) return segment.text;
    for (const item of items) {
      const split = splitHighlight(segment.text, item.selected_text);
      if (!split) continue;
      return (
        <>
          {split.before}
          <mark title={item.note ?? undefined}>{split.mark}</mark>
          {item.note && (
            <span className="ml-0.5 inline-flex align-middle text-ink-mute" title={item.note} aria-label={text("reader.note")}>
              <NoteIcon />
            </span>
          )}
          {split.after}
        </>
      );
    }
    return segment.text;
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
      className={`absolute left-0 z-10 w-64 overflow-y-auto p-2 shadow-lifted ${
        paged
          ? "top-0 max-h-full"
          : "top-[calc(var(--shell-top-h)+0.5rem)] max-h-[calc(100%-var(--shell-top-h)-var(--shell-bottom-h)-1rem)]"
      }`}
    >
      <nav>
        {opened.book.chapters.map((chapter, index) => (
          <ListRow
            key={chapter.id}
            dense
            active={chapter.id === activeChapter}
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
            title={<span className="truncate text-sm">{chapter.title}</span>}
          />
        ))}
      </nav>
    </Surface>
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
