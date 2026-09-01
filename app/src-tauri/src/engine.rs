//! The Python reading engine as a child process, and the speaker beside it.
//!
//! The shell stays thin on purpose: it forwards JSONL requests, turns `chunk`
//! events into PCM for rodio, and reports state to the webview. Everything
//! that knows Vietnamese - prosody, voices, caching - lives on the other side
//! of the pipe. Audio lives HERE rather than in the webview because reading
//! usually starts from a global shortcut, exactly where WKWebView's autoplay
//! policy would mute a web AudioContext.
//!
//! Flow control: chunks reach the audio thread over a BOUNDED channel. When a
//! whole book streams and the listener pauses, the channel fills, the reader
//! thread blocks, the OS pipe fills, and the Python engine stops synthesising
//! - backpressure for free, no protocol needed. A stop bumps the epoch so
//! chunks already in flight are dropped instead of played late.

use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::mpsc::{channel, sync_channel, Sender, SyncSender};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use base64::engine::general_purpose::STANDARD as BASE64;
use base64::Engine as _;
use serde_json::{json, Value};
use tauri::{AppHandle, Emitter};

// The Objective-C bridge, statically linked by build.rs. Returns 0 with a
// UTF-8 payload the caller must free, or a status code mirrored from the
// bridge's enum (1 permission, 2 no selection, 3 unsupported source,
// 4 clipboard restore failed, 5 unavailable, 6 concealed).
unsafe extern "C" {
    fn RDXSelectionAcquire(
        output: *mut *mut std::os::raw::c_char,
        length: *mut usize,
    ) -> std::os::raw::c_int;
    fn RDXSelectionFree(bytes: *mut std::os::raw::c_void);
}

pub fn selection_status_name(code: i32) -> &'static str {
    match code {
        1 => "permission_required",
        2 => "no_selection",
        3 => "unsupported_source",
        4 => "clipboard_restore_failed",
        6 => "concealed_source",
        _ => "unavailable",
    }
}

/// Ask the frontmost app for its selection, exactly like the Qt shell does.
pub fn acquire_selection() -> Result<String, i32> {
    let mut output: *mut std::os::raw::c_char = std::ptr::null_mut();
    let mut length: usize = 0;
    let code = unsafe { RDXSelectionAcquire(&mut output, &mut length) };
    if code != 0 {
        return Err(code);
    }
    if output.is_null() || length == 0 || length > 500_000 {
        if !output.is_null() {
            unsafe { RDXSelectionFree(output.cast()) };
        }
        return Err(5);
    }
    let bytes =
        unsafe { std::slice::from_raw_parts(output.cast::<u8>(), length) };
    let text = String::from_utf8(bytes.to_vec());
    unsafe { RDXSelectionFree(output.cast()) };
    text.map_err(|_| 5)
}

const SAMPLE_RATE: u32 = 48_000;
/// ~48 frames of ~0.1-0.5s each keeps a few seconds buffered, no more.
const AUDIO_QUEUE_FRAMES: usize = 48;

