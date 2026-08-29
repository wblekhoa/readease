#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
mode="${1:-install}"

MIN_MACOS_MAJOR=15
MIN_FREE_KIB=$((6 * 1024 * 1024))
UV_VERSION="0.9.13"
UV_ARCHIVE="uv-aarch64-apple-darwin.tar.gz"
UV_ARCHIVE_SHA256="9c594dce1c237e11680be2b6d1331448eeb6f8a1453fb851a66a40291bb624de"
# Long enough for a person to find the window, click through and let it download.
XCODE_WAIT_SECONDS=1800
UV_URL="https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$UV_ARCHIVE"

fail() {
  local reason="$1"
  shift
  printf 'READEASE_SOURCE_INSTALL RED reason=%s %s\n' "$reason" "$*" >&2
  exit 1
}

TOTAL_STEPS=5

step() {
  printf 'READEASE_STEP %s/%s %s\n' "$1" "$TOTAL_STEPS" "$2"
  local filled="" empty="" index
  for index in $(seq 1 "$TOTAL_STEPS"); do
    if [[ "$index" -le "$1" ]]; then filled+="#"; else empty+="."; fi
  done
  printf '\n  [%s%s]  step %s of %s\n' "$filled" "$empty" "$1" "$TOTAL_STEPS"
}

# Only ask when a person is actually watching. A double-click gets a terminal;
# an AI assistant, a pipe, or CI does not, and a prompt there would hang forever.
INTERACTIVE=0

ask() {
  local question="$1" default="$2" answer hint
  if [[ "$INTERACTIVE" -eq 0 ]]; then
    printf '  %s -> %s (non-interactive)\n' "$question" "$default"
    [[ "$default" == "y" ]]
    return
  fi
  hint="[Y/n]"
  [[ "$default" == "n" ]] && hint="[y/N]"
  printf '  %s %s ' "$question" "$hint"
  read -r answer || answer=""
  answer="${answer:-$default}"
  case "$answer" in
    [yY]*) return 0 ;;
    *) return 1 ;;
  esac
}

elapsed_label() {
  printf '%d:%02d' "$(( $1 / 60 ))" "$(( $1 % 60 ))"
}

# The two long steps used to print nothing at all. A terminal that sits silent
# for five minutes reads as a hang, not as work - so keep the full output in a
# log, show a clock and the latest line, and print the log if the step fails.
run_watched() {
  local label="$1" log="$2" limit="$3"
  shift 3
  # A step that cannot finish must not wait forever in silence: that is
  # exactly how an install appears to freeze with nothing to act on.
  limit="${READEASE_STEP_TIMEOUT:-$limit}"
  local worker start waited status=0 spin=0 tail_line last_report=0
  local frames='|/-\'

  "$@" >"$log" 2>&1 &
  worker=$!
  trap 'kill "$worker" 2>/dev/null || true' INT TERM
  start="$(date +%s)"

  while kill -0 "$worker" 2>/dev/null; do
    waited=$(( $(date +%s) - start ))
    if [[ "$waited" -ge "$limit" ]]; then
      kill "$worker" 2>/dev/null || true
      sleep 2
      kill -9 "$worker" 2>/dev/null || true
      wait "$worker" 2>/dev/null || true
      trap - INT TERM
      [[ "$INTERACTIVE" -eq 1 ]] && printf '\r%*s\r' 80 ''
      printf '  x  %s gave up after %s\n' "$label" "$(elapsed_label "$waited")" >&2
      printf '  This step is not allowed to run longer than that.\n' >&2
      printf '  Last 40 lines (full output: %s):\n' "$log" >&2
      tail -n 40 "$log" >&2 || true
      return 124
    fi
    if [[ "$INTERACTIVE" -eq 1 ]]; then
      tail_line="$(tail -n 1 "$log" 2>/dev/null | tr -d '\r' | cut -c1-46)"
      printf '\r  %s  %s  %s  %-46s' \
        "${frames:$spin:1}" "$(elapsed_label "$waited")" "$label" "$tail_line"
      spin=$(( (spin + 1) % 4 ))
      sleep 0.5
    else
      # No terminal to redraw: a periodic line still proves it is alive.
      if [[ $(( waited - last_report )) -ge 30 ]]; then
        last_report="$waited"
        printf '  ... %s still running, %s elapsed\n' "$label" "$(elapsed_label "$waited")"
      fi
      sleep 1
    fi
  done

  wait "$worker" || status=$?
  trap - INT TERM
  waited=$(( $(date +%s) - start ))

  if [[ "$INTERACTIVE" -eq 1 ]]; then
    printf '\r%*s\r' 80 ''
  fi
  if [[ "$status" -ne 0 ]]; then
    printf '  x  %s failed after %s\n' "$label" "$(elapsed_label "$waited")" >&2
    printf '  Last 40 lines (full output: %s):\n' "$log" >&2
    tail -n 40 "$log" >&2 || true
    return "$status"
  fi
  printf '  ok  %s  (%s)\n' "$label" "$(elapsed_label "$waited")"
  # The receipts each stage prints are the record that it really ran. The log
  # they were captured into is deleted on success, so keep them on screen.
  grep -E '^[A-Z][A-Z_]+ (PASS|phase=)' "$log" 2>/dev/null \
    | sed 's/^/     /' || true
}

