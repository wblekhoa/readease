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
use std::sync::mpsc::{channel, sync_channel, Receiver, Sender, SyncSender};
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
/// How many frames the engine may have in flight before it must wait for
/// credits: one less than the queue, so the reading's own `Done` frame can
/// always be enqueued behind a full window without blocking the reader.
///
/// This is what keeps replies flowing while the player is paused. The
/// queue is bounded, a paused device drains nothing, and an engine that
/// kept writing filled the queue and blocked the reader thread on `send` -
/// with every reply (`model.status`, the voice list, a config save) stuck
/// behind the audio in the same stdout until the 30 s timeout. The engine
/// now writes only as many frames as it has been given room for; the drain
/// loop hands room back one credit at a time (`Feedback::credit`).
const ENGINE_WINDOW: usize = AUDIO_QUEUE_FRAMES - 1;

/// What crosses into the audio thread, in the order the engine produced it.
/// Positions travel the same queue as the audio they belong to, so they are
/// announced when the ear reaches them, not when the model wrote them. Each
/// frame names the reading it belongs to, so the room it frees goes back to
/// that reading and not to whichever one is running by then.
enum Frame {
    Chunk { epoch: u64, read_id: u64, samples: Vec<f32> },
    Position { epoch: u64, read_id: u64, message: Value },
    /// The engine's final reply. Announced as `reading:done` only once the
    /// device has played everything before it - a "done" that arrived while
    /// the last sentences were still in the speakers flipped the shell to
    /// finished mid-voice.
    Done { epoch: u64, message: Value },
}

