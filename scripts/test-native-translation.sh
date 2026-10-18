#!/bin/bash
# No window, user text or downloads. --apple explicitly exercises installed
# Apple packs with two public sample sentences; --fixture uses a test server.
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
test_root="$(mktemp -d -t readease-translation-test)"
trap 'rm -f -- "$test_root/TranslationTests"; rmdir "$test_root"' EXIT
xcrun swiftc -parse-as-library -target arm64-apple-macosx15.0 \
  "$project_root/native/macos/Translation.swift" "$project_root/native/macos/TranslationTests.swift" \
  -o "$test_root/TranslationTests"
if [[ " $* " == *" --fixture "* ]]; then
  python3 "$project_root/tests/native/translation_fixture.py" "$test_root/TranslationTests" "$@"
else
  "$test_root/TranslationTests" "$@"
fi
