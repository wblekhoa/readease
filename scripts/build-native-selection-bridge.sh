#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
bundle="${1:-$project_root/dist/ReadEase.app}"
source_file="$project_root/native/macos/ReadEaseSelectionBridge.m"
native_source="$project_root/native/macos/ReadEaseSelectionNative.m"
output="$bundle/Contents/MacOS/ReadEaseSelectionBridge"
native_output="$bundle/Contents/MacOS/libReadEaseSelectionNative.dylib"

if [[ ! -d "$bundle/Contents/MacOS" ]]; then
  echo "NATIVE_SELECTION_BRIDGE_BUILD RED missing_bundle=$bundle" >&2
  exit 1
fi
if [[ ! -f "$source_file" ]]; then
  echo "NATIVE_SELECTION_BRIDGE_BUILD RED missing_source=$source_file" >&2
  exit 1
fi
if [[ ! -f "$native_source" ]]; then
  echo "NATIVE_SELECTION_BRIDGE_BUILD RED missing_source=$native_source" >&2
  exit 1
fi

xcrun --sdk macosx clang \
  -arch arm64 \
  -dynamiclib \
  -fobjc-arc \
  -fmodules \
  -O2 \
  -mmacosx-version-min=15.0 \
  "$native_source" \
  -framework Cocoa \
  -framework ApplicationServices \
  -framework Carbon \
  -o "$native_output"

xcrun --sdk macosx clang \
  -arch arm64 \
  -fobjc-arc \
  -fmodules \
  -O2 \
  -mmacosx-version-min=15.0 \
  "$source_file" \
  -framework Cocoa \
  -framework ApplicationServices \
  -framework Carbon \
  -o "$output"

codesign --force --sign - "$output"
codesign --force --sign - "$native_output"
file "$output" | grep -q 'arm64'
file "$native_output" | grep -q 'arm64'
codesign --verify --strict "$output"
codesign --verify --strict "$native_output"
echo "NATIVE_SELECTION_BRIDGE_BUILD PASS arch=arm64 signed=2"
