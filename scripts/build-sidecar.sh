#!/bin/bash
# Bundle the headless engine for the Tauri app: one folder, no Python needed.
# Mirrors the Nuitka build's exclusions - the shipped Qt app already proved
# the engine runs without librosa/soxr/soundfile/kaldi, and the sidecar has
# no Qt at all.
#
# The second block of exclusions is the sidecar diet (2026-09-07). Measured on
# the 384 MB sidecar: `--collect-all onnxruntime` drags in
# onnxruntime.transformers, whose metrics module imports pandas, which pulls
# numba and llvmlite (123 MB on its own) and scipy. None of it runs on the
# ONNX voice path - the engine uses onnxruntime's session API only, and
# sea_g2p/vieneu_utils are numpy. PIL stays: covers.py renders book covers
# with it, and excluding it killed the frozen engine at import (see the smoke
# note below). What is excluded is proven by the read below, not by the
# import graph: an excluded module that IS needed only fails in the frozen
# binary.
#
# `perth` is excluded by name: the `perth` on PyPI is not resemble-perth
# (vieneu's watermark extra, which this app does not install). A stray copy in
# a dev venv otherwise rides into the bundle and logs a watermark warning at
# every start of the engine.
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"
out="$project_root/app/src-tauri/engine"
rm -rf "$out" build/engine-build dist/readease-engine readease-engine.spec

# The bundle is whatever the venv holds, not what the lock says. `uv run` adds
# what is missing but leaves extras in place: after `uv lock` dropped `perth`,
# the venv still had it, PyInstaller froze it, and the engine logged a
# watermark warning at every start (2026-09-07). An exact sync first makes
# the venv equal to the lock, so what is frozen is what is inventoried.
uv sync --frozen

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
  --exclude-module onnxruntime.transformers \
  --exclude-module onnxruntime.quantization \
  --exclude-module onnxruntime.tools \
  --exclude-module pandas \
  --exclude-module numba \
  --exclude-module llvmlite \
  --exclude-module scipy \
  --exclude-module sklearn \
  --exclude-module fastapi \
  --exclude-module starlette \
  --exclude-module uvicorn \
  --exclude-module perth \
  scripts/engine_entry.py

mkdir -p "$(dirname "$out")"
mv dist/readease-engine "$out"

# Smoke: the frozen engine must start and answer. An excluded module only
# fails HERE - the venv suite imports everything happily. PIL was excluded
# (mirroring the old Nuitka list) the day covers.py started needing it, and
# the frozen engine died at import while 733 tests stayed green (2026-09-02).
smoke_home="$(mktemp -d)"
if ! printf '{"id":1,"method":"ping","params":{}}\n' \
    | HOME="$smoke_home" "$out/readease-engine" 2>"$smoke_home/stderr" \
    | head -1 | grep -q '"ok": true'; then
  echo "SIDECAR_SMOKE_FAILED - frozen engine did not answer ping:" >&2
  tail -5 "$smoke_home/stderr" >&2
  exit 1
fi
rm -rf "$smoke_home"
echo "SIDECAR_BUILT $(du -sh "$out" | cut -f1) (smoke: ping ok)"
