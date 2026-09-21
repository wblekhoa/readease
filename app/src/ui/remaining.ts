/** "Còn ~N phút": how the engine's forecast is rounded for the eye (HIG 3.24).
 *
 * The number is a forecast, so it is never shown finer than a minute, and
 * it always carries the "~". Under half a minute is "under a minute" rather
 * than "0 minutes"; from an hour up, hours and minutes. Pure, so the node
 * runner can pin it without React.
 */

export type RemainingParts =
  | { key: "remaining.under_minute"; params: Record<string, never> }
  | { key: "remaining.minutes"; params: { minutes: number } }
  | { key: "remaining.hours"; params: { hours: number; minutes: number } }
  | { key: "remaining.hours_even"; params: { hours: number } };

export function remainingParts(seconds: number): RemainingParts {
  if (!Number.isFinite(seconds) || seconds < 30) {
    return { key: "remaining.under_minute", params: {} };
  }
  const minutes = Math.max(1, Math.round(seconds / 60));
  if (minutes < 60) return { key: "remaining.minutes", params: { minutes } };
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0
    ? { key: "remaining.hours_even", params: { hours } }
    : { key: "remaining.hours", params: { hours, minutes: rest } };
}

/** Which scope phrase stands before the time: none for the whole document
 * (the natural referent needs no naming), "this chapter" for one, "N
 * chapters" otherwise. Mirrors `cost.scope_*` so the two never disagree. */
export function scopeKey(
  chapters: number | null,
): "cost.scope_one" | "cost.scope_chapters" | null {
  if (chapters === null) return null;
  return chapters === 1 ? "cost.scope_one" : "cost.scope_chapters";
}
