/** Which book comes first on the shelf - pure, so node:test can hold it.
 *
 * Books being read lead (the one you will reach for), newest import next;
 * within each group the later import date wins. One grid, not a "continue
 * reading" shelf above a grid: on a 3-30 book library that would list the
 * same book twice for the sake of a heading.
 */
export type ShelfBook = {
  id: string;
  segment_id: string | null;
  imported_at: string | null;
};

export function orderShelf<T extends ShelfBook>(books: readonly T[]): T[] {
  const stamp = (book: ShelfBook) => book.imported_at ?? "";
  return [...books].sort((a, b) => {
    const aReading = a.segment_id ? 1 : 0;
    const bReading = b.segment_id ? 1 : 0;
    if (aReading !== bReading) return bReading - aReading;
    return stamp(b).localeCompare(stamp(a));
  });
}