human_kib() {
  local kib="$1"
  if [[ "$kib" -ge 1048576 ]]; then
    printf '%s GB' "$((kib / 1048576))"
  else
    printf '%s MB' "$((kib / 1024))"
  fi
}

if [[ "$#" -gt 1 ]]; then
  fail "invalid_arguments" "Only --check or no argument is supported."
fi
case "$mode" in
  install|--check) ;;
  *) fail "invalid_arguments" "Usage: ./Install ReadEase.command [--check]" ;;
esac

step 1 "Checking this Mac and the source"

for required_file in \
  "$project_root/pyproject.toml" \
  "$project_root/uv.lock" \
  "$project_root/scripts/export-public-source.py" \
  "$project_root/scripts/build-app.sh" \
  "$project_root/scripts/install-app.sh"
do
  [[ -f "$required_file" ]] || fail "incomplete_source" "Missing file: $required_file"
done

if [[ -t 0 && "$mode" != "--check" && "${READEASE_ASSUME_YES:-}" != "1" ]]; then
  INTERACTIVE=1
fi

temp_root_probe="${TMPDIR:-/tmp}"
temp_root_probe="${temp_root_probe%/}"

system_name="$(uname -s)"
[[ "$system_name" == "Darwin" ]] || fail "unsupported_system" "ReadEase supports macOS only."

architecture="$(uname -m)"
[[ "$architecture" == "arm64" ]] || fail \
  "unsupported_arch" \
  "An Apple Silicon Mac (M1 or newer) is required; this Mac reports $architecture."

macos_version="$(sw_vers -productVersion)"
macos_major="${macos_version%%.*}"
case "$macos_major" in
  ''|*[!0-9]*) fail "unknown_macos" "Could not read the macOS version: $macos_version" ;;
esac
[[ "$macos_major" -ge "$MIN_MACOS_MAJOR" ]] || fail \
  "unsupported_macos" \
  "macOS $MIN_MACOS_MAJOR or newer is required; this Mac runs $macos_version."

for tool in curl tar shasum mktemp ditto; do
  command -v "$tool" >/dev/null 2>&1 || fail "missing_system_tool" "$tool was not found."
done
xcode_tools_present() {
  xcrun --find clang >/dev/null 2>&1 \
    && xcrun --sdk macosx --show-sdk-path >/dev/null 2>&1
}
needs_xcode_tools=0
xcode_tools_present || needs_xcode_tools=1
[[ -x /usr/bin/codesign ]] || fail "missing_system_tool" "codesign was not found."
[[ -x /usr/libexec/PlistBuddy ]] || fail "missing_system_tool" "PlistBuddy was not found."

