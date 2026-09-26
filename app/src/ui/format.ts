/** Pure formatting for row metadata - kept JSX-free so node:test can load it. */
import { currentLanguage } from "../i18n.ts";

/** "2,1 MB" - enough digits to tell two copies apart, no more. */
export function formatSize(bytes: number | null): string | null {
  if (!bytes) return null;
  const mb = bytes / 1_000_000;
  const locale = currentLanguage() === "vi" ? "vi-VN" : "en-US";
  return `${mb.toLocaleString(locale, { maximumFractionDigits: 1 })} MB`;
}

export function formatDate(stamp: string | null): string | null {
  if (!stamp) return null;
  const date = new Date(stamp.replace(" ", "T") + "Z");
  if (Number.isNaN(date.getTime())) return null;
  const locale = currentLanguage() === "vi" ? "vi-VN" : "en-US";
  return date.toLocaleDateString(locale, {
    day: "2-digit", month: "2-digit", year: "numeric",
  });
}

/** A day in words, the way the interface's language writes one - "10 tháng 9,
 * 2026", "10 September 2026" - never the ISO string the engine stored. A bare
 * day ("2026-09-10") is midnight UTC to `Date`, which is the day BEFORE
 * anywhere west of Greenwich, so it is written in UTC. And it stays on one
 * line: broken after its number, "giá tham khảo 10 / tháng 9, 2026" reads
 * as a price of 10 (27/09). */
export function formatDay(iso: string | null, language = currentLanguage()): string | null {
  if (!iso) return null;
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return iso;
  return when.toLocaleDateString(language === "vi" ? "vi-VN" : "en-GB", {
    day: "numeric", month: "long", year: "numeric",
    timeZone: /^\d{4}-\d{2}-\d{2}$/.test(iso) ? "UTC" : undefined,
  }).replace(/\s/g, "\u00a0");
}

/** What a clipped line should say when hovered: its OWN text, plus anything
 * that did not fit beside it.
 *
 * The Library's fact line was already carrying a tooltip - the chapter the
 * voice is in - while the facts themselves were the part being cut off. So
 * hovering the clipped words answered a question nobody had asked and left
 * the one they had. A tooltip on clipped text owes the text first.
 */
export function hoverText(...parts: unknown[]): string | undefined {
  const said = parts
    .filter((part): part is string => typeof part === "string" && part.trim() !== "")
    .map((part) => part.trim());
  return said.length ? said.join(" · ") : undefined;
}
