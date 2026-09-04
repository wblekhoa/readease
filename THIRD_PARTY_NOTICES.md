# Third-party notices

VieNeu Reader uses the components below. This file is attribution and inventory,
not a replacement for each component's license text. The exact dependency graph
is locked in `uv.lock`; the Nuitka compilation report records what enters a
particular bundle.

ReadEase first-party source and scaffold are available under
PolyForm-Noncommercial-1.0.0. This does not change the licenses of the
third-party components listed below.

The shipped macOS bundle (2026-09-04 onwards) is the **Tauri** shell: a Rust
host with a WebKit view, and the Python engine frozen by PyInstaller as a
sidecar. It carries no Qt or PySide at all, so the LGPL-3.0 path those
components needed no longer applies to it. It carries `LICENSE`, `NOTICE.md`
and this file in `Contents/Resources/Legal`, and a static provenance record in
`Contents/Resources/Provenance`. The generated component manifest described
below is still bound to the older Nuitka build and is not regenerated for this
one - `PUBLIC_RELEASE_CHECKLIST.md` names that gap. The bundle is ad-hoc
signed, not notarized. The PDF importer does not bundle PyMuPDF or MuPDF.

## Primary components and model assets

- **VieNeu SDK 3.3.0** — Apache License 2.0. Source:
  <https://github.com/pnnbao97/VieNeu-TTS>.
- **VieNeu-TTS v3 Turbo model**, pinned at
  `2da0efab622a1722125991736524f080b751ef5b` — Apache License 2.0. Model:
  <https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo>. The model is
  downloaded into Application Support and is not embedded in the app bundle.
- **MOSS Audio Tokenizer Nano / VieNeu codec assets**, pinned at
  `ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae` — Apache License 2.0. Model:
  <https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX>.
  The codec is downloaded into Application Support and is not embedded in the
  app bundle.
- **PySide6 / Qt for Python 6.11.2** — LGPL-3.0-only OR GPL-2.0-only OR
  GPL-3.0-only. Source and license details: <https://code.qt.io/pyside/pyside-setup>.
- **QtPdf 6.11.2** — PDF reading module distributed with Qt/PySide6 under
  LGPL-3.0-only OR GPL-2.0-only, with bundled PDFium third-party notices.
- **ONNX Runtime 1.29.0** — MIT License. Source:
  <https://github.com/microsoft/onnxruntime>.

## Locked Python runtime inventory

License labels below come from the installed package metadata for the locked
environment. Binary wheels can also carry bundled native-library notices; keep
their license directories and the compilation report with any distributed
build.

| Package | Version | Declared license |
| --- | ---: | --- |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.14.2 | MIT |
| audioop-lts | 0.2.2 | PSF-2.0 |
| brotli | 1.2.0 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |
| cffi | 2.1.1 | MIT-0 |
| charset-normalizer | 3.5.1 | MIT |
| click | 8.4.2 | BSD-3-Clause |
| decorator | 5.3.1 | BSD-2-Clause |
| fastapi | 0.141.1 | MIT |
| filelock | 3.32.4 | MIT |
| flatbuffers | 25.12.19 | Apache-2.0 |
| fsspec | 2026.7.0 | BSD-3-Clause |
| gradio | 6.26.0 | Apache-2.0 |
| gradio-client | 2.6.1 | Apache-2.0 |
| groovy | 0.1.2 | MIT |
| h11 | 0.16.0 | MIT |
| hf-gradio | 0.4.1 | MIT |
| hf-xet | 1.6.0 | Apache-2.0 |
| httpcore | 1.0.9 | BSD-3-Clause |
| httpx | 0.28.1 | BSD-3-Clause |
| huggingface-hub | 1.28.0 | Apache-2.0 |
| idna | 3.19 | BSD-3-Clause |
| Jinja2 | 3.1.6 | BSD-3-Clause |
| joblib | 1.5.3 | BSD-3-Clause |
| kaldi-native-fbank | 1.22.3 | Apache-2.0 |
| lazy-loader | 0.5 | BSD-3-Clause |
| librosa | 1.0.0 | ISC |
| llvmlite | 0.49.0 | BSD-2-Clause AND Apache-2.0 WITH LLVM-exception |
| markdown-it-py | 4.2.0 | MIT |
| MarkupSafe | 3.0.3 | BSD-3-Clause |
| mdurl | 0.1.2 | MIT |
| msgpack | 1.2.1 | Apache-2.0 |
| narwhals | 2.25.0 | MIT |
| numba | 0.67.0 | BSD |
| numpy | 2.5.2 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| onnxruntime | 1.29.0 | MIT |
| orjson | 3.12.0 | MPL-2.0 AND (Apache-2.0 OR MIT) |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pandas | 3.0.5 | BSD-3-Clause and bundled notices |
| perth | 1.0.0 | MIT |
| pillow | 12.3.0 | MIT-CMU |
| platformdirs | 4.11.4 | MIT |
| pooch | 1.9.0 | BSD-3-Clause |
| protobuf | 7.36.0 | BSD-3-Clause |
| pycparser | 3.0 | BSD-3-Clause |
| pydantic | 2.13.4 | MIT |
| pydantic-core | 2.46.4 | MIT |
| pydub | 0.25.1 | MIT |
| Pygments | 2.21.0 | BSD-2-Clause |
| PySide6 | 6.11.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| PySide6-Addons | 6.11.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| PySide6-Essentials | 6.11.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| python-dateutil | 2.9.0.post0 | BSD-3-Clause and Apache-2.0 |
| python-multipart | 0.0.32 | Apache-2.0 |
| pytz | 2026.3.post1 | MIT |
| PyYAML | 6.0.3 | MIT |
| requests | 2.34.2 | Apache-2.0 |
| rich | 15.0.0 | MIT |
| safehttpx | 0.1.7 | MIT |
| scikit-learn | 1.9.0 | BSD-3-Clause |
| scipy | 1.18.1 | BSD-3-Clause and bundled native-library notices |
| sea-g2p | 0.9.0 | Apache-2.0 |
| semantic-version | 2.10.0 | BSD |
| shellingham | 1.5.4 | ISC |
| shiboken6 | 6.11.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| six | 1.17.0 | MIT |
| soundfile | 0.14.0 | BSD-3-Clause |
| soxr | 1.1.0 | LGPL-2.1-or-later |
| starlette | 1.6.0 | BSD-3-Clause |
| threadpoolctl | 3.6.0 | BSD-3-Clause |
| tokenizers | 0.23.1 | Apache-2.0 |
| tomlkit | 0.14.0 | MIT |
| tqdm | 4.70.0 | MPL-2.0 AND MIT |
| typer | 0.27.1 | MIT |
| typing-inspection | 0.4.4 | MIT |
| typing-extensions | 4.16.0 | PSF-2.0 |
| urllib3 | 2.7.0 | MIT |
| uvicorn | 0.52.4 | BSD-3-Clause |
| vieneu | 3.3.0 | Apache-2.0 |

Nuitka is a build-time tool and is not an application runtime dependency. Its
license notice must be included with build tooling if redistributed.

The supported bundle excludes Qt Virtual Keyboard and optional VieNeu voice
cloning dependencies (`soxr`, SoundFile, and kaldi-native-fbank). The table is
the locked development environment inventory, not proof that every row entered
a particular binary. `Legal/THIRD_PARTY_MANIFEST.json` is the bundle-specific
source of truth.
