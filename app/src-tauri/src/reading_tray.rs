// RE-PLAY-023: menu state is independent of private text and of the webview.
#[derive(Default)]
struct Model {
    vi: bool,
    active: bool,
    paused: bool,
    current: u64,
    total: u64,
    external: bool,
    completed: bool,
    generation: u64,
}
impl Model {
    fn can_toggle(&self) -> bool { self.active && (self.total > 0 || self.paused) }
    fn labels(&self) -> (String, &'static str, &'static str, &'static str) {
        let state = match (self.vi, self.paused, self.total > 0) {
            (true, true, _) => "Tạm dừng",
            (false, true, _) => "Paused",
            (true, false, true) => "Đang đọc",
            (false, false, true) => "Reading",
            (true, false, false) => "Đang chuẩn bị…",
            (false, false, false) => "Preparing…",
        };
        let status = if self.total > 0 {
            format!(
                "{state} · {} {}/{}",
                if self.vi { "câu" } else { "sentence" },
                self.current,
                self.total
            )
        } else {
            state.into()
        };
        (
            status,
            match (self.vi, self.paused) {
                (true, true) => "Tiếp tục",
                (true, false) => "Tạm dừng",
                (false, true) => "Resume",
                (false, false) => "Pause",
            },
            if self.vi { "Dừng" } else { "Stop" },
            if self.vi {
                "Mở ReadEase"
            } else {
                "Open ReadEase"
            },
        )
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn a_pause_before_the_first_audio_can_always_resume() {
        let mut model = Model { active: true, ..Default::default() };
        assert!(!model.can_toggle());
        model.paused = true;
        assert!(model.can_toggle());
        model.active = false;
        assert!(!model.can_toggle());
    }
    #[test]
    fn preparing_progress_pause_and_languages() {
        let mut model = Model {
            active: true,
            ..Default::default()
        };
        assert_eq!(
            model.labels(),
            ("Preparing…".into(), "Pause", "Stop", "Open ReadEase")
        );
        model.current = 3;
        model.total = 12;
        assert_eq!(model.labels().0, "Reading · sentence 3/12");
        model.paused = true;
        assert_eq!(model.labels().0, "Paused · sentence 3/12");
        assert_eq!(model.labels().1, "Resume");
        model.vi = true;
        assert_eq!(
            model.labels(),
            (
                "Tạm dừng · câu 3/12".into(),
                "Tiếp tục",
                "Dừng",
                "Mở ReadEase"
            )
        );
        model.current = 0;
        model.total = 0;
        model.paused = false;
        assert_eq!(model.labels().0, "Đang chuẩn bị…");
    }
}

use std::sync::Mutex;
use tauri::menu::{Menu, MenuItem};
use tauri::{Emitter, Manager};

pub(crate) struct ReadingTray {
    model: Mutex<Model>,
    status: MenuItem<tauri::Wry>,
    toggle: MenuItem<tauri::Wry>,
    stop: MenuItem<tauri::Wry>,
    open: MenuItem<tauri::Wry>,
}

pub(crate) fn install(app: &tauri::AppHandle, vi: bool) -> tauri::Result<tauri::tray::TrayIcon> {
    let status = MenuItem::with_id(app, "reading-status", "", false, None::<&str>)?;
    let toggle = MenuItem::with_id(app, "reading-toggle", "", true, None::<&str>)?;
    let stop = MenuItem::with_id(app, "reading-stop", "", true, None::<&str>)?;
    let open = MenuItem::with_id(app, "reading-open", "", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&status, &toggle, &stop, &open])?;
    app.manage(ReadingTray {
        model: Mutex::new(Model {
            vi,
            ..Default::default()
        }),
        status,
        toggle,
        stop,
        open,
    });
    let tray = tauri::tray::TrayIconBuilder::with_id("reading")
        .icon(app.default_window_icon().cloned().expect("app icon"))
        .menu(&menu)
        .show_menu_on_left_click(true)
        .on_menu_event(|app, event| {
            match event.id().as_ref() {
                "reading-toggle" => {
                    self::toggle(app);
                }
                "reading-stop" => {
                    // The page may still be idle during acquisition. Silence and
                    // invalidate that capture natively, then reconcile its UI.
                    self::stop(app);
                }
                "reading-open" => {
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.unminimize();
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
                _ => {}
            }
        })
        .build(app)?;
    let _ = tray.set_visible(false);
    update(app, |_| {});
    Ok(tray)
}

pub(crate) fn stop(app: &tauri::AppHandle) {
    // Dismiss immediately, including during acquisition/engine warm-up.
    finished(app);
    let app = app.clone();
    std::thread::spawn(move || {
        if let Some(engine) = crate::engine_of(&app) {
            let _ = crate::stop_from_controls(&app, &engine);
        }
        let _ = app.emit("media:command", "stop");
    });
}

pub(crate) fn toggle(app: &tauri::AppHandle) {
    let can_toggle = app.try_state::<ReadingTray>()
        .is_some_and(|tray| tray.model.lock().unwrap().can_toggle());
    if can_toggle { let _ = app.emit("media:command", "toggle"); }
}

fn update(app: &tauri::AppHandle, change: impl FnOnce(&mut Model) + Send + 'static) {
    // Menu APIs hop to the main thread. Never hold this mutex on a worker
    // while synchronously waiting for that thread (a menu click may need it).
    let handle = app.clone();
    let _ = app.run_on_main_thread(move || apply(&handle, change));
}
fn apply(app: &tauri::AppHandle, change: impl FnOnce(&mut Model)) {
    let Some(tray) = app.try_state::<ReadingTray>() else {
        return;
    };
    let mut model = tray.model.lock().unwrap();
    change(&mut model);
    let (status, toggle, stop, open) = model.labels();
    let _ = tray.status.set_text(&status);
    let _ = tray.toggle.set_text(toggle);
    let _ = tray.toggle.set_enabled(model.can_toggle());
    let _ = tray.stop.set_text(stop);
    let _ = tray.open.set_text(open);
    crate::reading_panel::update(
        if model.active { 1 } else if model.completed { 2 } else { 0 },
        model.paused, model.current, model.total, model.external, model.vi, model.generation,
    );
    if let Some(icon) = app.tray_by_id("reading") {
        let _ = icon.set_tooltip(Some(format!("ReadEase · {status}")));
        let _ = icon.set_visible(model.active);
    }
}

pub(crate) fn preparing(app: &tauri::AppHandle, external: bool) {
    update(app, move |m| {
        m.active = true;
        m.paused = false;
        m.current = 0;
        m.total = 0;
        m.external = external;
        m.completed = false;
        m.generation += 1;
    });
}
pub(crate) fn language(app: &tauri::AppHandle, language: &str) {
    let vi = language == "vi";
    update(app, move |m| m.vi = vi);
}
pub(crate) fn paused(app: &tauri::AppHandle, paused: bool) {
    update(app, move |m| m.paused = paused);
}
pub(crate) fn finished(app: &tauri::AppHandle) {
    update(app, |m| { m.active = false; m.completed = false; });
}
pub(crate) fn is_external_active(app: &tauri::AppHandle) -> bool {
    app.try_state::<ReadingTray>().is_some_and(|tray| {
        let model = tray.model.lock().unwrap(); model.active && model.external
    })
}
pub(crate) fn is_active(app: &tauri::AppHandle) -> bool {
    app.try_state::<ReadingTray>().is_some_and(|tray| tray.model.lock().unwrap().active)
}
pub(crate) fn event(app: &tauri::AppHandle, event: &str, payload: &serde_json::Value) {
    match event {
        "reading:sentence" => {
            let current = payload["current"].as_u64().unwrap_or(0);
            let total = payload["total"].as_u64().unwrap_or(0);
            update(app, move |m| {
                m.current = current;
                m.total = total;
            });
        }
        "reading:done" => {
            let completed = payload["ok"].as_bool().unwrap_or(false);
            update(app, move |m| { m.active = false; m.completed = completed; });
        },
        _ => {}
    }
}
