//! ReadEase's own translator (RE-PLAY-031): the bundled llama.cpp server,
//! started on loopback with the model the engine downloaded, only while
//! translations are coming, and stopped after a few idle minutes or when the
//! model is removed. It speaks the same OpenAI-style API as LM Studio, so
//! the native bridge translates through it the way it already translates
//! through a local server - only the port is ours.
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

/// How long an idle server keeps its ~1.5 GB before it is let go.
const IDLE: Duration = Duration::from_secs(5 * 60);
/// A cold first start reads 1.1 GB from disk and compiles the Metal shaders.
const START_DEADLINE: Duration = Duration::from_secs(90);

struct Server {
    child: Child,
    port: u16,
    model: PathBuf,
    last_used: Instant,
}

static SERVER: Mutex<Option<Server>> = Mutex::new(None);
static REAPER: std::sync::Once = std::sync::Once::new();

fn binary(app: &tauri::AppHandle) -> Option<PathBuf> {
    use tauri::Manager;
    if !cfg!(debug_assertions) {
        if let Ok(resources) = app.path().resource_dir() {
            let bundled = resources.join("translator/llama-server");
            if bundled.is_file() { return Some(bundled); }
        }
    }
    let dev = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("translator/llama-server");
    dev.is_file().then_some(dev)
}

fn free_port() -> Result<u16, String> {
    let listener = TcpListener::bind("127.0.0.1:0").map_err(|_| "translation:local_unavailable")?;
    Ok(listener.local_addr().map_err(|_| "translation:local_unavailable")?.port())
}

/// `GET /health` answered 200: the model is loaded and the server serves.
pub(crate) fn healthy(port: u16) -> bool {
    let Ok(mut stream) = TcpStream::connect_timeout(&([127, 0, 0, 1], port).into(), Duration::from_millis(300)) else { return false };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(2)));
    if stream.write_all(b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n").is_err() { return false; }
    let mut head = [0u8; 16];
    matches!(stream.read(&mut head), Ok(n) if n >= 12 && &head[9..12] == b"200")
}

fn stop_locked(slot: &mut Option<Server>) {
    if let Some(mut server) = slot.take() {
        let _ = server.child.kill();
        let _ = server.child.wait();
    }
}

/// Stop the server now: the model is being removed, or the app is quitting.
pub(crate) fn stop() { stop_locked(&mut SERVER.lock().unwrap()); }

/// The port of a server running `model`, starting one if needed.
pub(crate) fn port(app: &tauri::AppHandle, model: &Path) -> Result<u16, String> {
    REAPER.call_once(|| {
        std::thread::spawn(|| loop {
            std::thread::sleep(Duration::from_secs(30));
            let mut slot = SERVER.lock().unwrap();
            if slot.as_ref().is_some_and(|server| server.last_used.elapsed() > IDLE) { stop_locked(&mut slot); }
        });
    });
    let mut slot = SERVER.lock().unwrap();
    if let Some(server) = slot.as_mut() {
        let alive = matches!(server.child.try_wait(), Ok(None));
        if alive && server.model == model {
            server.last_used = Instant::now();
            return Ok(server.port);
        }
    }
    stop_locked(&mut slot);
    let binary = binary(app).ok_or("translation:translator_missing")?;
    if !model.is_file() { return Err("translation:translator_missing".into()); }
    let port = free_port()?;
    let child = Command::new(binary)
        .arg("-m").arg(model)
        .args(["--host", "127.0.0.1", "--port", &port.to_string()])
        // Every layer on the GPU; a context that fits the longest piece the
        // paste splitter sends (5,000 characters) and its translation.
        .args(["-ngl", "99", "-c", "8192", "--no-webui", "--parallel", "1"])
        .stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null())
        .spawn().map_err(|_| "translation:local_unavailable")?;
    let mut server = Server { child, port, model: model.to_path_buf(), last_used: Instant::now() };
    let started = Instant::now();
    while !healthy(port) {
        if started.elapsed() > START_DEADLINE || !matches!(server.child.try_wait(), Ok(None)) {
            let _ = server.child.kill();
            let _ = server.child.wait();
            return Err("translation:local_unavailable".into());
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    server.last_used = Instant::now();
    *slot = Some(server);
    Ok(port)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn a_closed_port_is_not_healthy() {
        let port = free_port().unwrap();
        assert!(!healthy(port));
    }
    #[test]
    fn a_server_answering_200_is_healthy() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        std::thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            let mut request = [0u8; 256];
            let _ = stream.read(&mut request);
            let _ = stream.write_all(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}");
        });
        assert!(healthy(port));
    }
}
