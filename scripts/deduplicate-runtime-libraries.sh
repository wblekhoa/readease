#!/bin/bash
set -euo pipefail

# Drop the ONNX Runtime dylib that the finished bundle never links.

project_root="$(cd "$(dirname "$0")/.." && pwd)"
bundle="${1:-$project_root/dist/ReadEase.app}"

# Two layouts, one rule. Nuitka put the collected libraries beside the
# executable; the Tauri shell ships the engine as a PyInstaller sidecar, which
# keeps them under the onnxruntime package it froze. Measured on the Tauri
# bundle 2026-09-04: a real `read` through the frozen engine produced the same
# 3 audio chunks and the same ok:true with the 32 MB dylib DELETED as with it
# present - so it is dead weight in this layout too, not merely unlinked.
macos="$bundle/Contents/MacOS"
if [[ ! -e "$macos/libonnxruntime.1.dylib" ]]; then
  sidecar="$bundle/Contents/Resources/engine/_internal/onnxruntime/capi"
  if [[ -d "$sidecar" ]]; then macos="$sidecar"; fi
fi
compatibility_name="$macos/libonnxruntime.1.dylib"
versioned_library=""
versioned_count=0

for candidate in "$macos"/libonnxruntime.*.dylib; do
  if [[ ! -e "$candidate" || "$candidate" == "$compatibility_name" ]]; then
    continue
  fi
  versioned_library="$candidate"
  versioned_count=$((versioned_count + 1))
done

if [[ "$versioned_count" -eq 0 && ! -e "$compatibility_name" ]]; then
  # Already dropped by an earlier run over the same bundle. Saying so beats
  # failing a release for work that is done.
  echo "RUNTIME_DEDUP PASS removed=none (already dropped)"
  exit 0
fi

if [[ "$versioned_count" -ne 1 || ! -f "$versioned_library" ]]; then
  echo "RUNTIME_DEDUP RED expected_one_versioned_onnxruntime count=$versioned_count" >&2
  exit 1
fi

# ONNX Runtime 1.29 ships a self-contained onnxruntime_pybind11_state.so, so the
# only Mach-O in the bundle that names libonnxruntime is the dylib itself. The
# 33 MB library and its compatibility alias are dead weight the friend would
# download for nothing. Nuitka 4.1.1 still resolves the install name while it
# collects native libraries, so both files have to survive the build and can
# only be dropped here, once the bundle exists. The gated bundle contract
# re-proves the linkage claim after every build, so a future ONNX Runtime that
# does link the dylib fails that gate instead of shipping a bundle that cannot
# load its own speech backend.
removed="$(basename "$versioned_library"),$(basename "$compatibility_name")"
rm -f -- "$compatibility_name"
rm -f -- "$versioned_library"

echo "RUNTIME_DEDUP PASS removed=$removed"
