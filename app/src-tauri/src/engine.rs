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

use std::collections::{HashMap, HashSet};
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
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
/// How much synthesised audio may sit in the player ahead of the ear.
///
/// The engine synthesises far faster than playback, and the player's own
/// queue is unbounded - so without this the whole book races ahead, the
/// "backpressure" this module claims never engages, and the highlight (which
/// the engine emits as it SYNTHESISES) runs minutes ahead of the voice.
const PLAYER_LOOKAHEAD: usize = 2;

/// What crosses into the audio thread, in the order the engine produced it.
/// Positions travel the same queue as the audio they belong to, so they are
/// announced when the ear reaches them, not when the model wrote them.
enum Frame {
    Chunk(u64, Vec<f32>),
    Position(u64, Value),
}

pub struct EngineClient {
    stdin: Mutex<ChildStdin>,
    child: Mutex<Child>,
    next_id: AtomicU64,
    pending: Arc<Mutex<HashMap<u64, Sender<Value>>>>,
    current_read: Arc<Mutex<Option<u64>>>,
    /// Held for the whole of starting a reading, so two fast clicks queue up
    /// behind each other instead of interleaving their cancel-and-send.
    start: Mutex<()>,
    audio: SyncSender<Frame>,
    player: Arc<rodio::Player>,
    epoch: Arc<AtomicU64>,
    /// Pause is a state, not an event: the audio thread must not un-pause the
    /// player just because another chunk arrived.
    paused: Arc<AtomicBool>,
    tray: Arc<Mutex<Option<tauri::tray::TrayIcon>>>,
    voice_started: Arc<std::sync::atomic::AtomicBool>,
    /// Requests whose reply nobody waits for. Only these may surface as
    /// `engine:orphan_reply`; a superseded reading's late reply is dropped
    /// instead of being broadcast at whatever listener happens to be mounted.
    notified: Arc<Mutex<HashSet<u64>>>,
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
    paused: Arc<AtomicBool>,
    app: tauri::AppHandle,
) -> Result<(SyncSender<Frame>, Arc<rodio::Player>), String> {
    // The device sink is not Send, so a dedicated thread owns it for life.
    // The Player is all interior mutability, so pause/play/clear are safe
    // to call from command handlers while this thread appends.
    let (ready_tx, ready_rx) = channel();
    let (chunk_tx, chunk_rx) = sync_channel::<Frame>(AUDIO_QUEUE_FRAMES);
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
        for frame in chunk_rx {
            match frame {
                Frame::Chunk(chunk_epoch, samples) => {
                    if chunk_epoch != epoch.load(Ordering::SeqCst) {
                        continue; // a stop outran this frame; play nothing stale
                    }
                    // Keep only a little audio ahead of the ear. This is what
                    // finally makes the queue fill, the engine's writes block,
                    // and synthesis walk in step with playback.
                    while player.len() > PLAYER_LOOKAHEAD
                        && chunk_epoch == epoch.load(Ordering::SeqCst)
                    {
                        std::thread::sleep(std::time::Duration::from_millis(20));
                    }
                    if chunk_epoch != epoch.load(Ordering::SeqCst) {
                        continue;
                    }
                    player.append(rodio::buffer::SamplesBuffer::new(
                        rodio::ChannelCount::new(1).expect("mono"),
                        rodio::SampleRate::new(SAMPLE_RATE).expect("48kHz"),
                        samples,
                    ));
                    // Only the person may un-pause. Appending must not.
                    if !paused.load(Ordering::SeqCst) {
                        player.play();
                    }
                }
                Frame::Position(frame_epoch, message) => {
                    if frame_epoch != epoch.load(Ordering::SeqCst) {
                        continue;
                    }
                    let _ = app.emit("reading:position", &message);
                }
            }
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
        let paused = Arc::new(AtomicBool::new(false));
        let (audio, player) =
            spawn_audio(epoch.clone(), paused.clone(), app.clone())?;

        let client = Arc::new(Self {
            stdin: Mutex::new(stdin),
            child: Mutex::new(child),
            next_id: AtomicU64::new(1),
            pending: Arc::new(Mutex::new(HashMap::new())),
            current_read: Arc::new(Mutex::new(None)),
            audio,
            player,
            epoch,
            paused,
            start: Mutex::new(()),
            notified: Arc::new(Mutex::new(HashSet::new())),
            tray,
            voice_started: Arc::new(std::sync::atomic::AtomicBool::new(true)),
        });

        let pending = client.pending.clone();
        let current_read = client.current_read.clone();
        let audio = client.audio.clone();
        let epoch_for_reader = client.epoch.clone();
        let client_for_reader = client.clone();
        let voice_started = client.voice_started.clone();
        let notified_for_reader = client.notified.clone();
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
                        // Whose reading is this? An event from a superseded
                        // reading must die here - before it clears the warming
                        // notice or reaches the speakers.
                        let read_id = message.get("id").and_then(Value::as_u64);
                        if read_id != *current_read.lock().unwrap() {
                            continue;
                        }
                        let stamped = epoch_for_reader.load(Ordering::SeqCst);
                        if !voice_started.swap(true, Ordering::SeqCst) {
                            // First audio of this reading: the model finished
                            // warming, the silence is over.
                            let _ = app.emit("reading:started", ());
                        }
                        // Blocks when the queue is full - that IS the flow
                        // control described in the module docs.
                        let _ = audio.send(Frame::Chunk(stamped, samples));
                    }
                    Some("position") => {
                        if message.get("id").and_then(Value::as_u64)
                            != *current_read.lock().unwrap()
                        {
                            continue;
                        }
                        // Down the audio queue, not straight to the webview:
                        // the highlight belongs to the ear, and the engine is
                        // minutes ahead of it.
                        let _ = audio.send(Frame::Position(
                            epoch_for_reader.load(Ordering::SeqCst),
                            message,
                        ));
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
                                // download) finishes here; the webview is the
                                // only party still interested. A SUPERSEDED
                                // reading also lands here, and must not be
                                // broadcast - it would look like a download
                                // finishing to whatever listener is mounted.
                                if notified_for_reader.lock().unwrap().remove(&id) {
                                    let _ = app.emit("engine:orphan_reply", &message);
                                }
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

    /// Ask the engine something and wait for its answer.
    ///
    /// A REFUSAL COMES BACK AS `Err`. The engine answers every request with
    /// `{"ok": true, "result": …}` or `{"ok": false, "error": …}`, and this
    /// used to hand both to the caller as `Ok(envelope)` - so a refusal
    /// arrived in the webview looking like a success with no `result`, and
    /// `reply.result.value` threw. That is how one missing config key
    /// ("voice_shortlist", 05/09) crashed the voice-loading chain and put
    /// "could not fetch the voice list" under a list that had loaded fine.
    ///
    /// Every caller on the far side already has a `.catch` for a failed
    /// request. This makes those catches true: the harness has always
    /// modelled engine failure as a rejection, and now the real boundary
    /// does the same thing.
    pub fn request(&self, method: &str, params: Value) -> Result<Value, String> {
        let id = self.next_id.fetch_add(1, Ordering::SeqCst);
        let (sender, receiver) = channel();
        self.pending.lock().unwrap().insert(id, sender);
        self.send(id, method, params)?;
        let reply = receiver
            .recv_timeout(Duration::from_secs(30))
            .map_err(|_| format!("engine timeout on {method}"))?;
        if reply["ok"] == Value::Bool(false) {
            let said = reply["error"].as_str().unwrap_or("no reason given");
            return Err(format!("engine refused {method}: {said}"));
        }
        Ok(reply)
    }

    /// Start a reading, cancelling whatever was being read.
    ///
    /// One reading at a time is the whole contract. Without the cancel, the
    /// engine DEFERS the new request (it queues non-stop requests while it
    /// streams) and finishes the old text first - so an impatient second
    /// click used to buy a second full reading rather than a new one.
    ///
    /// The order matters and was got wrong once: current_read moves FIRST so
    /// the reader thread starts rejecting the old reading's events; only then
    /// is the epoch bumped to kill frames already past that filter.
    pub fn fire(&self, method: &str, params: Value) -> Result<(), String> {
        let _serialised = self.start.lock().unwrap();
        let was_reading = self.is_reading();
        let id = self.next_id.fetch_add(1, Ordering::SeqCst);
        *self.current_read.lock().unwrap() = Some(id);
        self.epoch.fetch_add(1, Ordering::SeqCst);
        self.player.clear();
        // `clear()` leaves the player paused (rodio does that deliberately),
        // and a person who pressed pause stays paused until they say so.
        self.paused.store(false, Ordering::SeqCst);
        self.player.play();
        if was_reading {
            // Tell the engine to abandon the old reading. It answers this
            // between utterances, so the reply is prompt, and the request we
            // send next is the one it picks up.
            let _ = self.request("stop", json!({}));
        }
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
        self.notified.lock().unwrap().insert(id);
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
        // Same lock as `fire`, and for the same reason: both rewrite
        // current_read, the epoch and the player. Without it, "stop this and
        // read from here" - one gesture, two commands, two Tauri threads -
        // could interleave so that stop wiped the id of the reading that had
        // just begun. Its reply then matched nobody, no `reading:done` was
        // ever emitted, and the shell sat on "đang đọc" in silence with no
        // way out. Found by independent review, 2026-09-02.
        let _serialised = self.start.lock().unwrap();
        let began = Instant::now();
        // Silence first, protocol second: the ear judges stop latency by the
        // player, not by the engine's bookkeeping.
        self.epoch.fetch_add(1, Ordering::SeqCst);
        *self.current_read.lock().unwrap() = None;
        self.player.clear();
        // Stopping releases the pause too: the next reading starts audible.
        self.paused.store(false, Ordering::SeqCst);
        self.show_tray(false);
        let reply = self.request("stop", json!({}));
        eprintln!("[stop] audio+engine in {:?}", began.elapsed());
        reply.map(|_| ())
    }

    pub fn pause(&self) {
        self.paused.store(true, Ordering::SeqCst);
        self.player.pause();
    }

    pub fn resume(&self) {
        self.paused.store(false, Ordering::SeqCst);
        self.player.play();
    }

    pub fn shutdown(&self) {
        if let Ok(mut child) = self.child.lock() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}
