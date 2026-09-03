/** Pages or a scroll - the owner's default is pages (02/09), the scroll
 * stays as a choice the way Apple Books keeps it. */
export type ReadingMode = "pages" | "scroll";
const KEY = "readease.reading-mode";

export function storedReadingMode(): ReadingMode {
  try {
    return localStorage.getItem(KEY) === "scroll" ? "scroll" : "pages";
  } catch {
    return "pages";
  }
}

export function rememberReadingMode(mode: ReadingMode): void {
  try {
    localStorage.setItem(KEY, mode);
  } catch {
    // Forgetting the mode costs one click, never a page.
  }
}
