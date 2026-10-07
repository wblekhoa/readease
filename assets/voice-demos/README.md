# Voice demos

The two clips the landing page plays in its Voices section, rendered on
07/10/2026 by `scripts/render-voice-demos.py` through the app's own local
engines, from a copy of the installed models (fp32). Nothing was recorded from
a person and nothing was edited after rendering, beyond a level and AAC
encoding (64 kb/s mono).

| File | Model | Voice | Text |
|---|---|---|---|
| `vi.m4a` | VieNeu-TTS v3 Turbo (Apache-2.0) | Ngọc Linh (preset) | Three sentences, 15 s (text in `scripts/render-voice-demos.py`) |
| `en.m4a` | Kokoro-82M v1.0 (Apache-2.0) | Heart (`af_heart`) | Three sentences, 18 s (text in `scripts/render-voice-demos.py`) |
| `openai-vi.m4a`, `openai-en.m4a` | OpenAI `gpt-4o-mini-tts` (the app's default) | Marin (stock) | Same text, Vietnamese / English |
| `elevenlabs-vi.m4a`, `elevenlabs-en.m4a` | ElevenLabs `eleven_flash_v2_5` (the app's default) | Sarah (premade) | Same text, Vietnamese / English |

Model revisions and licences: `legal/MODEL_PROVENANCE.md`. The VieNeu model
card states its preset voices carry commercial-use permission and speaker
consent (publisher-supplied, not independently audited).

Both files are pinned by hash in `scripts/audit-public-release.py`; a
re-render changes the hash and has to come back there. The wave the page draws
is the clips' own peaks, written to `site/src/voiceBars.js` by the same run.

The four paid-voice clips came from the owner's own keys through the app's
own provider code (`scripts/render-voice-demos.py --api`), on stock voices
only - no library or cloned voice. The ElevenLabs account is on a paid plan
(Starter on 07/10/2026), whose terms allow commercial use of the output;
OpenAI's usage policies ask that AI-generated voices be disclosed as such,
which the page does by naming the provider and voice beside each player.