pub struct EngineClient {
    stdin: Mutex<ChildStdin>,
    child: Mutex<Child>,
    next_id: AtomicU64,
    pending: Arc<Mutex<HashMap<u64, Sender<Value>>>>,
    current_read: Arc<Mutex<Option<u64>>>,
    audio: SyncSender<(u64, Vec<f32>)>,
    player: Arc<rodio::Player>,
    epoch: Arc<AtomicU64>,
    tray: Arc<Mutex<Option<tauri::tray::TrayIcon>>>,
    voice_started: Arc<std::sync::atomic::AtomicBool>,
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// Where the engine lives: the bundled copy in the app's resources, or the
/// repo venv while developing. The bundled binary needs no Python at all.
fn engine_command(app: &AppHandle) -> Command {
    use tauri::Manager;
    if !cfg!(debug_assertions) {
        if let Ok(resources) = app.path().resource_dir() {
            let bundled = resources.join("engine/readease-engine");
            if bundled.exists() {
                return Command::new(bundled);
            }
        }
    }
    let root = repo_root();
    let mut command = Command::new(root.join(".venv/bin/python"));
    command
        .args(["-m", "vieneu_reader.headless.server"])
        .current_dir(&root)
        .env("PYTHONPATH", root.join("src"));
    command
}

fn spawn_audio(
    epoch: Arc<AtomicU64>,
) -> Result<(SyncSender<(u64, Vec<f32>)>, Arc<rodio::Player>), String> {
    // The device sink is not Send, so a dedicated thread owns it for life.
    // The Player is all interior mutability, so pause/play/clear are safe
    // to call from command handlers while this thread appends.
    let (ready_tx, ready_rx) = channel();
    let (chunk_tx, chunk_rx) = sync_channel::<(u64, Vec<f32>)>(AUDIO_QUEUE_FRAMES);
    std::thread::spawn(move || {
        let device = match rodio::DeviceSinkBuilder::open_default_sink() {
            Ok(device) => device,
            Err(error) => {
                let _ = ready_tx.send(Err(format!("no output device: {error}")));
                return;
            }
        };
        let player = Arc::new(rodio::Player::connect_new(device.mixer()));
        let _ = ready_tx.send(Ok(player.clone()));
        for (chunk_epoch, samples) in chunk_rx {
            if chunk_epoch != epoch.load(Ordering::SeqCst) {
                continue; // a stop outran this frame; play nothing stale
            }
            player.append(rodio::buffer::SamplesBuffer::new(
                rodio::ChannelCount::new(1).expect("mono"),
                rodio::SampleRate::new(SAMPLE_RATE).expect("48kHz"),
                samples,
            ));
            player.play();
        }
    });
    let player = ready_rx
        .recv()
        .map_err(|_| "audio thread died".to_string())??;
    Ok((chunk_tx, player))
}

impl EngineClient {
    pub fn spawn(
        app: AppHandle,
        tray: Arc<Mutex<Option<tauri::tray::TrayIcon>>>,
    ) -> Result<Arc<Self>, String> {
        let mut child = engine_command(&app)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|error| format!("spawn engine: {error}"))?;

        let stdin = child.stdin.take().ok_or("engine stdin unavailable")?;
        let stdout = child.stdout.take().ok_or("engine stdout unavailable")?;

        let epoch = Arc::new(AtomicU64::new(0));
        let (audio, player) = spawn_audio(epoch.clone())?;

        let client = Arc::new(Self {
            stdin: Mutex::new(stdin),
            child: Mutex::new(child),
            next_id: AtomicU64::new(1),
            pending: Arc::new(Mutex::new(HashMap::new())),
            current_read: Arc::new(Mutex::new(None)),
            audio,
            player,
            epoch,
            tray,
            voice_started: Arc::new(std::sync::atomic::AtomicBool::new(true)),
        });