pub struct EngineClient {
    stdin: Arc<Mutex<ChildStdin>>,
    child: Mutex<Child>,
    next_id: AtomicU64,
    pending: Arc<Mutex<HashMap<u64, Sender<Value>>>>,
    current_read: Arc<Mutex<Option<u64>>>,
    /// Held for the whole of starting a reading, so two fast clicks queue up
    /// behind each other instead of interleaving their cancel-and-send.
    start: Mutex<()>,
    audio: SyncSender<Frame>,
    player: Arc<dyn AudioSink>,
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

/// The audio device as the drain loop sees it.
///
/// rodio's `Player` is the production implementation. A test hands in one
/// that never drains - which is exactly what a PAUSED device is - because the
/// defect this file has to survive (F1, audit 05/09) only shows when the
/// device stops taking frames while the engine keeps producing them. Without
/// this seam the only way to see that was a native run and a 30-second wait.
pub(crate) trait AudioSink: Send + Sync {
    /// Frames appended and not yet consumed by the device.
    fn queued(&self) -> usize;
    fn append(&self, samples: Vec<f32>);
    fn play(&self);
    fn pause(&self);
    fn clear(&self);
}

impl AudioSink for rodio::Player {
    fn queued(&self) -> usize {
        self.len()
    }
    fn append(&self, samples: Vec<f32>) {
        rodio::Player::append(
            self,
            rodio::buffer::SamplesBuffer::new(
                rodio::ChannelCount::new(1).expect("mono"),
                rodio::SampleRate::new(SAMPLE_RATE).expect("48kHz"),
                samples,
            ),
        );
    }
    fn play(&self) {
        rodio::Player::play(self)
    }
    fn pause(&self) {
        rodio::Player::pause(self)
    }
    fn clear(&self) {
        rodio::Player::clear(self)
    }
}

/// The window and the menu bar, as the two loops see them: something to
/// emit an event at, and a tray to show or hide. Tauri in production; a
/// recorder in tests.
pub(crate) trait Shell: Send + Sync {
    fn emit(&self, event: &str, payload: Value);
    fn tray(&self, visible: bool);
}

struct TauriShell {
    app: AppHandle,
    tray: Arc<Mutex<Option<tauri::tray::TrayIcon>>>,
}

impl Shell for TauriShell {
    fn emit(&self, event: &str, payload: Value) {
        let _ = self.app.emit(event, payload);
    }
    fn tray(&self, visible: bool) {
        if let Some(tray) = self.tray.lock().unwrap().as_ref() {
            let _ = tray.set_visible(visible);
        }
    }
}

/// What the audio thread tells the ENGINE, as opposed to the webview: room
/// freed on the queue, and positions the ear has actually reached.
pub(crate) trait Feedback: Send + Sync {
    fn credit(&self, read_id: u64);
    fn reached(&self, read_id: u64, segment_id: &str);
}

/// Notifications down the engine's stdin. No `id`: nothing is asked, and
/// the engine sends nothing back.
struct StdinFeedback {
    stdin: Arc<Mutex<ChildStdin>>,
}

impl StdinFeedback {
    fn tell(&self, method: &str, params: Value) {
        let line = json!({"method": method, "params": params});
        if let Ok(mut stdin) = self.stdin.lock() {
            let _ = writeln!(stdin, "{line}");
        }
    }
}

impl Feedback for StdinFeedback {
    fn credit(&self, read_id: u64) {
        self.tell("audio.credit", json!({"id": read_id, "frames": 1}));
    }
    fn reached(&self, read_id: u64, segment_id: &str) {
        self.tell(
            "progress.reached",
            json!({"id": read_id, "segment_id": segment_id}),
        );
    }
}

/// The audio thread's whole life: take frames off the bounded queue, keep
/// only a little ahead of the ear, announce positions as the ear reaches
/// them, hand the engine back the room each frame frees, and say "done"
/// only when the device has gone quiet. Lifted out of `spawn_audio` so a
/// test can run it against a sink that never drains.
fn drain(
    frames: Receiver<Frame>,
    sink: Arc<dyn AudioSink>,
    epoch: Arc<AtomicU64>,
    paused: Arc<AtomicBool>,
    shell: Arc<dyn Shell>,
    feedback: Arc<dyn Feedback>,
) {
    let current = |stamped: u64| stamped == epoch.load(Ordering::SeqCst);
    for frame in frames {
        match frame {
            Frame::Chunk { epoch: stamped, read_id, samples } => {
                if !current(stamped) {
                    continue; // a stop outran this frame; play nothing stale
                }
                // Room on the queue, handed back the moment it is free: the
                // engine may now write one more frame.
                feedback.credit(read_id);
                // Keep only a little audio ahead of the ear. This is what
                // finally makes the queue fill, the engine's writes block,
                // and synthesis walk in step with playback.
                while sink.queued() > PLAYER_LOOKAHEAD && current(stamped) {
                    std::thread::sleep(Duration::from_millis(20));
                }
                if !current(stamped) {
                    continue;
                }
                sink.append(samples);
                // Only the person may un-pause. Appending must not.
                if !paused.load(Ordering::SeqCst) {
                    sink.play();
                }
            }
            Frame::Position { epoch: stamped, read_id, message } => {
                if !current(stamped) {
                    continue;
                }
                feedback.credit(read_id);
                // The ear is here (within the lookahead): the highlight
                // moves, and the engine may now remember the place. Progress
                // used to be written when the position was SYNTHESISED,
                // minutes ahead of anything anyone had heard.
                if let Some(segment) =
                    message.get("segment_id").and_then(Value::as_str)
                {
                    feedback.reached(read_id, segment);
                }
                shell.emit("reading:position", message);
            }
            Frame::Done { epoch: stamped, message } => {
                // Wait for the speakers, not the model. A stop meanwhile
                // (epoch moved) makes this reading nobody's business: the
                // stop path has already told the shell what it needs.
                while sink.queued() > 0 && current(stamped) {
                    std::thread::sleep(Duration::from_millis(20));
                }
                if !current(stamped) {
                    continue;
                }
                shell.tray(false);
                shell.emit("reading:done", message);
            }
        }
    }
}

fn spawn_audio(
    epoch: Arc<AtomicU64>,
    paused: Arc<AtomicBool>,
    shell: Arc<dyn Shell>,
    feedback: Arc<dyn Feedback>,
) -> Result<(SyncSender<Frame>, Arc<dyn AudioSink>), String> {
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
        let player: Arc<dyn AudioSink> =
            Arc::new(rodio::Player::connect_new(device.mixer()));
        let _ = ready_tx.send(Ok(player.clone()));
        drain(chunk_rx, player, epoch, paused, shell, feedback);
    });
    let player = ready_rx
        .recv()
        .map_err(|_| "audio thread died".to_string())??;
    Ok((chunk_tx, player))
}

