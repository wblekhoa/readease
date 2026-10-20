mod audio;
mod engine;
mod identity;
mod reading_tray;
mod reading_panel;
mod translation;

use std::sync::atomic::Ordering;
use std::sync::Arc;

use engine::EngineClient;

mod log;
mod media;
use serde::Serialize;
use tauri::Manager;

#[derive(Serialize)]
struct Voice {
    id: String,
    label: String,
    /// Languages the provider has verified the voice in (BCP-47). Empty is
    /// "did not say" - the local model and OpenAI both arrive empty - and
    /// the shell must never draw that as "cannot".
    languages: Vec<String>,
    /// Provider-supplied gender metadata when known. Missing remains
    /// unknown; the shell must not infer it from a voice name.
    #[serde(skip_serializing_if = "Option::is_none")]
    gender: Option<String>,
}

type Engine = Arc<EngineClient>;

/// The live engine, swappable when a model switch demands a fresh process.
struct EngineSlot(std::sync::Mutex<Engine>);
// RE-PLAY-023: Stop invalidates selections still being captured or handed to the page.
#[derive(Default)]
struct SelectionRequest(std::sync::Mutex<u64>, std::sync::Mutex<()>, std::sync::Mutex<Option<String>>);

fn repeats_external_selection(external_active: bool, previous: Option<&str>, selected: &str) -> bool {
    external_active && previous == Some(selected)
}

#[cfg(test)]
mod selection_shortcut_tests {
    use super::repeats_external_selection;
    #[test]
    fn the_same_live_external_selection_toggles_but_a_new_selection_replaces_it() {
        assert!(repeats_external_selection(true, Some("first"), "first"));
        assert!(!repeats_external_selection(true, Some("first"), "second"));
        assert!(!repeats_external_selection(false, Some("first"), "first"));
        assert!(!repeats_external_selection(true, None, "first"));
    }
}

struct TraySlot(Arc<std::sync::Mutex<Option<tauri::tray::TrayIcon>>>);

/// An update downloaded and waiting to be installed when the app quits
/// (HIG 3.20, "Cài đặt khi thoát"). `armed` is the page's promise; `busy`
/// means the quit has been intercepted once and the page is installing -
/// a second close must not intercept again, and the safety net below ends
/// the wait if the page never answers.
#[derive(Default)]
struct InstallOnQuit {
    generation: std::sync::atomic::AtomicU64,
    armed: std::sync::atomic::AtomicBool,
    busy: std::sync::atomic::AtomicBool,
}

impl InstallOnQuit {
    fn disarm(&self) {
        self.generation.fetch_add(1, Ordering::SeqCst);
        self.armed.store(false, Ordering::SeqCst);
        self.busy.store(false, Ordering::SeqCst);
    }
    fn timeout_is_current(&self, generation: u64) -> bool {
        self.generation.load(Ordering::SeqCst) == generation
            && self.armed.load(Ordering::SeqCst) && self.busy.load(Ordering::SeqCst)
    }
}

#[cfg(test)]
mod update_quit_tests {
    use super::*;
    #[test]
    fn cancelled_or_superseded_quit_cannot_trigger_an_old_timeout() {
        let state = InstallOnQuit::default();
        state.armed.store(true, Ordering::SeqCst);
        state.busy.store(true, Ordering::SeqCst);
        let old = state.generation.load(Ordering::SeqCst);
        assert!(state.timeout_is_current(old));
        state.disarm();
        assert!(!state.timeout_is_current(old));
        state.armed.store(true, Ordering::SeqCst);
        state.busy.store(true, Ordering::SeqCst);
        assert!(!state.timeout_is_current(old));
    }
}

#[tauri::command]
fn set_install_on_quit(state: tauri::State<InstallOnQuit>, armed: bool) {
    if armed { state.armed.store(true, Ordering::SeqCst); } else { state.disarm(); }
}

/// The page has installed the waiting update: leave now, no relaunch.
#[tauri::command]
fn exit_now(app: tauri::AppHandle) {
    if engine_of(&app).is_some_and(|engine| engine.is_exporting()) {
        use tauri::Emitter;
        let _ = app.emit("export:quit-requested", ());
        return;
    }
    app.exit(0);
}

