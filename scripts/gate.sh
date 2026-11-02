#!/bin/bash
# ReadEase gate, run by the maintainer's shared git hooks: pre-commit calls it with --fast, pre-push without.
# --fast (pre-commit): app UI tests, UI and mock audits, TypeScript check.
# full (pre-push): the same, then scripts/verify.sh (Python unit tests, native selection bridge, Rust tests, compileall).
set -euo pipefail
cd "$(dirname "$0")/.."
(cd app && npm run -s test:ui && npm run -s audit:ui && npm run -s audit:mock && npx tsc --noEmit -p .)
if [ "${1:-}" = --fast ]; then exit 0; fi
# The Tauri build script needs the built engine/ and translator/ resources (gitignored): borrow the checkout's copies.
# Cargo output goes to one shared cache so each push builds incrementally instead of from scratch.
repo="${JAK_GATE_REPO:-$PWD}"
for res in engine translator; do
  if [ ! -e "app/src-tauri/$res" ] && [ -d "$repo/app/src-tauri/$res" ]; then ln -s "$repo/app/src-tauri/$res" "app/src-tauri/$res"; fi
done
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$HOME/.cache/jak-gate/readease-target}" UV_NO_SYNC=1
exec ./scripts/verify.sh
