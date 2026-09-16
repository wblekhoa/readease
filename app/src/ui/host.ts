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
