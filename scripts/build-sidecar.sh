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
