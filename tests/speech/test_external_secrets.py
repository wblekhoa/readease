"""The key stays on this machine - proved at each place it could leave.

The owner's one hard condition for outside voices (04/09): "tránh việc key mà
user nhập bị public trên mạng, miễn là vẫn ở local là được". These are the
three ways a key gets off a local machine in THIS codebase, each closed and
each checked here.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from vieneu_reader.speech.external import redacted  # noqa: E402


KEY = "sk-proj-0123456789abcdefghijklmnopqrstuvwxyz"


class RedactionTests(unittest.TestCase):
    def test_a_provider_error_that_quotes_the_key_is_scrubbed(self) -> None:
        # Some providers echo the Authorization header back in a 401 body.
        # That string is on its way to a Notice on screen.
        body = f'{{"error":{{"message":"Incorrect API key provided: {KEY}"}}}}'
        cleaned = redacted(body, KEY)
        self.assertNotIn(KEY, cleaned)
        self.assertIn("***", cleaned)
        self.assertIn("Incorrect API key provided", cleaned)

    def test_it_takes_whatever_str_would_take(self) -> None:
        # The usual caller is redacted(error, key) on an exception object.
        error = RuntimeError(f"HTTP 401 for key {KEY}")
        self.assertNotIn(KEY, redacted(error, KEY))

    def test_several_keys_at_once_and_none_at_all(self) -> None:
        other = "xi-api-key-abcdefghijklmnop"
        message = f"{KEY} and {other} both refused"
        cleaned = redacted(message, KEY, other)
        self.assertNotIn(KEY, cleaned)
        self.assertNotIn(other, cleaned)
        self.assertEqual(redacted("nothing to hide"), "nothing to hide")

    def test_an_empty_or_tiny_secret_does_not_blank_out_prose(self) -> None:
        # A key that is not set must not turn every message into "***", and a
        # two-letter "secret" would match ordinary words.
        self.assertEqual(redacted("mạng không nối được", None, "", "sk"), "mạng không nối được")


class ExportTests(unittest.TestCase):
    def test_the_public_source_export_can_never_carry_a_key_file(self) -> None:
        # The exporter is allowlist-based, so a key in Application Support is
        # already out of reach. This is the second lock: even a stray
        # settings.json or .env INSIDE the tree is refused by name, wherever
        # it sits.
        import importlib.util

        script = ROOT / "scripts" / "export-public-source.py"
        spec = importlib.util.spec_from_file_location("export_public_source", script)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        manifest = json.loads(
            (ROOT / "scripts" / "public-source-manifest.json").read_text(encoding="utf-8")
        )
        for leaky in (
            Path("settings.json"),
            Path("src/vieneu_reader/settings.json"),
            Path("tests/fixtures/.env"),
            Path(".env"),
        ):
            self.assertTrue(
                module._excluded(leaky, manifest),
                f"{leaky} would have been copied into a public source export",
            )
        # And the allowlist does not name them either.
        self.assertNotIn("settings.json", manifest["root_files"])
        self.assertNotIn(".env", manifest["root_files"])


class WriteOnlyConfigTests(unittest.TestCase):
    def test_the_shell_can_set_a_key_and_ask_if_one_is_set_but_never_read_it(self) -> None:
        from tests.headless.test_server import FakeEngine, run_server

        with TemporaryDirectory() as directory:
            settings = Path(directory) / "settings.json"
            replies = run_server(
                [
                    {"id": 1, "method": "config.set",
                     "params": {"key": "openai_api_key", "value": KEY}},
                    {"id": 2, "method": "config.get", "params": {"key": "openai_api_key"}},
                    {"id": 3, "method": "config.get", "params": {"key": "ui_language"}},
                ],
                FakeEngine(),
                settings_path=settings,
            )
            self.assertTrue(replies[0]["result"]["saved"])
            # Written to disk...
            stored = json.loads(settings.read_text(encoding="utf-8"))
            self.assertEqual(stored["openai_api_key"], KEY)
            # ...and never handed back over the pipe.
            self.assertEqual(replies[1]["result"], {"value": None, "set": True})
            self.assertNotIn(KEY, json.dumps(replies[1]))
            # An ordinary key still reads back normally.
            self.assertIsNone(replies[2]["result"]["value"])
            # And the file it landed in is readable by this user alone: the
            # settings store writes 0600, which is the difference between "on
            # my machine" and "on my machine, and anyone else's account on it".
            self.assertEqual(settings.stat().st_mode & 0o777, 0o600)

    def test_a_key_that_is_not_set_says_so_without_failing(self) -> None:
        from tests.headless.test_server import FakeEngine, run_server

        with TemporaryDirectory() as directory:
            replies = run_server(
                [{"id": 1, "method": "config.get", "params": {"key": "elevenlabs_api_key"}}],
                FakeEngine(),
                settings_path=Path(directory) / "settings.json",
            )
            self.assertEqual(replies[0]["result"], {"value": None, "set": False})


if __name__ == "__main__":
    unittest.main()
