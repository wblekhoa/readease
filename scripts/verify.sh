#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

export PYTHONPATH="$project_root/src"
# The installer asks for one line per test, so a watcher can see which one is
# running. Everything else keeps the quiet output.
verbosity="${READEASE_UNITTEST_FLAG:--q}"
echo "VERIFY phase=unit-tests"
uv run --frozen python \
  -W error \
  -m unittest discover -s tests "$verbosity"
echo "VERIFY phase=headless-reader-smoke"
QT_QPA_PLATFORM=offscreen uv run --frozen python tests/ui/headless_reader_smoke.py
echo "VERIFY phase=native-selection-bridge"
"$project_root/scripts/test-native-selection-bridge.sh"
# The shell's own tests. Rust had none until 05/09; now the playback
# receipts live there (engine.rs `mod tests`), and a test nothing runs is a
# claim nobody checks. A Mac without cargo says so out loud instead of
# quietly passing: contributors have cargo, end users never run this file.
echo "VERIFY phase=rust-tests"
if command -v cargo >/dev/null 2>&1; then
  # `--lib` only: the tests live in the library crate, and a `tail` over both
  # binaries reported the EMPTY main.rs summary ("0 passed") as the result.
  (cd app/src-tauri && cargo test --offline --lib 2>&1 | grep -E "^test result|FAILED|panicked at")
else
  echo "VERIFY phase=rust-tests SKIPPED: cargo not installed (Rust receipts not run)"
fi
echo "VERIFY phase=compileall"
uv run --frozen python -m compileall -q src tests
if command -v git >/dev/null 2>&1 \
  && git -C "$project_root" rev-parse --is-inside-work-tree >/dev/null 2>&1
then
  git -C "$project_root" diff --check
fi
