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
