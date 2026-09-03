/** The paginated book: one chapter at a time, cut into pages by CSS columns.
 *
 * This is how Apple Books (also WebKit) does it: the chapter flows into
 * columns one page wide, the flow is fixed to the page height, and turning
 * a page is sliding the flow one view to the left. Nothing is measured by
 * hand except where a segment landed, which the browser reports.
 *
 * Positions are addressed by segment id, never by page number: pages
 * change with the type size and the window, segments do not - so the voice,
 * the contents list and the saved place all keep working unchanged.
 */
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { text } from "../i18n";
import { EdgeZone } from "../ui/patterns";
import { columnAt, layoutPages, viewCount, viewStart, type PageLayout } from "../ui/pageLayout";

/** Why a page came on screen. "turn" is the reader's own hand; everything
 * else is the app taking them somewhere, which never counts as wandering. */
export type PageReason = "open" | "voice" | "contents" | "figure" | "turn" | "reflow" | "idle";
/** "__end__" as the segment id opens the chapter on its last page. */
export type PageTarget = { segmentId: string; source: PageReason };

export function PageFlow({
  chapterIndex,
  chapterCount,
  size,
  target,
  onTargetReached,
  onChapterChange,
  onPageShown,
  children,
}: {
  chapterIndex: number;
  chapterCount: number;
  size: number;
  /** A place to show; consumed once the page holding it is on screen. */
  target: PageTarget | null;
  onTargetReached: () => void;
  onChapterChange: (index: number, edge: "start" | "end") => void;
  /** The segments now on screen, first to last - the reflow anchor and the
   * "is the voice still in view" question both come from this. */
  /** Also says which page of how many this is - the screen keeps that as
   * secondary information (a tooltip), never as a line under the page. */
  onPageShown: (segmentIds: string[], reason: PageReason, page: number, pages: number) => void;
  children: ReactNode;
}) {
  const box = useRef<HTMLDivElement>(null);
  const flow = useRef<HTMLDivElement>(null);
  const [layout, setLayout] = useState<PageLayout | null>(null);
  const [boxWidth, setBoxWidth] = useState(0);
  const [pageHeight, setPageHeight] = useState(0);
  const [view, setView] = useState(0);
  const [views, setViews] = useState(1);
  const [animate, setAnimate] = useState(false);
  const reason = useRef<PageReason>("open");
  /* The report callback is read through a ref: it changes identity with
   * every voice position, and a page must be reported once per page shown,
   * not once per identity - a stale "turn" re-reported on a voice advance
   * flagged the reader as having wandered off (advisor, 02/09). */
  const report = useRef(onPageShown);
  useEffect(() => { report.current = onPageShown; }, [onPageShown]);
  /* The first segment on the page that was last shown: when the type size
   * or the window changes, the chapter reflows and this is what stays on
   * screen - the way Apple Books keeps your place through a resize. */
  const anchor = useRef<string | null>(null);
  const layoutKey = useRef("");

  // The page box is whatever the shell leaves between its bars.
  useLayoutEffect(() => {
    const element = box.current;
    if (!element) return;
    const measure = () => {
      const rect = element.getBoundingClientRect();
      setLayout(layoutPages(rect.width, size));
      setBoxWidth(rect.width);
      setPageHeight(Math.floor(rect.height));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [size]);

  const columnOf = useCallback((element: Element): number => {
    const host = flow.current;
    if (!host || !layout) return 0;
    const x = element.getBoundingClientRect().left - host.getBoundingClientRect().left;
    return columnAt(x, layout);
  }, [layout]);

  const countViews = useCallback(() => {
    const host = flow.current;
    if (!host || !layout) return 1;
    const columns = Math.round((host.scrollWidth + layout.gap) / layout.step);
    return viewCount(columns, layout.cols);
  }, [layout]);

  /** The view that shows `segmentId` ("__end__" = the chapter's last). */
  const showing = useCallback((segmentId: string, total: number) => {
    if (!layout) return 0;
    if (segmentId === "__end__") return total - 1;
    const element = flow.current?.querySelector(`[data-segment="${segmentId}"]`);
    const column = element ? columnOf(element) : 0;
    return Math.min(total - 1, viewStart(column, layout.cols) / layout.cols);
  }, [layout, columnOf]);

  // After every layout pass: how many views the chapter takes, and - if a
  // place was asked for - which view holds it.
  useLayoutEffect(() => {
    if (!layout || !pageHeight) return;
    const total = countViews();
    setViews(total);
    const key = `${chapterIndex}:${layout.cols}:${layout.pageWidth}:${pageHeight}:${size}`;
    const reflowed = layoutKey.current !== "" && layoutKey.current !== key && !target;
    layoutKey.current = key;
    if (target) {
      reason.current = target.source;
      // The place the app took the reader to stays the anchor until THEY
      // turn a page: a picture landing a moment later reflows the chapter,
      // and the page must re-find this segment, not the first one it saw.
      anchor.current = target.segmentId === "__end__" ? null : target.segmentId;
      setAnimate(false);
      setView(showing(target.segmentId, total));
      onTargetReached();
    } else if (reflowed && anchor.current) {
      reason.current = "reflow";
      setAnimate(false);
      setView(showing(anchor.current, total));
    } else {
      setView((current) => Math.min(current, total - 1));
    }
  }, [layout, pageHeight, size, target, chapterIndex, countViews, showing, onTargetReached]);

  // Tell the screen what is on the page now.
  useEffect(() => {
    const host = flow.current;
    if (!host || !layout) return;
    const first = view * layout.cols;
    const last = first + layout.cols - 1;
    const shown: string[] = [];
    host.querySelectorAll<HTMLElement>("[data-segment]").forEach((element) => {
      const column = columnOf(element);
      if (column >= first && column <= last) shown.push(element.dataset.segment!);
    });
    // A turn by hand moves the anchor to what is now on the page; the
    // app's own moves keep the segment they aimed at (set above).
    if (reason.current === "turn" && shown[0]) anchor.current = shown[0];
    report.current(shown, reason.current, view + 1, views);
    reason.current = "idle";
  }, [view, views, layout, chapterIndex, columnOf]);

  // A picture arriving after the first layout makes the chapter longer:
  // recount so "Trang 1/2" never turns into "2/3" a page later. Pictures
  // load eagerly on pages (see Figure), but a chapter's images still land
  // after its text.
  useEffect(() => {
    const host = flow.current;
    if (!host) return;
    const recount = () => {
      const total = countViews();
      setViews(total);
      if (anchor.current) {
        reason.current = "reflow";
        setView(showing(anchor.current, total));
      }
    };
    host.addEventListener("load", recount, true);
    const frame = requestAnimationFrame(recount);
    return () => {
      host.removeEventListener("load", recount, true);
      cancelAnimationFrame(frame);
    };
  }, [countViews, showing, chapterIndex]);

  const turn = useCallback((delta: 1 | -1) => {
    reason.current = "turn";
    setAnimate(true);
    if (delta === 1) {
      if (view + 1 < views) setView(view + 1);
      else if (chapterIndex + 1 < chapterCount) onChapterChange(chapterIndex + 1, "start");
    } else if (view > 0) setView(view - 1);
    else if (chapterIndex > 0) onChapterChange(chapterIndex - 1, "end");
  }, [view, views, chapterIndex, chapterCount, onChapterChange]);

  // Keys and the trackpad turn pages; typing fields and the lightbox keep them.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const element = event.target as HTMLElement | null;
      const tag = element?.tagName ?? "";
      // A focused button already answers Space/Enter itself - the arrow
      // would turn twice, play/pause would toggle AND turn.
      if (/INPUT|TEXTAREA|SELECT|BUTTON/.test(tag) || element?.getAttribute("role") === "button") return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (document.querySelector("[data-lightbox]")) return;
      if (["ArrowRight", "ArrowDown", "PageDown", " "].includes(event.key)) { event.preventDefault(); turn(1); }
      else if (["ArrowLeft", "ArrowUp", "PageUp"].includes(event.key)) { event.preventDefault(); turn(-1); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [turn]);

  const wheelLock = useRef(0);
  const onWheel = useCallback((event: React.WheelEvent) => {
    const now = Date.now();
    if (now < wheelLock.current) return;
    const horizontal = Math.abs(event.deltaX) > Math.abs(event.deltaY);
    const delta = horizontal ? event.deltaX : event.deltaY;
    if (Math.abs(delta) < 40) return;
    wheelLock.current = now + 500;
    turn(delta > 0 ? 1 : -1);
  }, [turn]);

  const atBookStart = chapterIndex === 0 && view === 0;
  const atBookEnd = chapterIndex + 1 >= chapterCount && view + 1 >= views;
  const viewWidth = layout ? layout.cols * layout.pageWidth + (layout.cols - 1) * layout.gap : 0;
  // The turn zones own the margin from the box's edge to the page's edge -
  // the 40px of padding plus whatever the page leaves free - minus the 8px a
  // paragraph outdents for its hover wash, so the zone never sits on top of
  // anything a click or a drag on the text could mean.
  const zoneWidth = Math.max(32, Math.round((boxWidth - viewWidth) / 2) + 32);

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      {/* The measured box is the CONTENT box: the padding beside it belongs
          to the arrows, and a spread sized to the padded width ran under
          them (seen at 1300px, 02/09). */}
      <div className="min-h-0 flex-1 px-10" onWheel={onWheel}>
        <div ref={box} className="h-full">
        {/* 8px of air each side inside the clip: a paragraph's hover wash
            outdents that far (-mx-2) and was being cut at the page edge
            (owner, 02/09). The zones stop at this frame's edge. */}
        {layout && pageHeight > 0 && (
          <div className="mx-auto h-full overflow-hidden px-2" style={{ width: viewWidth + 16 }}>
            <div
              ref={flow}
              className="select-text"
              style={{
                height: pageHeight,
                columnWidth: layout.pageWidth,
                columnGap: layout.gap,
                columnFill: "auto",
                fontSize: `${size}px`,
                lineHeight: 1.75,
                transform: `translateX(${-view * layout.cols * layout.step}px)`,
                transition: animate ? "transform 220ms ease-out" : "none",
                ["--page-h" as string]: `${pageHeight}px`,
              }}
            >
              {children}
            </div>
          </div>
        )}
        </div>
      </div>
      <EdgeZone side="left" width={zoneWidth} disabled={atBookStart} label={text("reader.prev_page")} onPress={() => turn(-1)} />
      <EdgeZone side="right" width={zoneWidth} disabled={atBookEnd} label={text("reader.next_page")} onPress={() => turn(1)} />
    </div>
  );
}
