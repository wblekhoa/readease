/** Which of the things somebody dropped on the window are books.
 *
 * A drop from Finder arrives as file paths, and people drop whatever they
 * had in hand: a folder, a screenshot, three PDFs and a DMG. Only the two
 * formats the engine reads are imported; the rest is left alone without a
 * word, because "cannot import screenshot.png" beside "imported book.pdf"
 * would be answering a question nobody asked. Order is kept: the shelf
 * lists newest first, so the last one dropped lands on top, the way the
 * files were picked.
 */

export const BOOK_EXTENSIONS = ["pdf", "epub"] as const;

export function bookPaths(paths: readonly string[]): string[] {
  const seen = new Set<string>();
  const books: string[] = [];
  for (const path of paths) {
    const dot = path.lastIndexOf(".");
    if (dot < 0) continue;
    const extension = path.slice(dot + 1).toLowerCase();
    if (!(BOOK_EXTENSIONS as readonly string[]).includes(extension)) continue;
    if (seen.has(path)) continue;
    seen.add(path);
    books.push(path);
  }
  return books;
}
