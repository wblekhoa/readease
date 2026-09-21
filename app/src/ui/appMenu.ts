/**
 * The menu bar (HIG 4.1, 20/09): every command's home, with its shortcut
 * beside it - Apple's rule that the menu is where a command is FOUND, and
 * the window's buttons are only the short way to it.
 *
 * Built from the page with Tauri's menu API rather than in Rust, so the
 * labels sit with the rest of `i18n.ts` and the actions with the state
 * they act on. The seven predefined items of the Edit menu are the ones a
 * custom menu must never drop: without them ⌘C/⌘V die in every field.
 *
 * Rebuilt whenever what it says or allows changes (language, a document
 * open or not, the reading state, the column, the appearance) - a handful
 * of times a session, cheaper than keeping hold of every item.
 */
import { getVersion } from "@tauri-apps/api/app";
import { CheckMenuItem, Menu, MenuItem, PredefinedMenuItem, Submenu } from "@tauri-apps/api/menu";
import { text } from "../i18n";
import type { ThemePreference } from "./theme";

/** Every command the menu can issue. `App.tsx::perform` answers each one,
 * and the page's own key handler issues the same names in the browser. */
export type MenuCommand =
  | "add-to-library"
  | "apple-books"
  | "close-document"
  | "find"
  | "toggle-sidebar"
  | "go-1" | "go-2" | "go-3" | "go-4"
  | "text-larger" | "text-smaller" | "text-default"
  | "appearance-light" | "appearance-dark" | "appearance-system"
  | "play-pause"
  | "stop"
  | "read-selection"
  | "voice-settings"
  | "hub"
  | "help-guide" | "help-feedback" | "help-releases" | "help-logs"
  | "check-updates";

export interface MenuState {
  /** A document is open: the ⌘1-⌘3 items name its lists, ⌘W and ⌘F and
   * the text sizes come alive. */
  inBook: boolean;
  reading: "idle" | "reading" | "paused";
  sideOpen: boolean;
  appearance: ThemePreference;
  /** Something is selected on the page, so "Read Selection" can. */
  hasSelection: boolean;
}

export const HELP_URLS = {
  "help-guide": "https://github.com/wblekhoa/readease#readme",
  "help-feedback": "https://github.com/wblekhoa/readease/issues/new",
  "help-releases": "https://github.com/wblekhoa/readease/releases/latest",
} as const;

/** Builds the whole bar and installs it. Returns the menu so the caller
 * can drop it when the next one replaces it. */
