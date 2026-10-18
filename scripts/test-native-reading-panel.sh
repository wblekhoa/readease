#!/bin/bash
# Requires a logged-in macOS graphical session; never opens a window.
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
test_root="$(mktemp -d -t readease-reading-panel-test)"
trap 'rm -f -- "$test_root/ReadingPanelTests"; rmdir "$test_root"' EXIT
xcrun --sdk macosx clang -fobjc-arc -fmodules -mmacosx-version-min=15.0 \
  "$project_root/native/macos/ReadingPanelTests.m" \
  -framework Cocoa -framework QuartzCore -o "$test_root/ReadingPanelTests"
"$test_root/ReadingPanelTests"