/// Called on the way out: true when the quit was intercepted for an
/// install and the page has been told, false to let the quit proceed.
fn intercept_quit_for_install(app: &tauri::AppHandle) -> bool {
    use tauri::Emitter;
    let Some(state) = app.try_state::<InstallOnQuit>() else { return false };
    if !state.armed.load(Ordering::SeqCst) || state.busy.swap(true, Ordering::SeqCst) {
        return false;
    }
    let _ = app.emit("update:install-now", ());
    // If the page dies or hangs mid-install, the app still quits.
    let generation = state.generation.load(Ordering::SeqCst);
    let fallback = app.clone();
    std::thread::spawn(move || {
        std::thread::sleep(std::time::Duration::from_secs(60));
        if fallback.try_state::<InstallOnQuit>().is_some_and(|s| s.timeout_is_current(generation)) {
            fallback.exit(0);
        }
    });
    true
}

/// Documents macOS asked the app to open - a double-click in Finder, a
/// drop on the Dock icon, "Open With" - waiting for the page to take them.
/// A queue rather than an event with a payload, because the first of them
/// arrives BEFORE the webview exists (the app was launched by the file):
/// the page drains it once it is up, and again on every `files:opened`
/// nudge, so nothing is opened twice and nothing is lost.
struct OpenedFiles(std::sync::Mutex<Vec<String>>);

/// Which output the voice goes to (HIG 3.21) - asked once the page is up,
/// since the audio thread's own event fired before there was a page.
#[tauri::command]
fn audio_output(slot: tauri::State<EngineSlot>) -> audio::AudioOutput {
    client_of(&slot).output.lock().unwrap().clone()
}

/// The Mac's preferred languages, first choice first (System Settings ›
/// General › Language & Region). Not `navigator.language`: in the WebView
/// that is the app's own localization, English for a bundle with no
/// Vietnamese .lproj, so a Vietnamese Mac would read as English.
#[tauri::command]
fn system_languages() -> Vec<String> {
    #[cfg(target_os = "macos")]
    {
        objc2_foundation::NSLocale::preferredLanguages()
            .iter()
            .map(|language| language.to_string())
            .collect()
    }
    #[cfg(not(target_os = "macos"))]
    {
        Vec::new()
    }
}

#[tauri::command]
fn take_opened_files(queue: tauri::State<OpenedFiles>) -> Vec<String> {
    std::mem::take(&mut *queue.0.lock().unwrap())
}

fn client_of(slot: &tauri::State<EngineSlot>) -> Engine {
    // Bind, then drop the guard: a temporary guard lives to the end of the
    // whole statement, which would hold the slot locked through a blocking
    // request - and freeze the stop button exactly when it matters.
    let client = slot.0.lock().unwrap().clone();
    client
}

fn engine_of(app: &tauri::AppHandle) -> Option<Engine> {
    app.try_state::<EngineSlot>()
        .map(|slot| slot.0.lock().unwrap().clone())
}

// Every command below touches the engine, and several WAIT on it: a stop is
// answered between utterances, book.open builds a presentation, an import
// parses the whole file, a restart loads the model. Tauri runs a plain `fn`
// command on the MAIN thread ("sync" in tauri-macros' wrapper.rs), so each of
// those waits froze the window for its whole duration - the "app đứng" the
// owner reported (2026-09-02). `(async)` runs the same synchronous body on
// the thread pool instead; nothing here needs the main thread.
#[tauri::command(async)]
fn engine_voices(engine: tauri::State<EngineSlot>) -> Result<Vec<Voice>, String> {
    let reply = client_of(&engine).request("voices", serde_json::json!({}))?;
    let voices = reply["result"]["voices"]
        .as_array()
        .ok_or("voices missing")?
        .iter()
        .map(|voice| Voice {
            id: voice["id"].as_str().unwrap_or_default().to_string(),
            label: voice["label"].as_str().unwrap_or_default().to_string(),
            languages: voice["languages"]
                .as_array()
                .map(|tags| {
                    tags.iter()
                        .filter_map(|tag| tag.as_str())
                        .map(str::to_string)
                        .collect()
                })
                .unwrap_or_default(),
            gender: voice["gender"].as_str().map(str::to_string),
        })
        .collect();
    Ok(voices)
}

