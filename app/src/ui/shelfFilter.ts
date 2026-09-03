/** Ordering and filtering of an Apple Books shelf - pure, for node:test.
 *
 * One flat list, most useful first: books that can come in (those carrying
 * highlights before those without), then books already here whose
 * highlights can be synced, then the rest already here, then what cannot
 * come in. The filter is what a person types with or without accents, and
 * it also understands the status words ("drm", "ghi chú") so a long shelf
 * can be narrowed without a separate control.
 */
export type ShelfStatus = "linked" | "importable" | "encrypted" | "too_large" | "missing";
export type ShelfItem = { title: string; status: ShelfStatus; highlights: number };

/** Lowercased, accents and marks stripped, whitespace collapsed. */
export function fold(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

export function priority(item: ShelfItem): number {
  if (item.status === "importable") return item.highlights ? 0 : 1;
  if (item.status === "linked") return item.highlights ? 2 : 3;
  return 4;
}

export function orderShelfItems<T extends ShelfItem>(items: readonly T[]): T[] {
  return [...items].sort((a, b) => priority(a) - priority(b) || a.title.localeCompare(b.title, "vi"));
}

/** Words a status answers to, in the folded form. */
const STATUS_WORDS: Record<ShelfStatus, string> = {
  importable: "nhap duoc import",
  linked: "da co trong thu vien in library",
  encrypted: "drm ma hoa encrypted khong nhap duoc",
  too_large: "qua lon too large khong nhap duoc",
  missing: "khong thay tep missing khong nhap duoc",
};

export function matchesQuery(item: ShelfItem, query: string): boolean {
  const needle = fold(query);
  if (!needle) return true;
  const haystack = `${fold(item.title)} ${STATUS_WORDS[item.status]} ${item.highlights ? "ghi chu highlight" : ""}`;
  return needle.split(" ").every((word) => haystack.includes(word));
}

/** Above this many books the shelf shows a search box. */
export const SEARCH_ABOVE = 6;
