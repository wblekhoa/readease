//! The log file (HIG 3.22): where the host's and the sidecar's `stderr` go
//! when the app was opened from Finder and there is no terminal to read
//! them. Done once, at the top of `run()`, by pointing fd 2 at the file -
//! nothing that prints has to know.
use std::fs::{self, File, OpenOptions};
use std::io::Write;
use std::os::unix::io::AsRawFd;
use std::path::PathBuf;

/// One generation is kept: past this size the current file becomes `.1`.
const ROTATE_AT: u64 = 2 * 1024 * 1024;

pub fn path() -> Option<PathBuf> {
    let home = std::env::var_os("HOME")?;
    Some(PathBuf::from(home).join("Library/Logs/ReadEase/readease.log"))
}

/// Sends `stderr` to the log file when no terminal is reading it. Returns
/// the file's path when it did; `tauri dev` in a terminal keeps its output.
/// `CFBundleVersion` as the build script stamped it ("0.1.10+9c85738"),
/// read from the bundle's own Info.plist; the plain version outside a bundle.
pub fn bundle_version(fallback: &str) -> String {
    let plist = std::env::current_exe()
        .ok()
        .and_then(|exe| exe.parent()?.parent().map(|c| c.join("Info.plist")))
        .and_then(|p| fs::read_to_string(p).ok());
    plist
        .and_then(|text| version_from_plist(&text))
        .unwrap_or_else(|| fallback.to_string())
}

/// The `CFBundleVersion` string out of an XML plist, without a plist
/// parser: the bundler writes the key and its value on adjacent lines.
fn version_from_plist(text: &str) -> Option<String> {
    string_after_key(text, "CFBundleVersion")
}

/// The `<string>` that follows `<key>name</key>` in an XML plist.
fn string_after_key(text: &str, name: &str) -> Option<String> {
    let key = format!("<key>{name}</key>");
    let at = text.find(&key)? + key.len();
    let rest = &text[at..];
    let start = rest.find("<string>")? + "<string>".len();
    let end = rest[start..].find("</string>")? + start;
    Some(rest[start..end].to_string())
}

/// What a bug report needs to be read (RE-HELP-001): this build, the macOS
/// version and the chip family. Nothing from the document, the library or
/// the settings - these three go into a GitHub address the reader can see.
#[derive(serde::Serialize)]
pub struct FeedbackFacts {
    build: String,
    macos: Option<String>,
    arch: &'static str,
}

#[tauri::command]
pub fn feedback_facts(app: tauri::AppHandle) -> FeedbackFacts {
    let macos = fs::read_to_string("/System/Library/CoreServices/SystemVersion.plist")
        .ok()
        .and_then(|text| string_after_key(&text, "ProductVersion"));
    FeedbackFacts {
        build: bundle_version(&app.package_info().version.to_string()),
        macos,
        arch: std::env::consts::ARCH,
    }
}

#[cfg(test)]
mod tests {
    use super::{string_after_key, version_from_plist};

    #[test]
    fn the_stamped_build_id_is_read_out_of_the_plist() {
        let plist = "<key>CFBundleShortVersionString</key>\n<string>0.1.10</string>\n\
                     <key>CFBundleVersion</key>\n\t<string>0.1.10+9c85738</string>\n";
        assert_eq!(version_from_plist(plist).as_deref(), Some("0.1.10+9c85738"));
    }

    #[test]
    fn a_plist_without_the_key_yields_nothing() {
        assert_eq!(version_from_plist("<key>Other</key><string>x</string>"), None);
    }

    // RE-HELP-001
    #[test]
    fn the_macos_version_is_read_out_of_the_system_plist() {
        let plist = "<key>ProductBuildVersion</key>\n<string>27A123</string>\n\
                     <key>ProductVersion</key>\n\t<string>27.0</string>\n";
        assert_eq!(string_after_key(plist, "ProductVersion").as_deref(), Some("27.0"));
    }
}

pub fn capture_stderr(version: &str) -> Option<PathBuf> {
    // A terminal on fd 2 means a developer is watching; leave it alone.
    if unsafe { libc::isatty(2) } == 1 {
        return None;
    }
    let path = path()?;
    fs::create_dir_all(path.parent()?).ok()?;
    if fs::metadata(&path).map(|m| m.len() > ROTATE_AT).unwrap_or(false) {
        let _ = fs::rename(&path, path.with_extension("log.1"));
    }
    let mut file: File = OpenOptions::new().create(true).append(true).open(&path).ok()?;
    let stamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let _ = writeln!(file, "=== ReadEase {version} · unix {stamp} ===");
    // From here on, everything written to fd 2 - by this process and by the
    // children that inherit it - lands in the file.
    if unsafe { libc::dup2(file.as_raw_fd(), 2) } == -1 {
        return None;
    }
    std::mem::forget(file); // the descriptor now belongs to fd 2
    Some(path)
}

#[tauri::command]
pub fn log_path() -> Option<String> {
    path().map(|p| p.to_string_lossy().into_owned())
}
