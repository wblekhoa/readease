//! Now Playing and the media keys (HIG 3.19): while a reading runs the app
//! is the system's now-playing app, so F8, an AirPod's stem and Control
//! Center's ⏯ reach the reading, and Control Center names what is read.
//!
//! Everything here talks to MediaPlayer on the main thread: the remote
//! command handlers are registered once at setup, and each `now_playing`
//! update is hopped there by the command. The handler targets are kept for
//! the life of the app - MediaPlayer holds them weakly.
use std::ptr::NonNull;
use std::sync::Mutex;

use base64::engine::general_purpose::STANDARD as BASE64;
use base64::Engine as _;
use block2::RcBlock;
use objc2::rc::Retained;
use objc2::runtime::AnyObject;
use objc2::AllocAnyThread as _;
use objc2_app_kit::NSImage;
use objc2_core_foundation::CGSize;
use objc2_foundation::{NSData, NSDictionary, NSNumber, NSString};
use objc2_media_player::{
    MPMediaItemArtwork, MPMediaItemPropertyArtist, MPMediaItemPropertyArtwork,
    MPMediaItemPropertyTitle, MPNowPlayingInfoCenter, MPNowPlayingInfoMediaType,
    MPNowPlayingInfoPropertyMediaType, MPNowPlayingInfoPropertyPlaybackRate,
    MPNowPlayingPlaybackState, MPRemoteCommand, MPRemoteCommandCenter, MPRemoteCommandEvent,
    MPRemoteCommandHandlerStatus,
};
use tauri::{Emitter, Manager};

/// What the page tells the system about the reading.
#[derive(serde::Deserialize)]
pub struct NowPlayingInfo {
    pub title: String,
    #[serde(default)]
    pub subtitle: String,
    /// "playing" | "paused" | anything else = stopped (withdrawn).
    pub state: String,
    /// The cover, when the reading has one (HIG 3.19).
    #[serde(default)]
    pub artwork: Option<Artwork>,
}

/// The cover as the page sends it: the bytes ride along only the first
/// time a `key` (the document's id) is seen - `now_playing` fires on every
/// state change, and a cover is 100-200 KB.
#[derive(serde::Deserialize)]
pub struct Artwork {
    pub key: String,
    /// Base64 of the image file (NSImage reads the format off the bytes),
    /// present only when the page has not sent this key before.
    #[serde(default)]
    pub data: Option<String>,
}

/// The one cover the host holds, by key. Bytes rather than the built
/// `MPMediaItemArtwork`: bytes are `Send`, and building the artwork on the
/// main thread costs a millisecond per state change.
#[derive(Default)]
pub struct ArtworkCache(Mutex<Option<(String, Vec<u8>)>>);

impl ArtworkCache {
    /// Remember what the page just sent, then answer with the bytes for
    /// `key` if they are known.
    fn bytes_for(&self, artwork: &Artwork) -> Option<Vec<u8>> {
        let mut held = self.0.lock().unwrap();
        if let Some(encoded) = &artwork.data {
            if let Ok(bytes) = BASE64.decode(encoded) {
                *held = Some((artwork.key.clone(), bytes));
            }
        }
        held.as_ref()
            .filter(|(key, _)| *key == artwork.key)
            .map(|(_, bytes)| bytes.clone())
    }
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
    let cover = info
        .artwork
        .as_ref()
        .and_then(|artwork| app.state::<ArtworkCache>().bytes_for(artwork));
    app.run_on_main_thread(move || unsafe { apply(&info, cover) })
        .map_err(|error| error.to_string())
}

/// The cover as MediaPlayer wants it: an image behind a request block.
/// The block owns the image, and MediaPlayer owns the block, so the
/// pointer it hands back stays good for as long as the system shows it.
unsafe fn artwork_of(bytes: &[u8]) -> Option<Retained<MPMediaItemArtwork>> {
    let data = NSData::with_bytes(bytes);
    let image = NSImage::initWithData(NSImage::alloc(), &data)?;
    let size: CGSize = image.size();
    if size.width <= 0.0 || size.height <= 0.0 {
        return None;
    }
    let handler = RcBlock::new(move |_wanted: CGSize| NonNull::from(&*image));
    Some(MPMediaItemArtwork::initWithBoundsSize_requestHandler(
        MPMediaItemArtwork::alloc(),
        size,
        &handler,
    ))
}

unsafe fn apply(info: &NowPlayingInfo, cover: Option<Vec<u8>>) {
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
    let mut keys: Vec<&NSString> = vec![
        MPMediaItemPropertyTitle,
        MPMediaItemPropertyArtist,
        MPNowPlayingInfoPropertyMediaType,
        MPNowPlayingInfoPropertyPlaybackRate,
    ];
    let mut values: Vec<&AnyObject> = vec![&title, &artist, &media_type, &rate];
    // A cover that cannot be read is simply left out: the system then
    // shows the app's icon, as it did before covers were sent at all.
    let artwork = cover.as_deref().and_then(|bytes| artwork_of(bytes));
    if let Some(artwork) = &artwork {
        keys.push(MPMediaItemPropertyArtwork);
        values.push(artwork);
    }
    let dict: Retained<NSDictionary<NSString, AnyObject>> = NSDictionary::from_slices(&keys, &values);
    center.setNowPlayingInfo(Some(&dict));
    center.setPlaybackState(state);
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A 1×1 white PNG, so the receipt needs no file.
    const PNG: &str = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC";

    #[test]
    fn the_cover_travels_once_and_is_answered_from_the_cache_after() {
        let cache = ArtworkCache::default();
        let first = Artwork { key: "book-1".into(), data: Some(PNG.into()) };
        let bytes = cache.bytes_for(&first).expect("decoded and kept");
        assert_eq!(&bytes[..8], b"\x89PNG\r\n\x1a\n");
        // The key alone, later: the same bytes.
        let again = Artwork { key: "book-1".into(), data: None };
        assert_eq!(cache.bytes_for(&again), Some(bytes.clone()));
        // Another key without bytes: nothing - the wrong cover must never show.
        let other = Artwork { key: "book-2".into(), data: None };
        assert_eq!(cache.bytes_for(&other), None);
        // Bad base64 leaves what was held alone.
        let broken = Artwork { key: "book-3".into(), data: Some("*not base64*".into()) };
        assert_eq!(cache.bytes_for(&broken), None);
        assert_eq!(cache.bytes_for(&again), Some(bytes));
    }

    #[test]
    fn readable_bytes_become_an_artwork_and_junk_becomes_none() {
        let bytes = BASE64.decode(PNG).unwrap();
        let artwork = unsafe { artwork_of(&bytes) };
        assert!(artwork.is_some(), "a PNG the system can read");
        assert!(unsafe { artwork_of(b"not an image at all") }.is_none());
    }
}
