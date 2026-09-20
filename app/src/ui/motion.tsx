/**
 * The app's motion, in one place (HIG 3.17, 20/09): a floating layer that
 * enters and LEAVES, and the two facts every animation has to respect - the
 * person's Reduce Motion setting, and a window that is not on screen.
 *
 * The numbers themselves live in index.css as tokens (`--dur-*`, `--ease-*`);
 * nothing here knows a millisecond.
 */
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";

/** How long a leaving layer stays mounted, read from the token so the two
 * cannot drift. A window that is hidden, or a person who asked for less
 * motion, gets it at whatever the stylesheet says for them. */
function exitMs(): number {
  if (typeof window === "undefined") return 0;
  const raw = getComputedStyle(document.documentElement).getPropertyValue("--dur-exit").trim();
  const value = parseFloat(raw);
  if (!Number.isFinite(value)) return 0;
  return raw.endsWith("ms") ? value : value * 1000;
}

/** Keeps a floating layer mounted for the length of its exit, and tells the
 * stylesheet which way it is going.
 *
 * React unmounts a layer the frame `open` turns false, which is a layer
 * vanishing mid-frame - the thing §3.17 reversed on 20/09. So the last
 * children rendered while open are remembered and drawn once more, under
 * `data-state="closed"`, for `--dur-exit`; the CSS on `.layer-*` does the
 * fading. Remembered rather than re-rendered because the props the child
 * needs may already be gone (a settings panel whose settings went null).
 *
 * Entering is the same door the other way: the first paint is `closed`, the
 * next frame flips to `open`, and the transition runs from one to the other.
 * Not `@starting-style`: in a WKWebView that is hidden the timeline stands
 * still and an element stays at its starting state (measured 16/09, §3.16).
 * A wrapper of `display: contents` so the layer's own positioning is
 * untouched; `pointer-events: none` while leaving, so nothing can be pressed
 * on the way out. */
export function Presence({ open, children }: { open: boolean; children: ReactNode }) {
  const [mounted, setMounted] = useState(open);
  const [state, setState] = useState<"open" | "closed">("closed");
  const last = useRef<ReactNode>(children);
  if (open) last.current = children;

  useLayoutEffect(() => {
    if (open) {
      setMounted(true);
      // One frame at `closed` so there is a state to transition FROM; a
      // hidden window skips it (html[data-hidden] zeroes the durations).
      const frame = requestAnimationFrame(() => setState("open"));
      return () => cancelAnimationFrame(frame);
    }
    setState("closed");
    const timer = window.setTimeout(() => setMounted(false), exitMs());
    return () => window.clearTimeout(timer);
  }, [open]);

  if (!open && !mounted) return null;
  return (
    <div data-state={state} className="contents">
      {open ? children : last.current}
    </div>
  );
}

/** Marks the document while its window is off screen, so the stylesheet can
 * zero every transition: a layer opened while the window is hidden must not
 * sit at opacity 0 waiting for a timeline that is not running. Called once,
 * at the root. */
export function useHiddenGuard() {
  useEffect(() => {
    const sync = () => {
      if (document.visibilityState === "hidden") {
        document.documentElement.dataset.hidden = "";
      } else {
        delete document.documentElement.dataset.hidden;
      }
    };
    sync();
    document.addEventListener("visibilitychange", sync);
    return () => document.removeEventListener("visibilitychange", sync);
  }, []);
}

/** `scrollIntoView`'s behaviour for a place the PERSON asked for: smooth,
 * unless they asked the system for less motion (Apple replaces a scroll
 * with a cut under Reduce Motion). Following the voice stays instant and
 * never comes through here. */
export function scrollBehavior(): ScrollBehavior {
  if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return "auto";
  }
  return "smooth";
}
