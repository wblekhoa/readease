/** Light or dark: the system decides until the reader decides.
 *
 * The DS flips its tokens on `[data-theme]`; this is the one place that
 * writes it. A stored choice wins; without one the OS appearance is
 * followed live (owner asked for a switch, 02/09).
 */
export type ThemePreference = "system" | "light" | "dark";
export type Theme = "light" | "dark";
const KEY = "readease.theme";

export function storedThemePreference(): ThemePreference {
  try {
    const saved = localStorage.getItem(KEY);
    return saved === "light" || saved === "dark" ? saved : "system";
  } catch {
    return "system";
  }
}

export function rememberThemePreference(preference: ThemePreference): void {
  try {
    if (preference === "system") localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, preference);
  } catch {
    // The choice lasts the session either way.
  }
}

/** What actually shows, given the preference and what the OS says. */
export function resolveTheme(preference: ThemePreference, systemDark: boolean): Theme {
  if (preference === "system") return systemDark ? "dark" : "light";
  return preference;
}

/** The theme a click on the switch should go to: the opposite of what shows. */
export function nextTheme(current: Theme): Theme {
  return current === "dark" ? "light" : "dark";
}
