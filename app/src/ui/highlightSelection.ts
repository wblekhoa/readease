/** A selection on the page, paragraph by paragraph (RE-NOTE-005).
 *
 * A highlight is kept as the words of each paragraph it covers - Books'
 * shape, and the shape `markParagraph` draws. So a selection is cut at the
 * paragraphs it crosses, and each cut is read as the page prints it, minus
 * what is on the page but not in the book: the voice's position control,
 * the note icon, anything only a screen reader hears.
 */
export type SelectedPiece = { segment_id: string; selected_text: string };

const NOT_THE_BOOK = "button, [aria-hidden], .sr-only";

export function selectionPieces(selection: Selection | null, root: HTMLElement | null): SelectedPiece[] {
  if (!selection || !root || selection.isCollapsed || selection.rangeCount === 0) return [];
  const range = selection.getRangeAt(0);
  if (!root.contains(range.commonAncestorContainer)) return [];
  const pieces: SelectedPiece[] = [];
  for (const paragraph of root.querySelectorAll<HTMLElement>("[data-segment]")) {
    if (!range.intersectsNode(paragraph)) continue;
    const part = document.createRange();
    part.selectNodeContents(paragraph);
    if (range.compareBoundaryPoints(Range.START_TO_START, part) > 0) part.setStart(range.startContainer, range.startOffset);
    if (range.compareBoundaryPoints(Range.END_TO_END, part) < 0) part.setEnd(range.endContainer, range.endOffset);
    const copy = part.cloneContents();
    copy.querySelectorAll(NOT_THE_BOOK).forEach((node) => node.remove());
    const words = (copy.textContent ?? "").replace(/\s+/g, " ").trim();
    if (words) pieces.push({ segment_id: paragraph.dataset.segment!, selected_text: words });
  }
  return pieces;
}
