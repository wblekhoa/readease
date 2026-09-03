/** Every highlight in a book, in the order the book reads.
 *
 * The reader receives annotations as a flat list keyed by segment id, in
 * whatever order they were matched. A person looking for "that thing I
 * marked in chapter three" needs them the other way round: by chapter, and
 * inside a chapter by where they fall on the page. Pure, so the ordering is
 * testable without a book on screen.
 */

export type Annotation = {
  id: string;
  segment_id: string;
  selected_text: string;
  note: string | null;
  /** Apple Books' colour number: 1 green, 2 blue, 3 yellow, 4 pink,
   * 5 purple. 0 (or absent) is no colour. */
  style?: number;
};

type Chapter = { id: string; title: string; segments: { id: string }[] };

export type AnnotationGroup = {
  chapterId: string;
  chapterTitle: string;
  items: Annotation[];
};

/** Group by chapter, in document order.
 *
 * An annotation whose segment is not in this book is DROPPED rather than
 * shown under a guessed chapter: it can only come from a stale match, and a
 * row that jumps nowhere is worse than a row that is not there.
 */
export function groupAnnotations(
  chapters: readonly Chapter[],
  annotations: readonly Annotation[],
): AnnotationGroup[] {
  const place = new Map<string, { chapter: number; segment: number }>();
  chapters.forEach((chapter, index) => {
    chapter.segments.forEach((segment, position) => {
      place.set(segment.id, { chapter: index, segment: position });
    });
  });
  const known = annotations.filter((item) => place.has(item.segment_id));
  const ordered = [...known].sort((a, b) => {
    const left = place.get(a.segment_id)!;
    const right = place.get(b.segment_id)!;
    return left.chapter - right.chapter || left.segment - right.segment;
  });
  const groups: AnnotationGroup[] = [];
  for (const item of ordered) {
    const index = place.get(item.segment_id)!.chapter;
    const chapter = chapters[index];
    const last = groups[groups.length - 1];
    if (last && last.chapterId === chapter.id) last.items.push(item);
    else groups.push({ chapterId: chapter.id, chapterTitle: chapter.title, items: [item] });
  }
  return groups;
}

/** How many of them carry a note, for a count that says something. */
export function noteCount(annotations: readonly Annotation[]): number {
  return annotations.filter((item) => item.note).length;
}
