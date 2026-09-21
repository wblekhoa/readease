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

use std::collections::{HashMap, HashSet, VecDeque};
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::mpsc::{channel, sync_channel, Receiver, RecvTimeoutError, Sender, SyncSender};
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
///
/// Four frames, not two (19/09): at two the device held 0.4-1 s, and a
/// model that stumbles for longer than that - the fp32 build on a busy
/// Mac - left the speakers with nothing to say for a moment, which the
/// owner heard as a stutter in the voice samples. Positions are announced
/// by frames finished, not by this number, so the highlight keeps time.
const PLAYER_LOOKAHEAD: usize = 4;
/// How much audio a reading gathers before its first sound.
///
/// The model's first chunks arrive at about the speed they play (measured
/// 19/09 on the shipped fp32 build: 0.23 s of audio, then 0.24 s until the
/// next; 0.28 s, then 0.32 s) - so a device that starts on the first chunk
/// runs dry twice in the first second. Holding this much first costs the
/// first sound that long and buys an unbroken one. A reading shorter than
/// this plays as soon as its last frame is in; a slow engine is not waited
/// for past `PREBUFFER_MAX_WAIT`, and a full lookahead ends the hold too.
const PREBUFFER_SECS: f32 = 0.6;
const PREBUFFER_MAX_WAIT: Duration = Duration::from_millis(1500);
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
/// A pause this long is a break, not a breath: resuming after it goes back
/// to the start of the sentence in the ear (HIG 3.23). Measured on the wall
/// clock so a Mac that slept through the pause counts it too.
const REWIND_AFTER: Duration = Duration::from_secs(30);

/// Whether resuming now should replay the sentence: only after a real break.
fn should_rewind(paused_since: Option<std::time::SystemTime>, now: std::time::SystemTime) -> bool {
    paused_since
        .and_then(|since| now.duration_since(since).ok())
        .is_some_and(|paused| paused >= REWIND_AFTER)
}

/// What a reader is told when the engine process disappears underneath a
/// reading. Written in Vietnamese, like the engine's own sentences, so the
/// shell's `engineMessage()` says it in the reader's language; the pair
/// lives in `RUNTIME_EN` and `engineMessage.test.ts` pins both halves.
const ENGINE_GONE: &str = "Bộ máy đọc đã dừng đột ngột. Hãy khởi động lại ứng dụng.";

/// What crosses into the audio thread, in the order the engine produced it.
/// Positions travel the same queue as the audio they belong to, so they are
/// announced when the ear reaches them, not when the model wrote them. Each
/// frame names the reading it belongs to, so the room it frees goes back to
/// that reading and not to whichever one is running by then.
enum Frame {
    /// `voiced` is the engine's `from_voice`: a rest between sentences, a
    /// paragraph pause, a chime or a figure cue is `false`. It is how the
    /// audio thread knows where a sentence begins (HIG 3.23).
    Chunk { epoch: u64, read_id: u64, samples: Vec<f32>, voiced: bool },
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
    /// When the pause began, on the wall clock - a resume after `REWIND_AFTER`
    /// replays the sentence (HIG 3.23).
    paused_since: Mutex<Option<std::time::SystemTime>>,
    /// The audio thread's order to replay the sentence in the ear, served
    /// wherever that thread next looks up.
    rewind: Arc<AtomicBool>,
    tray: Arc<Mutex<Option<tauri::tray::TrayIcon>>>,
    voice_started: Arc<std::sync::atomic::AtomicBool>,
    /// Where the voice goes (HIG 3.21), for the page to ask after it has
    /// loaded - the `audio:device` event fires before it exists.
    pub output: AudioOutput,
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

/// A position the ear has not reached yet: announced once every frame
/// appended before it has finished playing.
struct DuePosition {
    epoch: u64,
    read_id: u64,
    /// How many frames had been handed to the device when this position was
    /// dequeued - the count the device must have finished before the ear is
    /// here.
    at: u64,
    message: Value,
}

/// How often the drain loop looks at the device while nothing new arrives:
/// the ceiling on how late a position can be announced.
const POSITION_POLL: Duration = Duration::from_millis(20);

/// The frames handed to the device since the start of the sentence before
/// the one in the ear - what a resume after a long pause replays (HIG
/// 3.23). The engine cannot help here: it is up to `ENGINE_WINDOW` frames
/// ahead and does not un-synthesise; only this thread ever held exactly
/// what was heard.
///
/// A sentence starts at a voiced frame that follows a silent one: the
/// engine marks rests between sentences, paragraph pauses, chimes and figure
/// cues all `from_voice: false`, so one rule finds every joint. Trimmed as
/// the ear moves on, so it never holds more than two begun sentences plus
/// whatever is still in the device.
struct Shadow {
    epoch: u64,
    /// Absolute index (frames handed to the device before it) of `frames[0]`.
    base: u64,
    frames: VecDeque<(bool, Vec<f32>)>,
    /// Samples held in `frames`, so the bound below is cheap to keep.
    samples: usize,
    /// Absolute indexes where a sentence begins, oldest first.
    starts: VecDeque<u64>,
}

/// The most a shadow may hold, whatever the engine sends: a minute. Two
/// sentences never come near it; a reading with no rests in it would.
const SHADOW_MAX_SAMPLES: usize = 60 * SAMPLE_RATE as usize;

impl Shadow {
    fn new() -> Self {
        Shadow { epoch: 0, base: 0, frames: VecDeque::new(), samples: 0, starts: VecDeque::new() }
    }

    fn drop_front(&mut self) {
        if let Some((_, samples)) = self.frames.pop_front() {
            self.samples -= samples.len();
            self.base += 1;
        }
    }