export async function installAppMenu(
  state: MenuState,
  perform: (command: MenuCommand) => void,
): Promise<Menu> {
  const version = await getVersion().catch(() => "");
  const item = (id: MenuCommand, label: string, accelerator?: string, enabled = true) =>
    MenuItem.new({ id, text: label, accelerator, enabled, action: () => perform(id) });
  const check = (id: MenuCommand, label: string, checked: boolean) =>
    CheckMenuItem.new({ id, text: label, checked, action: () => perform(id) });
  const separator = () => PredefinedMenuItem.new({ item: "Separator" });

  const app = await Submenu.new({
    text: "ReadEase",
    items: [
      await PredefinedMenuItem.new({
        text: text("menu.about"),
        item: {
          About: {
            name: "ReadEase — Thư Âm",
            version,
            copyright: "© 2026 Khoa Le",
            license: "PolyForm Noncommercial 1.0.0",
            website: "https://github.com/wblekhoa/readease",
            websiteLabel: "github.com/wblekhoa/readease",
          },
        },
      }),
      // Apple's slot for it: right under About (HIG 3.20).
      await item("check-updates", text("menu.check_updates")),
      await separator(),
      await PredefinedMenuItem.new({ text: text("menu.services"), item: "Services" }),
      await separator(),
      await PredefinedMenuItem.new({ text: text("menu.hide"), item: "Hide" }),
      await PredefinedMenuItem.new({ text: text("menu.hide_others"), item: "HideOthers" }),
      await PredefinedMenuItem.new({ text: text("menu.show_all"), item: "ShowAll" }),
      await separator(),
      await PredefinedMenuItem.new({ text: text("menu.quit"), item: "Quit" }),
    ],
  });

  const file = await Submenu.new({
    text: text("menu.file"),
    items: [
      // ⇧⌘O, Books' own "Add to Library" chord: ⌘O is kept for "open a
      // document", which a shelf app does not have.
      await item("add-to-library", text("menu.add_to_library"), "Shift+Cmd+O"),
      await item("apple-books", text("menu.apple_books")),
      await separator(),
      // ⌘W closes the DOCUMENT: this is a one-window app, and the system's
      // Close Window would leave an app with nothing to show.
      await item("close-document", text("menu.close_document"), "Cmd+W", state.inBook),
    ],
  });

  const edit = await Submenu.new({
    text: text("menu.edit"),
    items: [
      await PredefinedMenuItem.new({ text: text("menu.undo"), item: "Undo" }),
      await PredefinedMenuItem.new({ text: text("menu.redo"), item: "Redo" }),
      await separator(),
      await PredefinedMenuItem.new({ text: text("menu.cut"), item: "Cut" }),
      await PredefinedMenuItem.new({ text: text("menu.copy"), item: "Copy" }),
      await PredefinedMenuItem.new({ text: text("menu.paste"), item: "Paste" }),
      await PredefinedMenuItem.new({ text: text("menu.select_all"), item: "SelectAll" }),
      await separator(),
      await item("find", text("menu.find"), "Cmd+F", state.inBook),
    ],
  });

  // ⌘1-⌘4: the four screens outside a document, the column's three lists
  // inside one (HIG §4) - the SAME four items with their words changed, so
  // no two items ever share a key.
  const places = state.inBook
    ? [text("reader.toc_title"), text("sidebar.notes_tab"), text("sidebar.search_tab"), null]
    : [text("nav.library"), text("nav.paste"), text("nav.external"), text("nav.transfer")];
  const view = await Submenu.new({
    text: text("menu.view"),
    items: [
      await item("toggle-sidebar", text(state.sideOpen ? "menu.sidebar_hide" : "menu.sidebar_show"), "Alt+Cmd+S"),
      await separator(),
      await item("go-1", places[0] ?? "", "Cmd+1", places[0] !== null),
      await item("go-2", places[1] ?? "", "Cmd+2", places[1] !== null),
      await item("go-3", places[2] ?? "", "Cmd+3", places[2] !== null),
      await item("go-4", places[3] ?? text("nav.transfer"), "Cmd+4", places[3] !== null),
      await separator(),
      await item("text-larger", text("menu.text_larger"), "Cmd+=", state.inBook),
      await item("text-smaller", text("menu.text_smaller"), "Cmd+-", state.inBook),
      await item("text-default", text("menu.text_default"), "Cmd+0", state.inBook),
      await separator(),
      await Submenu.new({
        text: text("menu.appearance"),
        items: [
          await check("appearance-light", text("settings.light"), state.appearance === "light"),
          await check("appearance-dark", text("settings.dark"), state.appearance === "dark"),
          await check("appearance-system", text("settings.system"), state.appearance === "system"),
        ],
      }),
      await separator(),
      await PredefinedMenuItem.new({ text: text("menu.fullscreen"), item: "Fullscreen" }),
    ],
  });

  const reading = await Submenu.new({
    text: text("menu.reading"),
    items: [
      // No accelerator: Space in a menu item would take Space from every
      // field. The page's own Space handler keeps doing it.
      await item(
        "play-pause",
        text(state.reading === "reading" ? "menu.pause" : "menu.play"),
        undefined,
        state.reading !== "idle",
      ),
      await item("stop", text("menu.stop"), "Cmd+.", state.reading !== "idle"),
      await separator(),
      // No accelerator here either: ⌥⌘R is the system-wide hotkey the
      // plugin registers; the same chord on a menu item would fire twice
      // with the app in front.
      await item("read-selection", text("menu.read_selection"), undefined, state.hasSelection),
      await separator(),
      await item("voice-settings", text("menu.voice_settings")),
      await item("hub", text("menu.hub"), "Cmd+,"),
    ],
  });

  const window = await Submenu.new({
    text: text("menu.window"),
    items: [
      await PredefinedMenuItem.new({ text: text("menu.minimize"), item: "Minimize" }),
      await PredefinedMenuItem.new({ text: text("menu.zoom"), item: "Maximize" }),
      await separator(),
      await PredefinedMenuItem.new({ text: text("menu.bring_all_to_front"), item: "BringAllToFront" }),
    ],
  });

  const help = await Submenu.new({
    text: text("menu.help"),
    items: [
      await item("help-guide", text("menu.guide")),
      await item("help-feedback", text("menu.feedback")),
      await separator(),
      await item("help-releases", text("menu.releases")),
      // The file "Báo lỗi" can attach (HIG 3.22): Finder, with it selected.
      await item("help-logs", text("menu.logs")),
    ],
  });

  const menu = await Menu.new({ items: [app, file, edit, view, reading, window, help] });
  await menu.setAsAppMenu();
  // The system's own Window and Help behaviours (the window list, the
  // Help search field) hang off these two.
  await window.setAsWindowsMenuForNSApp().catch(() => undefined);
  await help.setAsHelpMenuForNSApp().catch(() => undefined);
  return menu;
}
