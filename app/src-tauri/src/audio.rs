//! The speaker beside the engine: the audio thread and everything it
//! holds. Frames come off a bounded queue, a little is kept ahead of the
//! ear, positions are announced when the ear reaches them, the engine is
//! handed back the room each frame frees, "done" is said only once the
//! device has gone quiet - and a resume after a break replays the sentence
//! (HIG 3.23). The engine process, its protocol and its stdin live in
//! `engine.rs`; this module knows nothing about JSON lines.
//!
//! Flow control: chunks reach the audio thread over a BOUNDED channel. When a
//! whole book streams and the listener pauses, the channel fills, the reader
//! thread blocks, the OS pipe fills, and the Python engine stops synthesising
//! - backpressure for free, no protocol needed. A stop bumps the epoch so
//! chunks already in flight are dropped instead of played late.

use std::collections::VecDeque;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::mpsc::{channel, sync_channel, Receiver, RecvTimeoutError, SyncSender};
use std::sync::Arc;
use std::time::{Duration, Instant};

use serde_json::{json, Value};

pub(crate) const SAMPLE_RATE: u32 = 48_000;
/// ~48 frames of ~0.1-0.5s each keeps a few seconds buffered, no more.
pub(crate) const AUDIO_QUEUE_FRAMES: usize = 48;
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
pub(crate) const PLAYER_LOOKAHEAD: usize = 4;
/// How much audio a reading gathers before its first sound.
///
/// The model's first chunks arrive at about the speed they play (measured
/// 19/09 on the shipped fp32 build: 0.23 s of audio, then 0.24 s until the
/// next; 0.28 s, then 0.32 s) - so a device that starts on the first chunk
/// runs dry twice in the first second. Holding this much first costs the
/// first sound that long and buys an unbroken one. A reading shorter than
/// this plays as soon as its last frame is in; a slow engine is not waited
/// for past `PREBUFFER_MAX_WAIT`, and a full lookahead ends the hold too.
pub(crate) const PREBUFFER_SECS: f32 = 0.6;
pub(crate) const PREBUFFER_MAX_WAIT: Duration = Duration::from_millis(1500);
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
pub(crate) const ENGINE_WINDOW: usize = AUDIO_QUEUE_FRAMES - 1;
/// A pause this long is a break, not a breath: resuming after it goes back
/// to the start of the sentence in the ear (HIG 3.23). Measured on the wall
/// clock so a Mac that slept through the pause counts it too.
pub(crate) const REWIND_AFTER: Duration = Duration::from_secs(30);

/// Whether resuming now should replay the sentence: only after a real break.
pub(crate) fn should_rewind(paused_since: Option<std::time::SystemTime>, now: std::time::SystemTime) -> bool {
    paused_since
        .and_then(|since| now.duration_since(since).ok())
        .is_some_and(|paused| paused >= REWIND_AFTER)
}


/// What crosses into the audio thread, in the order the engine produced it.
/// Positions travel the same queue as the audio they belong to, so they are
/// announced when the ear reaches them, not when the model wrote them. Each
/// frame names the reading it belongs to, so the room it frees goes back to
/// that reading and not to whichever one is running by then.
pub(crate) enum Frame {
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


/// What the audio thread tells the ENGINE, as opposed to the webview: room
/// freed on the queue, and positions the ear has actually reached.
pub(crate) trait Feedback: Send + Sync {
    fn credit(&self, read_id: u64);
    fn reached(&self, read_id: u64, segment_id: &str);
}


/// A position the ear has not reached yet: announced once every frame
/// appended before it has finished playing.
pub(crate) struct DuePosition {
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
pub(crate) const POSITION_POLL: Duration = Duration::from_millis(20);

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
pub(crate) struct Shadow {
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
pub(crate) const SHADOW_MAX_SAMPLES: usize = 60 * SAMPLE_RATE as usize;

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
pub(crate) fn drain(
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
                // A stop that landed while the sentence was being put back
                // has cleared the device once already; what was appended
                // after that is a sentence audible after Stop unless it
                // goes too. The single-frame path accepts this window; ten
                // frames wide, it is not accepted.
                if !current(shadow.epoch) {
                    sink.clear();
                    return;
                }
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

pub(crate) fn spawn_audio(
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
pub(crate) fn open_output() -> Result<(rodio::MixerDeviceSink, AudioOutput), String> {
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

#[cfg(test)]
mod tests {
    use super::*;

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
}