    /// Remember a frame as it goes to the device. `index` is how many went
    /// before it; a new epoch (a stop, a new reading) forgets the old ones.
    fn push(&mut self, epoch: u64, index: u64, voiced: bool, samples: &[f32]) {
        if epoch != self.epoch || self.frames.is_empty() {
            self.epoch = epoch;
            self.base = index;
            self.frames.clear();
            self.samples = 0;
            self.starts.clear();
        }
        let after_silence = self.frames.back().is_none_or(|(voiced, _)| !voiced);
        if voiced && after_silence {
            self.starts.push_back(index);
        }
        self.samples += samples.len();
        self.frames.push_back((voiced, samples.to_vec()));
    }

    /// Let go of what a rewind could no longer want: `ear` is the index of
    /// the frame the device is playing (`appended - queued`). Two begun
    /// sentences are kept - the one in the ear and the one before it.
    fn trim(&mut self, ear: u64) {
        while self.starts.len() >= 3 && self.starts[2] <= ear {
            self.starts.pop_front();
        }
        let keep_from = match self.starts.front() {
            Some(start) => *start,
            // Nothing voiced yet: nothing to rewind to, hold only the device's own.
            None => ear,
        };
        while self.base < keep_from && !self.frames.is_empty() {
            self.drop_front();
        }
        // The bound: what is already behind the ear goes first, and a
        // sentence start that fell off with it is no longer a target.
        while self.samples > SHADOW_MAX_SAMPLES && self.base < ear {
            self.drop_front();
        }
        while self.starts.front().is_some_and(|start| *start < self.base) {
            self.starts.pop_front();
        }
    }

    /// Where a resume after a break should start again from: the sentence
    /// before the one in the ear, or - when the ear is in the silence after
    /// a sentence, the common place to have pressed pause - that sentence.
    fn target(&self, ear: u64) -> Option<u64> {
        let in_voice = ear
            .checked_sub(self.base)
            .and_then(|offset| self.frames.get(offset as usize))
            .is_some_and(|(voiced, _)| *voiced);
        let mut begun = self.starts.iter().copied().filter(|start| *start <= ear);
        let current = begun.next_back()?;
        if in_voice {
            Some(begun.next_back().unwrap_or(current))
        } else {
            Some(current)
        }
    }

