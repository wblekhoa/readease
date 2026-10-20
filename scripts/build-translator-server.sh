#!/bin/bash
# Build the translator's server (RE-PLAY-031): llama.cpp's `llama-server`,
# one static arm64 executable with its Metal shaders embedded, bundled as the
# `translator` resource. The host starts it on 127.0.0.1 with the model the
# engine downloaded, only while translations are coming.
#
# Pinned to one llama.cpp commit (MIT). Built without OpenSSL - it serves
# loopback HTTP only and must not link Homebrew's libssl, which a reader's
# Mac does not have - and without libcurl, so it can never fetch a model
# itself. Every model it reads arrives through the engine's checked download.
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
revision="a01ce9ffc64cf370439d6f861a534a65100133ae"
work="$project_root/build/llama.cpp"
out="$project_root/app/src-tauri/translator"

if [[ ! -d "$work/.git" ]]; then
  git clone --quiet https://github.com/ggml-org/llama.cpp "$work"
fi
git -C "$work" fetch --quiet --depth 1 origin "$revision"
git -C "$work" checkout --quiet --detach "$revision"

export MACOSX_DEPLOYMENT_TARGET=15.0
cmake -S "$work" -B "$work/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DBUILD_SHARED_LIBS=OFF \
  -DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON \
  -DLLAMA_OPENSSL=OFF -DLLAMA_CURL=OFF \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF >/dev/null
cmake --build "$work/build" -j "$(sysctl -n hw.ncpu)" --target llama-server >/dev/null

binary="$work/build/bin/llama-server"
# Only the system's own libraries may be linked: anything under /opt or
# /usr/local would be missing on the reader's Mac.
if otool -L "$binary" | tail -n +2 | grep -Ev '^\s+(/System/Library/|/usr/lib/)'; then
  echo "BUILD_FAILED: llama-server links a library outside macOS" >&2
  exit 1
fi
mkdir -p "$out"
cp "$binary" "$out/llama-server"
cp "$work/LICENSE" "$out/LICENSE-llama.cpp"
echo "translator server: $(du -h "$out/llama-server" | cut -f1) at $revision"