#[tauri::command(async)]
fn read_text(
    app: tauri::AppHandle,
    engine: tauri::State<EngineSlot>,
    text: String,
    segment_id: Option<String>,
    voice_id: String,
    rate: f64,
    // The shell's word that this text is the app's own sample sentence and
    // not the reader's. Only that lets the engine keep the clip; see
    // `_speak`'s `app_text`.
    app_text: Option<bool>,
) -> Result<(), String> {
    let request = app.state::<SelectionRequest>();
    let mut generation = request.0.lock().unwrap();
    *generation += 1;
    translation::cancel_before(*generation);
    client_of(&engine).fire("read", serde_json::json!({
        "text": text, "segment_id": segment_id,
        "voice_id": voice_id, "rate": rate,
        "app_text": app_text.unwrap_or(false),
    }))
}

/// Pasted text read into a WAV (and its subtitles) at `path`, which the
/// webview got from the save panel. Long work: the answer arrives as
/// `engine:export_done`, progress as `engine:export_progress`, both carrying
/// the id returned here. A stop (`stop_reading`) cancels it.
#[tauri::command(async)]
fn export_text(
    app: tauri::AppHandle,
    engine: tauri::State<EngineSlot>,
    text: String,
    voice_id: String,
    voice_label: String,
    rate: f64,
    path: String,
) -> Result<u64, String> {
    let software = format!("ReadEase {}", app.package_info().version);
    let request = app.state::<SelectionRequest>();
    let mut generation = request.0.lock().unwrap();
    *generation += 1;
    translation::cancel_before(*generation);
    client_of(&engine).notify_as("export.text", serde_json::json!({
        "text": text, "voice_id": voice_id, "voice_label": voice_label,
        "rate": rate, "path": path, "software": software,
    }), "engine:export_done")
}

/// Long-lived export: the webview listens for progress and completion.
#[tauri::command(async)]
fn export_book(
    app: tauri::AppHandle, engine: tauri::State<EngineSlot>,
    book_id: String, voice_id: String, voice_label: String, rate: f64,
    path: String, from_chapter: u64, chapters: u64,
) -> Result<u64, String> {
    let request = app.state::<SelectionRequest>();
    let mut generation = request.0.lock().unwrap();
    *generation += 1;
    translation::cancel_before(*generation);
    client_of(&engine).notify_as("export.book", serde_json::json!({
        "book_id": book_id, "voice_id": voice_id, "voice_label": voice_label,
        "rate": rate, "path": path, "from_chapter": from_chapter, "chapters": chapters,
        "software": format!("ReadEase {}", app.package_info().version),
    }), "engine:export_done")
}

/// A quiet Dock notification only when the person is in another window.
fn export_attention(app: tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        if !window.is_focused().unwrap_or(true) {
            let _ = window.request_user_attention(Some(tauri::UserAttentionType::Informational));
        }
    }
}

/// One sentence of the last export as it stands in the file, played like a
/// reading (so Stop, the tray and the device all behave as they do for one).
#[tauri::command(async)]
fn play_take(
    engine: tauri::State<EngineSlot>,
    session: String,
    index: u64,
) -> Result<(), String> {
    client_of(&engine).fire("export.play", serde_json::json!({
        "session": session, "index": index,
    }))
}

/// Rewrite the last export's WAV and subtitles from its takes as they now
/// stand. Answered on `engine:export_done`, like the export itself.
#[tauri::command(async)]
fn save_export(
    engine: tauri::State<EngineSlot>,
    session: String,
) -> Result<u64, String> {
    client_of(&engine).notify_as("export.save", serde_json::json!({
        "session": session,
    }), "engine:export_done")
}

#[tauri::command(async)]
fn read_book(
    app: tauri::AppHandle,
    engine: tauri::State<EngineSlot>,
    book_id: String,
    segment_id: Option<String>,
    voice_id: String,
    rate: f64,
    // RE-PLAY-027: the scope the button quoted; None reads to the end of the
    // book. Tauri drops an undeclared argument silently, so before this the
    // chapter count bounded only the price, never the reading.
    chapters: Option<u32>,
) -> Result<(), String> {
    let request = app.state::<SelectionRequest>();
    let mut generation = request.0.lock().unwrap();
    *generation += 1;
    translation::cancel_before(*generation);
    client_of(&engine).fire("read.book", serde_json::json!({
        "book_id": book_id, "segment_id": segment_id,
        "voice_id": voice_id, "rate": rate, "chapters": chapters,
    }))
}