    /// Hand the device everything from `target` on, again, in order.
    fn replay(&self, target: u64, sink: &dyn AudioSink) -> usize {
        let skip = target.saturating_sub(self.base) as usize;
        let mut count = 0;
        for (_, samples) in self.frames.iter().skip(skip) {
            sink.append(samples.clone());
            count += 1;
        }
        count
    }
}

/// The audio thread's whole life: take frames off the bounded queue, keep
/// only a little ahead of the ear, announce positions as the ear reaches
/// them, hand the engine back the room each frame frees, and say "done"
/// only when the device has gone quiet. Lifted out of `spawn_audio` so a
/// test can run it against a sink that never drains.
///
/// A position is announced when the ear REACHES it, not when it is
/// dequeued. Measured 15/09: dequeued, it fired while up to three frames
/// of the previous sentence were still in the device - and a frame is a
/// whole sentence when that sentence came from the cache - so the
/// highlight moved a paragraph early, every paragraph. Now each position
/// remembers how many frames went to the device before it and waits until
/// that many have finished playing (`appended - queued`); the device is
/// looked at every `POSITION_POLL` even when no frame arrives, so a
/// position due while the engine is slow is not held until the next chunk.
fn drain(
    frames: Receiver<Frame>,
    sink: Arc<dyn AudioSink>,
    epoch: Arc<AtomicU64>,
    paused: Arc<AtomicBool>,
    rewind: Arc<AtomicBool>,
    shell: Arc<dyn Shell>,
    feedback: Arc<dyn Feedback>,
) {
    let current = |stamped: u64| stamped == epoch.load(Ordering::SeqCst);
    // Frames handed to the device over the thread's whole life; with what
    // the device still holds, that is how many it has finished.
    let mut appended: u64 = 0;
    let mut due: VecDeque<DuePosition> = VecDeque::new();
    let mut shadow = Shadow::new();
    // A resume after a break (HIG 3.23): the device is cleared and handed
    // the sentence again from its start. `appended` is deliberately NOT
    // moved - the frames are the same frames - so `appended - queued` is
    // still the index of the frame in the ear and every position still
    // waiting in `due` fires when the ear passes it the second time. The
    // page only ever calls `play()` itself for a SHORT pause; here the
    // device starts again only once the sentence is back in it, and only
    // if nobody pressed pause again meanwhile.
    let rewind_if_asked = |shadow: &mut Shadow, appended: u64| {
        if !rewind.swap(false, Ordering::SeqCst) {
            return;
        }
        if current(shadow.epoch) {
            let ear = appended.saturating_sub(sink.queued() as u64);
            if let Some(target) = shadow.target(ear) {
                sink.clear();
                let replayed = shadow.replay(target, &*sink);
                eprintln!("[audio] resumed after a break: {} frame(s) again", replayed);
            }
        }
        if !paused.load(Ordering::SeqCst) {
            sink.play();
        }
    };
    // The prebuffer: which reading (by epoch) is being held back from the
    // speakers, how much of it has been gathered, and since when.
    let mut hold: Option<(u64, f32, Instant)> = None;
    let release = |hold: &mut Option<(u64, f32, Instant)>| {
        if hold.take().is_some() && !paused.load(Ordering::SeqCst) {
            sink.play();
        }
    };
    let announce = |due: &mut VecDeque<DuePosition>, appended: u64| {
        let played = appended.saturating_sub(sink.queued() as u64);
        while due.front().is_some_and(|next| next.at <= played) {
            let next = due.pop_front().expect("checked");
            if !current(next.epoch) {
                continue; // a stop outran it; the highlight must not move
            }
            // The ear is here: the highlight moves, and the engine may now
            // remember the place. Progress used to be written when the
            // position was SYNTHESISED, minutes ahead of anything anyone
            // had heard.
            if let Some(segment) = next.message.get("segment_id").and_then(Value::as_str) {
                feedback.reached(next.read_id, segment);
            }
            shell.emit("reading:position", next.message);
        }
    };
    loop {
        let frame = match frames.recv_timeout(POSITION_POLL) {
            Ok(frame) => frame,
            Err(RecvTimeoutError::Timeout) => {
                announce(&mut due, appended);
                rewind_if_asked(&mut shadow, appended);
                shadow.trim(appended.saturating_sub(sink.queued() as u64));
                // An engine too slow to fill the prebuffer is not waited
                // for: what has been gathered plays.
                if hold.is_some_and(|(_, _, since)| since.elapsed() >= PREBUFFER_MAX_WAIT) {
                    release(&mut hold);
                }
                continue;
            }
            Err(RecvTimeoutError::Disconnected) => break,
        };
        match frame {
            Frame::Chunk { epoch: stamped, read_id, samples, voiced } => {
                if !current(stamped) {
                    continue; // a stop outran this frame; play nothing stale
                }
                // Room on the queue, handed back the moment it is free: the
                // engine may now write one more frame.
                feedback.credit(read_id);
                // Before this frame could start the device on its own.
                rewind_if_asked(&mut shadow, appended);
                // A reading's first frame: hold the device until enough of
                // the reading is in it to play without running dry. The
                // device is paused for it explicitly - after a `Done` it is
                // still playing, and would speak this frame on its own.
                if hold.as_ref().is_none_or(|(held, _, _)| *held != stamped) {
                    hold = Some((stamped, 0.0, Instant::now()));
                    sink.pause();
                }
                // Keep only a little audio ahead of the ear. This is what
                // finally makes the queue fill, the engine's writes block,
                // and synthesis walk in step with playback. A held device
                // cannot drain, so the hold ends before this could wait.
                if sink.queued() > PLAYER_LOOKAHEAD {
                    release(&mut hold);
                }
                while sink.queued() > PLAYER_LOOKAHEAD && current(stamped) {
                    announce(&mut due, appended);
                    rewind_if_asked(&mut shadow, appended);
                    shadow.trim(appended.saturating_sub(sink.queued() as u64));
                    std::thread::sleep(POSITION_POLL);
                }
                if !current(stamped) {
                    continue;
                }
                let seconds = samples.len() as f32 / SAMPLE_RATE as f32;
                shadow.push(stamped, appended, voiced, &samples);
                sink.append(samples);
                appended += 1;
                if let Some((_, gathered, _)) = hold.as_mut() {
                    *gathered += seconds;
                    if *gathered >= PREBUFFER_SECS {
                        release(&mut hold);
                    }
                } else if !paused.load(Ordering::SeqCst) {
                    // Only the person may un-pause. Appending must not.
                    sink.play();
                }
                announce(&mut due, appended);
            }
            Frame::Position { epoch: stamped, read_id, message } => {
                if !current(stamped) {
                    continue;
                }
                feedback.credit(read_id);
                due.push_back(DuePosition { epoch: stamped, read_id, at: appended, message });
                announce(&mut due, appended);
            }
            Frame::Done { epoch: stamped, message } => {
                // A reading shorter than the prebuffer - a voice sample, one
                // line - is whole now: play it.
                if hold.is_some_and(|(held, _, _)| held == stamped) {
                    release(&mut hold);
                }
                // Wait for the speakers, not the model. A stop meanwhile
                // (epoch moved) makes this reading nobody's business: the
                // stop path has already told the shell what it needs.
                while sink.queued() > 0 && current(stamped) {
                    announce(&mut due, appended);
                    rewind_if_asked(&mut shadow, appended);
                    std::thread::sleep(POSITION_POLL);
                }
                if !current(stamped) {
                    continue;
                }
                announce(&mut due, appended);
                shell.tray(false);
                shell.emit("reading:done", message);
            }
        }
    }
}

fn spawn_audio(
    epoch: Arc<AtomicU64>,
    paused: Arc<AtomicBool>,
    rewind: Arc<AtomicBool>,
    shell: Arc<dyn Shell>,
    feedback: Arc<dyn Feedback>,
) -> Result<(SyncSender<Frame>, Arc<dyn AudioSink>, AudioOutput), String> {
    // The device sink is not Send, so a dedicated thread owns it for life.
    // The Player is all interior mutability, so pause/play/clear are safe
    // to call from command handlers while this thread appends.
    let (ready_tx, ready_rx) = channel();
    let (chunk_tx, chunk_rx) = sync_channel::<Frame>(AUDIO_QUEUE_FRAMES);
    std::thread::spawn(move || {
        let (device, output) = match open_output() {
            Ok(opened) => opened,
            Err(error) => {
                let _ = ready_tx.send(Err(format!("no output device: {error}")));
                return;
            }
        };
        // Said out loud, both ways: the log for whoever debugs a silent Mac,
        // the page for the person - a voice that went to the wrong device
        // used to be undiagnosable from either side (owner's note, 20/09).
        eprintln!(
            "[audio] opened \"{}\"{}",
            output.name,
            if output.default { "" } else { " - NOT the system's default output" }
        );
        shell.emit("audio:device", json!({ "name": output.name, "default": output.default }));
        let player: Arc<dyn AudioSink> =
            Arc::new(rodio::Player::connect_new(device.mixer()));
        let _ = ready_tx.send(Ok((player.clone(), output)));
        drain(chunk_rx, player, epoch, paused, rewind, shell, feedback);
    });
    let (player, output) = ready_rx
        .recv()
        .map_err(|_| "audio thread died".to_string())??;
    Ok((chunk_tx, player, output))
}

/// Which output the voice goes to, as the page and the log see it.
#[derive(Clone, Debug, serde::Serialize)]
pub struct AudioOutput {
    pub name: String,
    /// It is the device the system calls the default output. False means
    /// the default could not be opened and another one answered instead.
    pub default: bool,
}

/// The system's default output device, by name; only when that one will
/// not open, the first other output that does - never silently. rodio's
/// own `open_default_sink` does the same search but cannot say which
/// device won, and on this Mac the first other device is a monitor.
fn open_output() -> Result<(rodio::MixerDeviceSink, AudioOutput), String> {
    use rodio::cpal::traits::{DeviceTrait, HostTrait};
    fn on_stream_error(error: rodio::cpal::StreamError) {
        eprintln!("[audio] stream error: {error}");
    }
    let open = |device: rodio::cpal::Device| -> Result<rodio::MixerDeviceSink, String> {
        rodio::DeviceSinkBuilder::from_device(device)
            .and_then(|builder| builder.with_error_callback(on_stream_error).open_stream())
            .map_err(|error| error.to_string())
    };
    let host = rodio::cpal::default_host();
    let mut first_error = None;
    let name_of = |device: &rodio::cpal::Device| {
        device.description().map(|d| d.name().to_string()).unwrap_or_else(|_| "?".to_string())
    };
    if let Some(device) = host.default_output_device() {
        let name = name_of(&device);
        match open(device) {
            Ok(sink) => return Ok((sink, AudioOutput { name, default: true })),
            Err(error) => {
                eprintln!("[audio] the default output \"{name}\" would not open: {error}");
                first_error = Some(error);
            }
        }
    }
    let devices = host.output_devices().map_err(|error| error.to_string())?;
    for device in devices {
        let name = name_of(&device);
        if let Ok(sink) = open(device) {
            return Ok((sink, AudioOutput { name, default: false }));
        }
    }
    Err(first_error.unwrap_or_else(|| "no output device".to_string()))
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

/// Writing to the engine's stdin fails for exactly one reason: the engine is
/// not there to read it. The reader is told that, in the sentence the shell
/// can translate, rather than `engine write: Broken pipe (os error 32)` -
/// which is what a Vietnamese reader got until 10/09, and got again on every
/// action afterwards. The operating system's words still reach stderr, where
/// they are useful; they were never useful on screen.
fn write_failed(error: &std::io::Error) -> String {
    eprintln!("[engine] write failed: {error}");
    ENGINE_GONE.to_string()
}

impl Pump {
    fn run(&self, lines: impl Iterator<Item = String>) {
        self.pump(lines);
        // stdout closed: the engine is gone - killed, crashed, or swapped
        // out by `restart_engine`. A reading in flight has to END, because
        // nothing else will ever end it: no final reply is coming, and the
        // shell's only other signal is a request timing out 30 s later.
        // Measured 10/09 before this existed: the pump returned in silence,
        // the shell kept `reading` set and went on showing a reading that
        // had stopped making sound, with nothing on screen and no way back.
        //
        // Down the audio queue like any other ending, so whatever is already
        // in the device still plays and a stop meanwhile (epoch moved) makes
        // this nobody's business - the same two rules `Frame::Done` follows
        // for an ordinary reply.
        let mut reading = self.current_read.lock().unwrap();
        if reading.take().is_some() {
            drop(reading);
            let _ = self.audio.send(Frame::Done {
                epoch: self.epoch.load(Ordering::SeqCst),
                message: json!({"ok": false, "error": ENGINE_GONE}),
            });
        }
    }

    fn pump(&self, lines: impl Iterator<Item = String>) {
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
                    let voiced = message
                        .get("from_voice")
                        .and_then(Value::as_bool)
                        .unwrap_or(true);
                    let _ = self.audio.send(Frame::Chunk {
                        epoch: stamped,
                        read_id,
                        samples,
                        voiced,
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
        let rewind = Arc::new(AtomicBool::new(false));
        let shell: Arc<dyn Shell> = Arc::new(TauriShell {
            app: app.clone(),
            tray: tray.clone(),
        });
        let feedback: Arc<dyn Feedback> =
            Arc::new(StdinFeedback { stdin: stdin.clone() });
        let (audio, player, output) =
            spawn_audio(epoch.clone(), paused.clone(), rewind.clone(), shell.clone(), feedback)?;

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
            paused_since: Mutex::new(None),
            rewind,
            start: Mutex::new(()),
            notified: Arc::new(Mutex::new(HashSet::new())),
            tray,
            voice_started: Arc::new(std::sync::atomic::AtomicBool::new(true)),
            output,
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
        writeln!(stdin, "{line}").map_err(|error| write_failed(&error))
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
        self.forget_pause();
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
        self.forget_pause();
        self.show_tray(false);
        let reply = self.request("stop", json!({}));
        eprintln!("[stop] audio+engine in {:?}", began.elapsed());
        reply.map(|_| ())
    }

    pub fn pause(&self) {
        self.paused.store(true, Ordering::SeqCst);
        *self.paused_since.lock().unwrap() = Some(std::time::SystemTime::now());
        self.player.pause();
    }

    /// Carry on - from where the device stopped after a breath, from the
    /// start of the sentence after a break (HIG 3.23). In the second case
    /// the device is NOT started here: the audio thread starts it once the
    /// sentence is back in it, or 20 ms of the old place would play first.
    pub fn resume(&self) {
        let since = self.paused_since.lock().unwrap().take();
        if should_rewind(since, std::time::SystemTime::now()) {
            self.rewind.store(true, Ordering::SeqCst);
            self.paused.store(false, Ordering::SeqCst);
            return;
        }
        self.paused.store(false, Ordering::SeqCst);
        self.player.play();
    }

    /// A stop or a new reading: whatever pause there was is over, and an
    /// order to replay left over from it must not reach the next reading.
    fn forget_pause(&self) {
        *self.paused_since.lock().unwrap() = None;
        self.rewind.store(false, Ordering::SeqCst);
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
        /// Times the drain loop told the device to play: the prebuffer's
        /// receipt is that this stays at zero until enough is gathered.
        plays: AtomicUsize,
        /// Times the device was emptied: a rewind's receipt is exactly one.
        clears: AtomicUsize,
    }

    impl FakeSink {
        /// The ear catches up: everything queued has been played.
        fn play_out(&self) {
            self.queued.store(0, Ordering::SeqCst);
        }
        /// The device finishes `frames` of what it holds, no more.
        fn played(&self, frames: usize) {
            let _ = self.queued.fetch_update(Ordering::SeqCst, Ordering::SeqCst, |held| {
                Some(held.saturating_sub(frames))
            });
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
        fn play(&self) {
            self.plays.fetch_add(1, Ordering::SeqCst);
        }
        fn pause(&self) {}
        fn clear(&self) {
            self.clears.fetch_add(1, Ordering::SeqCst);
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
        fn count(&self, event: &str) -> usize {
            self.events.lock().unwrap().iter().filter(|e| *e == event).count()
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
        paused: Arc<AtomicBool>,
        rewind: Arc<AtomicBool>,
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

        /// What `EngineClient::resume()` does after a break: the order to
        /// replay goes in, then the pause is lifted - and the device is
        /// left for the audio thread to start.
        fn resume_after_break(&self) {
            self.rewind.store(true, Ordering::SeqCst);
            self.paused.store(false, Ordering::SeqCst);
        }

        /// The sample counts the device was handed, in order.
        fn handed(&self) -> Vec<usize> {
            self.sink.appended.lock().unwrap().clone()
        }
    }

    /// The two loops wired exactly as `spawn()` wires them, minus the
    /// subprocess and the device. `queued` is the frames the "device" holds
    /// at the start; `paused` is whether the person has pressed pause.
    fn harness(queued: usize, paused: bool) -> Harness {
        let sink = Arc::new(FakeSink {
            queued: AtomicUsize::new(queued),
            appended: Mutex::new(Vec::new()),
            plays: AtomicUsize::new(0),
            clears: AtomicUsize::new(0),
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
        let rewind = Arc::new(AtomicBool::new(false));
        let (audio, frames) = sync_channel::<Frame>(AUDIO_QUEUE_FRAMES);
        {
            let (sink, epoch, paused, rewind, shell) =
                (sink.clone(), epoch.clone(), paused.clone(), rewind.clone(), shell.clone());
            std::thread::spawn(move || drain(frames, sink, epoch, paused, rewind, shell, feedback));
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
        Harness {
            sink, shell: recorder, feedback: feedback_recorder, epoch, paused, rewind,
            current_read, pending, lines,
        }
    }

    /// Wait until the shell has seen `event` `times` times, or give up.
    fn settle(shell: &RecordingShell, event: &str, times: usize) -> bool {
        let deadline = Instant::now() + Duration::from_secs(2);
        while shell.count(event) < times && Instant::now() < deadline {
            std::thread::sleep(Duration::from_millis(5));
        }
        shell.count(event) >= times
    }

    /// The highlight moved a paragraph early, every paragraph (owner,
    /// 15/09). A position used to be announced the moment it was dequeued,
    /// with up to three frames of the previous sentence still unplayed in
    /// the device - and a cached sentence is one whole frame.
    #[test]
    fn a_position_waits_for_the_audio_before_it_to_finish_playing() {
        let h = harness(0, false);
        h.lines.send(position_line("s1")).unwrap();
        for _ in 0..3 {
            h.lines.send(chunk_line()).unwrap();
        }
        h.lines.send(position_line("s2")).unwrap();

        // s1 had nothing before it and is announced at once; s2 sits behind
        // three unplayed frames and must not be.
        assert!(settle(&h.shell, "reading:position", 1));
        std::thread::sleep(Duration::from_millis(80));
        assert_eq!(h.shell.count("reading:position"), 1, "s2 báo trước khi tai tới");
        assert_eq!(h.sink.queued(), 3);

        // Two of the three play out: still not there.
        h.sink.played(2);
        std::thread::sleep(Duration::from_millis(80));
        assert_eq!(h.shell.count("reading:position"), 1, "s2 báo khi còn một khung chưa phát");

        // The last one plays: the ear is at s2 - and nothing new had to
        // arrive from the engine for the loop to notice.
        h.sink.played(1);
        assert!(settle(&h.shell, "reading:position", 2), "s2 không bao giờ được báo");
        let reached = h.feedback.reached.lock().unwrap();
        assert_eq!(reached.iter().map(|(_, s)| s.as_str()).collect::<Vec<_>>(), ["s1", "s2"]);
    }

    /// A stop between the position and its audio: the highlight must not
    /// move to a sentence nobody will hear.
    #[test]
    fn a_stop_drops_the_positions_still_waiting() {
        let h = harness(0, false);
        h.lines.send(position_line("s1")).unwrap();
        h.lines.send(chunk_line()).unwrap();
        h.lines.send(position_line("s2")).unwrap();
        assert!(settle(&h.shell, "reading:position", 1));

        h.stop(); // clears the device too: everything counts as played
        std::thread::sleep(Duration::from_millis(80));

        assert_eq!(h.shell.count("reading:position"), 1, "vị trí của bài đọc đã dừng vẫn được báo");
    }

    fn chunk_line() -> String {
        json!({"event": "chunk", "id": 1, "pcm": BASE64.encode([0u8; 4])}).to_string()
    }

    /// A chunk of `seconds` of silence at the pipe's rate.
    fn chunk_line_of(seconds: f32) -> String {
        let bytes = vec![0u8; (seconds * SAMPLE_RATE as f32) as usize * 4];
        json!({"event": "chunk", "id": 1, "pcm": BASE64.encode(bytes)}).to_string()
    }

    /// A frame of `samples` samples the engine marked as voice - or, with
    /// `voiced` false, as a rest between sentences.
    fn frame_line(samples: usize, voiced: bool) -> String {
        json!({
            "event": "chunk", "id": 1, "from_voice": voiced,
            "pcm": BASE64.encode(vec![0u8; samples * 4]),
        })
        .to_string()
    }

    /// Three one-frame sentences with a rest between each: `a r b r c`, as
    /// the cache hands them over (one frame per sentence). Lengths differ
    /// so the receipts can tell the frames apart.
    const A: usize = 100;
    const B: usize = 200;
    const C: usize = 300;
    const REST: usize = 10;

    fn three_sentences(h: &Harness) {
        for line in [
            frame_line(A, true),
            frame_line(REST, false),
            frame_line(B, true),
            frame_line(REST, false),
            frame_line(C, true),
        ] {
            h.lines.send(line).unwrap();
        }
        assert!(wait_until(|| h.sink.queued() == 5, Duration::from_secs(2)), "five frames in the device");
    }

    /// The pause landed mid-sentence: the resume replays the sentence
    /// BEFORE it as well, so the ear gets a whole sentence of context
    /// (HIG 3.23). Nothing else moves - `appended` stays, so the device
    /// count and the frame index agree again once the sentence has played.
    #[test]
    fn a_break_mid_sentence_resumes_from_the_sentence_before() {
        let h = harness(0, false);
        three_sentences(&h);
        h.sink.played(2); // the ear is in `b`
        h.paused.store(true, Ordering::SeqCst);
        h.resume_after_break();
        assert!(wait_until(|| h.sink.clears.load(Ordering::SeqCst) == 1, Duration::from_secs(2)));
        assert!(wait_until(|| h.handed().len() == 10, Duration::from_secs(2)), "{:?}", h.handed());
        assert_eq!(h.handed()[5..], [A, REST, B, REST, C], "from the start of `a`");
        assert_eq!(h.sink.queued(), 5);
        assert!(wait_until(|| h.sink.plays.load(Ordering::SeqCst) >= 1, Duration::from_secs(1)), "the device restarts");
    }

    /// The pause landed in the rest after `b` - the usual place, the end of
    /// a breath: `b` itself is the context, and it is what plays again.
    #[test]
    fn a_break_in_the_silence_after_a_sentence_replays_that_sentence() {
        let h = harness(0, false);
        three_sentences(&h);
        h.sink.played(3); // the ear is in the rest after `b`
        h.paused.store(true, Ordering::SeqCst);
        h.resume_after_break();
        assert!(wait_until(|| h.handed().len() == 8, Duration::from_secs(2)), "{:?}", h.handed());
        assert_eq!(h.handed()[5..], [B, REST, C]);
        assert_eq!(h.sink.clears.load(Ordering::SeqCst), 1);
    }

    /// Positions still waiting fire where they always did: a rewind moves
    /// the ear back, not the marks, so the highlight lands on the second
    /// pass exactly where it would have on the first (the 15/09 bug must
    /// not come back through this door).
    #[test]
    fn positions_waiting_across_a_rewind_fire_on_the_second_pass() {
        let h = harness(0, false);
        h.lines.send(position_line("s1")).unwrap();
        h.lines.send(frame_line(A, true)).unwrap();
        h.lines.send(frame_line(REST, false)).unwrap();
        h.lines.send(frame_line(B, true)).unwrap();
        h.lines.send(position_line("s2")).unwrap(); // due once 3 frames are done
        h.lines.send(frame_line(REST, false)).unwrap();
        h.lines.send(frame_line(C, true)).unwrap();
        assert!(settle(&h.shell, "reading:position", 1));
        assert!(wait_until(|| h.sink.queued() == 5, Duration::from_secs(2)));

        h.sink.played(2); // in `b`, one frame short of s2
        h.paused.store(true, Ordering::SeqCst);
        h.resume_after_break();
        assert!(wait_until(|| h.sink.clears.load(Ordering::SeqCst) == 1, Duration::from_secs(2)));
        std::thread::sleep(Duration::from_millis(60));
        assert_eq!(h.shell.count("reading:position"), 1, "s2 báo sớm vì lùi");

        // The second pass: a, rest, b play out again - now s2 is due.
        h.sink.played(3);
        assert!(settle(&h.shell, "reading:position", 2), "s2 không báo sau khi tai tới lần hai");
        assert_eq!(h.sink.queued(), 2);
    }

    /// The person pressed pause again in the moment between resuming and
    /// the audio thread getting there: the sentence is put back, and the
    /// device stays quiet for them.
    #[test]
    fn a_pause_pressed_again_keeps_the_device_quiet_after_the_rewind() {
        let h = harness(0, false);
        three_sentences(&h);
        h.sink.played(2);
        let plays_before = h.sink.plays.load(Ordering::SeqCst);
        h.rewind.store(true, Ordering::SeqCst);
        h.paused.store(true, Ordering::SeqCst);
        assert!(wait_until(|| h.sink.clears.load(Ordering::SeqCst) == 1, Duration::from_secs(2)));
        std::thread::sleep(Duration::from_millis(60));
        assert_eq!(h.sink.plays.load(Ordering::SeqCst), plays_before, "un-paused the person");
    }

    /// A stop moved the epoch: the shadow belongs to a reading that is
    /// over, and an order left over from it replays nothing.
    #[test]
    fn a_rewind_after_a_stop_replays_nothing() {
        let h = harness(0, false);
        three_sentences(&h);
        h.stop();
        let handed = h.handed().len();
        h.resume_after_break();
        std::thread::sleep(Duration::from_millis(80));
        assert_eq!(h.handed().len(), handed);
        assert_eq!(h.sink.clears.load(Ordering::SeqCst), 1, "only the stop's own clear");
    }

    /// Only a break earns a rewind; a breath resumes in place. And the
    /// clock is the wall clock, so a Mac asleep through the pause counts.
    #[test]
    fn only_a_break_of_thirty_seconds_earns_a_rewind() {
        use std::time::SystemTime;
        let now = SystemTime::now();
        assert!(!should_rewind(None, now));
        assert!(!should_rewind(Some(now - Duration::from_secs(29)), now));
        assert!(should_rewind(Some(now - REWIND_AFTER), now));
        assert!(should_rewind(Some(now - Duration::from_secs(3600)), now));
    }

    /// A sentence with no rest in it for minutes on end - not a book, but
    /// an engine could send one - must not grow the shadow with it: what
    /// is behind the ear goes once a minute is held.
    #[test]
    fn the_shadow_never_holds_more_than_a_minute() {
        let mut shadow = Shadow::new();
        let second = vec![0.0f32; SAMPLE_RATE as usize];
        for index in 0..90u64 {
            shadow.push(1, index, true, &second);
            shadow.trim(index); // the ear keeps up with the device
        }
        assert!(shadow.samples <= SHADOW_MAX_SAMPLES);
        assert!(shadow.base > 0);
        // The one start fell off with the frames before the bound: no
        // sentence to go back to, so a resume after a break plays on.
        assert_eq!(shadow.target(89), None);
    }

    /// The shadow forgets what the ear has left behind: two begun
    /// sentences and the device's own frames, never the whole reading.
    #[test]
    fn the_shadow_keeps_two_sentences_and_no_more() {
        let mut shadow = Shadow::new();
        let mut index = 0;
        for _ in 0..6 {
            shadow.push(1, index, true, &[0.0; 4]);
            index += 1;
            shadow.push(1, index, false, &[0.0; 1]);
            index += 1;
        }
        // The ear is in the sixth sentence (index 10): keep the fifth and sixth.
        shadow.trim(10);
        assert_eq!(shadow.starts, [8, 10]);
        assert_eq!(shadow.base, 8);
        assert_eq!(shadow.frames.len(), 4);
        assert_eq!(shadow.target(10), Some(8));
        assert_eq!(shadow.target(11), Some(10), "in the rest after the sixth");
    }

    /// The voice samples stuttered (owner, 19/09): the model's first chunks
    /// arrive about as fast as they play, and a device that starts on the
    /// first one runs dry between them. The first frames of a reading are
    /// held until `PREBUFFER_SECS` of it is in the device.
    #[test]
    fn a_reading_holds_its_first_frames_until_the_prebuffer_is_full() {
        let h = harness(0, false);
        h.lines.send(chunk_line_of(0.2)).unwrap();
        h.lines.send(chunk_line_of(0.2)).unwrap();
        assert!(wait_until(|| h.sink.appended.lock().unwrap().len() == 2, Duration::from_secs(2)));
        std::thread::sleep(Duration::from_millis(60));
        assert_eq!(h.sink.plays.load(Ordering::SeqCst), 0, "the device was started on 0.4 s of audio");
        h.lines.send(chunk_line_of(0.3)).unwrap();
        assert!(
            wait_until(|| h.sink.plays.load(Ordering::SeqCst) == 1, Duration::from_secs(2)),
            "0.7 s gathered and the device still held"
        );
        // Once released, a reading is not held again: the next frame plays on.
        h.lines.send(chunk_line_of(0.1)).unwrap();
        assert!(wait_until(|| h.sink.plays.load(Ordering::SeqCst) == 2, Duration::from_secs(2)));
    }

    /// A voice sample is shorter than the prebuffer: it plays the moment
    /// its last frame is in, not after a wait for audio that never comes.
    #[test]
    fn a_reading_shorter_than_the_prebuffer_plays_when_it_is_whole() {
        let h = harness(0, false);
        h.lines.send(chunk_line_of(0.1)).unwrap();
        assert!(wait_until(|| h.sink.appended.lock().unwrap().len() == 1, Duration::from_secs(2)));
        std::thread::sleep(Duration::from_millis(60));
        assert_eq!(h.sink.plays.load(Ordering::SeqCst), 0);
        h.lines.send(final_reply_line()).unwrap();
        assert!(
            wait_until(|| h.sink.plays.load(Ordering::SeqCst) == 1, Duration::from_secs(2)),
            "the whole reading was in the device and it stayed held"
        );
    }

    /// A slow engine is not waited for past `PREBUFFER_MAX_WAIT`: what has
    /// been gathered plays rather than the speakers staying silent.
    #[test]
    fn the_hold_never_outwaits_a_slow_engine() {
        let h = harness(0, false);
        h.lines.send(chunk_line_of(0.1)).unwrap();
        assert!(wait_until(|| h.sink.appended.lock().unwrap().len() == 1, Duration::from_secs(2)));
        assert_eq!(h.sink.plays.load(Ordering::SeqCst), 0);
        assert!(
            wait_until(|| h.sink.plays.load(Ordering::SeqCst) == 1, PREBUFFER_MAX_WAIT + Duration::from_millis(500)),
            "a reading was held for ever behind a slow engine"
        );
    }

    /// The person's pause outranks the hold's release: gathering enough
    /// audio while paused must not start the device.
    #[test]
    fn a_full_prebuffer_does_not_unpause_the_person() {
        let h = harness(0, true);
        h.lines.send(chunk_line_of(0.7)).unwrap();
        assert!(wait_until(|| h.sink.appended.lock().unwrap().len() == 1, Duration::from_secs(2)));
        std::thread::sleep(Duration::from_millis(60));
        assert_eq!(h.sink.plays.load(Ordering::SeqCst), 0, "appending un-paused the person");
    }

    fn position_line(segment: &str) -> String {
        json!({"event": "position", "id": 1, "segment_id": segment}).to_string()
    }

    fn final_reply_line() -> String {
        json!({"id": 1, "ok": true, "result": {"frames": 3}}).to_string()
    }

    /// Ask something while a reading is in flight, the way `request()` does:
    /// register the waiter, then let the engine's reply line arrive.
    /// The engine process disappearing under a reading, which is what a
    /// crash, an OOM kill or `restart_engine` all look like from here:
    /// stdout closes and no final reply is ever coming.
    ///
    /// Measured 10/09 BEFORE the fix, with the same harness: events reaching
    /// the shell `[]`, the pending request never answered, and
    /// `current_read` still set - so the shell went on showing a reading
    /// that had stopped making sound, indefinitely, with nothing on screen.
    /// A reading that ends has to SAY it ended; that is the whole finding.
    #[test]
    fn a_dead_engine_ends_the_reading_it_was_in() {
        let h = harness(0, false);
        h.lines.send(chunk_line()).unwrap();
        // The engine dies: its stdout closes.
        drop(h.lines);

        let deadline = Instant::now() + Duration::from_secs(2);
        while !h.shell.saw("reading:done") && Instant::now() < deadline {
            // The ear catches up. `Frame::Done` waits for the device by
            // design, and this fake only drains when a test says so - so
            // without this the wait below would time out on the harness,
            // not on the behaviour being measured.
            h.sink.play_out();
            std::thread::sleep(Duration::from_millis(10));
        }

        assert!(h.shell.saw("reading:done"), "vỏ không hề biết engine đã chết");
        assert!(
            h.current_read.lock().unwrap().is_none(),
            "vỏ vẫn tin là đang đọc sau khi engine chết",
        );
    }

    /// The other half of the same finding: the engine can die while nobody
    /// is reading - the shelf is open, the sidecar is killed under memory
    /// pressure - and then the FIRST thing the reader does fails at the
    /// write. Measured 10/09: `engineMessage()` returned
    /// `engine write: Broken pipe (os error 32)` unchanged in Vietnamese,
    /// because `ENGINE_REFUSAL` only ever strips `engine refused …:`. The
    /// transport's own words are English by a documented choice; this is not
    /// the transport reporting on itself, it is the one condition that has a
    /// sentence written for it.
    #[test]
    fn a_write_to_a_dead_engine_speaks_to_the_reader_not_about_the_pipe() {
        let broken = std::io::Error::new(std::io::ErrorKind::BrokenPipe, "broken pipe");

        assert_eq!(write_failed(&broken), ENGINE_GONE);
    }

    /// The regression the fix above could easily have introduced.
    ///
    /// `restart_engine` KILLS the engine on purpose - a model switch is the
    /// ordinary reason - and it calls `stop()` first, which clears
    /// `current_read`. So the EOF that follows must stay silent: telling a
    /// reader "the engine stopped unexpectedly" every time they change voice
    /// quality would be worse than the silence this fix replaced.
    #[test]
    fn an_engine_killed_on_purpose_does_not_cry_wolf() {
        let h = harness(0, false);
        h.stop();
        drop(h.lines);

        let deadline = Instant::now() + Duration::from_millis(400);
        while Instant::now() < deadline {
            h.sink.play_out();
            std::thread::sleep(Duration::from_millis(10));
        }

        assert!(
            !h.shell.saw("reading:done"),
            "một lần tắt engine có chủ ý bị báo thành engine chết",
        );
    }

    /// And it says so with the sentence the shell can translate: the literal
    /// is pinned here and its English half in `engineMessage.test.ts`, so a
    /// reworded constant cannot quietly leave an English reader with
    /// Vietnamese on screen.
    #[test]
    fn a_dead_engine_says_so_in_a_sentence_the_shell_can_translate() {
        assert_eq!(
            ENGINE_GONE,
            "Bộ máy đọc đã dừng đột ngột. Hãy khởi động lại ứng dụng.",
        );
    }

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

    /// What the reader is TOLD they have spent has to keep arriving.
    ///
    /// The engine counts money up and announces it on `spend`; the pump has
    /// no branch for that name, so it goes out under `engine:spend` like any
    /// event this host does not know about. Nothing in Rust says "spend"
    /// anywhere - which is exactly why it is worth a test: the catch-all is
    /// load-bearing, and a later branch added "for tidiness" would take the
    /// running total off the reader's screen with nothing going red.
    #[test]
    fn a_spend_the_engine_reports_reaches_the_webview() {
        let h = harness(0, false);
        h.lines
            .send(json!({"id": 1, "event": "spend", "chars": 44, "usd": 0.06}).to_string())
            .unwrap();
        assert!(
            wait_until(|| h.shell.saw("engine:spend"), Duration::from_secs(2)),
            "vỏ không hề biết tiền đã tiêu",
        );
    }

    /// And it must NOT be filtered the way audio is.
    ///
    /// `chunk` and `position` die here when they belong to a superseded
    /// reading - a stopped reading must not keep speaking or moving the
    /// highlight. Money is the opposite case: characters that went out were
    /// paid for whether or not the reader stopped listening, so a spend from
    /// an old reading is still theirs to see.
    #[test]
    fn a_spend_from_a_reading_already_stopped_is_still_reported() {
        let h = harness(0, false);
        h.stop();
        h.lines
            .send(json!({"id": 1, "event": "spend", "chars": 44, "usd": 0.06}).to_string())
            .unwrap();
        assert!(
            wait_until(|| h.shell.saw("engine:spend"), Duration::from_secs(2)),
            "tiền đã tiêu bị bỏ đi cùng lượt đọc đã dừng",
        );
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
