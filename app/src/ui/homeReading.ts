/** RE-HOME-001: derive recent content from the library and this session only. */
export type RecentBook = { id: string; title: string; imported_at: string | null; listened_at?: string | null; damaged?: boolean };
export type RecentCapture = { at: number; text: string; target?: string };
export type PasteDraft = { text: string; at: number };
export type HomeRecent<B extends RecentBook = RecentBook, C extends RecentCapture = RecentCapture> =
  | { id: string; at: number; kind: "book"; source: B }
  | { id: string; at: number; kind: "paste"; source: PasteDraft }
  | { id: string; at: number; kind: "external"; source: C };
export function homeRecents<B extends RecentBook, C extends RecentCapture>(books: readonly B[], paste: PasteDraft | null, captures: readonly C[]): HomeRecent<B, C>[] {
  const items: HomeRecent<B, C>[] = books.filter(book => !book.damaged).map(book => ({
    id: `book:${book.id}`, at: Date.parse(book.listened_at ?? book.imported_at ?? "") || 0, kind: "book", source: book,
  }));
  if (paste?.text.trim()) items.push({ id: "paste", at: paste.at, kind: "paste", source: paste });
  for (const capture of captures) if (capture.text.trim() && Number.isFinite(capture.at)) items.push({ id: `external:${capture.at}`, at: capture.at, kind: "external", source: capture });
  return items.sort((a, b) => b.at - a.at).slice(0, 5);
}