available_kib="$(df -Pk "$project_root" | awk 'NR == 2 { print $4 }')"
case "$available_kib" in
  ''|*[!0-9]*) fail "unknown_disk" "Could not read the free disk space." ;;
esac
[[ "$available_kib" -ge "$MIN_FREE_KIB" ]] || fail \
  "insufficient_disk" \
  "At least 6 GB of free space is needed during the build; about $((available_kib / 1024 / 1024)) GB is free."

# Everything the run will do is collected first and shown once, so nobody has
# to answer questions one at a time while watching a 20-minute build.
plan_install=()
plan_replace=()
plan_close=()
plan_clean=()
plan_keep=()
needs_quarantine_clear=0
remove_stale=0

install_root="${READEASE_INSTALL_ROOT:-$HOME/Applications}"
if [[ -d "$install_root" ]]; then
  [[ -w "$install_root" ]] || fail "install_not_writable" "Cannot write to $install_root."
else
  [[ -w "$HOME" ]] || fail "install_not_writable" "Cannot create $install_root."
fi

# What is already on this machine, so nobody has to guess what will change.
installed_app="$install_root/ReadEase.app"
legacy_app="$install_root/VieNeu Reader.app"
if [[ -d "$installed_app" ]]; then
  installed_version="$(/usr/libexec/PlistBuddy \
    -c 'Print :CFBundleShortVersionString' \
    "$installed_app/Contents/Info.plist" 2>/dev/null || true)"
  [[ -n "$installed_version" ]] || installed_version="unreadable"
  printf 'READEASE_EXISTING installed version=%s\n' "$installed_version"
  plan_replace+=("ReadEase $installed_version in $install_root - the new build replaces it, and the current one is kept until the new install succeeds")
else
  printf 'READEASE_EXISTING none\n'
  plan_install+=("ReadEase.app into $install_root - first install on this Mac")
fi

# A running app cannot have its bundle replaced. Catching that here costs five
# seconds; catching it in install-app.sh costs the whole 20-minute build and
# leaves a multi-gigabyte workspace behind.
running_app_pids() {
  ps -axo pid=,command= 2>/dev/null \
    | grep -F "$installed_app/Contents/MacOS/" \
    | grep -v grep \
    | awk '$1 ~ /^[0-9]+$/ { print $1 }' || true
}

close_running_app() {
  local signal attempt pids
  for signal in TERM KILL; do
    pids="$(running_app_pids)"
    [[ -z "$pids" ]] && return 0
    # shellcheck disable=SC2086
    kill -"$signal" $pids 2>/dev/null || true
    for attempt in $(seq 1 50); do
      [[ -z "$(running_app_pids)" ]] && return 0
      sleep 0.1
    done
  done
  [[ -z "$(running_app_pids)" ]]
}

needs_app_close=0
if [[ -n "$(running_app_pids)" ]]; then
  printf 'READEASE_RUNNING present\n'
  needs_app_close=1
  plan_close+=("ReadEase, which is running now - its bundle cannot be replaced while open")
else
  printf 'READEASE_RUNNING none\n'
fi

if [[ -d "$legacy_app" ]]; then
  printf 'READEASE_LEGACY present\n'
  plan_clean+=("the older bundle named \"VieNeu Reader\" - removed only after the new install succeeds")
fi

# Gatekeeper quarantine: set when the source arrived as a browser download.
# It does not block this script (Terminal execution is unaffected), but it is
# exactly what blocks double-clicking "Install ReadEase.command" in Finder.
if xattr -p com.apple.quarantine "$project_root" >/dev/null 2>&1 \
  || xattr -p com.apple.quarantine "$project_root/Install ReadEase.command" >/dev/null 2>&1
then
  printf 'READEASE_QUARANTINE present\n'
  if [[ "$mode" == "--check" ]]; then
    plan_keep+=("the Gatekeeper download flag on this source folder - a real run clears it; to do it yourself:  xattr -d com.apple.quarantine $(printf '%q' "$project_root")  (or use git clone, which is never flagged)")
  else
    needs_quarantine_clear=1
    plan_clean+=("the Gatekeeper download flag on this source folder, so Finder can open it next time")
  fi
