//! ReadEase's own translator (RE-PLAY-031): the bundled llama.cpp server,
//! started on loopback with the model the engine downloaded, only while
//! translations are coming, and stopped after a few idle minutes or when the
//! model is removed. It speaks the same OpenAI-style API as LM Studio, so
//! the native bridge translates through it the way it already translates
//! through a local server - only the port is ours.
use std::io::{BufRead, BufReader, Read, Write};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
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
    /// Answering /health; until then a second caller must not reuse it.
    ready: bool,
}

static SERVER: Mutex<Option<Server>> = Mutex::new(None);
static REAPER: std::sync::Once = std::sync::Once::new();
static STARTING: Mutex<()> = Mutex::new(());

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

/// A translation is under way: a long paste is many pieces, and the idle
/// clock must not run out between them.
pub(crate) fn touch() {
    if let Some(server) = SERVER.lock().unwrap().as_mut() { server.last_used = Instant::now(); }
}

/// The port of a server running `model`, starting one if needed.
pub(crate) fn port(app: &tauri::AppHandle, model: &Path) -> Result<u16, String> {
    let binary = binary(app).ok_or("translation:translator_missing")?;
    port_with(&binary, model)
}

pub(crate) fn port_with(binary: &Path, model: &Path) -> Result<u16, String> {
    // One start at a time - but `stop()` and `touch()` only ever take SERVER,
    // and SERVER is never held while the server warms up: quitting or removing
    // the model during a cold start (up to 90 s) must not freeze the app.
    REAPER.call_once(|| {
        std::thread::spawn(|| loop {
            std::thread::sleep(Duration::from_secs(30));
            let mut slot = SERVER.lock().unwrap();
            if slot.as_ref().is_some_and(|server| server.ready && server.last_used.elapsed() > IDLE) { stop_locked(&mut slot); }
        });
    });
    let _starting = STARTING.lock().unwrap();
    {
        let mut slot = SERVER.lock().unwrap();
        if let Some(server) = slot.as_mut() {
            let alive = matches!(server.child.try_wait(), Ok(None));
            if alive && server.model == model && server.ready {
                server.last_used = Instant::now();
                return Ok(server.port);
            }
        }
        stop_locked(&mut slot);
    }
    if !model.is_file() { return Err("translation:translator_missing".into()); }
    let port = free_port()?;
    let mut child = Command::new(binary)
        .arg("-m").arg(model)
        .args(["--host", "127.0.0.1", "--port", &port.to_string()])
        // Every layer on the GPU; a context that fits the longest piece the
        // paste splitter sends (5,000 characters) and its translation.
        .args(["-ngl", "99", "-c", "8192", "--no-webui", "--parallel", "1"])
        .stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::piped())
        .spawn().map_err(|_| "translation:local_unavailable")?;
    // The server's own words while it starts, for the log if it fails; after
    // that its output is drained unread - it carries request details, and
    // nothing a reader translates may reach a log.
    let starting = Arc::new(AtomicBool::new(true));
    let said = Arc::new(Mutex::new(Vec::<String>::new()));
    if let Some(stderr) = child.stderr.take() {
        let (starting, said) = (starting.clone(), said.clone());
        std::thread::spawn(move || {
            for line in BufReader::new(stderr).lines().map_while(Result::ok) {
                if starting.load(Ordering::Relaxed) {
                    let mut said = said.lock().unwrap();
                    if said.len() == 40 { said.remove(0); }
                    said.push(line);
                }
            }
        });
    }
    let pid = child.id();
    // In the slot from the start, so a stop() during the warm-up kills it.
    *SERVER.lock().unwrap() = Some(Server { child, port, model: model.to_path_buf(), last_used: Instant::now(), ready: false });
    let started = Instant::now();
    let failed = |reason: &str| {
        starting.store(false, Ordering::Relaxed);
        eprintln!("translator: the server did not start ({reason})");
        for line in said.lock().unwrap().iter() { eprintln!("translator: {line}"); }
        Err::<u16, String>("translation:local_unavailable".into())
    };
    loop {
        if healthy(port) { break; }
        {
            let mut slot = SERVER.lock().unwrap();
            let ours = slot.as_mut().filter(|server| server.child.id() == pid);
            match ours {
                // Stopped from elsewhere (quit, model removed) mid-start.
                None => { starting.store(false, Ordering::Relaxed); return Err("translation:local_unavailable".into()); }
                Some(server) => {
                    if !matches!(server.child.try_wait(), Ok(None)) { stop_locked(&mut slot); drop(slot); return failed("exited"); }
                    if started.elapsed() > START_DEADLINE { stop_locked(&mut slot); drop(slot); return failed("timed out"); }
                }
            }
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    starting.store(false, Ordering::Relaxed);
    said.lock().unwrap().clear();
    let mut slot = SERVER.lock().unwrap();
    match slot.as_mut().filter(|server| server.child.id() == pid) {
        Some(server) => { server.ready = true; server.last_used = Instant::now(); Ok(port) }
        None => Err("translation:local_unavailable".into()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    /// The real thing, end to end: `READEASE_TRANSLATOR_MODEL=<gguf> cargo
    /// test --lib -- --ignored` with `translator/llama-server` built.
    #[test]
    #[ignore]
    fn starts_the_bundled_server_on_the_model_and_stops_it() {
        let model = PathBuf::from(std::env::var("READEASE_TRANSLATOR_MODEL").expect("READEASE_TRANSLATOR_MODEL"));
        let binary = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("translator/llama-server");
        let port = port_with(&binary, &model).expect("server starts");
        assert!(healthy(port));
        assert_eq!(port_with(&binary, &model).unwrap(), port, "a running server is reused");
        stop();
        assert!(!healthy(port));
    }
    /// Quitting (or removing the model) while the server is still warming up
    /// returns at once and the start gives up - nothing waits out the 90 s.
    #[test]
    #[ignore]
    fn a_stop_during_the_warm_up_does_not_wait_for_it() {
        let model = PathBuf::from(std::env::var("READEASE_TRANSLATOR_MODEL").expect("READEASE_TRANSLATOR_MODEL"));
        let binary = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("translator/llama-server");
        let starting = std::thread::spawn(move || port_with(&binary, &model));
        std::thread::sleep(Duration::from_millis(150));
        let asked = Instant::now();
        stop();
        assert!(asked.elapsed() < Duration::from_secs(1), "stop waited {:?}", asked.elapsed());
        assert!(starting.join().unwrap().is_err());
    }
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
