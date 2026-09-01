#!/bin/bash
# Bundle the headless engine for the Tauri app: one folder, no Python needed.
# Mirrors the Nuitka build's exclusions - the shipped Qt app already proved
# the engine runs without librosa/soxr/soundfile/kaldi, and the sidecar has
# no Qt at all.
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"
out="$project_root/app/src-tauri/engine"
rm -rf "$out" build/engine-build dist/readease-engine readease-engine.spec

uv run pyinstaller \
  --distpath dist \
  --workpath build/engine-build \
  --noconfirm \
  --onedir \
  --name readease-engine \
  --target-arch arm64 \
  --collect-all vieneu \
  --collect-all sea_g2p \
  --collect-all onnxruntime \
  --collect-all tokenizers \
  --exclude-module PySide6 \
  --exclude-module shiboken6 \
  --exclude-module librosa \
  --exclude-module soxr \
  --exclude-module soundfile \
  --exclude-module kaldi_native_fbank \
  --exclude-module gradio \
  --exclude-module matplotlib \
  --exclude-module PIL \
  scripts/engine_entry.py

mkdir -p "$(dirname "$out")"
mv dist/readease-engine "$out"
echo "SIDECAR_BUILT $(du -sh "$out" | cut -f1)"
