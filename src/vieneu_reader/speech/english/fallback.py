"""Phonemes for a word the lexicon does not have.

The same network the original G2P falls back to - `PeterReid/
graphemes_to_phonemes_en_us`, a one-layer BART trained on the lexicon
itself (Apache-2.0) - run through onnxruntime instead of torch. The two
graphs (encoder, decoder without a cache) were exported once at development
time and ship inside the package: they are 3 MB together, and a word is
never more than a few dozen letters, so re-running the decoder over the
prefix at every step costs nothing anyone can hear.

Greedy decoding, up to the network's own position limit. Names, technical
terms and typos - 1.2% of the words in a real English book - come through
here; without it they were simply not said.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any, Tuple

import numpy as np

from .g2p import MToken

ASSETS = Path(__file__).with_name("fallback_assets")
ENCODER = ASSETS / "encoder.onnx"
DECODER = ASSETS / "decoder.onnx"
ALPHABET = ASSETS / "alphabet.json"

#: What the network answered its words with, as the G2P rates them: below
#: a lexicon hit (4) and a stem (3).
RATING = 1


class Fallback:
    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: Tuple[Any, Any] | None = None
        alphabet = json.loads(ALPHABET.read_text(encoding="utf-8"))
        # Both alphabets begin with four placeholders (pad, start, end,
        # unknown); a letter the network never saw is the unknown token.
        self._grapheme = {char: index for index, char in enumerate(alphabet["grapheme_chars"])}
        self._phoneme = {index: char for index, char in enumerate(alphabet["phoneme_chars"])}
        self._start = int(alphabet["decoder_start_token_id"])
        self._end = int(alphabet["eos_token_id"])
        self._max_length = int(alphabet["max_length"])

    def _load(self) -> Tuple[Any, Any]:
        with self._lock:
            if self._sessions is None:
                import onnxruntime

                options = onnxruntime.SessionOptions()
                options.intra_op_num_threads = 1
                options.log_severity_level = 3
                providers = ["CPUExecutionProvider"]
                self._sessions = (
                    onnxruntime.InferenceSession(str(ENCODER), options, providers=providers),
                    onnxruntime.InferenceSession(str(DECODER), options, providers=providers),
                )
            return self._sessions

    def phonemes(self, word: str) -> str:
        encoder, decoder = self._load()
        letters = [1] + [self._grapheme.get(char, 3) for char in word] + [2]
        hidden = encoder.run(None, {"input_ids": np.array([letters], dtype=np.int64)})[0]
        spoken = [self._start]
        # The last position the network was trained with is the forced end
        # marker, which is why the loop stops one short of the limit.
        while len(spoken) < self._max_length - 1:
            logits = decoder.run(None, {
                "decoder_input_ids": np.array([spoken], dtype=np.int64),
                "hidden": hidden,
            })[0]
            next_token = int(np.argmax(logits[0, -1]))
            if next_token == self._end:
                break
            spoken.append(next_token)
        return "".join(self._phoneme.get(token, "") for token in spoken if token > 3)

    def __call__(self, token: MToken) -> Tuple[str | None, int | None]:
        with self._lock:
            phonemes = self.phonemes(token.text)
        return (phonemes or None), (RATING if phonemes else None)
