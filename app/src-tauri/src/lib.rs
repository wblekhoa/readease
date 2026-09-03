mod engine;

use std::sync::Arc;

use engine::EngineClient;
use serde::Serialize;
use tauri::Manager;

#[derive(Serialize)]
struct Voice {
    id: String,
    label: String,
}

type Engine = Arc<EngineClient>;

/// The live engine, swappable when a model switch demands a fresh process.
struct EngineSlot(std::sync::Mutex<Engine>);
struct TraySlot(Arc<std::sync::Mutex<Option<tauri::tray::TrayIcon>>>);

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
        })
        .collect();
    Ok(voices)
}

#[tauri::command(async)]
fn read_text(
    engine: tauri::State<EngineSlot>,
    text: String,
    voice_id: String,
    rate: f64,
) -> Result<(), String> {
    client_of(&engine).fire("read", serde_json::json!({
        "text": text, "voice_id": voice_id, "rate": rate,
    }))
}

#[tauri::command(async)]
fn read_book(
    engine: tauri::State<EngineSlot>,
    book_id: String,
    segment_id: Option<String>,
    voice_id: String,
    rate: f64,
) -> Result<(), String> {
    client_of(&engine).fire("read.book", serde_json::json!({
        "book_id": book_id, "segment_id": segment_id,
        "voice_id": voice_id, "rate": rate,
    }))
}

#[tauri::command(async)]
fn read_selection_text(
    app: tauri::AppHandle,
    engine: tauri::State<EngineSlot>,
    text: String,
    voice_id: String,
    rate: f64,
) -> Result<(), String> {
    let _ = app;
    client_of(&engine).fire("read", serde_json::json!({
        "text": text, "voice_id": voice_id, "rate": rate,
    }))
}

#[tauri::command(async)]
fn import_book_bytes(
    engine: tauri::State<EngineSlot>,
    name: String,
    data_base64: String,
) -> Result<serde_json::Value, String> {
    use base64::Engine as _;
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(data_base64)
        .map_err(|error| format!("bad payload: {error}"))?;
    // The webview cannot see real file paths; it hands us the bytes and the
    // engine imports from a temp copy. Identity is content-hashed, so the
    // book id is identical to an import from the original path.
    let safe: String = name
        .chars()
        .map(|c| if c.is_alphanumeric() || c == '.' || c == '-' { c } else { '_' })
        .collect();
    let path = std::env::temp_dir().join(format!(
        "readease-import-{}-{safe}",
        std::process::id()
    ));
    std::fs::write(&path, bytes).map_err(|error| format!("temp write: {error}"))?;
    let reply = client_of(&engine).request(
        "library.import",
        serde_json::json!({"path": path.to_string_lossy()}),
    );
    let _ = std::fs::remove_file(&path);
    reply
}

#[tauri::command(async)]
fn engine_request(
    engine: tauri::State<EngineSlot>,
    method: String,
    params: serde_json::Value,
) -> Result<serde_json::Value, String> {
    client_of(&engine).request(&method, params)
}

#[tauri::command(async)]
fn stop_reading(engine: tauri::State<EngineSlot>) -> Result<(), String> {
    client_of(&engine).stop()
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

#[tauri::command(async)]
fn prepare_model(engine: tauri::State<EngineSlot>) -> Result<(), String> {
    client_of(&engine).notify("model.prepare", serde_json::json!({}))
}

#[tauri::command(async)]
fn restart_engine(
    app: tauri::AppHandle,
    engine: tauri::State<EngineSlot>,
    tray: tauri::State<TraySlot>,
) -> Result<(), String> {
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
    // Pressed again while a reading is under way, the shortcut stops it -
    // the same contract the Qt shell shipped.
    if engine.is_reading() {
        let _ = engine.stop();
        return;
    }
    match engine::acquire_selection() {
        Ok(selection) => {
            let _ = app.emit("reading:external", serde_json::json!({
                "text": selection,
            }));
            let _ = app.emit("external:status", serde_json::json!({
                "reason": "reading",
            }));
        }
        Err(code) => {
            let _ = app.emit("external:status", serde_json::json!({
                "reason": engine::selection_status_name(code),
            }));
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_macos_permissions::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .setup(|app| {
            let tray_slot: Arc<std::sync::Mutex<Option<tauri::tray::TrayIcon>>> =
                Arc::new(std::sync::Mutex::new(None));
            let client = EngineClient::spawn(app.handle().clone(), tray_slot.clone())
                .map_err(|error| -> Box<dyn std::error::Error> { error.into() })?;
            app.manage(EngineSlot(std::sync::Mutex::new(client.clone())));
            app.manage(TraySlot(tray_slot.clone()));

            // Menu bar indicator: exists for the whole app life, visible only
            // while reading; one click stops without surfacing the window.
            let tray = tauri::tray::TrayIconBuilder::with_id("reading")
                .icon(app.default_window_icon().cloned().expect("app icon"))
                .tooltip("ReadEase đang đọc - bấm để dừng")
                .on_tray_icon_event(|tray, event| {
                    if let tauri::tray::TrayIconEvent::Click { .. } = event {
                        if let Some(engine) = engine_of(tray.app_handle()) {
                            let _ = engine.stop();
                        }
                    }
                })
                .build(app)?;
            let _ = tray.set_visible(false);
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
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(engine) = engine_of(window.app_handle()) {
                    engine.shutdown();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            engine_voices,
            read_text,
            read_book,
            engine_request,
            import_book_bytes,
            read_selection_text,
            set_selection_shortcut,
            restart_engine,
            prepare_model,
            stop_reading,
            pause_audio,
            resume_audio
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
