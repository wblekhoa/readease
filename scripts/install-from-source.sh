#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
mode="${1:-install}"

MIN_MACOS_MAJOR=15
MIN_FREE_KIB=$((6 * 1024 * 1024))
UV_VERSION="0.9.13"
UV_ARCHIVE="uv-aarch64-apple-darwin.tar.gz"
UV_ARCHIVE_SHA256="9c594dce1c237e11680be2b6d1331448eeb6f8a1453fb851a66a40291bb624de"
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
if ! xcrun --find clang >/dev/null 2>&1 || ! xcrun --sdk macosx --show-sdk-path >/dev/null 2>&1; then
  fail \
    "missing_xcode_tools" \
    "Run 'xcode-select --install', finish Apple's installer window, then try again."
fi
[[ -x /usr/bin/codesign ]] || fail "missing_system_tool" "codesign was not found."
[[ -x /usr/libexec/PlistBuddy ]] || fail "missing_system_tool" "PlistBuddy was not found."

available_kib="$(df -Pk "$project_root" | awk 'NR == 2 { print $4 }')"
case "$available_kib" in
  ''|*[!0-9]*) fail "unknown_disk" "Could not read the free disk space." ;;
esac
[[ "$available_kib" -ge "$MIN_FREE_KIB" ]] || fail \
  "insufficient_disk" \
  "At least 6 GB of free space is needed during the build; about $((available_kib / 1024 / 1024)) GB is free."

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
  printf '  ReadEase %s is already installed. The new build replaces it, and the\n' \
    "$installed_version"
  printf '  current one is kept until the new install succeeds.\n'
  if [[ "$mode" != "--check" ]]; then
    if ! ask "Replace the installed ReadEase?" y; then
      printf 'READEASE_SOURCE_INSTALL CANCELLED reason=user-declined\n'
      printf '  Nothing was changed.\n'
      exit 0
    fi
  fi
else
  printf 'READEASE_EXISTING none\n'
  printf '  No ReadEase found on this Mac. This is a first install.\n'
fi

if [[ -d "$legacy_app" ]]; then
  printf 'READEASE_LEGACY present\n'
  printf '  An older bundle named "VieNeu Reader" is present. It is removed after a\n'
  printf '  successful install. Your books and reading progress are kept.\n'
fi

# Gatekeeper quarantine: set when the source arrived as a browser download.
# It does not block this script (Terminal execution is unaffected), but it is
# exactly what blocks double-clicking "Install ReadEase.command" in Finder.
if xattr -p com.apple.quarantine "$project_root" >/dev/null 2>&1 \
  || xattr -p com.apple.quarantine "$project_root/Install ReadEase.command" >/dev/null 2>&1
then
  printf 'READEASE_QUARANTINE present\n'
  printf '  This source came from a browser download, so macOS flagged it (Gatekeeper).\n'
  printf '  Running it from Terminal, as now, is unaffected. Only a Finder double-click\n'
  printf '  is blocked.\n'
  quarantine_cleared=0
  if [[ "$mode" != "--check" ]]; then
    if ask "Remove the flag so Finder can open it next time?" y; then
      if xattr -d -r com.apple.quarantine "$project_root" 2>/dev/null; then
        printf 'READEASE_QUARANTINE cleared\n'
        quarantine_cleared=1
      fi
    fi
  fi
  if [[ "$quarantine_cleared" -eq 0 ]]; then
    printf '  To remove it yourself:\n'
    printf '    xattr -d com.apple.quarantine %s\n' "$(printf '%q' "$project_root")"
    printf '  Or get the source with git clone, which is never flagged:\n'
    printf '    git clone https://github.com/wblekhoa/readease.git\n'
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
  printf '  %s leftover build workspace(s) from a failed install, about %s.\n' \
    "${#stale_dirs[@]}" "$(human_kib "$stale_total_kib")"
  stale_removed=0
  if [[ "$mode" != "--check" ]]; then
    if ask "Remove them now to reclaim the space?" n; then
      for stale_dir in "${stale_dirs[@]}"; do
        case "$stale_dir" in
          "$temp_root_probe"/readease-source-install.*)
            rm -R -- "$stale_dir" && stale_removed=$((stale_removed + 1))
            ;;
        esac
      done
      printf 'READEASE_STALE_BUILD removed=%s\n' "$stale_removed"
    fi
  fi
  if [[ "$stale_removed" -eq 0 ]]; then
    printf '  Remove them yourself whenever you like:\n'
    printf '    rm -R %s/readease-source-install.*\n' "$temp_root_probe"
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

if [[ "$mode" == "--check" ]]; then
  uv_status="pinned-download"
  [[ -n "$existing_uv" ]] && uv_status="available"
  printf 'READEASE_PREFLIGHT PASS arch=%s macos=%s free_gib=%s uv=%s\n' \
    "$architecture" \
    "$macos_version" \
    "$((available_kib / 1024 / 1024))" \
    "$uv_status"
  exit 0
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
"$uv_bin" run \
  --isolated \
  --no-project \
  --managed-python \
  --python 3.13 \
  python \
  "$project_root/scripts/export-public-source.py" \
  --output "$export_root"

export PATH="$(dirname "$uv_bin"):$PATH"
step 4 "Compiling the app - the longest step, usually 10-20 minutes"
(
  cd "$export_root"
  ./scripts/build-app.sh
)
step 5 "Installing into $install_root"
(
  cd "$export_root"
  ./scripts/install-app.sh
)

completed=1
printf 'READEASE_SOURCE_INSTALL PASS target=%s/ReadEase.app\n' "$install_root"
