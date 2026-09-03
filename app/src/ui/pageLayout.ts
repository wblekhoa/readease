/** How a chapter is cut into pages - pure, so node:test can hold the rules.
 *
 * The owner chose (02/09) the shape every reading app converges on: pages,
 * not a scroll; two pages side by side when the window is wide and the type
 * is not large; each page no wider than the reading measure. Chapter
 * boundaries are page boundaries, as in Apple Books, which keeps the layout
 * work to one chapter at a time on a 6,700-segment book.
 */
export const PAGE_GAP = 48;
/** The reading measure in em - the same 40em the scroll column uses. */
export const MEASURE_EM = 40;
/** Two pages need this much reading area (about an 1100px window). */
export const SPREAD_MIN_AREA = 1040;
/** Above this size one page is already plenty of text; a spread would be two
 * narrow columns of big type. */
export const SPREAD_MAX_SIZE = 19;

export type PageLayout = { cols: 1 | 2; pageWidth: number; gap: number; step: number };

export function layoutPages(areaWidth: number, size: number): PageLayout {
  const cols: 1 | 2 = areaWidth >= SPREAD_MIN_AREA && size <= SPREAD_MAX_SIZE ? 2 : 1;
  const measure = size * MEASURE_EM;
  const available = Math.floor((areaWidth - PAGE_GAP * (cols - 1)) / cols);
  const pageWidth = Math.max(240, Math.min(measure, available));
  return { cols, pageWidth, gap: PAGE_GAP, step: pageWidth + PAGE_GAP };
}

/** The column a point `x` (from the flow's left edge) falls in. */
export function columnAt(x: number, layout: PageLayout): number {
  return Math.max(0, Math.floor((x + layout.gap / 2) / layout.step));
}

/** The first column of the view that shows `column`. */
export function viewStart(column: number, cols: number): number {
  return column - (column % cols);
}

/** How many views a chapter of `totalColumns` columns takes. */
export function viewCount(totalColumns: number, cols: number): number {
  return Math.max(1, Math.ceil(totalColumns / cols));
}
