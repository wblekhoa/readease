/** True while the window is too short for a floating panel to spend rows on
 * anything but its content.
 *
 * The number is the same one `short-hidden` uses in `index.css`, and it is
 * not a guess: a layer's height cap is `100vh` minus the two bars minus a
 * margin, so at 640px a panel gets about 460 - enough for its chrome and
 * three or four rows of list. Below that the chrome starts eating the list,
 * and at the 423px window the owner measured on 07/09 it ate all of it.
 *
 * Kept in ONE place because CSS and TypeScript both need it and a panel
 * whose stylesheet folds at one height while its script folds at another is
 * a panel with two layouts nobody drew.
 */
import { useEffect, useState } from "react";

export const SHORT_WINDOW = "(max-height: 640px)";

export function useShortWindow(): boolean {
  const [short, setShort] = useState(
    () => typeof window !== "undefined" && window.matchMedia(SHORT_WINDOW).matches,
  );
  useEffect(() => {
    const media = window.matchMedia(SHORT_WINDOW);
    const follow = () => setShort(media.matches);
    follow();
    // Both, because they are not the same promise. `change` is the precise
    // one and fires only when the answer flips; `resize` is the backstop for
    // a host that resizes the viewport without emitting a media-query event,
    // which is exactly what the preview harness does (07/09). A panel that
    // folds its rows only until the first resize is worse than one that
    // never folds them.
    media.addEventListener("change", follow);
    window.addEventListener("resize", follow);
    return () => {
      media.removeEventListener("change", follow);
      window.removeEventListener("resize", follow);
    };
  }, []);
  return short;
}
