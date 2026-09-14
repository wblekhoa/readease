"""A paid provider's catalogue is asked for once, off the request thread.

Listing voices is the first thing the shell asks. ElevenLabs answers it
over the network - 1-1.8 s measured 14/09 - and the engine answers requests
one at a time, so that round trip used to sit between the app starting and
the window deciding which screen to show, and was paid again on every
listing. Now the answer is remembered per credential, fetched in the
background at start-up, and a listing that lands while the fetch is still
out says `pending` and is told, by the `voices` event, when to ask again.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time
import unittest
import unittest.mock

from tests.headless.test_server import FakeEngine, run_server

from vieneu_reader.headless import server
from vieneu_reader.speech.external.provider import ExternalVoiceError, ProviderVoice

KEY = "sk-eleven-0123456789abcdefghijklmnopqrstuvwxyz"


class CountingProvider:
    """Answers with two voices, and counts how often it was asked."""

    name = "elevenlabs"
    model = "eleven_flash_v2_5"

    def __init__(self, gate: threading.Event | None = None, fail: str | None = None):
        self.asked = 0
        self.gate = gate
        self.fail = fail

    def voices(self):
        self.asked += 1
        if self.gate is not None:
            self.gate.wait(5)
        if self.fail:
            raise ExternalVoiceError(self.fail, "no")
        return (
            ProviderVoice(id="nhu", label="Nhu · ElevenLabs", model=self.model, languages=("vi",)),
            ProviderVoice(id="rob", label="Rob · ElevenLabs", model=self.model),
        )

    def verify(self):
        return self.voices()


class CatalogueCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = CountingProvider()
        self._original = server._external_provider
        server._external_provider = lambda provider, voice_id, settings: (
            self.provider if provider == "elevenlabs" else None
        )
        self.addCleanup(setattr, server, "_external_provider", self._original)
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.settings = Path(self.temp_dir.name) / "settings.json"
        self.settings.write_text(json.dumps({"elevenlabs_api_key": KEY}), encoding="utf-8")

    def _paid(self, reply):
        return sorted(v["id"].split(":")[-1] for v in reply["result"]["voices"] if v["paid"])

    def test_the_same_key_is_asked_once_per_process(self) -> None:
        replies = run_server(
            [{"id": 1, "method": "voices"}, {"id": 2, "method": "voices"},
             {"id": 3, "method": "voices"}],
            FakeEngine(), settings_path=self.settings,
        )

        self.assertEqual(self.provider.asked, 1)
        for reply in replies:
            self.assertEqual(self._paid(reply), ["nhu", "rob"])
            self.assertEqual(reply["result"]["pending"], [])

    def test_a_new_key_is_a_new_question(self) -> None:
        run_server(
            [{"id": 1, "method": "voices"},
             {"id": 2, "method": "config.verify_key",
              "params": {"provider": "elevenlabs", "value": KEY + "-rotated"}},
             {"id": 3, "method": "voices"}],
            FakeEngine(), settings_path=self.settings,
        )

        # Once for the first listing, once for the check - and the listing
        # after the check is answered from what the check listed.
        self.assertEqual(self.provider.asked, 2)

    def test_a_refusal_is_remembered_briefly_not_for_ever(self) -> None:
        self.provider.fail = "network"
        replies = run_server(
            [{"id": 1, "method": "voices"}, {"id": 2, "method": "voices"}],
            FakeEngine(), settings_path=self.settings,
        )

        self.assertEqual(self.provider.asked, 1)
        self.assertEqual(
            replies[1]["result"]["unreachable"], [{"provider": "elevenlabs", "code": "network"}]
        )

    def test_a_lapsed_refusal_is_asked_again_off_the_request_loop(self) -> None:
        """On a network that swallows packets the ask is a 60 s timeout; the
        listing must not carry it, nor anything queued behind the listing."""
        self.provider.fail = "network"
        gate = threading.Event()
        writer = io.StringIO()
        with unittest.mock.patch.object(server, "_FAILURE_MEMORY", 0.0):
            reader = io.StringIO(json.dumps({"id": 1, "method": "voices"}) + "\n")
            session = server._Session(reader, writer, FakeEngine(), settings_path=self.settings)
            session.run()   # first ask: synchronous, refused, remembered
            self.assertEqual(self.provider.asked, 1)
            # The memory has lapsed (0 s). The next listing hangs on nothing.
            self.provider.gate = gate
            started = time.monotonic()
            catalogue, unreachable, pending = session._voice_catalogue()
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertEqual(pending, ["elevenlabs"])
        self.assertEqual(unreachable, [])
        self.assertTrue(all(not voice["paid"] for voice in catalogue))
        gate.set()
        deadline = time.monotonic() + 5
        while self.provider.asked < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        deadline = time.monotonic() + 5
        while "\"event\": \"voices\"" not in writer.getvalue() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(self.provider.asked, 2)
        self.assertIn({"event": "voices", "providers": ["elevenlabs"]},
                      [json.loads(line) for line in writer.getvalue().splitlines()])

    def test_a_listing_during_the_prefetch_does_not_wait_for_it(self) -> None:
        gate = threading.Event()
        self.provider.gate = gate
        reader = io.StringIO(json.dumps({"id": 1, "method": "voices"}) + "\n")
        writer = io.StringIO()
        session = server._Session(reader, writer, FakeEngine(), settings_path=self.settings)
        session.start_background_work()
        # The prefetch is out and blocked on the gate; the listing must not be.
        deadline = time.monotonic() + 5
        while self.provider.asked == 0 and time.monotonic() < deadline:
            time.sleep(0.01)
        started = time.monotonic()
        session.run()
        self.assertLess(time.monotonic() - started, 2.0)
        first = json.loads(writer.getvalue().splitlines()[0])
        self.assertEqual(first["result"]["pending"], ["elevenlabs"])
        self.assertEqual(self._paid(first), [])

        gate.set()
        deadline = time.monotonic() + 5
        while "\"event\": \"voices\"" not in writer.getvalue() and time.monotonic() < deadline:
            time.sleep(0.01)
        lines = [json.loads(line) for line in writer.getvalue().splitlines()]
        self.assertIn({"event": "voices", "providers": ["elevenlabs"]}, lines)
        self.assertEqual(self.provider.asked, 1)

    def test_lines_from_two_threads_never_interleave(self) -> None:
        class SlowPipe(io.StringIO):
            """A pipe that yields the interpreter between writes, the way a
            real one blocks - so two writers without a lock DO collide."""

            def write(self, text: str) -> int:
                time.sleep(0.0005)
                return super().write(text)

        writer = SlowPipe()
        session = server._Session(io.StringIO(""), writer, FakeEngine(), settings_path=self.settings)
        payload = {"event": "x", "filler": "y" * 200}

        def talk():
            for _ in range(50):
                session._send(payload)

        threads = [threading.Thread(target=talk) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        lines = writer.getvalue().splitlines()
        self.assertEqual(len(lines), 200)
        for line in lines:
            self.assertEqual(json.loads(line), payload)


if __name__ == "__main__":
    unittest.main()