#[tauri::command(async)]
fn read_selection_text(
    app: tauri::AppHandle,
    engine: tauri::State<EngineSlot>,
    text: String,
    segment_id: Option<String>,
    voice_id: String,
    rate: f64,
    capture_id: Option<u64>,
    entry_id: Option<u64>,
    selection_key: Option<String>,
    translation: Option<translation::Options>,
) -> Result<Option<serde_json::Value>, String> {
    let request = app.state::<SelectionRequest>();
    let id = {
        let mut generation = request.0.lock().unwrap();
        if capture_id.is_some_and(|id| id != *generation) { return Ok(None); }
        if capture_id.is_none() { *generation += 1; }
        translation::cancel_before(*generation);
        *generation
    };
    let client = client_of(&engine);
    if client.is_exporting() { return Err("translation:export_busy".into()); }
    let selected = selection_key.unwrap_or_else(|| text.clone());
    let mut spoken = text;
    let mut voice = voice_id;
    let mut target = None;
    if let Some(options) = translation {
        options.validate()?;
        {
            let generation = request.0.lock().unwrap();
            if *generation != id { return Ok(None); }
            client.stop()?;
            reading_tray::translating(&app);
        }
        let result = translation::translate(&spoken, &options, id);
        let generation = request.0.lock().unwrap();
        if *generation != id { return Ok(None); }
        match result {
            Ok(result) => {
                spoken = result["text"].as_str().ok_or("translation:invalid_output")?.to_string();
                target = Some(options.target);
                voice = options.voice_id;
            }
            Err(error) => { reading_tray::finished(&app); return Err(error); }
        }
    }
    let generation = request.0.lock().unwrap();
    if *generation != id { return Ok(None); }
    if target.is_some() {
        use tauri::Emitter;
        // The UI must accept an immediate speech failure even when it arrives
        // before the command's result; only the translation phase ignores old audio.
        let _ = app.emit("reading:translation_ready", serde_json::json!({"entry_id": entry_id}));
    }
    client.fire("read", serde_json::json!({
        "text": spoken, "segment_id": if target.is_some() { None } else { segment_id },
        "voice_id": voice, "rate": rate, "_external": true,
    }))?;
    *request.2.lock().unwrap() = Some(selected);
    Ok(Some(serde_json::json!({ "text": spoken, "voice_id": voice, "target": target })))
}

#[tauri::command(async)]
fn engine_request(
    app: tauri::AppHandle,
    engine: tauri::State<EngineSlot>,
    method: String,
    params: serde_json::Value,
) -> Result<serde_json::Value, String> {
    let reply = client_of(&engine).request(&method, params.clone())?;
    if method == "config.set" && params["key"] == "ui_language" {
        reading_tray::language(&app, params["value"].as_str().unwrap_or("en"));
    }
    if method == "config.set" && params["key"] == "selection_translation" {
        *app.state::<SelectionRequest>().2.lock().unwrap() = None;
    }
    Ok(reply)
}

#[tauri::command(async)]
fn stop_reading(app: tauri::AppHandle, engine: tauri::State<EngineSlot>) -> Result<(), String> {
    stop_from_controls(&app, &client_of(&engine))
}

fn stop_from_controls(app: &tauri::AppHandle, engine: &Engine) -> Result<(), String> {
    let request = app.state::<SelectionRequest>();
    let mut generation = request.0.lock().unwrap();
    *generation += 1;
    translation::cancel_before(*generation);
    engine.stop()
}

#[tauri::command(async)]
fn pause_audio(engine: tauri::State<EngineSlot>) {
    client_of(&engine).pause();
}

#[tauri::command(async)]
fn resume_audio(engine: tauri::State<EngineSlot>) {
    client_of(&engine).resume();
}

fn register_selection_shortcut(
    app: &tauri::AppHandle,
    accelerator: &str,
) -> Result<(), String> {
    use tauri_plugin_global_shortcut::GlobalShortcutExt;
    let shortcuts = app.global_shortcut();
    shortcuts
        .unregister_all()
        .map_err(|error| format!("unregister: {error}"))?;
    shortcuts
        .on_shortcut(accelerator, move |handle, _shortcut, event| {
            if event.state == tauri_plugin_global_shortcut::ShortcutState::Pressed {
                if let Some(engine) = engine_of(handle) {
                    read_current_selection(handle, &engine);
                }
            }
        })
        .map_err(|error| format!("register {accelerator}: {error}"))
}

