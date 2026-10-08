//! The bundle id changed on 08/10/2026 (the old one named a company the
//! app has nothing to do with). The library lives under "VieNeu Reader"
//! and never depended on the id, but two things macOS files by bundle id
//! did: the WebView's storage (theme, reading size, reading mode, the side
//! column, the cost scope) and the window frame. An installed copy gets
//! this build through the updater, so the new binary carries both over on
//! its first launch - by copying, never moving, so the old app still opens.
//!
//! Runs at the top of `run()`, before the Tauri builder: once a WebView has
//! opened its storage, a copy dropped underneath it is ignored.
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

/// The id every install up to 0.1.19 ran under. Kept only so those
/// installs migrate; safe to drop once no one runs a build that old.
const LEGACY_ID: &str = "vn.dolenglish.vieneureader";
const CURRENT_ID: &str = "com.wblekhoa.readease";

/// The window-state plugin's file, in the id's Application Support folder.
const WINDOW_STATE: &str = ".window-state.json";

/// Carries the old id's WebView storage and window frame across, once.
/// Every outcome goes to stderr, which `log::capture_stderr` has already
/// pointed at the log file.
pub fn carry_over_legacy_state() {
    let Some(home) = std::env::var_os("HOME") else { return };
    for line in carry_over(&PathBuf::from(home)) {
        eprintln!("{line}");
    }
}

/// The copy itself, against any home folder so a test can use a scratch
/// one. A destination that already exists is the "done" mark: nothing is
/// ever overwritten, and the second launch does nothing.
fn carry_over(home: &Path) -> Vec<String> {
    let library = home.join("Library");
    let mut notes = Vec::new();

    let old_web = library.join("WebKit").join(LEGACY_ID);
    let new_web = library.join("WebKit").join(CURRENT_ID);
    if old_web.is_dir() && !new_web.exists() {
        match copy_tree(&old_web, &new_web) {
            Ok(files) => notes.push(format!("identity: carried {files} WebView files over from {LEGACY_ID}")),
            Err(error) => {
                // A half copy would mark the job done; take it back so the
                // next launch tries again from scratch.
                let _ = fs::remove_dir_all(&new_web);
                notes.push(format!("identity: WebView storage not carried over: {error}"));
            }
        }
    }

    let support = library.join("Application Support");
    let old_frame = support.join(LEGACY_ID).join(WINDOW_STATE);
    let new_frame = support.join(CURRENT_ID).join(WINDOW_STATE);
    if old_frame.is_file() && !new_frame.exists() {
        let copied = fs::create_dir_all(support.join(CURRENT_ID))
            .and_then(|()| fs::copy(&old_frame, &new_frame));
        match copied {
            Ok(_) => notes.push("identity: carried the window frame over".to_string()),
            Err(error) => notes.push(format!("identity: window frame not carried over: {error}")),
        }
    }
    notes
}

/// Copies a folder tree and returns how many files it copied. Symlinks are
/// left behind: WebKit's storage holds none, and following one could copy
/// something outside the folder.
fn copy_tree(from: &Path, to: &Path) -> io::Result<usize> {
    fs::create_dir_all(to)?;
    let mut files = 0;
    for entry in fs::read_dir(from)? {
        let entry = entry?;
        let kind = entry.file_type()?;
        let target = to.join(entry.file_name());
        if kind.is_dir() {
            files += copy_tree(&entry.path(), &target)?;
        } else if kind.is_file() {
            fs::copy(entry.path(), &target)?;
            files += 1;
        }
    }
    Ok(files)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scratch_home(name: &str) -> PathBuf {
        let home = std::env::temp_dir().join(format!("readease-identity-{name}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&home);
        fs::create_dir_all(&home).unwrap();
        home
    }

    fn write(path: &Path, text: &str) {
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, text).unwrap();
    }

    #[test]
    fn the_old_ids_storage_and_frame_come_across_once() {
        let home = scratch_home("once");
        let library = home.join("Library");
        let local = "WebsiteData/Default/salt/salt/LocalStorage/localstorage.sqlite3";
        write(&library.join("WebKit").join(LEGACY_ID).join(local), "theme=dark");
        write(&library.join("Application Support").join(LEGACY_ID).join(WINDOW_STATE), "{\"main\":{}}");

        let notes = carry_over(&home);
        assert_eq!(notes.len(), 2, "{notes:?}");
        assert_eq!(fs::read_to_string(library.join("WebKit").join(CURRENT_ID).join(local)).unwrap(), "theme=dark");
        assert_eq!(
            fs::read_to_string(library.join("Application Support").join(CURRENT_ID).join(WINDOW_STATE)).unwrap(),
            "{\"main\":{}}",
        );
        // Copied, not moved: the old app still finds its own.
        assert!(library.join("WebKit").join(LEGACY_ID).join(local).is_file());

        // The second launch finds the job done and touches nothing.
        write(&library.join("WebKit").join(CURRENT_ID).join(local), "theme=light");
        assert!(carry_over(&home).is_empty());
        assert_eq!(fs::read_to_string(library.join("WebKit").join(CURRENT_ID).join(local)).unwrap(), "theme=light");
        let _ = fs::remove_dir_all(&home);
    }

    #[test]
    fn a_fresh_install_has_nothing_to_carry() {
        let home = scratch_home("fresh");
        assert!(carry_over(&home).is_empty());
        assert!(!home.join("Library/WebKit").join(CURRENT_ID).exists());
        let _ = fs::remove_dir_all(&home);
    }
}
