/** RE-HOME-001: derive recent content from the library, this session and the
 * paste/scan history kept on this Mac (RE-HIST-001). */
export type RecentBook = { id: string; title: string; imported_at: string | null; listened_at?: string | null; damaged?: boolean };
export type RecentCapture = { at: number; text: string; target?: string };
export type PasteDraft = { text: string; at: number };
export type HomeRecent<B extends RecentBook = RecentBook, C extends RecentCapture = RecentCapture> =
  | { id: string; at: number; kind: "book"; source: B }
  | { id: string; at: number; kind: "paste"; source: PasteDraft }
  | { id: string; at: number; kind: "external"; source: C };
export function homeRecents<B extends RecentBook, C extends RecentCapture>(books: readonly B[], paste: PasteDraft | null, captures: readonly C[], pastes: readonly PasteDraft[] = [], limit = 5): HomeRecent<B, C>[] {
  const items: HomeRecent<B, C>[] = books.filter(book => !book.damaged).map(book => ({
    id: `book:${book.id}`, at: Date.parse(book.listened_at ?? book.imported_at ?? "") || 0, kind: "book", source: book,
  }));
  if (paste?.text.trim()) items.push({ id: "paste", at: paste.at, kind: "paste", source: paste });
  // Stored pastes; the open draft is the same text, so it is not listed twice.
  for (const stored of pastes) if (stored.text.trim() && stored.text !== paste?.text) items.push({ id: `paste:${stored.at}`, at: stored.at, kind: "paste", source: stored });
  for (const capture of captures) if (capture.text.trim() && Number.isFinite(capture.at)) items.push({ id: `external:${capture.at}`, at: capture.at, kind: "external", source: capture });
  return items.sort((a, b) => b.at - a.at).slice(0, limit);
}

/** The book to offer "Continue reading" for: the most recently heard one that
 * is started and not finished. A book only imported is not resumed. */
export function continueBook<B extends RecentBook & { progress_ratio: number | null }>(books: readonly B[]): B | null {
  const started = books.filter(book => !book.damaged && book.listened_at && book.progress_ratio !== null
    && book.progress_ratio > 0 && book.progress_ratio < 0.995);
  started.sort((a, b) => (Date.parse(b.listened_at ?? "") || 0) - (Date.parse(a.listened_at ?? "") || 0));
  return started[0] ?? null;
}

/** "Hôm nay 09:57", "Hôm qua", "3 ngày trước", then the date - how a list
 * of things read recently is scanned. `labels` keeps this pure. */
export function relativeDay(at: number, now: number, locale: string, labels: { today: string; yesterday: string; daysAgo: (n: number) => string }): string {
  if (!at) return "";
  const day = (t: number) => { const d = new Date(t); return Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()); };
  const days = Math.round((day(now) - day(at)) / 86_400_000);
  if (days <= 0) return `${labels.today} ${new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit" }).format(at)}`;
  if (days === 1) return labels.yesterday;
  if (days < 7) return labels.daysAgo(days);
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short" }).format(at);
}