/// `model` names which download: nothing for the Vietnamese voice (the
/// setup screen's, and the build switch's), `"english"` for the English one.
#[tauri::command(async)]
fn prepare_model(
    engine: tauri::State<EngineSlot>,
    model: Option<String>,
) -> Result<(), String> {
    if client_of(&engine).is_exporting() { return Err("export_busy".into()); }
    let params = match model.as_deref() {
        Some(name) => serde_json::json!({ "engine": name }),
        None => serde_json::json!({}),
    };
    client_of(&engine).notify("model.prepare", params)
}

#[tauri::command(async)]
fn restart_engine(
    app: tauri::AppHandle,
    engine: tauri::State<EngineSlot>,
    tray: tauri::State<TraySlot>,
) -> Result<(), String> {
    if client_of(&engine).is_exporting() { return Err("export_busy".into()); }
    // A model switch loads at engine construction, so the choice only
    // becomes real in a fresh process. The old one dies by the same EOF
    // contract the orphan test proved.
    let fresh = EngineClient::spawn(app.clone(), tray.0.clone())?;
    let old = {
        let mut slot = engine.0.lock().unwrap();
        std::mem::replace(&mut *slot, fresh)
    };
    // A reading cut off by the swap must still end as a reading that ended:
    // stop clears the tray and the queue before the process goes away.
    let _ = old.stop();
    old.shutdown();
    Ok(())
}

#[tauri::command(async)]
fn set_selection_shortcut(
    app: tauri::AppHandle,
    accelerator: String,
) -> Result<(), String> {
    register_selection_shortcut(&app, &accelerator)
}

