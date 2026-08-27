#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

export PYTHONPATH="$project_root/src"
exec uv run python tests/ui/real_book_smoke.py "$@"
