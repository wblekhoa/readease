"""Every failure the engine names, the shipping shell must be able to say.

`speech/external/provider.py` opens by promising that "the shell turns each
code into one sentence in the reader's language; nothing here is a display
string". That promise is carried by two hand-written lists in two languages -
`ErrorCode` + `BlockedReason` on this side, `FAULT_CODES` in
`app/src/ui/voiceFault.ts` on the other - and until now nothing held them
together. Neither `grep FAULT_CODES` nor `grep voiceerr.` finds anything in
`src/`; the shell's own tests check its list against its sentences, and stop
at its own edge.

What the gap costs, when it opens: `readingFault()` returns `code: null` for a
word it does not know, the footer falls back to the raw engine string, and
somebody mid-chapter who has just been charged reads
`voice_failed: <new_code>: <whatever the provider said in English>` where a
sentence written for exactly that moment was waiting. The eight sentences
exist BECAUSE that failure already happened once.

The lists agree today; this is what keeps them agreeing. Read by regex on the
far side, because it is TypeScript and a Python test cannot import it - the
same shape as the tab-name guard and the engine-sentence guard.

Limits, stated rather than papered over: this checks the DECLARED vocabulary
and the raise sites that name a code literally. A code assembled at runtime
(`openai.py` builds `"quota"` / `"rate_limit"` in a conditional) is covered by
`ErrorCode` only, not by the raise-site scan below.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import get_args

from vieneu_reader.speech.external.elevenlabs import BY_STATUS
from vieneu_reader.speech.external.provider import ErrorCode
from vieneu_reader.speech.external.route import BlockedReason

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHELL_FAULTS = PROJECT_ROOT / "app" / "src" / "ui" / "voiceFault.ts"
ENGINE_SRC = PROJECT_ROOT / "src" / "vieneu_reader"

#: Both halves of the vocabulary reach the shell down the same wire and
#: through the same parser: `voice_failed: <code>: …` for a provider that was
#: asked and said no, `voice_unavailable: <reason>` for a reading that was
#: never sent. `voiceFault.ts` matches one list against both prefixes, so the
#: contract is against the union.
ENGINE_CODES = frozenset(get_args(ErrorCode)) | frozenset(get_args(BlockedReason))


def _shell_codes() -> frozenset[str]:
    """`FAULT_CODES` as the shipping shell declares it."""
    source = SHELL_FAULTS.read_text(encoding="utf-8")
    body = re.search(r"FAULT_CODES\s*=\s*\[(.*?)\]", source, re.DOTALL)
    if body is None:
        return frozenset()
    return frozenset(re.findall(r'"([a-z_]+)"', body.group(1)))


class ShellCanNameEveryEngineFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.shell = _shell_codes()

    def test_both_lists_were_found(self) -> None:
        # A rename on either side would otherwise empty this file's teeth
        # while leaving it green.
        self.assertGreaterEqual(len(ENGINE_CODES), 7)
        self.assertGreaterEqual(len(self.shell), 7)

    def test_every_failure_the_engine_names_can_be_said_by_the_shell(self) -> None:
        unsayable = sorted(ENGINE_CODES - self.shell)

        self.assertEqual(
            unsayable,
            [],
            "the engine can fail with these codes and the shipping shell has "
            "no sentence for any of them, so a reader who has just been "
            "charged gets the provider's raw English instead:\n"
            + "\n".join(unsayable),
        )

    def test_the_shell_names_no_failure_the_engine_cannot_emit(self) -> None:
        orphaned = sorted(self.shell - ENGINE_CODES)

        self.assertEqual(
            orphaned,
            [],
            "the shell keeps a sentence for these codes but nothing emits "
            "them any more - either the engine dropped one or the shell "
            "invented one:\n" + "\n".join(orphaned),
        )

    def test_provider_status_words_map_into_the_named_vocabulary(self) -> None:
        # `elevenlabs.py` silences the type checker here (`# type: ignore
        # [arg-type]`, because BY_STATUS is a plain str dict), and verify.sh
        # runs no type checker at all - so this is the only thing standing
        # between a new status word and an unnamed fault on a reader's screen.
        stray = sorted(set(BY_STATUS.values()) - frozenset(get_args(ErrorCode)))

        self.assertEqual(stray, [], "\n".join(stray))

    def test_every_literal_raise_uses_a_declared_code(self) -> None:
        declared = frozenset(get_args(ErrorCode))
        stray: list[str] = []
        for path in sorted(ENGINE_SRC.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            for found in re.finditer(
                r'ExternalVoiceError\(\s*"([a-z_]+)"', source
            ):
                if found.group(1) not in declared:
                    stray.append(f"{path.relative_to(PROJECT_ROOT)}: {found.group(1)}")

        self.assertEqual(
            stray,
            [],
            "these raise a code that is not in `ErrorCode`, so it never "
            "reached the shell's list either:\n" + "\n".join(stray),
        )


if __name__ == "__main__":
    unittest.main()
