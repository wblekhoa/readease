#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-run}"
APP_NAME="ReadEase"
BUNDLE_ID="vn.dolenglish.vieneureader"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_BUNDLE="$ROOT_DIR/dist/$APP_NAME.app"

bundle_executable() {
  local plist="$APP_BUNDLE/Contents/Info.plist"
  local executable_name
  executable_name="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$plist")"
  printf '%s\n' "$APP_BUNDLE/Contents/MacOS/$executable_name"
}

matching_bundle_pids() {
  local executable="$1"
  local pid command
  while read -r pid command; do
    if [[ "$command" == "$executable" || "$command" == "$executable "* ]]; then
      printf '%s\n' "$pid"
    fi
  done < <(ps -axo pid=,command=)
}

stop_existing_bundle() {
  if [[ ! -d "$APP_BUNDLE" ]]; then
    return
  fi
  local executable pid
  executable="$(bundle_executable)"
  while read -r pid; do
    [[ -n "$pid" ]] && kill "$pid"
  done < <(matching_bundle_pids "$executable")
}

open_app() {
  /usr/bin/open -n "$APP_BUNDLE"
}

stop_existing_bundle
"$ROOT_DIR/scripts/build-app.sh"
"$ROOT_DIR/scripts/verify-app.sh" "$APP_BUNDLE"

APP_EXECUTABLE="$(bundle_executable)"
PROCESS_NAME="$(basename "$APP_EXECUTABLE")"

case "$MODE" in
  run)
    open_app
    ;;
  --debug|debug)
    lldb -- "$APP_EXECUTABLE"
    ;;
  --logs|logs)
    open_app
    /usr/bin/log stream --info --style compact --predicate "process == \"$PROCESS_NAME\""
    ;;
  --telemetry|telemetry)
    open_app
    /usr/bin/log stream --info --style compact --predicate "subsystem == \"$BUNDLE_ID\""
    ;;
  --verify|verify)
    open_app
    sleep 2
    if [[ -z "$(matching_bundle_pids "$APP_EXECUTABLE")" ]]; then
      echo "RUN_VERIFY RED process_not_found=$APP_EXECUTABLE" >&2
      exit 1
    fi
    echo "RUN_VERIFY PASS app=$APP_NAME bundle_id=$BUNDLE_ID"
    ;;
  *)
    echo "usage: $0 [run|--debug|--logs|--telemetry|--verify]" >&2
    exit 2
    ;;
esac
