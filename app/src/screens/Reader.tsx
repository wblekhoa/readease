/** The one screen where the content IS the product and chrome is the cost.
 *
 * Two positions are tracked here, not one: where the EYE is (what you have
 * scrolled to, which marks the chapter in the contents) and where the VOICE
 * is (the segment being spoken, painted in `band`). They diverge the moment
 * someone scrolls ahead while listening, and the screen must not fight that -
 * it stops following, and offers a way back instead. Written up in
 * docs/readease-hig.md §3.9.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { text } from "../i18n";
import { Button, IconButton } from "../ui/controls";
import { ListRow } from "../ui/patterns";
import { ChevronLeftIcon, CloseIcon, SidebarIcon } from "../ui/icons";

type BookSegment = { id: string; text: string; kind: string };
type BookFigure = {
  id: string;
  anchor_segment_id: string;
  placement: string;
  alt: string | null;
};
type BookChapter = {
  id: string;
  title: string;
  figures: BookFigure[];
  segments: BookSegment[];
};
type OpenedBook = {
  book: { id: string; title: string; chapters: BookChapter[] };
  progress: { segment_id: string | null };
};

/** Reading size is a CONTENT decision, not the 14px UI scale - and it is a
 * variable rather than a class per step, so nothing drifts. */
const SIZES = [15, 16, 17, 19, 21];
const SIZE_KEY = "readease.reading-size";

function storedSize(): number {
  try {
    const saved = Number(localStorage.getItem(SIZE_KEY));
    return SIZES.includes(saved) ? saved : 16;
  } catch {
    return 16;
  }
}

/** One EPUB figure: modest in the flow of reading, full size on demand. */
function Figure({
  bookId,
  figure,
  onOpen,
}: {
  bookId: string;
  figure: BookFigure;
  onOpen: (source: string, alt: string) => void;
}) {
  const [source, setSource] = useState<string | null>(null);
  const holder = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = holder.current;
    if (!element) return;
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      invoke<{ result: { media_type: string; data: string } }>(
        "engine_request",
        { method: "book.figure", params: { book_id: bookId, figure_id: figure.id } },
      )
        .then((reply) =>
          setSource(`data:${reply.result.media_type};base64,${reply.result.data}`),
        )
        .catch(() => setSource(null));
    }, { rootMargin: "400px" });
    observer.observe(element);
    return () => observer.disconnect();
  }, [bookId, figure.id]);

  return (
    <figure ref={holder} className="my-6">
      {source && (
        <>
          <img
            src={source}
            alt={figure.alt ?? ""}
            title={text("reader.figure_open")}
            onClick={() => onOpen(source, figure.alt ?? "")}
            className="mx-auto max-h-[46vh] max-w-full cursor-zoom-in rounded-2xl"
          />
          {figure.alt && (
            <figcaption className="mt-2 text-center text-xs text-ink-mute">
              {figure.alt}
            </figcaption>
          )}
        </>
      )}
    </figure>
  );
}

