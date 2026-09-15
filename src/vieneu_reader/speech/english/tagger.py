"""The part-of-speech tagger behind the English G2P: spaCy's small English
pipeline, loaded once, with only the two components the G2P reads.

A seam on purpose. The G2P wants one function - text in, `(word, tag,
whitespace)` out - and this is the only file that knows the function is
spaCy. A test hands the G2P a tagger of its own and never imports spaCy.
"""

from __future__ import annotations

from threading import Lock
from typing import Any, Sequence

from .g2p import TaggedToken

PIPELINE = "en_core_web_sm"
#: The tagger needs the embedding in front of it; nothing else is read.
COMPONENTS = ("tok2vec", "tagger")

_pipeline: Any = None
_load_lock = Lock()


def _load() -> Any:
    global _pipeline
    with _load_lock:
        if _pipeline is None:
            import spacy

            _pipeline = spacy.load(PIPELINE, enable=list(COMPONENTS))
    return _pipeline


def tag(text: str) -> Sequence[TaggedToken]:
    """Penn Treebank tags for each token of `text`, with its whitespace."""

    return [(token.text, token.tag_, token.whitespace_) for token in _load()(text)]
