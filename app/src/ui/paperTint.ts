/** Paper covers for documents that have none of their own (owner, 23/10:
 * "hướng A · Trang giấy … font giữ không chân … random màu thông minh").
 *
 * A Markdown note or a Word file has no artwork, and a grey slab with its
 * title said nothing. So it gets a sheet of tinted paper. The tint is
 * "random" the way a person would want it:
 *
 *  - stable: the same document is the same colour every launch, on every
 *    Mac - it comes from a hash of the book's id, not from Math.random;
 *  - never twinned: two documents side by side on the shelf never share a
 *    tint (the second steps on to the next free hue);
 *  - calm in both themes: every hue is a DS `-matte` paper with its `-stress`
 *    ink, so the pair is contrast-checked by the token set, light and dark.
 *
 * Pure, so node:test holds the rules.
 */

/** DS hues with a paper (`--fill-{hue}-matte`) and an ink
 * (`--text-color-{hue}-stress`), in an order where neighbours differ. */
export const PAPER_HUES = ["deepsky", "orange", "teal", "pink", "lemon", "purple", "success", "plum"] as const;
export type PaperHue = (typeof PAPER_HUES)[number];

/** FNV-1a, 32 bit: small, fast, and spreads short ids evenly. */
export function hashText(value: string): number {
  let hash = 0x811c9dc5;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash >>> 0;
}

/** Formats that bring their own cover (or the publisher's look). Everything
 * else on the shelf is a document and gets paper when it has no cover. */
const BOOK_FORMATS = new Set(["epub", "pdf"]);

export function wantsPaper(format: string): boolean {
  return !BOOK_FORMATS.has(format.toLowerCase());
}

/** A tint for every document, in shelf order. Each starts from its own
 * hash; one that would match the document just before it on the shelf
 * takes the next hue round the wheel instead. Only the left neighbour is
 * avoided - the row above changes with the window's width, and a colour
 * that shifted on a resize would not be "the same document". */
export function paperHues(ids: readonly string[]): Map<string, PaperHue> {
  const out = new Map<string, PaperHue>();
  let previous: PaperHue | null = null;
  for (const id of ids) {
    let index = hashText(id) % PAPER_HUES.length;
    if (PAPER_HUES[index] === previous) index = (index + 1) % PAPER_HUES.length;
    const hue = PAPER_HUES[index];
    out.set(id, hue);
    previous = hue;
  }
  return out;
}
