import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
const browserPreview = import.meta.env.DEV && !("__TAURI_INTERNALS__" in window);

// In a plain browser there is no Tauri host, so the screens that need the
// engine cannot be looked at. Dev only, and stripped from the build.
if (import.meta.env.DEV && !("__TAURI_INTERNALS__" in window)) {
  await import("./dev/mockTauri");
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

// RE-PG-003: dev browser only; the build removes this driver with the mock host.
if (browserPreview && new URLSearchParams(location.search).has('pilot')) {
  void import('./dev/playgroundDriver').then(({ runPlaygroundScenario }) => runPlaygroundScenario());
}