/// Everything the reader thread shares with the rest of the client, and the
/// loop itself. Lifted out of `spawn` so a test can feed it lines instead of
/// a subprocess's stdout and watch what reaches `pending`.
pub(crate) struct Pump {
    pending: Arc<Mutex<HashMap<u64, Sender<Value>>>>,
    current_read: Arc<Mutex<Option<u64>>>,
    audio: SyncSender<Frame>,
    epoch: Arc<AtomicU64>,
    voice_started: Arc<AtomicBool>,
    notified: Arc<Mutex<HashSet<u64>>>,
    shell: Arc<dyn Shell>,
}

impl Pump {
    fn run(&self, lines: impl Iterator<Item = String>) {
        for line in lines {
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
                    let Some(read_id) = read_id
                        .filter(|id| Some(*id) == *self.current_read.lock().unwrap())
                    else { continue };
                    let stamped = self.epoch.load(Ordering::SeqCst);
                    if !self.voice_started.swap(true, Ordering::SeqCst) {
                        // First audio of this reading: the model finished
                        // warming, the silence is over.
                        self.shell.emit("reading:started", Value::Null);
                    }
                    // Never blocks while the engine honours its window: it
                    // has at most ENGINE_WINDOW frames in flight, and the
                    // queue holds one more. An engine that ignored the
                    // window would block here - bounded memory is the
                    // property a wrong fix would trade away.
                    let _ = self.audio.send(Frame::Chunk {
                        epoch: stamped,
                        read_id,
                        samples,
                    });
                }
                Some("position") => {
                    let read_id = message.get("id").and_then(Value::as_u64);
                    let Some(read_id) = read_id
                        .filter(|id| Some(*id) == *self.current_read.lock().unwrap())
                    else { continue };
                    // Down the audio queue, not straight to the webview:
                    // the highlight belongs to the ear, and the engine is
                    // minutes ahead of it.
                    let _ = self.audio.send(Frame::Position {
                        epoch: self.epoch.load(Ordering::SeqCst),
                        read_id,
                        message,
                    });
                }
                Some(name) => {
                    // Progress and any future event reach the webview
                    // under a stable namespace instead of dying here.
                    self.shell.emit(&format!("engine:{name}"), message);
                }
                None => {
                    let id = message.get("id").and_then(Value::as_u64);
                    if let Some(id) = id {
                        if let Some(waiter) =
                            self.pending.lock().unwrap().remove(&id)
                        {
                            let _ = waiter.send(message);
                            continue;
                        }
                        let mut reading = self.current_read.lock().unwrap();
                        if *reading == Some(id) {
                            *reading = None;
                            drop(reading);
                            // Behind the audio, not ahead of it: the shell
                            // hears "done" when the device does.
                            let _ = self.audio.send(Frame::Done {
                                epoch: self.epoch.load(Ordering::SeqCst),
                                message,
                            });
                        } else {
                            drop(reading);
                            // A fire-without-waiting request (model
                            // download) finishes here; the webview is the
                            // only party still interested. A SUPERSEDED
                            // reading also lands here, and must not be
                            // broadcast - it would look like a download
                            // finishing to whatever listener is mounted.
                            if self.notified.lock().unwrap().remove(&id) {
                                self.shell.emit("engine:orphan_reply", message);
                            }
                        }
                    }
                }
            }
        }
    }
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

        let stdin = Arc::new(Mutex::new(
            child.stdin.take().ok_or("engine stdin unavailable")?,
        ));
        let stdout = child.stdout.take().ok_or("engine stdout unavailable")?;

        let epoch = Arc::new(AtomicU64::new(0));
        let paused = Arc::new(AtomicBool::new(false));
        let shell: Arc<dyn Shell> = Arc::new(TauriShell {
            app: app.clone(),
            tray: tray.clone(),
        });
        let feedback: Arc<dyn Feedback> =
            Arc::new(StdinFeedback { stdin: stdin.clone() });
        let (audio, player) =
            spawn_audio(epoch.clone(), paused.clone(), shell.clone(), feedback)?;

        let client = Arc::new(Self {
            stdin,
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

        let pump = Pump {
            pending: client.pending.clone(),
            current_read: client.current_read.clone(),
            audio: client.audio.clone(),
            epoch: client.epoch.clone(),
            voice_started: client.voice_started.clone(),
            notified: client.notified.clone(),
            shell,
        };
        std::thread::spawn(move || {
            // A line that fails to read ends the pump, as it always did.
            pump.run(BufReader::new(stdout).lines().map_while(Result::ok));
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
    pub fn fire(&self, method: &str, mut params: Value) -> Result<(), String> {
        let _serialised = self.start.lock().unwrap();
        // The engine's window onto our queue. Sent with every reading so a
        // shell without it (a batch caller, an old build) still gets the
        // unbounded stream it always did.
        if let Some(object) = params.as_object_mut() {
            object.insert("window".into(), json!(ENGINE_WINDOW));
        }
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

#[cfg(test)]
mod tests {
    //! Receipts for the playback-reliability goal (Apps/ai-memory/plans/
    //! readease-playback-reliability.md). No device, no subprocess: the two
    //! loops run against a sink that behaves like a paused device and a
    //! shell that only records.

    use super::*;
    use std::sync::atomic::AtomicUsize;

    /// A device that holds whatever `queued` says and drains only when the
    /// test says so - a paused device, in other words. `append` fills it
    /// like a real player; `clear()` empties it, which is what the real
    /// `stop()`/`fire()` path does before sending anything.
    struct FakeSink {
        queued: AtomicUsize,
        appended: Mutex<Vec<usize>>,
    }

    impl FakeSink {
        /// The ear catches up: everything queued has been played.
        fn play_out(&self) {
            self.queued.store(0, Ordering::SeqCst);
        }
    }

    impl AudioSink for FakeSink {
        fn queued(&self) -> usize {
            self.queued.load(Ordering::SeqCst)
        }
        fn append(&self, samples: Vec<f32>) {
            self.appended.lock().unwrap().push(samples.len());
            self.queued.fetch_add(1, Ordering::SeqCst);
        }
        fn play(&self) {}
        fn pause(&self) {}
        fn clear(&self) {
            self.queued.store(0, Ordering::SeqCst);
        }
    }

    struct RecordingShell {
        events: Mutex<Vec<String>>,
    }

    impl RecordingShell {
        fn saw(&self, event: &str) -> bool {
            self.events.lock().unwrap().iter().any(|e| e == event)
        }
    }

    impl Shell for RecordingShell {
        fn emit(&self, event: &str, _payload: Value) {
            self.events.lock().unwrap().push(event.to_string());
        }
        fn tray(&self, _visible: bool) {}
    }

    /// The engine's side of the feedback: credits become room a producer
    /// may spend, positions reached are kept for the assertions.
    struct RecordingFeedback {
        credits: Mutex<Vec<u64>>,
        room: Arc<AtomicUsize>,
        reached: Mutex<Vec<(u64, String)>>,
    }

    impl Feedback for RecordingFeedback {
        fn credit(&self, read_id: u64) {
            self.credits.lock().unwrap().push(read_id);
            self.room.fetch_add(1, Ordering::SeqCst);
        }
        fn reached(&self, read_id: u64, segment_id: &str) {
            self.reached.lock().unwrap().push((read_id, segment_id.to_string()));
        }
    }

    struct Harness {
        sink: Arc<FakeSink>,
        shell: Arc<RecordingShell>,
        feedback: Arc<RecordingFeedback>,
        epoch: Arc<AtomicU64>,
        current_read: Arc<Mutex<Option<u64>>>,
        pending: Arc<Mutex<HashMap<u64, Sender<Value>>>>,
        lines: Sender<String>,
    }

    impl Harness {
        /// What `EngineClient::stop()` does to the shared state, in the
        /// order it does it: the reading's id goes first so the pump starts
        /// rejecting its lines, then the epoch kills frames already past
        /// that filter, then the device is silenced.
        fn stop(&self) {
            *self.current_read.lock().unwrap() = None;
            self.epoch.fetch_add(1, Ordering::SeqCst);
            self.sink.clear();
        }
    }

    /// The two loops wired exactly as `spawn()` wires them, minus the
    /// subprocess and the device. `queued` is the frames the "device" holds
    /// at the start; `paused` is whether the person has pressed pause.
    fn harness(queued: usize, paused: bool) -> Harness {
        let sink = Arc::new(FakeSink {
            queued: AtomicUsize::new(queued),
            appended: Mutex::new(Vec::new()),
        });
        let recorder = Arc::new(RecordingShell { events: Mutex::new(Vec::new()) });
        let shell: Arc<dyn Shell> = recorder.clone();
        let feedback_recorder = Arc::new(RecordingFeedback {
            credits: Mutex::new(Vec::new()),
            room: Arc::new(AtomicUsize::new(ENGINE_WINDOW)),
            reached: Mutex::new(Vec::new()),
        });
        let feedback: Arc<dyn Feedback> = feedback_recorder.clone();
        let epoch = Arc::new(AtomicU64::new(0));
        let paused = Arc::new(AtomicBool::new(paused));
        let (audio, frames) = sync_channel::<Frame>(AUDIO_QUEUE_FRAMES);
        {
            let (sink, epoch, paused, shell) =
                (sink.clone(), epoch.clone(), paused.clone(), shell.clone());
            std::thread::spawn(move || drain(frames, sink, epoch, paused, shell, feedback));
        }
        let pending = Arc::new(Mutex::new(HashMap::new()));
        // A reading is in flight, so chunk lines carrying id 1 are OURS and
        // reach the queue instead of being filtered as stale.
        let current_read = Arc::new(Mutex::new(Some(1)));
        let pump = Pump {
            pending: pending.clone(),
            current_read: current_read.clone(),
            audio,
            epoch: epoch.clone(),
            voice_started: Arc::new(AtomicBool::new(true)),
            notified: Arc::new(Mutex::new(HashSet::new())),
            shell,
        };
        let (lines, feed) = channel::<String>();
        std::thread::spawn(move || pump.run(feed.into_iter()));
        Harness { sink, shell: recorder, feedback: feedback_recorder, epoch, current_read, pending, lines }
    }

    fn chunk_line() -> String {
        json!({"event": "chunk", "id": 1, "pcm": BASE64.encode([0u8; 4])}).to_string()
    }

    fn position_line(segment: &str) -> String {
        json!({"event": "position", "id": 1, "segment_id": segment}).to_string()
    }

    fn final_reply_line() -> String {
        json!({"id": 1, "ok": true, "result": {"frames": 3}}).to_string()
    }

    /// Ask something while a reading is in flight, the way `request()` does:
    /// register the waiter, then let the engine's reply line arrive.
    fn ask(h: &Harness, id: u64) -> Receiver<Value> {
        let (tx, rx) = channel();
        h.pending.lock().unwrap().insert(id, tx);
        rx
    }

    /// An engine that honours its window: writes a frame only when it has
    /// room, spending one credit per frame. Gives up when no room comes for
    /// a while, so a broken drain loop fails the test instead of hanging it.
    fn honouring_engine(h: &Harness, frames: usize) -> std::thread::JoinHandle<usize> {
        let room = h.feedback.room.clone();
        let lines = h.lines.clone();
        std::thread::spawn(move || {
            let mut sent = 0;
            let mut idle = 0;
            while sent < frames {
                if room.load(Ordering::SeqCst) > 0 {
                    room.fetch_sub(1, Ordering::SeqCst);
                    lines.send(chunk_line()).unwrap();
                    sent += 1;
                    idle = 0;
                } else {
                    idle += 1;
                    if idle > 100 {
                        break; // ~1 s without room: the device is paused
                    }
                    std::thread::sleep(Duration::from_millis(10));
                }
            }
            sent
        })
    }

    fn wait_until(what: impl Fn() -> bool, timeout: Duration) -> bool {
        let began = Instant::now();
        while began.elapsed() < timeout {
            if what() {
                return true;
            }
            std::thread::sleep(Duration::from_millis(10));
        }
        what()
    }

    /// Enough to fill the bounded queue AND the drain loop's one held frame,
    /// with room to spare: 48 in the channel, one in the loop, one blocked.
    const MORE_THAN_THE_QUEUE: usize = 60;

    /// F1, fixed. The device is paused holding three frames (> lookahead), so
    /// the drain loop waits and nothing plays; an engine that honours its
    /// window fills it and then waits for credits; a reply to an unrelated
    /// request arrives on time, because the reader never blocked.
    #[test]
    fn an_engine_that_honours_its_window_never_starves_a_reply_while_paused() {
        let h = harness(PLAYER_LOOKAHEAD + 1, true);
        let reply = ask(&h, 7);
        let engine = honouring_engine(&h, MORE_THAN_THE_QUEUE);
        // Let the window fill before the request goes out, so this is a
        // reply behind a FULL window and not behind an empty queue.
        assert!(
            wait_until(|| h.feedback.room.load(Ordering::SeqCst) == 0, Duration::from_secs(2)),
            "the window never filled - the engine did not send"
        );
        h.lines.send(json!({"id": 7, "ok": true, "result": {}}).to_string()).unwrap();
        assert!(
            reply.recv_timeout(Duration::from_millis(500)).is_ok(),
            "reply starved behind a full audio queue"
        );
        let sent = engine.join().unwrap();
        // The drain loop took exactly one frame (the one it is holding while
        // the device stays full) and handed that room straight back.
        assert_eq!(sent, ENGINE_WINDOW + 1, "credits granted: {:?}", h.feedback.credits.lock().unwrap());
        assert!(h.feedback.credits.lock().unwrap().iter().all(|id| *id == 1));
        // Id 7 is a plain request, not the reading's final reply: the pump
        // must route it to its waiter and NOT declare the reading finished.
        assert!(!h.shell.saw("reading:done"), "an unrelated reply was mistaken for the end of the reading");
    }

    /// The tail slot. A full window plus the final reply's own `Done` frame
    /// must still fit the queue, or the reader blocks on the very last line
    /// of a paused reading - F1 again, at the end of every chapter.
    #[test]
    fn the_final_reply_of_a_paused_reading_does_not_block_the_reader() {
        let h = harness(PLAYER_LOOKAHEAD + 1, true);
        let engine = honouring_engine(&h, ENGINE_WINDOW + 1);
        assert_eq!(engine.join().unwrap(), ENGINE_WINDOW + 1);
        h.lines.send(final_reply_line()).unwrap();
        // A later, unrelated reply proves the pump got past the Done frame.
        let reply = ask(&h, 8);
        h.lines.send(json!({"id": 8, "ok": true, "result": {}}).to_string()).unwrap();
        assert!(reply.recv_timeout(Duration::from_millis(500)).is_ok(), "the reader blocked enqueueing Done");
        // Paused, with audio still in the device: NOT done yet.
        assert!(!h.shell.saw("reading:done"));
    }

    /// The control for the misbehaving case, and the finding it pins: Stop
    /// self-heals. An engine that IGNORES the window jams the reader (the
    /// pre-fix world); what `stop()` does first - move the epoch, clear the
    /// device - frees it, and not one stale frame reaches the speakers.
    #[test]
    fn a_stop_frees_a_reader_jammed_by_an_engine_that_ignores_the_window() {
        let h = harness(PLAYER_LOOKAHEAD + 1, true);
        let reply = ask(&h, 7);
        for _ in 0..MORE_THAN_THE_QUEUE {
            h.lines.send(chunk_line()).unwrap();
        }
        h.lines.send(json!({"id": 7, "ok": true, "result": {}}).to_string()).unwrap();
        // The jam is real: the reply sits behind the audio.
        assert!(reply.recv_timeout(Duration::from_millis(300)).is_err(), "no jam formed - the queue never filled");
        h.stop();
        assert!(reply.recv_timeout(Duration::from_secs(5)).is_ok(), "reply did not arrive after the stop");
        assert!(h.sink.appended.lock().unwrap().is_empty(), "a stale frame reached the device after the stop");
    }

    /// R5: bounded memory is the property a wrong fix would trade away. A
    /// device that never drains is handed the lookahead and nothing more,
    /// however much the engine produces.
    #[test]
    fn a_device_that_never_drains_is_never_overfed() {
        let h = harness(0, false);
        for _ in 0..MORE_THAN_THE_QUEUE {
            h.lines.send(chunk_line()).unwrap();
        }
        assert!(wait_until(
            || h.sink.appended.lock().unwrap().len() == PLAYER_LOOKAHEAD + 1,
            Duration::from_secs(2),
        ));
        std::thread::sleep(Duration::from_millis(200));
        assert_eq!(h.sink.appended.lock().unwrap().len(), PLAYER_LOOKAHEAD + 1);
    }

    /// F2, the shell's half. "Done" waits for the device to go quiet, and a
    /// position is reported to the engine as REACHED when the ear gets
    /// there - not when the model wrote it.
    #[test]
    fn done_is_announced_only_after_the_device_has_played_out() {
        let h = harness(0, false);
        h.lines.send(position_line("s-1")).unwrap();
        h.lines.send(chunk_line()).unwrap();
        h.lines.send(final_reply_line()).unwrap();
        assert!(wait_until(|| h.shell.saw("reading:position"), Duration::from_secs(2)));
        assert_eq!(*h.feedback.reached.lock().unwrap(), vec![(1, "s-1".to_string())]);
        // The chunk is in the device and has not played: not done.
        std::thread::sleep(Duration::from_millis(200));
        assert!(!h.shell.saw("reading:done"), "done arrived while audio was still in the speakers");
        h.sink.play_out();
        assert!(wait_until(|| h.shell.saw("reading:done"), Duration::from_secs(2)), "done never arrived after the device drained");
    }

    /// A stop while the tail is still playing makes the reading nobody's
    /// business: no late "done" for a reading the shell already ended.
    #[test]
    fn a_stopped_reading_never_reports_done() {
        let h = harness(0, false);
        h.lines.send(chunk_line()).unwrap();
        h.lines.send(final_reply_line()).unwrap();
        assert!(wait_until(|| !h.sink.appended.lock().unwrap().is_empty(), Duration::from_secs(2)));
        h.stop();
        std::thread::sleep(Duration::from_millis(200));
        assert!(!h.shell.saw("reading:done"));
    }
}
