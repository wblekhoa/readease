# Third-party notices

ReadEase — Thư Âm is built on the components below. This file is the
human-readable attribution; it does not replace any component's own licence
text. The exact, per-build inventory is generated into the app bundle at
`Contents/Resources/Legal/`:

- `THIRD_PARTY_INVENTORY.md` — every component, its version, licence and
  source, in three tables (Python engine, Rust host, models);
- `THIRD_PARTY_LICENSES.txt` — every licence text, once each, with the
  components and copyright holders it applies to;
- `THIRD_PARTY_MANIFEST.json` — the same, machine-readable, bound by SHA-256
  to the `uv.lock` and `Cargo.lock` the build was made from.

`scripts/package-license-payload.py` produces all three from what the bundle
actually contains - the frozen engine's PyInstaller table of contents and the
host's `Cargo.lock` - and refuses to finish if any component has no licence
text to ship. ReadEase's own source and scaffold are under
PolyForm-Noncommercial-1.0.0; that does not change the licence of anything
listed here.

## Landing website (separate from the macOS bundle)

The `site/` build uses React and React DOM 19.3.0 (MIT, including Scheduler)
and GSAP/ScrollTrigger 3.15.0 under the
[GSAP Standard No Charge License](https://gsap.com/standard-license/), not MIT.
Vite and tsx are development/build tools, not additional app dependencies.
Versions and integrity hashes are pinned in `site/package-lock.json`.
The website build emits `THIRD_PARTY_LICENSES.txt` with installed React licences
and the original GSAP runtime notices. No private DOL components are included.

## Development and audit tools (not in the shipped app)

The render audit runs **axe-core** 4.13 (Mozilla Public License 2.0) inside a
headless browser to check the interface against WCAG 2 A/AA. It is a
`devDependency` of `app/`, never bundled: the audit script reads it from
`node_modules` and injects it into the page it is auditing.

## What the shipped app is made of

The macOS bundle is a **Tauri** shell - a Rust host with a WebKit view - and
the Python speech engine frozen by **PyInstaller** as a sidecar. It carries no
Qt and no PySide. It is ad-hoc signed, not notarized.

### Speech engine (Python, frozen)

- **VieNeu SDK 3.6.3** — Apache-2.0. <https://github.com/pnnbao97/VieNeu-TTS>
- **ONNX Runtime 1.29** — MIT. <https://github.com/microsoft/onnxruntime>
- **tokenizers**, **huggingface_hub**, **hf-xet** — Apache-2.0.
- **sea-g2p** — Apache-2.0 (phonemiser; its `sea_g2p.bin` data ships in the
  bundle).
- **pypdfium2 5.13** — Apache-2.0 OR BSD-3-Clause, binding **PDFium**
  (BSD-3-Clause). <https://github.com/pypdfium2-team/pypdfium2>
- **spaCy 3.8** and its **en_core_web_sm 3.8.0** English pipeline — MIT;
  **thinc**, **srsly**, **preshed**, **cymem**, **murmurhash**, **wasabi**,
  **catalogue**, **confection** — MIT; **blis** — BSD-3-Clause. The tagger
  behind the English voice's pronunciation. <https://spacy.io>
- **misaki** English G2P — Apache-2.0, ported into
  `src/vieneu_reader/speech/english/g2p.py` (revision
  `fba1236595f2d2bf21d414ba6e57d25256afada3`) without its torch, num2words
  and spaCy-loading seams. <https://github.com/hexgrad/misaki>
- **numpy**, **httpx**, **requests**, **pydantic**, **Pillow**, **PyYAML**,
  **rich** and the rest of the frozen graph — MIT, BSD and Apache-2.0 family;
  the inventory names each one.
- **CPython 3.13** — PSF-2.0. The frozen engine embeds the interpreter.
- **PyInstaller bootloader** — GPL-2.0-or-later WITH Bootloader-exception.
  The exception is what lets a frozen program carry any licence of its own.

### Host (Rust)

- **Tauri 2**, **wry**, **tao** — Apache-2.0 OR MIT. <https://tauri.app>
- **rodio**, **cpal**, **symphonia** (audio output and decoding) — MIT and
  Apache-2.0; the **symphonia** crates are MPL-2.0, and their source is at the
  repository the inventory names for each.
- The remaining ~500 crates in `Cargo.lock` are MIT, Apache-2.0, BSD, Zlib,
  Unicode-3.0 or MPL-2.0. **None is under a copyleft licence that reaches the
  binary**; the MPL-2.0 crates are unmodified and their source locations are
  in the inventory, which is what MPL §3.2 asks for.

### Models (downloaded on first run, never inside the bundle)

- **VieNeu-TTS v3 Turbo**, pinned at `2da0efab622a1722125991736524f080b751ef5b`
  — Apache-2.0 (publisher declaration).
  <https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo>
- **MOSS Audio Tokenizer Nano ONNX**, pinned at
  `ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae` — Apache-2.0 (publisher
  declaration). <https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX>

- **Kokoro-82M v1.0 ONNX** (the optional English voice), pinned at
  `1939ad2a8e416c0acfeecc08a694d14ef25f2231` — Apache-2.0 (publisher
  declaration). <https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX>
- **misaki English lexicon** (`us_gold.json`, `us_silver.json`), pinned at
  `fba1236595f2d2bf21d414ba6e57d25256afada3` — Apache-2.0.
  <https://github.com/hexgrad/misaki>

The Vietnamese model and codec are fetched into
`~/Library/Application Support/VieNeu Reader/Models` by the app on first use;
the English model and lexicon land in the same folder only when the reader
asks for them under Settings › Reading models. Provenance and pinning:
`legal/MODEL_PROVENANCE.md`.

One model does ship inside the bundle: **graphemes_to_phonemes_en_us**
(BART, 3 MB, exported to ONNX), pinned at
`a5631b285d18d59483c32c0c3379cb9fac924f4b` — Apache-2.0 (publisher
declaration). <https://huggingface.co/PeterReid/graphemes_to_phonemes_en_us>
It reads the English words the lexicon does not have.

### Sounds (inside the bundle)

Three short chimes mark a chapter's start when the reader leaves that
setting on (`src/vieneu_reader/speech/chimes/`, about 470 KB together):

| File | Length | Generated from |
|---|---|---|
| `marimba.wav` | 0.9 s | "A soft, warm two-note marimba chime for an audiobook chapter transition, gentle and clean, quiet, no long reverb tail" |
| `harp.wav` | 2.0 s | "A short calm harp arpeggio of three rising notes, intimate and quiet, an audiobook chapter interlude" |
| `piano.wav` | 2.0 s | "Two soft felt piano notes forming a gentle major fifth, slow and quiet, a new chapter begins" |

They were generated on 16/09/2026 with **ElevenLabs'** sound-effects model
(`eleven_text_to_sound_v2`) from the maintainer's own account, then
downmixed to mono 48 kHz, trimmed of silence and levelled to −14 dBFS here.
They are not recordings of anyone and not a model; ElevenLabs' terms in
force at generation govern what the account holder may do with generated
output, and this app is non-commercial. The public-release audit pins each
file by hash (`scripts/audit-public-release.py`), so a re-render is a
reviewed change, not a silent one.

### Optional, off by default, never bundled

A reader who enters their own key can read with **OpenAI** or **ElevenLabs**
voices. Those are services, not components: nothing of theirs ships in the
app, and `PRIVACY.md` sets out exactly what is sent when the reader turns one
on.

## Excluded on purpose

The frozen engine leaves out `librosa`, `soxr`, `soundfile`,
`kaldi-native-fbank`, `gradio`, `scipy`, `numba`, `pandas`, `fastapi`,
`uvicorn` and `matplotlib` (see `readease-engine.spec`). They are reachable
from the VieNeu SDK's optional features - voice cloning, a demo server - that
ReadEase does not use. Reintroducing one is a licence review, not a one-line
change: `soxr` is LGPL-2.1.
