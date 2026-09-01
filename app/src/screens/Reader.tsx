import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { text } from "../i18n";
import { Button, Surface } from "../ui/controls";
import { ListRow } from "../ui/patterns";

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

/** One EPUB figure, fetched lazily the first time it scrolls near view. */
function Figure({ bookId, figure }: { bookId: string; figure: BookFigure }) {
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
    <div ref={holder} className="my-3">
      {source && (
        <img
          src={source}
          alt={figure.alt ?? ""}
          className="mx-auto max-h-[420px] max-w-full rounded-lg"
        />
      )}
    </div>
  );
}
type OpenedBook = {
  book: { id: string; title: string; chapters: BookChapter[] };
  progress: { segment_id: string | null };
};

export function Reader({
  bookId,
  currentSegment,
  onBack,
  onSegments,
  onReadFrom,
  onReadSelection,
}: {
  bookId: string;
  currentSegment: string | null;
  onBack: () => void;
  onSegments: (ids: string[]) => void;
  onReadFrom: (segmentId: string) => void;
  onReadSelection: (text: string) => void;
}) {
  const [opened, setOpened] = useState<OpenedBook | null>(null);
  const [selection, setSelection] = useState("");
  const column = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    if (!currentSegment || !column.current) return;
    column.current
      .querySelector(`[data-segment="${currentSegment}"]`)
      ?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [currentSegment]);

  if (!opened) return null;
  const marker = currentSegment ?? opened.progress.segment_id;
  // Derived, never stored: clicking a paragraph mid-column moves the marker,
  // and the sidebar has to agree with it rather than track its own idea.
  const activeChapter = opened.book.chapters.find((chapter) =>
    chapter.segments.some((segment) => segment.id === marker),
  )?.id;

  return (
    <section className="relative flex min-h-0 flex-1 flex-col">
      <div className="flex items-center gap-3">
        <Button onClick={onBack} className="px-3">
          {text("reader.back")}
        </Button>
        <h2 className="m-0 truncate text-base font-bold">{opened.book.title}</h2>
      </div>
      <div className="mt-3 flex min-h-0 flex-1 gap-4">
        <nav className="w-56 shrink-0 overflow-y-auto">
          {opened.book.chapters.map((chapter) => (
            <ListRow
              key={chapter.id}
              active={chapter.id === activeChapter}
              onPress={() => onReadFrom(chapter.segments[0].id)}
              title={<span className="truncate text-sm">{chapter.title}</span>}
            />
          ))}
        </nav>
        <Surface className="min-h-0 flex-1 overflow-y-auto px-8 py-6">
          <div ref={column}>
          <div className="mx-auto max-w-[65ch] select-text">
            {opened.book.chapters.map((chapter) => (
              <div key={chapter.id}>
                {chapter.segments.map((segment) => (
                  <div key={segment.id}>
                  {chapter.figures
                    .filter((figure) =>
                      figure.anchor_segment_id === segment.id &&
                      figure.placement === "before")
                    .map((figure) => (
                      <Figure key={figure.id} bookId={bookId} figure={figure} />
                    ))}
                  <p
                    data-segment={segment.id}
                    onClick={() => onReadFrom(segment.id)}
                    className={
                      "cursor-pointer rounded-lg px-2 py-1 leading-relaxed transition-colors " +
                      (segment.kind === "heading"
                        ? "mt-5 text-base font-bold "
                        : "text-sm ") +
                      (segment.id === marker
                        ? "bg-band"
                        : "hover:bg-wash")
                    }
                  >
                    {segment.text}
                  </p>
                  {chapter.figures
                    .filter((figure) =>
                      figure.anchor_segment_id === segment.id &&
                      figure.placement === "after")
                    .map((figure) => (
                      <Figure key={figure.id} bookId={bookId} figure={figure} />
                    ))}
                  </div>
                ))}
              </div>
            ))}
          </div>
          </div>
        </Surface>
      </div>
      {selection && (
        <div className="pointer-events-none absolute inset-x-0 bottom-16 flex justify-center">
          <Button
            variant="primary"
            className="pointer-events-auto h-[32px] rounded-full px-5 shadow-lg"
            onClick={() => {
              onReadSelection(selection);
              window.getSelection()?.removeAllRanges();
            }}
          >
            {text("reader.selection")}
          </Button>
        </div>
      )}
    </section>
  );
}
