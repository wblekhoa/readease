/** ReadEase as the system's now-playing app (HIG 3.19), lifted out of App.
 *
 * Two halves of one conversation with macOS: what the system is told about
 * the reading (title, chapter, state, cover), and what it sends back when
 * somebody presses F8, squeezes an AirPod or uses Control Center. Both are
 * only ever true inside the real window - the preview harness has no host to
 * answer, which is what `inWindow` is for.
 */
import { useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { artworkPayload } from "./nowPlaying";
import { useCover } from "./useCover";
import { text } from "../i18n";
import type { Reading } from "./playback";
import type { LibraryBook } from "../screens/Library";

/** Where the reading came from: a document, pasted text, or a selection
 * captured from another app. Null when nothing has been read yet. */
export type ReadingOrigin =
  | { kind: "book"; book: LibraryBook }
  | { kind: "paste" }
  | { kind: "external" }
  | null;

/** The commands the system can send. They go through the page's own
 * dispatcher (HIG 4.1), so a key, a menu item and an earbud all take the
 * same road. */
export type MediaCommand = "play-pause" | "stop";

export function useNowPlaying({
  reading,
  origin,
  chapterTitle,
  language,
  inWindow,
  perform,
}: {
  reading: Reading;
  origin: ReadingOrigin;
  /** The chapter the voice is in, for the second line. */
  chapterTitle?: string;
  /** Re-sent when the interface language changes: "Paste text" is a label,
   * and the system shows it to the person. */
  language: string;
  inWindow: boolean;
  perform: (command: MediaCommand) => void;
}) {
  /* The cover rides along for a document - its bytes once per document, the
     key alone after that (`artworkPayload`); the shelf's own cover cache
     answers, so nothing is fetched twice. */
  const cover = useCover(origin?.kind === "book" ? origin.book.id : null);
  const sentArtwork = useRef<string | null>(null);
  const dispatch = useRef(perform);
  dispatch.current = perform;

  useEffect(() => {
    if (!inWindow) return;
    const artwork = origin?.kind === "book" && reading !== "idle"
      ? artworkPayload(origin.book.id, cover, sentArtwork.current)
      : null;
    const info = reading === "idle"
      ? { title: "", subtitle: "", state: "stopped" }
      : origin?.kind === "book"
        ? { title: origin.book.title, subtitle: chapterTitle ?? "", state: reading, artwork }
        : origin?.kind === "external"
          ? { title: text("nav.external"), subtitle: text("now_playing.selection"), state: reading }
          : { title: text("nav.paste"), subtitle: "", state: reading };
    invoke("now_playing", { info })
      .then(() => { if (artwork) sentArtwork.current = artwork.key; })
      .catch((error: unknown) => console.error("[now playing]", error));
  }, [inWindow, reading, origin, chapterTitle, language, cover]);

  useEffect(() => {
    if (!inWindow) return;
    const heard = listen<string>("media:command", (event) => {
      const command = event.payload;
      // A command against the state is ignored, never inverted: "play"
      // while playing must not pause.
      if (command === "toggle") dispatch.current("play-pause");
      else if (command === "play" && reading === "paused") dispatch.current("play-pause");
      else if (command === "pause" && reading === "reading") dispatch.current("play-pause");
      else if (command === "stop" && reading !== "idle") dispatch.current("stop");
    });
    return () => { heard.then((unlisten) => unlisten()).catch(() => undefined); };
  }, [inWindow, reading]);
}
