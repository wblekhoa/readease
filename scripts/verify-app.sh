#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

bundle="${1:-$project_root/dist/ReadEase.app}"
if [[ ! -d "$bundle" ]]; then
  echo "BUNDLE_GATE RED missing=$bundle" >&2
  exit 1
fi

QT_QPA_PLATFORM=offscreen uv run scripts/verify.sh
VIENEU_READER_BUNDLE_TEST=1 VIENEU_READER_BUNDLE_PATH="$bundle" \
  uv run python -m unittest tests.packaging.test_bundle_contract -v
uv run --frozen python "$project_root/scripts/audit-macos-compatibility.py" "$bundle"

plist="$bundle/Contents/Info.plist"
executable_name="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$plist")"
executable="$bundle/Contents/MacOS/$executable_name"
temp_root="${TMPDIR:-/tmp}"
temp_root="${temp_root%/}"
data_root="$(mktemp -d -t vieneu-reader-bundle-smoke)"
crash_marker="$(mktemp -t vieneu-reader-crash-marker)"

VIENEU_READER_DATA_ROOT="$data_root" \
VIENEU_READER_SMOKE_QUIT_MS=1500 \
"$executable" >/tmp/vieneu-reader-bundle-smoke.log 2>&1 &
app_pid=$!

cleanup_smoke() {
  local exit_code=$?
  trap - EXIT
  if [[ -n "${app_pid:-}" ]] && kill -0 "$app_pid" 2>/dev/null; then
    kill "$app_pid"
    wait "$app_pid" || true
  fi
  case "$data_root" in
    "$temp_root"/vieneu-reader-bundle-smoke.*)
      rm -R -- "$data_root" || exit_code=1
      ;;
    *)
      echo "BUNDLE_GATE RED refused temp cleanup: $data_root" >&2
      exit_code=1
      ;;
  esac
  case "$crash_marker" in
    "$temp_root"/vieneu-reader-crash-marker.*)
      rm -f -- "$crash_marker" || exit_code=1
      ;;
    *)
      echo "BUNDLE_GATE RED refused marker cleanup: $crash_marker" >&2
      exit_code=1
      ;;
  esac
  exit "$exit_code"
}
trap cleanup_smoke EXIT

sleep 0.3
if ! kill -0 "$app_pid" 2>/dev/null; then
  wait "$app_pid"
  echo "BUNDLE_GATE RED app exited before readiness probe" >&2
  exit 1
fi

listeners="$(lsof -Pan -p "$app_pid" -iTCP -sTCP:LISTEN 2>/dev/null || true)"
if [[ -n "$listeners" ]]; then
  echo "BUNDLE_GATE RED unexpected listening socket" >&2
  echo "$listeners" >&2
  exit 1
fi

wait "$app_pid"
app_pid=""

new_reports="$(find "$HOME/Library/Logs/DiagnosticReports" -maxdepth 1 \( -name 'ReadEase-*.ips' -o -name 'VieNeu Reader-*.ips' \) -newer "$crash_marker" -print 2>/dev/null || true)"
if [[ -n "$new_reports" ]]; then
  echo "BUNDLE_GATE RED crash report created" >&2
  echo "$new_reports" >&2
  exit 1
fi

echo "BUNDLE_GATE PASS arch=arm64 signed=1 listener=0 launch=1"
