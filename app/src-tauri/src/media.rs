//! Now Playing and the media keys (HIG 3.19): while a reading runs the app
//! is the system's now-playing app, so F8, an AirPod's stem and Control
//! Center's ⏯ reach the reading, and Control Center names what is read.
//!
//! Everything here talks to MediaPlayer on the main thread: the remote
//! command handlers are registered once at setup, and each `now_playing`
//! update is hopped there by the command. The handler targets are kept for
//! the life of the app - MediaPlayer holds them weakly.
use std::ptr::NonNull;

use block2::RcBlock;
use objc2::rc::Retained;
use objc2::runtime::AnyObject;
use objc2_foundation::{NSDictionary, NSNumber, NSString};
use objc2_media_player::{
    MPMediaItemPropertyArtist, MPMediaItemPropertyTitle, MPNowPlayingInfoCenter,
    MPNowPlayingInfoMediaType, MPNowPlayingInfoPropertyMediaType,
    MPNowPlayingInfoPropertyPlaybackRate, MPNowPlayingPlaybackState, MPRemoteCommand,
    MPRemoteCommandCenter, MPRemoteCommandEvent, MPRemoteCommandHandlerStatus,
};
use tauri::Emitter;

/// What the page tells the system about the reading.
#[derive(serde::Deserialize)]
pub struct NowPlayingInfo {
    pub title: String,
    #[serde(default)]
    pub subtitle: String,
    /// "playing" | "paused" | anything else = stopped (withdrawn).
    pub state: String,
}

/// The registered handlers' targets; dropping them would silently
/// unregister the commands.
pub struct RemoteCommands(#[allow(dead_code)] Vec<Retained<AnyObject>>);

// MediaPlayer's opaque targets are main-thread objects the app never touches
// again; holding them in managed state only keeps them alive.
unsafe impl Send for RemoteCommands {}
unsafe impl Sync for RemoteCommands {}

/// Registers the four commands the reading can answer and disables the
/// track-skipping ones, so Control Center draws no button that does
/// nothing. Main thread only (called from `setup`).
pub fn register(app: &tauri::AppHandle) -> RemoteCommands {
    let mut targets = Vec::new();
    unsafe {
        let center = MPRemoteCommandCenter::sharedCommandCenter();
        let mut wire = |command: Retained<MPRemoteCommand>, name: &'static str| {
            let app = app.clone();
            let handler = RcBlock::new(move |_event: NonNull<MPRemoteCommandEvent>| {
                let _ = app.emit("media:command", name);
                MPRemoteCommandHandlerStatus::Success
            });
            command.setEnabled(true);
            targets.push(command.addTargetWithHandler(&handler));
        };
        wire(center.togglePlayPauseCommand(), "toggle");
        wire(center.playCommand(), "play");
        wire(center.pauseCommand(), "pause");
        wire(center.stopCommand(), "stop");
        center.nextTrackCommand().setEnabled(false);
        center.previousTrackCommand().setEnabled(false);
    }
    RemoteCommands(targets)
}

/// Sets, or withdraws, what the system shows for the reading.
#[tauri::command]
pub fn now_playing(app: tauri::AppHandle, info: NowPlayingInfo) -> Result<(), String> {
    app.run_on_main_thread(move || unsafe { apply(&info) })
        .map_err(|error| error.to_string())
}

unsafe fn apply(info: &NowPlayingInfo) {
    let center = MPNowPlayingInfoCenter::defaultCenter();
    let state = match info.state.as_str() {
        "playing" => MPNowPlayingPlaybackState::Playing,
        "paused" => MPNowPlayingPlaybackState::Paused,
        _ => MPNowPlayingPlaybackState::Stopped,
    };
    if state == MPNowPlayingPlaybackState::Stopped {
        // Withdraw entirely: a "stopped ReadEase" left in Control Center is
        // the thing §3.19 forbids.
        center.setNowPlayingInfo(None);
        center.setPlaybackState(state);
        return;
    }
    let title = NSString::from_str(&info.title);
    let artist = NSString::from_str(if info.subtitle.is_empty() { "ReadEase" } else { &info.subtitle });
    let media_type = NSNumber::new_usize(MPNowPlayingInfoMediaType::Audio.0);
    let rate = NSNumber::new_f64(if state == MPNowPlayingPlaybackState::Playing { 1.0 } else { 0.0 });
    let keys: [&NSString; 4] = [
        MPMediaItemPropertyTitle,
        MPMediaItemPropertyArtist,
        MPNowPlayingInfoPropertyMediaType,
        MPNowPlayingInfoPropertyPlaybackRate,
    ];
    let values: [&AnyObject; 4] = [&title, &artist, &media_type, &rate];
    let dict: Retained<NSDictionary<NSString, AnyObject>> = NSDictionary::from_slices(&keys, &values);
    center.setNowPlayingInfo(Some(&dict));
    center.setPlaybackState(state);
}
