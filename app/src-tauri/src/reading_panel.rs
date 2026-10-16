//! Main-thread bridge to the small AppKit controller. No second webview.
use std::sync::OnceLock;
use tauri::Manager;

static APP: OnceLock<tauri::AppHandle> = OnceLock::new();
extern "C" {
    fn RDXReadingPanelInstall(window: *mut std::ffi::c_void, action: extern "C" fn(i32));
    fn RDXReadingPanelUpdate(phase: i32, paused: i32, current: u64, total: u64, external: i32, vi: i32, generation: u64);
    fn RDXReadingPanelEnabled() -> i32;
    fn RDXReadingPanelSetEnabled(enabled: i32);
}

extern "C" fn action(command: i32) {
    let Some(app) = APP.get() else { return };
    match command {
        1 => crate::reading_tray::toggle(app),
        2 => crate::reading_tray::stop(app),
        _ => {},
    }
}

pub(crate) fn install(app: &tauri::AppHandle) {
    let Some(window) = app.get_webview_window("main") else { return };
    let Ok(native) = window.ns_window() else { return };
    let _ = APP.set(app.clone());
    unsafe { RDXReadingPanelInstall(native, action); }
}

pub(crate) fn update(phase: i32, paused: bool, current: u64, total: u64, external: bool, vi: bool, generation: u64) {
    // Called only from reading_tray::apply, on AppKit's main thread.
    unsafe { RDXReadingPanelUpdate(phase, paused as i32, current, total, external as i32, vi as i32, generation); }
}

#[tauri::command]
pub(crate) fn floating_controller_enabled() -> bool {
    unsafe { RDXReadingPanelEnabled() != 0 }
}

#[tauri::command]
pub(crate) fn set_floating_controller_enabled(app: tauri::AppHandle, enabled: bool) -> Result<(), String> {
    app.run_on_main_thread(move || unsafe { RDXReadingPanelSetEnabled(enabled as i32); })
        .map_err(|error| error.to_string())
}