else
  printf 'READEASE_QUARANTINE none\n'
fi

# A failed build deliberately keeps its workspace. Report it always; remove it
# only when a person in front of a terminal says so.
stale_dirs=()
stale_total_kib=0
for stale_dir in "$temp_root_probe"/readease-source-install.*; do
  [[ -d "$stale_dir" ]] || continue
  stale_dirs+=("$stale_dir")
  stale_kib="$(du -sk "$stale_dir" 2>/dev/null | awk '{ print $1 }')"
  stale_total_kib=$((stale_total_kib + ${stale_kib:-0}))
done
if [[ "${#stale_dirs[@]}" -gt 0 ]]; then
  printf 'READEASE_STALE_BUILD count=%s size_kib=%s\n' "${#stale_dirs[@]}" "$stale_total_kib"
  if [[ "$INTERACTIVE" -eq 1 ]]; then
    remove_stale=1
    plan_clean+=("${#stale_dirs[@]} leftover build workspace(s) from a failed install, about $(human_kib "$stale_total_kib")")
  else
    # Only a person may throw away the evidence of a failed build.
    plan_keep+=("${#stale_dirs[@]} leftover build workspace(s), about $(human_kib "$stale_total_kib") - remove them yourself with:  rm -R $temp_root_probe/readease-source-install.*")
  fi
fi

existing_uv=""
if [[ -n "${READEASE_UV_BIN:-}" && -x "${READEASE_UV_BIN}" ]]; then
  explicit_uv_version="$("$READEASE_UV_BIN" --version 2>/dev/null | awk '{ print $2 }' || true)"
  [[ "$explicit_uv_version" == "$UV_VERSION" ]] || fail \
    "uv_version_mismatch" \
    "READEASE_UV_BIN must point at uv $UV_VERSION."
  existing_uv="$READEASE_UV_BIN"
elif command -v uv >/dev/null 2>&1; then
  candidate_uv="$(command -v uv)"
  candidate_uv_version="$("$candidate_uv" --version 2>/dev/null | awk '{ print $2 }' || true)"
  if [[ "$candidate_uv_version" == "$UV_VERSION" ]]; then
    existing_uv="$candidate_uv"
  fi
fi

if [[ -z "$existing_uv" ]]; then
  plan_install+=("uv $UV_VERSION and Python 3.13, checksum-pinned, into a temporary build folder that is deleted afterwards")
else
  plan_install+=("Python 3.13 into a temporary build folder that is deleted afterwards (uv $UV_VERSION is already here)")
fi
if [[ "$needs_xcode_tools" -eq 1 ]]; then
  # First in the list: it is the only entry that installs into the system
  # itself, and the only one where Apple, not this script, does the installing.
  plan_install=("Apple's Xcode Command Line Tools - Apple's own installer window opens; needed to compile the app" "${plan_install[@]}")
fi

show_plan() {
  local entry
  printf '\n'
  printf 'READEASE_PLAN entries=%s\n' \
    "$(( ${#plan_install[@]} + ${#plan_replace[@]} + ${#plan_close[@]} + ${#plan_clean[@]} ))"
  printf '  ┌─ What this will do ─────────────────────────────────────────\n'
  if [[ "${#plan_install[@]}" -gt 0 ]]; then
    printf '  │\n  │  INSTALL\n'
    for entry in "${plan_install[@]}"; do printf '  │    + %s\n' "$entry"; done
  fi
  if [[ "${#plan_replace[@]}" -gt 0 ]]; then
    printf '  │\n  │  REPLACE\n'
    for entry in "${plan_replace[@]}"; do printf '  │    ~ %s\n' "$entry"; done
  fi
  if [[ "${#plan_close[@]}" -gt 0 ]]; then
    printf '  │\n  │  CLOSE\n'
    for entry in "${plan_close[@]}"; do printf '  │    x %s\n' "$entry"; done
  fi
  if [[ "${#plan_clean[@]}" -gt 0 ]]; then
    printf '  │\n  │  REMOVE\n'
    for entry in "${plan_clean[@]}"; do printf '  │    - %s\n' "$entry"; done
  fi
  if [[ "${#plan_keep[@]}" -gt 0 ]]; then
    printf '  │\n  │  LEFT ALONE\n'
    for entry in "${plan_keep[@]}"; do printf '  │    = %s\n' "$entry"; done
  fi
  printf '  │\n  │  NEVER TOUCHED\n'
  printf '  │    . sudo, your password, your shell profile\n'
  printf '  │    . your books, reading progress and downloaded voices\n'
  printf '  │\n  │  About 15-30 minutes. Nothing is asked after you say yes.\n'
  printf '  └─────────────────────────────────────────────────────────────\n\n'
}

