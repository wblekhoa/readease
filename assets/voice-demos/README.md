# Voice demos

The two clips the landing page plays in its Voices section, rendered on
07/10/2026 by `scripts/render-voice-demos.py` through the app's own local
engines, from a copy of the installed models (fp32). Nothing was recorded from
a person and nothing was edited after rendering, beyond a level and AAC
encoding (64 kb/s mono).

| File | Model | Voice | Text |
|---|---|---|---|
| `vi.m4a` | VieNeu-TTS v3 Turbo (Apache-2.0) | Minh Đức (preset) | Để chữ cất lời. ReadEase đọc tài liệu, bài viết hay đoạn bạn vừa chọn, ngay trên máy Mac của bạn. |
| `en.m4a` | Kokoro-82M v1.0 (Apache-2.0) | Heart (`af_heart`) | Let words speak. ReadEase reads your documents, articles, or any passage you select, right on your Mac. |

Model revisions and licences: `legal/MODEL_PROVENANCE.md`. The VieNeu model
card states its preset voices carry commercial-use permission and speaker
consent (publisher-supplied, not independently audited).

Both files are pinned by hash in `scripts/audit-public-release.py`; a
re-render changes the hash and has to come back there. The wave the page draws
is the clips' own peaks, written to `site/src/voiceBars.js` by the same run.