        let pending = client.pending.clone();
        let current_read = client.current_read.clone();
        let audio = client.audio.clone();
        let epoch_for_reader = client.epoch.clone();
        let client_for_reader = client.clone();
        let voice_started = client.voice_started.clone();
        std::thread::spawn(move || {
            let reader = BufReader::new(stdout);
            for line in reader.lines() {
                let Ok(line) = line else { break };
                let Ok(message) = serde_json::from_str::<Value>(&line) else {
                    continue;
                };
                match message.get("event").and_then(Value::as_str) {
                    Some("chunk") => {
                        let Some(pcm) =
                            message.get("pcm").and_then(Value::as_str)
                        else { continue };
                        let Ok(bytes) = BASE64.decode(pcm) else { continue };
                        let samples = bytes
                            .chunks_exact(4)
                            .map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]]))
                            .collect::<Vec<f32>>();
                        let stamped = epoch_for_reader.load(Ordering::SeqCst);
                        if !voice_started.swap(true, Ordering::SeqCst) {
                            // First audio of this reading: the model finished
                            // warming, the silence is over.
                            let _ = app.emit("reading:started", ());
                        }
                        // Blocks when the queue is full - that IS the flow
                        // control described in the module docs.
                        let _ = audio.send((stamped, samples));
                    }
                    Some("position") => {
                        let _ = app.emit("reading:position", &message);
                    }
                    Some(name) => {
                        // Progress and any future event reach the webview
                        // under a stable namespace instead of dying here.
                        let _ = app.emit(&format!("engine:{name}"), &message);
                    }
                    None => {
                        let id = message.get("id").and_then(Value::as_u64);
                        if let Some(id) = id {
                            if let Some(waiter) =
                                pending.lock().unwrap().remove(&id)
                            {
                                let _ = waiter.send(message);
                                continue;
                            }
                            let mut reading = current_read.lock().unwrap();
                            if *reading == Some(id) {
                                *reading = None;
                                drop(reading);
                                client_for_reader.show_tray(false);
                                let _ = app.emit("reading:done", &message);
                            } else {
                                drop(reading);
                                // A fire-without-waiting request (model
                                // download) finishes here; the webview is
                                // the only party still interested.
                                let _ = app.emit("engine:orphan_reply", &message);
                            }
                        }
                    }
                }
            }
            eprintln!("[engine] pipe closed");
        });

        Ok(client)
    }

    fn send(&self, id: u64, method: &str, params: Value) -> Result<(), String> {
        let line = json!({"id": id, "method": method, "params": params});
        let mut stdin = self.stdin.lock().unwrap();
        writeln!(stdin, "{line}").map_err(|error| format!("engine write: {error}"))
    }

    pub fn request(&self, method: &str, params: Value) -> Result<Value, String> {
        let id = self.next_id.fetch_add(1, Ordering::SeqCst);
        let (sender, receiver) = channel();
        self.pending.lock().unwrap().insert(id, sender);
        self.send(id, method, params)?;
        receiver
            .recv_timeout(Duration::from_secs(30))
            .map_err(|_| format!("engine timeout on {method}"))
    }

    /// A streaming request: chunks flow as events, completion is emitted.
    pub fn fire(&self, method: &str, params: Value) -> Result<(), String> {
        let id = self.next_id.fetch_add(1, Ordering::SeqCst);
        *self.current_read.lock().unwrap() = Some(id);
        // The menu bar indicator lives for the whole reading - including
        // paused, which the Qt shell got wrong and left no way out.
        self.show_tray(true);
        self.voice_started
            .store(false, std::sync::atomic::Ordering::SeqCst);
        self.send(id, method, params)
    }

    /// Send a request whose reply arrives as an `engine:orphan_reply`
    /// event instead of blocking a thread - for work that outlives any
    /// sane timeout, like a 625MB model download.
    pub fn notify(&self, method: &str, params: Value) -> Result<(), String> {
        let id = self.next_id.fetch_add(1, Ordering::SeqCst);
        self.send(id, method, params)
    }

    pub fn is_reading(&self) -> bool {
        self.current_read.lock().unwrap().is_some()
    }

    fn show_tray(&self, visible: bool) {
        if let Some(tray) = self.tray.lock().unwrap().as_ref() {
            let _ = tray.set_visible(visible);
        }
    }

    pub fn stop(&self) -> Result<(), String> {
        let began = Instant::now();
        // Silence first, protocol second: the ear judges stop latency by the
        // player, not by the engine's bookkeeping.
        self.epoch.fetch_add(1, Ordering::SeqCst);
        self.player.clear();
        *self.current_read.lock().unwrap() = None;
        self.show_tray(false);
        let reply = self.request("stop", json!({}));
        eprintln!("[stop] audio+engine in {:?}", began.elapsed());
        reply.map(|_| ())
    }

    pub fn pause(&self) {
        self.player.pause();
    }

    pub fn resume(&self) {
        self.player.play();
    }

    pub fn shutdown(&self) {
        if let Ok(mut child) = self.child.lock() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}
