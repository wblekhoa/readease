/** What the app says out loud about a reading, for a screen reader (HIG 4.2).
 *
 * A person who is not looking at the screen has to hear three things happen:
 * the voice is being prepared, it started, it stopped. Nothing else - a live
 * region that speaks on every change is a live region people switch off, so
 * the position marker (one per paragraph) and the remaining time stay silent
 * and are read only when asked for.
 *
 * Pure so the rule can be tested without a browser: the caller renders
 * whatever key comes back into an `aria-live="polite"` region. Errors do not
 * come through here; they are already a `role="alert"` notice, which is the
 * right rudeness for something that just cost somebody money.
 */
import type { Playback } from "./playback";

export type AnnounceKey =
  | "a11y.preparing"
  | "a11y.reading"
  | "a11y.paused"
  | "a11y.resumed"
  | "a11y.stopped"
  | "a11y.finished";

/** The announcement for a transition, or null when nothing worth saying
 * changed. `before` is the state the shell was in; `after` the new one. */
export function announcement(before: Playback, after: Playback): AnnounceKey | null {
  if (before.reading === after.reading && before.warming === after.warming) return null;
  if (after.reading === "reading" && after.warming) return "a11y.preparing";
  if (after.reading === "reading" && !after.warming) {
    // Warming ended, or the person pressed resume: two different sentences,
    // because "reading" after a pause is news of a different kind.
    return before.reading === "paused" ? "a11y.resumed" : "a11y.reading";
  }
  if (after.reading === "paused") return "a11y.paused";
  // Idle: the reading either ended by itself or was stopped by the person.
  // `done` clears warming and leaves no error; `stop` is the same shape, so
  // the caller passes which one it was through `after.error` being untouched.
  return before.reading === "idle" ? null : "a11y.stopped";
}