if [[ "$mode" == "--check" ]]; then
  uv_status="pinned-download"
  [[ -n "$existing_uv" ]] && uv_status="available"
  xcode_status="ready"
  [[ "$needs_xcode_tools" -eq 1 ]] && xcode_status="will-be-installed"
  show_plan
  printf 'READEASE_PREFLIGHT PASS arch=%s macos=%s free_gib=%s uv=%s xcode=%s\n' \
    "$architecture" \
    "$macos_version" \
    "$((available_kib / 1024 / 1024))" \
    "$uv_status" \
    "$xcode_status"
  exit 0
fi

show_plan
if ! ask "Go ahead?" y; then
  printf 'READEASE_SOURCE_INSTALL CANCELLED reason=user-declined\n'
  printf '  Nothing was changed.\n'
  exit 0
fi

# From here on the run is unattended. Every branch below was listed above.
if [[ "$needs_xcode_tools" -eq 1 ]]; then
  if [[ "$INTERACTIVE" -eq 0 ]]; then
    # The Apple installer needs a person to click through it; a pipe or CI cannot.
    fail \
      "missing_xcode_tools" \
      "Run 'xcode-select --install', finish the Apple installer window, then try again."
  fi
  printf 'READEASE_XCODE_TOOLS installing\n'
  printf '  Opening the Apple installer. Click Install and accept the licence;\n'
  printf '  this waits for it to finish.\n'
  xcode-select --install >/dev/null 2>&1 || true
  xcode_waited=0
  while ! xcode_tools_present; do
    if [[ "$xcode_waited" -ge "$XCODE_WAIT_SECONDS" ]]; then
      printf '\n'
      fail \
        "missing_xcode_tools" \
        "Apple's tools were still missing after $((XCODE_WAIT_SECONDS / 60)) minutes. Finish 'xcode-select --install', then run this again."
    fi
    printf '\r  waiting for the Apple installer ... %s' "$(elapsed_label "$xcode_waited")"
    sleep 5
    xcode_waited=$((xcode_waited + 5))
  done
  printf '\r  The Apple tools are ready.%*s\n' 30 ''
  printf 'READEASE_XCODE_TOOLS ready\n'
fi

if [[ "$needs_app_close" -eq 1 ]]; then
  if close_running_app; then
    printf 'READEASE_RUNNING closed\n'
  else
    fail "app_still_running" "ReadEase would not close. Quit it manually and run this again."
  fi
fi

if [[ "$needs_quarantine_clear" -eq 1 ]]; then
  if xattr -d -r com.apple.quarantine "$project_root" 2>/dev/null; then
    printf 'READEASE_QUARANTINE cleared\n'
  else
    printf '  Could not clear the Gatekeeper flag. To do it yourself:\n'
    printf '    xattr -d -r com.apple.quarantine %s\n' "$(printf '%q' "$project_root")"
  fi
fi

if [[ "$remove_stale" -eq 1 && "${#stale_dirs[@]}" -gt 0 ]]; then
  stale_removed=0
  for stale_dir in "${stale_dirs[@]}"; do
    case "$stale_dir" in
      "$temp_root_probe"/readease-source-install.*)
        rm -R -- "$stale_dir" && stale_removed=$((stale_removed + 1))
        ;;
    esac
  done
  printf 'READEASE_STALE_BUILD removed=%s\n' "$stale_removed"