export function Reader({
  bookId,
  currentSegment,
  reading,
  onBack,
  onSegments,
  onReadFrom,
  onReadSelection,
}: {
  bookId: string;
  currentSegment: string | null;
  reading: boolean;
  onBack: () => void;
  onSegments: (ids: string[]) => void;
  onReadFrom: (segmentId: string) => void;
  onReadSelection: (text: string) => void;
}) {
  const [opened, setOpened] = useState<OpenedBook | null>(null);
  const [selection, setSelection] = useState("");
  const [showToc, setShowToc] = useState(true);
  const [size, setSize] = useState(storedSize);
  const [seenChapter, setSeenChapter] = useState<string | null>(null);
  const [following, setFollowing] = useState(true);
  const [zoomed, setZoomed] = useState<{ source: string; alt: string } | null>(null);
  const column = useRef<HTMLDivElement>(null);
  const scroller = useRef<HTMLDivElement>(null);

  const marker = currentSegment ?? opened?.progress.segment_id ?? null;

  useEffect(() => {
    const onSelection = () => {
      const active = window.getSelection();
      const inside =
        active &&
        !active.isCollapsed &&
        column.current?.contains(active.anchorNode) &&
        column.current?.contains(active.focusNode);
      setSelection(inside ? active.toString().trim() : "");
    };
    document.addEventListener("selectionchange", onSelection);
    return () => document.removeEventListener("selectionchange", onSelection);
  }, []);

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
      })
      .catch(console.error);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId]);

  const jumpTo = useCallback((segmentId: string, smooth = true) => {
    column.current
      ?.querySelector(`[data-segment="${segmentId}"]`)
      ?.scrollIntoView({ block: "center", behavior: smooth ? "smooth" : "auto" });
  }, []);

  // The voice moved. Follow it only while the reader is still watching the
  // spoken line; if they have scrolled away, leave them where they are.
  useEffect(() => {
    if (!currentSegment || !following) return;
    jumpTo(currentSegment);
  }, [currentSegment, following, jumpTo]);

  // Scroll-spy: the topmost chapter heading at or above the reading line is
  // the one the eye is in. Cheap enough to run on scroll with rAF.
  useEffect(() => {
    const root = scroller.current;
    if (!root || !opened) return;
    let frame = 0;
    const measure = () => {
      frame = 0;
      const line = root.getBoundingClientRect().top + 80;
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
          setFollowing(box.bottom > view.top && box.top < view.bottom);
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
  }, [opened, currentSegment]);

  useEffect(() => {
    if (!zoomed) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setZoomed(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [zoomed]);

  const changeSize = (step: number) => {
    const next = SIZES[Math.min(SIZES.length - 1, Math.max(0, SIZES.indexOf(size) + step))];
    setSize(next);
    try {
      localStorage.setItem(SIZE_KEY, String(next));
    } catch {
      // A reader that cannot remember the size still reads fine.
    }
  };

  if (!opened) return null;
  // The contents mark where the EYE is; `marker` marks where the voice is.
  const activeChapter =
    seenChapter ??
    opened.book.chapters.find((chapter) =>
      chapter.segments.some((segment) => segment.id === marker),
    )?.id;

  return (
    <section className="relative flex min-h-0 flex-1 flex-col">
      <div className="flex items-center gap-1">
        <IconButton onClick={onBack} aria-label={text("reader.back")} title={text("reader.back")}>
          <ChevronLeftIcon />
        </IconButton>
        <IconButton
          onClick={() => setShowToc((value) => !value)}
          aria-label={showToc ? text("reader.toc_hide") : text("reader.toc_show")}
          title={showToc ? text("reader.toc_hide") : text("reader.toc_show")}
          className={showToc ? "text-ink" : ""}
        >
          <SidebarIcon />
        </IconButton>
        <h2 className="m-0 min-w-0 flex-1 truncate px-1 text-base font-bold">
          {opened.book.title}
        </h2>
        <IconButton
          onClick={() => changeSize(-1)}
          disabled={size === SIZES[0]}
          aria-label={text("reader.text_smaller")}
          title={text("reader.text_smaller")}
        >
          <span className="text-xs font-bold">A</span>
        </IconButton>
        <IconButton
          onClick={() => changeSize(1)}
          disabled={size === SIZES[SIZES.length - 1]}
          aria-label={text("reader.text_larger")}
          title={text("reader.text_larger")}
        >
          <span className="text-base font-bold">A</span>
        </IconButton>
      </div>

      <div className="mt-2 flex min-h-0 flex-1 gap-5">
        {showToc && (
          <nav className="w-52 shrink-0 overflow-y-auto pr-1">
            {opened.book.chapters.map((chapter) => (
              <ListRow
                key={chapter.id}
                dense
                active={chapter.id === activeChapter}
                onPress={() => {
                  jumpTo(chapter.segments[0].id);
                  if (reading) onReadFrom(chapter.segments[0].id);
                }}
                title={<span className="truncate text-sm">{chapter.title}</span>}
              />
            ))}
          </nav>
        )}
        <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto">
          <div
            ref={column}
            className="mx-auto max-w-[36em] px-2 pb-16"
            style={{ fontSize: `${size}px`, lineHeight: 1.75 }}
          >
            {opened.book.chapters.map((chapter) => (
              <div key={chapter.id}>
                {chapter.segments.map((segment) => (
                  <div key={segment.id}>
                    {chapter.figures
                      .filter((figure) =>
                        figure.anchor_segment_id === segment.id &&
                        figure.placement === "before")
                      .map((figure) => (
                        <Figure key={figure.id} bookId={bookId} figure={figure} onOpen={(source, alt) => setZoomed({ source, alt })} />
                      ))}
                    <p
                      data-segment={segment.id}
                      data-chapter={segment.kind === "heading" ? chapter.id : undefined}
                      onClick={() => onReadFrom(segment.id)}
                      className={
                        "-mx-2 cursor-pointer rounded-lg px-2 py-1 transition-colors " +
                        (segment.kind === "heading"
                          ? "mt-10 mb-2 text-[1.35em] font-bold leading-snug "
                          : "my-3 ") +
                        (segment.id === marker ? "bg-band" : "hover:bg-wash")
                      }
                    >
                      {segment.text}
                    </p>
                    {chapter.figures
                      .filter((figure) =>
                        figure.anchor_segment_id === segment.id &&
                        figure.placement === "after")
                      .map((figure) => (
                        <Figure key={figure.id} bookId={bookId} figure={figure} onOpen={(source, alt) => setZoomed({ source, alt })} />
                      ))}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* The eye wandered off from the voice: offer the way back, never drag. */}
      {marker && !following && reading && (
        <div className="pointer-events-none absolute inset-x-0 bottom-4 flex justify-center">
          <Button
            className="pointer-events-auto rounded-full shadow-raised"
            onClick={() => {
              setFollowing(true);
              jumpTo(marker);
            }}
          >
            {text("reader.follow")}
          </Button>
        </div>
      )}

      {selection && (
        <div className="pointer-events-none absolute inset-x-0 bottom-4 flex justify-center">
          <Button
            variant="primary"
            className="pointer-events-auto rounded-full px-5 shadow-raised"
            onClick={() => {
              onReadSelection(selection);
              window.getSelection()?.removeAllRanges();
            }}
          >
            {text("reader.selection")}
          </Button>
        </div>
      )}

      {zoomed && (
        <div
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
