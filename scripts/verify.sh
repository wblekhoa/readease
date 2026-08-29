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
echo "VERIFY phase=compileall"
uv run --frozen python -m compileall -q src tests
if command -v git >/dev/null 2>&1 \
  && git -C "$project_root" rev-parse --is-inside-work-tree >/dev/null 2>&1
then
  git -C "$project_root" diff --check
fi
