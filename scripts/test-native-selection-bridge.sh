#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
source_file="$project_root/native/macos/ReadEaseSelectionBridge.m"
native_file="$project_root/native/macos/ReadEaseSelectionNative.m"
test_file="$project_root/native/macos/SelectionBridgeTests.m"

if [[ ! -f "$source_file" ]]; then
  echo "NATIVE_SELECTION_BRIDGE_TEST RED missing_source=$source_file" >&2
  exit 1
fi
if [[ ! -f "$native_file" ]]; then
  echo "NATIVE_SELECTION_BRIDGE_TEST RED missing_source=$native_file" >&2
  exit 1
fi

test_root="$(mktemp -d -t readease-native-selection-test)"
cleanup() {
  rm -f -- "$test_root/SelectionBridgeTests"
  rm -f -- "$test_root/ReadEaseSelectionBridge"
  rm -f -- "$test_root/libReadEaseSelectionNative.dylib"
  rmdir "$test_root"
}
trap cleanup EXIT

xcrun --sdk macosx clang \
  -dynamiclib \
  -fobjc-arc \
  -fmodules \
  -mmacosx-version-min=15.0 \
  "$native_file" \
  -framework Cocoa \
  -framework ApplicationServices \
  -framework Carbon \
  -o "$test_root/libReadEaseSelectionNative.dylib"

xcrun --sdk macosx clang \
  -fobjc-arc \
  -fmodules \
  -mmacosx-version-min=15.0 \
  "$source_file" \
  -framework Cocoa \
  -framework ApplicationServices \
  -framework Carbon \
  -o "$test_root/ReadEaseSelectionBridge"

xcrun --sdk macosx clang \
  -fobjc-arc \
  -fmodules \
  -mmacosx-version-min=15.0 \
  -I "$project_root/native/macos" \
  "$test_file" \
  -framework Cocoa \
  -framework ApplicationServices \
  -framework Carbon \
  -o "$test_root/SelectionBridgeTests"

"$test_root/SelectionBridgeTests"
