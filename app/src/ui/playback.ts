/** The playback state machine, as a pure function.
 *
 * It lived as five hand-written `setReading(...)` calls scattered through
 * App.tsx, and the scattering is what the owner felt: two of the five forgot
 * to clear the warming notice, and Stop waited for the engine to answer
 * before the button changed - so pressing Stop looked like nothing happened,
 * and people pressed it again (2026-09-02).
 *
 * The rules here are about the SHELL's own state only. What the audio does is
 * the Rust client's business; this decides what the person sees, immediately.
 */

export type Reading = "idle" | "reading" | "paused";

export interface Playback {
  reading: Reading;
  /** True from asking for speech until the first audio arrives. */
  warming: boolean;
  /** Last failure to report, cleared by any fresh attempt. */
  error: string | null;
}

export const IDLE: Playback = { reading: "idle", warming: false, error: null };

export type PlaybackEvent =
  /** The person asked for speech: a book, pasted text, a selection. */
  | { type: "start" }
  /** The person asked to stop. Applied BEFORE the engine is told, on purpose. */
  | { type: "stop" }
  /** The person toggled pause/resume. */
  | { type: "toggle" }
  /** The request could not even be sent. */
  | { type: "failed"; error?: string | null }
  /** First audio of this reading reached the speakers. */
  | { type: "voice" }
  /** The engine finished this reading, well or badly. */
  | { type: "done"; error?: string | null };

export function playback(state: Playback, event: PlaybackEvent): Playback {
  switch (event.type) {
    case "start":
      // A new reading always supersedes; the Rust client cancels the old one,
      // so the shell must not carry the old one's warming or error forward.
      return { reading: "reading", warming: true, error: null };
    case "stop":
      // Optimistic by design: the engine round trip can take a moment (it
      // answers a stop between utterances), and a transport that waits for it
      // reads as broken.
      return { reading: "idle", warming: false, error: state.error };
    case "toggle":
      if (state.reading === "reading") return { ...state, reading: "paused" };
      if (state.reading === "paused") return { ...state, reading: "reading" };
      return state;
    case "failed":
      return { reading: "idle", warming: false, error: event.error ?? null };
    case "voice":
      // Only meaningful while something is playing; a late frame from a
      // superseded reading must not revive a stopped transport.
      return state.reading === "idle" ? state : { ...state, warming: false };
    case "done":
      return { reading: "idle", warming: false, error: event.error ?? null };
  }
}
