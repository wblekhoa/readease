/** Which book comes first on the shelf - pure, so node:test can hold it.
 *
 * Books being read lead, the one HEARD most recently first (owner, 23/09:
 * "các sách vừa được nghe gần nhất sẽ lên đầu"): `listened_at` is when a
 * passage of it was last heard, which opening a book does not move. The
 * rest follow, newest import first. Before 23/09 the books being read were
 * ordered by import date too, so the one heard yesterday could sit under
 * one abandoned a week ago. One grid, not a "continue reading" shelf above
 * a grid: on a 3-30 book library that would list the same book twice for
 * the sake of a heading.
 */
export type ShelfBook = {
  id: string;
  segment_id: string | null;
  imported_at: string | null;
  /** When a passage of it was last heard; null (or absent) until then. */
  listened_at?: string | null;
};

export function orderShelf<T extends ShelfBook>(books: readonly T[]): T[] {
  const imported = (book: ShelfBook) => book.imported_at ?? "";
  const heard = (book: ShelfBook) => book.listened_at ?? "";
  return [...books].sort((a, b) => {
    const aReading = a.segment_id ? 1 : 0;
    const bReading = b.segment_id ? 1 : 0;
    if (aReading !== bReading) return bReading - aReading;
    if (aReading) {
      const byEar = heard(b).localeCompare(heard(a));
      if (byEar) return byEar;
    }
    return imported(b).localeCompare(imported(a));
  });
}