fi

step 2 "Preparing the pinned build tool (uv $UV_VERSION)"

temp_root="$temp_root_probe"
work_root="$(mktemp -d "$temp_root/readease-source-install.XXXXXX")"
completed=0

cleanup_work_root() {
  local status=$?
  trap - EXIT
  if [[ "$completed" -eq 1 && "$status" -eq 0 ]]; then
    case "$work_root" in
      "$temp_root"/readease-source-install.*)
        rm -R -- "$work_root"
        printf 'READEASE_BUILD_CLEANUP PASS retained=installed-app-only\n'
        ;;
      *)
        printf 'READEASE_BUILD_CLEANUP RED unexpected_path=%s\n' "$work_root" >&2
        exit 1
        ;;
    esac
  else
    local kept_kib
    kept_kib="$(du -sk "$work_root" 2>/dev/null | awk '{ print $1 }')"
    printf 'READEASE_BUILD_PRESERVED path=%s reason=failed-install size_kib=%s\n' \
      "$work_root" "${kept_kib:-0}" >&2
    printf 'The unfinished build workspace was kept for diagnosis (about %s).\n' \
      "$(human_kib "${kept_kib:-0}")" >&2
    printf 'Remove it when you no longer need it:\n    rm -R %s\n' "$work_root" >&2
  fi
  exit "$status"
}
trap cleanup_work_root EXIT

export UV_CACHE_DIR="$work_root/uv-cache"
export UV_PYTHON_INSTALL_DIR="$work_root/uv-python"

uv_bin="$existing_uv"
if [[ -z "$uv_bin" ]]; then
  tool_root="$work_root/tools"
  archive="$tool_root/$UV_ARCHIVE"
  mkdir -p "$tool_root"
  if ! curl \
    --fail \
    --location \
    --proto '=https' \
    --tlsv1.2 \
    --output "$archive" \
    "$UV_URL"
  then
    fail "uv_download_failed" "Could not download the pinned build tool from GitHub."
  fi
  archive_sha256="$(shasum -a 256 "$archive" | awk '{ print $1 }')"
  [[ "$archive_sha256" == "$UV_ARCHIVE_SHA256" ]] || fail \
    "uv_checksum_mismatch" \
    "The download did not match its checksum; stopped before running it."
  tar -xzf "$archive" -C "$tool_root"
  uv_bin="$tool_root/uv-aarch64-apple-darwin/uv"
  [[ -x "$uv_bin" ]] || fail "uv_archive_invalid" "The uv archive did not contain the expected binary."
  installed_uv_version="$("$uv_bin" --version | awk '{ print $2 }')"
  [[ "$installed_uv_version" == "$UV_VERSION" ]] || fail \
    "uv_version_mismatch" \
    "The uv binary is not version $UV_VERSION."
fi

step 3 "Creating a clean source export"

export_root="$work_root/ReadEase-source"
run_watched "exporting a clean copy of the source" "$work_root/export.log" 600 \
  "$uv_bin" run \
  --isolated \
  --no-project \
  --managed-python \
  --python 3.13 \
  python \
  "$project_root/scripts/export-public-source.py" \
  --output "$export_root"

export PATH="$(dirname "$uv_bin"):$PATH"

build_in_export() { ( cd "$export_root" && ./scripts/build-app.sh ); }
install_in_export() { ( cd "$export_root" && ./scripts/install-app.sh ); }

step 4 "Compiling the app - the longest step, usually 10-20 minutes"
run_watched "compiling" "$work_root/build.log" 5400 build_in_export

step 5 "Verifying and installing into $install_root - runs the full test suite, 3-5 minutes"
run_watched "verifying and installing" "$work_root/install.log" 2700 install_in_export

completed=1
printf 'READEASE_SOURCE_INSTALL PASS target=%s/ReadEase.app\n' "$install_root"
