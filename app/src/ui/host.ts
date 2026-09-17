/** What the page is running in - the Tauri window, or a browser holding the
 * mock - for the one layout fact that differs: the Mac's window buttons.
 *
 * With the title bar an overlay (16/09), the close/minimise/zoom buttons
 * sit over the page's top-left corner, and the column's head and the
 * toolbar leave 52px for them. In a browser there are no buttons, and the
 * gap read as an empty corner (owner, 16/09: "UI đang bị trống ở bên
 * trái") - so the room is left only where the buttons are. */
declare global {
  interface Window {
    __READEASE_MOCK__?: boolean;
  }
}

export const WINDOW_BUTTONS_IN_PAGE =
  typeof window !== "undefined" && "__TAURI_INTERNALS__" in window && !window.__READEASE_MOCK__;

/** Whether the page is inside the Tauri window at all - the mock in a
 * browser is not. The window is transparent behind the side column, where
 * macOS paints its sidebar material (HIG 3.16, owner 17/09: "sidebar sẽ có
 * background blur"); the page paints its own ground everywhere else. */
export const IN_WINDOW = typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

if (IN_WINDOW && typeof document !== "undefined") {
  document.documentElement.dataset.host = "window";
}
