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

Both are fetched into `~/Library/Application Support/VieNeu Reader/Models`
by the app on first use. Provenance and pinning: `legal/MODEL_PROVENANCE.md`.

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
