#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

export PYTHONPATH="$project_root/src"
uv run --frozen python \
  -W error \
  -m unittest discover -s tests -q
QT_QPA_PLATFORM=offscreen uv run --frozen python tests/ui/headless_reader_smoke.py
"$project_root/scripts/test-native-selection-bridge.sh"
uv run --frozen python -m compileall -q src tests
if command -v git >/dev/null 2>&1 \
  && git -C "$project_root" rev-parse --is-inside-work-tree >/dev/null 2>&1
then
  git -C "$project_root" diff --check
fi
