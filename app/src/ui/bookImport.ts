/** RE-HOME-001: keep all native file requests until the shelf catches up. */
export async function drainBookImports<B extends { id: string; damaged?: boolean }>(queue: string[], importOne: (path: string) => Promise<string>, refresh: () => Promise<B[] | null>): Promise<{ book?: B; error?: unknown }> {
  let last: string | undefined;
  let error: unknown;
  let books: B[] | null = null;
  do {
    while (queue.length) {
      try { last = await importOne(queue.shift()!); }
      catch (cause) { error = cause; }
    }
    books = await refresh();
    // A second Finder/drop request can arrive while refresh awaits the engine.
  } while (queue.length);
  return { book: books?.find(book => book.id === last && !book.damaged), error };
}