fn read_current_selection(app: &tauri::AppHandle, engine: &Engine) {
    use tauri::Emitter;
    if engine.is_exporting() {
        export_attention(app.clone());
        return;
    }
    // The synthesis request can already be finished while audio remains
    // queued or paused. The ear's state, not current_read, owns the toggle.
    let was_reading = reading_tray::is_active(app);
    let was_translating = reading_tray::is_translating(app);
    let capture_id = {
        let state = app.state::<SelectionRequest>();
        let mut generation = state.0.lock().unwrap();
        *generation += 1;
        translation::cancel_before(*generation);
        if !was_reading { *state.2.lock().unwrap() = None; }
        *generation
    };
    if !was_reading { reading_tray::preparing(app, true); }
    let app = app.clone();
    std::thread::spawn(move || {
        let request = app.state::<SelectionRequest>();
        // Clipboard save/copy/restore must never overlap between shortcuts.
        let _capture = request.1.lock().unwrap();
        if *request.0.lock().unwrap() != capture_id { return; }
        let selection = engine::acquire_selection();
        let generation = request.0.lock().unwrap();
        if *generation != capture_id { return; }
        match selection {
            Ok(selection) => {
                let mut previous = request.2.lock().unwrap();
                if repeats_external_selection(was_reading && reading_tray::is_external_active(&app), previous.as_deref(), &selection) {
                    reading_tray::toggle(&app);
                    return;
                }
                *previous = None;
                let _ = app.emit("reading:external", serde_json::json!({
                    "text": selection, "capture_id": capture_id,
                }));
                let _ = app.emit("external:status", serde_json::json!({"reason": "reading"}));
            }
            Err(code) => {
                if !was_reading || was_translating { reading_tray::finished(&app); }
                let _ = app.emit("external:status", serde_json::json!({
                    "reason": engine::selection_status_name(code),
                }));
            }
        }
    });
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // First, before anything prints: the log file takes stderr when no
    // terminal is reading it (HIG 3.22).
    let context = tauri::generate_context!();
    log::capture_stderr(&log::bundle_version(&context.package_info().version.to_string()));
    // Before the builder: the WebView must open the carried-over storage.
    identity::carry_over_legacy_state();
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_macos_permissions::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        // In-app updates (HIG 3.20): the page asks, downloads and relaunches;
        // the manifest and the archive live with the GitHub release.
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        // The window comes back where and how big it was left (HIG 3.16):
        // size and position only. Not fullscreen or visibility - restoring
        // a fullscreen flag onto a transparent, overlay-title-bar window is
        // the classic vibrancy glitch, and the window is always shown.
        .plugin(
            tauri_plugin_window_state::Builder::new()
                .with_state_flags(
                    tauri_plugin_window_state::StateFlags::SIZE
                        | tauri_plugin_window_state::StateFlags::POSITION,
                )
                .build(),
        )
        .setup(|app| {
            let tray_slot: Arc<std::sync::Mutex<Option<tauri::tray::TrayIcon>>> =
                Arc::new(std::sync::Mutex::new(None));
            let client = EngineClient::spawn(app.handle().clone(), tray_slot.clone())
                .map_err(|error| -> Box<dyn std::error::Error> { error.into() })?;
            app.manage(EngineSlot(std::sync::Mutex::new(client.clone())));
            app.manage(TraySlot(tray_slot.clone()));
            app.manage(SelectionRequest::default());
            app.manage(OpenedFiles(std::sync::Mutex::new(Vec::new())));
            app.manage(InstallOnQuit::default());
            // Now Playing's remote commands (HIG 3.19), once, on the main
            // thread that `setup` runs on - and the one cover it shows.
            app.manage(media::register(app.handle()));
            app.manage(media::ArtworkCache::default());
            reading_panel::install(app.handle());

            // RE-PLAY-023: controls stay in a native menu, in the app language.
            let language = client.request("config.get", serde_json::json!({"key": "ui_language"}))
                .ok().and_then(|reply| reply["result"]["value"].as_str().map(str::to_owned));
            let tray = reading_tray::install(app.handle(), language.as_deref() == Some("vi"))?;
            *tray_slot.lock().unwrap() = Some(tray);

            // The saved shortcut lives in the engine's settings.json, so it
            // survives the shell rewrite the same file survived the rebrand.
            let saved = client
                .request("config.get", serde_json::json!({
                    "key": "tauri_selection_shortcut",
                }))
                .ok()
                .and_then(|reply| {
                    reply["result"]["value"].as_str().map(str::to_owned)
                });
            let accelerator = saved.as_deref().unwrap_or("alt+super+r");
            if let Err(error) =
                register_selection_shortcut(app.handle(), accelerator)
            {
                // A taken shortcut must not kill the app; the screen offers
                // the recorder to pick another.
                eprintln!("[shortcut] {error}");
            }
            Ok(())
        })
        .on_window_event(|window, event| match event {
            // Closing the one window is quitting; with an update waiting,
            // the page installs it first (HIG 3.20).
            tauri::WindowEvent::CloseRequested { api, .. } => {
                if engine_of(window.app_handle()).is_some_and(|engine| engine.is_exporting()) {
                    api.prevent_close();
                    let _ = window.minimize();
                } else if intercept_quit_for_install(window.app_handle()) {
                    api.prevent_close();
                }
            }
            tauri::WindowEvent::Destroyed => {
                if let Some(engine) = engine_of(window.app_handle()) {
                    engine.shutdown();
                }
            }
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![
            engine_voices,
            translation::translation_status,
            translation::translation_models,
            read_text,
            read_book,
            engine_request,
            reading_panel::floating_controller_enabled,
            reading_panel::set_floating_controller_enabled,
            read_selection_text,
            set_selection_shortcut,
            restart_engine,
            prepare_model,
            export_text,
            export_book,
            play_take,
            save_export,
            stop_reading,
            pause_audio,
            resume_audio,
            take_opened_files,
            system_languages,
            audio_output,
            media::now_playing,
            log::log_path,
            log::feedback_facts,
            set_install_on_quit,
            exit_now
        ])
        .build(context)
        .expect("error while building tauri application")
        .run(|app, event| {
            // The system's "open these documents" (HIG 3.18): queue the
            // paths and nudge the page; it takes them when it can.
            // ⌘Q with an update waiting: the page installs, then `exit_now`.
            if let tauri::RunEvent::ExitRequested { api, .. } = &event {
                if engine_of(app).is_some_and(|engine| engine.is_exporting()) {
                    use tauri::Emitter;
                    api.prevent_exit();
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.unminimize();
                        let _ = window.set_focus();
                    }
                    let _ = app.emit("export:quit-requested", ());
                    return;
                }
                if intercept_quit_for_install(app) {
                    api.prevent_exit();
                    return;
                }
            }
            #[cfg(target_os = "macos")]
            if let tauri::RunEvent::Opened { urls } = event {
                use tauri::Emitter;
                let paths: Vec<String> = urls
                    .iter()
                    .filter_map(|url| url.to_file_path().ok())
                    .map(|path| path.to_string_lossy().into_owned())
                    .collect();
                if paths.is_empty() {
                    return;
                }
                if let Some(queue) = app.try_state::<OpenedFiles>() {
                    queue.0.lock().unwrap().extend(paths);
                }
                let _ = app.emit("files:opened", ());
            }
            #[cfg(not(target_os = "macos"))]
            let _ = (app, event);
        });
}
