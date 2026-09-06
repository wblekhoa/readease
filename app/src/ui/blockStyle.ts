/** How a block of book text should LOOK, decided from what the importer
 * says it is and from what the book itself put in the text.
 *
 * Measured over the owner's nine books (05-06/09) before any rule: 30-66% of
 * segments are `split` tails of a longer paragraph, cut for the voice; list
 * items arrive three ways (a "•" glyph in the text, a "1." in the text, or
 * clean); and translated books use <blockquote> both for real quotations
 * and for one-to-three-word diagram labels. Pure functions, so the rules
 * are testable without a page. */

export type Joint = "block" | "line" | "split";

/** A marker the book wrote INTO the text of a list item. Only list items
 * are looked at: a paragraph opening with "1." may be prose. */
const LEAD = /^\s*(?:([•·◦▪‣●■\-–—*])|(\(?\d{1,3}[.)])|([a-zA-Z][.)]))\s+/;

export type ListLead = {
  /** What to draw in the gutter: a dot for a glyph, the book's own number
   * ("1.", "a)") for an enumerated item. */
  marker: { kind: "dot" } | { kind: "number"; label: string };
  /** The item's text without the marker the book typed in front of it. */
  rest: string;
};

export function listLead(text: string): ListLead {
  const match = text.match(LEAD);
  if (!match) return { marker: { kind: "dot" }, rest: text };
  const rest = text.slice(match[0].length);
  if (match[1]) return { marker: { kind: "dot" }, rest };
  return { marker: { kind: "number", label: (match[2] ?? match[3]).trim() }, rest };
}

/** A <blockquote> is a quotation when it reads like one. A block of one to
 * three words with no closing punctuation is a label - a diagram's caption
 * word, a name under a quotation - and is drawn small, not indented. */
export function quoteRole(text: string): "quotation" | "label" {
  const trimmed = text.trim();
  const words = trimmed.split(/\s+/).filter(Boolean).length;
  const closed = /[.!?…:;"”’)]$/.test(trimmed);
  return words <= 3 && !closed ? "label" : "quotation";
}

/** Does this block continue the one before it (a cut paragraph), so the
 * page must not open a paragraph gap above it? */
export function continues(joint: Joint | undefined): boolean {
  return joint === "split";
}
