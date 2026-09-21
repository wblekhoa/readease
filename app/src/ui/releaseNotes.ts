/**
 * The release notes as the update sheet shows them (HIG 3.20). Pure, so
 * the node tests can read it without React or the Tauri plugins.
 */
/** Markdown is what the release notes are written in, hard-wrapped at 72
 * columns; on this sheet the wraps are undone (a line that is not a bullet
 * continues the one before it), headings are dropped and emphasis stripped, and a
 * bullet becomes a paragraph of its own - eight at most. */
export function excerpt(notes: string): string {
  const paragraphs: string[] = [];
  for (const raw of notes.split("\n")) {
    // A heading is the version, which the sheet already says.
    if (/^#+\s/.test(raw)) { paragraphs.push(""); continue; }
    const line = raw.replace(/\*\*/g, "").trim();
    if (line.length === 0 || line === "---") { paragraphs.push(""); continue; }
    const bullet = /^[-*]\s+/.test(line);
    const text = bullet ? "• " + line.replace(/^[-*]\s+/, "") : line;
    const last = paragraphs.length - 1;
    if (!bullet && last >= 0 && paragraphs[last].length > 0) paragraphs[last] += " " + text;
    else paragraphs.push(text);
  }
  return paragraphs.filter((p) => p.length > 0).slice(0, 8).join("\n");
}

/** The manifest's `pub_date` (RFC 3339) as a short local date; the raw
 * string when it will not parse. */
export function releaseDate(iso: string, locale = "vi"): string {
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return iso;
  return when.toLocaleDateString(locale === "vi" ? "vi-VN" : "en-GB", { day: "numeric", month: "long", year: "numeric" });
}
