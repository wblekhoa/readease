#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
bundle="$project_root/dist/ReadEase.app"
install_root="${READEASE_INSTALL_ROOT:-$HOME/Applications}"
target="$install_root/ReadEase.app"
legacy_target="$install_root/VieNeu Reader.app"

"$project_root/scripts/verify-app.sh" "$bundle"
mkdir -p "$install_root"

rollback_root="$(mktemp -d "$install_root/.readease-install-rollback.XXXXXX")"
previous_target="$rollback_root/ReadEase.app"
previous_legacy_target="$rollback_root/VieNeu Reader.app"
target_moved=0
legacy_target_moved=0
new_target_written=0

cleanup_install() {
  local status=$?
  trap - EXIT

  if [[ "$status" -ne 0 ]]; then
    if [[ "$new_target_written" == 1 && -e "$target" ]]; then
      mv "$target" "$rollback_root/failed-ReadEase.app"
    fi
    if [[ "$target_moved" == 1 && -d "$previous_target" ]]; then
      mv "$previous_target" "$target"
      echo "Restored previous installed app after failed install: $target" >&2
    fi
    if [[ "$legacy_target_moved" == 1 && -d "$previous_legacy_target" ]]; then
      mv "$previous_legacy_target" "$legacy_target"
      echo "Restored legacy app after failed install: $legacy_target" >&2
    fi
  fi

  case "$rollback_root" in
    "$install_root"/.readease-install-rollback.*)
      rm -R -- "$rollback_root"
      ;;
    *)
      echo "INSTALL_CLEANUP_REFUSED: unexpected rollback path $rollback_root" >&2
      exit 1
      ;;
  esac
  exit "$status"
}
trap cleanup_install EXIT

stop_installed_bundle() {
  local candidate="$1"
  local plist="$candidate/Contents/Info.plist"
  local executable executable_name helper pid command
  if [[ ! -f "$plist" ]]; then
    return
  fi
  executable_name="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$plist")"
  executable="$candidate/Contents/MacOS/$executable_name"
  helper="$candidate/Contents/MacOS/ReadEaseSelectionBridge"
  while read -r pid command; do
    if [[ "$command" == "$executable" || "$command" == "$executable "* \
      || "$command" == "$helper" || "$command" == "$helper "* ]]; then
      kill "$pid" 2>/dev/null || true
    fi
  done < <(ps -axo pid=,command=)
  # A Qt app holding a TTS model in memory needs longer than three seconds to
  # exit. Wait properly, then escalate rather than giving up on the install.
  local escalated=0
  for _attempt in $(seq 1 200); do
    if ! ps -axo command= | awk -v executable="$executable" -v helper="$helper" '
      {
        command = $0
        sub(/^[[:space:]]+/, "", command)
        if (command == executable || index(command, executable " ") == 1 ||
            command == helper || index(command, helper " ") == 1) {
          found = 1
        }
      }
      END { exit found ? 0 : 1 }
    '; then
      return
    fi
    if [[ "$_attempt" -eq 100 && "$escalated" -eq 0 ]]; then
      escalated=1
      while read -r pid command; do
        if [[ "$command" == "$executable" || "$command" == "$executable "* \
          || "$command" == "$helper" || "$command" == "$helper "* ]]; then
          kill -9 "$pid" 2>/dev/null || true
        fi
      done < <(ps -axo pid=,command=)
    fi
    sleep 0.1
  done
  echo "INSTALL_APP RED running_bundle=$candidate" >&2
  exit 1
}

stop_installed_bundle "$target"
stop_installed_bundle "$legacy_target"

if [[ -e "$target" ]]; then
  mv "$target" "$previous_target"
  target_moved=1
fi

if [[ -e "$legacy_target" ]]; then
  mv "$legacy_target" "$previous_legacy_target"
  legacy_target_moved=1
fi

new_target_written=1
ditto "$bundle" "$target"
codesign --verify --deep --strict "$target"
open "$target"
echo "INSTALL_APP PASS target=$target"
