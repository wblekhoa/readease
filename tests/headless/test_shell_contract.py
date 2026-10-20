"""The playback protocol, pinned from BOTH sources at once.

The Rust shell (`app/src-tauri/src/engine.rs` + `audio.rs`) and the Python engine
(`vieneu_reader/headless/server.py`) each have their own unit receipts for
the flow control and the listening-progress ack added on 2026-09-05. Neither
can see the other. These tests read the two source files and check that the
words they exchange are the same words - the drift that unit tests on either
side can never catch, and that a native run would only catch after install.
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
# The shell's half is two files since 22/09: the engine process and its
# protocol (`engine.rs`), and the audio thread with the queue the window
# is sized from (`audio.rs`). The contract spans both.
RUST = "\n".join(
    (ROOT / "app" / "src-tauri" / "src" / name).read_text(encoding="utf-8")
    for name in ("engine.rs", "audio.rs")
)
PYTHON = (ROOT / "src" / "vieneu_reader" / "headless" / "server.py").read_text(encoding="utf-8")


def rust_notifications() -> dict[str, set[str]]:
    """Method → param keys, for every `tell("method", json!({...}))` in Rust."""
    found: dict[str, set[str]] = {}
    for match in re.finditer(r'tell\(\s*"([a-z_.]+)"\s*,\s*json!\(\{([^}]*)\}\)', RUST, re.S):
        keys = set(re.findall(r'"([a-z_]+)"\s*:', match.group(2)))
        found[match.group(1)] = keys
    return found


def python_streaming_methods() -> set[str]:
    """Methods the engine answers while a reading streams (`_absorb`)."""
    body = PYTHON[PYTHON.index("def _absorb("):PYTHON.index("def _await_credit(")]
    return set(re.findall(r'method == "([a-z_.]+)"', body))


def python_idle_methods() -> set[str]:
    body = PYTHON[PYTHON.index("def _dispatch("):PYTHON.index("def _read(")]
    return set(re.findall(r'method == "([a-z_.]+)"', body))


class ShellEngineContractTests(unittest.TestCase):
    def test_every_notification_the_shell_sends_is_handled_streaming_and_idle(self) -> None:
        sent = rust_notifications()
        self.assertEqual(set(sent), {"audio.credit", "progress.reached"})
        # Streaming: a credit or an ack lands between chunks. Idle: the last
        # acks land after the reply, through the dispatcher.
        self.assertTrue(set(sent) <= python_streaming_methods(), python_streaming_methods())
        self.assertTrue(set(sent) <= python_idle_methods(), python_idle_methods())

    def test_the_param_keys_match_what_the_engine_reads(self) -> None:
        sent = rust_notifications()
        self.assertEqual(sent["audio.credit"], {"id", "frames"})
        self.assertEqual(sent["progress.reached"], {"id", "segment_id"})
        take_credit = PYTHON[PYTHON.index("def _take_credit("):PYTHON.index("def _progress_reached(")]
        self.assertIn('params.get("id")', take_credit)
        self.assertIn('params.get("frames")', take_credit)
        reached = PYTHON[PYTHON.index("def _progress_reached("):PYTHON.index("def run(")]
        self.assertIn('params.get("id")', reached)
        self.assertIn('params.get("segment_id")', reached)

    def test_the_window_is_injected_by_the_shell_and_read_by_the_engine(self) -> None:
        self.assertRegex(RUST, r'object\.insert\("window"\.into\(\), json!\(ENGINE_WINDOW\)\)')
        self.assertEqual(PYTHON.count('window=params.get("window")'), 2, "read AND read.book")
        # One less than the queue, so the reading's own Done frame always fits.
        self.assertIn("const ENGINE_WINDOW: usize = AUDIO_QUEUE_FRAMES - 1;", RUST)

    def test_the_events_the_shell_reads_are_the_events_the_engine_writes(self) -> None:
        for event in ("chunk", "position", "sentence"):
            self.assertIn(f'Some("{event}")', RUST)
            self.assertIn(f'"event": "{event}"', PYTHON)
        # What the shell pulls off each event.
        self.assertIn('message.get("pcm")', RUST)
        self.assertIn('"pcm": base64', PYTHON)
        self.assertIn('message.get("segment_id")', RUST)
        self.assertIn('"segment_id": utterance.segment_id', PYTHON)

    def test_neither_notification_gets_a_reply(self) -> None:
        """A reply to a request that carried no id would be `{"id": null}`
        noise on stdout; the shell drops it, but it should not exist."""
        for name in ("_take_credit", "_progress_reached"):
            start = PYTHON.index(f"def {name}(")
            end = PYTHON.index("\n    def ", start + 1)
            self.assertNotIn("self._reply", PYTHON[start:end])
            self.assertNotIn("self._fail", PYTHON[start:end])


LIB = (ROOT / "app" / "src-tauri" / "src" / "lib.rs").read_text(encoding="utf-8")
PAGE = "\n".join(
    path.read_text(encoding="utf-8")
    for path in (ROOT / "app" / "src").rglob("*.ts*")
    if "dev" not in path.parts
)


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)([A-Z])", lambda m: "_" + m.group(1).lower(), name)


def page_args(command: str) -> set[str]:
    """Argument names the page passes to `invoke("command", {...})`, as the
    Rust parameter names Tauri maps them to (camelCase → snake_case)."""
    keys: set[str] = set()
    for match in re.finditer(r'invoke(?:<[^>]*>)?\(\s*"' + command + r'"\s*,\s*\{([^}]*)\}', PAGE, re.S):
        for part in match.group(1).split(","):
            name = part.split(":", 1)[0].strip()
            if re.fullmatch(r"[A-Za-z_]\w*", name):
                keys.add(_snake(name))
    return keys - {"request"}  # a spread object is checked by its own type


def rust_params(command: str) -> set[str]:
    start = LIB.index(f"fn {command}(")
    signature = re.sub(r"//[^\n]*", "", LIB[start:LIB.index(") ->", start)])
    names = set(re.findall(r"(?:^|[(,])\s*(\w+)\s*:(?!:)", signature))
    return names - {"app", "engine"}


def rust_forwarded(method: str) -> set[str]:
    match = re.search(r'"' + re.escape(method) + r'"\s*,\s*serde_json::json!\(\{([^}]*)\}', LIB, re.S)
    return set(re.findall(r'"([a-z_]+)"\s*:', match.group(1))) if match else set()


class PageShellEngineBookContractTests(unittest.TestCase):
    """What the page sends for a book reading must reach the engine: Tauri
    drops an argument the command does not declare without a word, so the
    quoted chapter scope once bounded only the price, never the reading."""

    # RE-PLAY-027
    def test_every_argument_the_page_sends_to_read_book_is_declared(self) -> None:
        sent = page_args("read_book")
        self.assertIn("chapters", sent)
        self.assertLessEqual(sent, rust_params("read_book"), sent - rust_params("read_book"))

    # RE-PLAY-027
    def test_the_chapter_scope_is_forwarded_and_read(self) -> None:
        self.assertIn("chapters", rust_forwarded("read.book"))
        body = PYTHON[PYTHON.index("def _read_book("):PYTHON.index("\n    def ", PYTHON.index("def _read_book(") + 1)]
        self.assertIn('params.get("chapters")', body)

    def test_the_audiobook_range_is_forwarded_too(self) -> None:
        self.assertLessEqual({"from_chapter", "chapters"}, rust_forwarded("export.book"))


if __name__ == "__main__":
    unittest.main()
