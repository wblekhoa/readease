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

if [[ "$#" -gt 1 ]]; then
  fail "invalid_arguments" "Chỉ hỗ trợ --check hoặc không truyền tham số."
fi
case "$mode" in
  install|--check) ;;
  *) fail "invalid_arguments" "Dùng: ./Install ReadEase.command [--check]" ;;
esac

for required_file in \
  "$project_root/pyproject.toml" \
  "$project_root/uv.lock" \
  "$project_root/scripts/export-public-source.py" \
  "$project_root/scripts/build-app.sh" \
  "$project_root/scripts/install-app.sh"
do
  [[ -f "$required_file" ]] || fail "incomplete_source" "Thiếu file: $required_file"
done

system_name="$(uname -s)"
[[ "$system_name" == "Darwin" ]] || fail "unsupported_system" "ReadEase chỉ hỗ trợ macOS."

architecture="$(uname -m)"
[[ "$architecture" == "arm64" ]] || fail \
  "unsupported_arch" \
  "Cần máy Mac Apple Silicon (M1 trở lên); máy hiện tại báo $architecture."

macos_version="$(sw_vers -productVersion)"
macos_major="${macos_version%%.*}"
case "$macos_major" in
  ''|*[!0-9]*) fail "unknown_macos" "Không đọc được phiên bản macOS: $macos_version" ;;
esac
[[ "$macos_major" -ge "$MIN_MACOS_MAJOR" ]] || fail \
  "unsupported_macos" \
  "Cần macOS $MIN_MACOS_MAJOR trở lên; máy hiện tại là $macos_version."

for tool in curl tar shasum mktemp ditto; do
  command -v "$tool" >/dev/null 2>&1 || fail "missing_system_tool" "Không tìm thấy $tool."
done
if ! xcrun --find clang >/dev/null 2>&1 || ! xcrun --sdk macosx --show-sdk-path >/dev/null 2>&1; then
  fail \
    "missing_xcode_tools" \
    "Hãy chạy 'xcode-select --install', hoàn tất cửa sổ cài đặt rồi thử lại."
fi
[[ -x /usr/bin/codesign ]] || fail "missing_system_tool" "Không tìm thấy codesign."
[[ -x /usr/libexec/PlistBuddy ]] || fail "missing_system_tool" "Không tìm thấy PlistBuddy."

available_kib="$(df -Pk "$project_root" | awk 'NR == 2 { print $4 }')"
case "$available_kib" in
  ''|*[!0-9]*) fail "unknown_disk" "Không đọc được dung lượng trống." ;;
esac
[[ "$available_kib" -ge "$MIN_FREE_KIB" ]] || fail \
  "insufficient_disk" \
  "Cần tối thiểu 6 GB trống trong lúc build; hiện còn khoảng $((available_kib / 1024 / 1024)) GB."

install_root="$HOME/Applications"
if [[ -d "$install_root" ]]; then
  [[ -w "$install_root" ]] || fail "install_not_writable" "Không thể ghi vào $install_root."
else
  [[ -w "$HOME" ]] || fail "install_not_writable" "Không thể tạo $install_root."
fi

existing_uv=""
if [[ -n "${READEASE_UV_BIN:-}" && -x "${READEASE_UV_BIN}" ]]; then
  explicit_uv_version="$("$READEASE_UV_BIN" --version 2>/dev/null | awk '{ print $2 }' || true)"
  [[ "$explicit_uv_version" == "$UV_VERSION" ]] || fail \
    "uv_version_mismatch" \
    "READEASE_UV_BIN phải trỏ tới uv $UV_VERSION."
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

temp_root="${TMPDIR:-/tmp}"
temp_root="${temp_root%/}"
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
    printf 'READEASE_BUILD_PRESERVED path=%s reason=failed-install\n' "$work_root" >&2
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
    fail "uv_download_failed" "Không tải được công cụ build đã khóa từ GitHub."
  fi
  archive_sha256="$(shasum -a 256 "$archive" | awk '{ print $1 }')"
  [[ "$archive_sha256" == "$UV_ARCHIVE_SHA256" ]] || fail \
    "uv_checksum_mismatch" \
    "File tải về không khớp checksum; đã dừng trước khi chạy."
  tar -xzf "$archive" -C "$tool_root"
  uv_bin="$tool_root/uv-aarch64-apple-darwin/uv"
  [[ -x "$uv_bin" ]] || fail "uv_archive_invalid" "Archive uv không có binary mong đợi."
  installed_uv_version="$("$uv_bin" --version | awk '{ print $2 }')"
  [[ "$installed_uv_version" == "$UV_VERSION" ]] || fail \
    "uv_version_mismatch" \
    "Binary uv không đúng phiên bản $UV_VERSION."
fi

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
(
  cd "$export_root"
  ./scripts/build-app.sh
  ./scripts/install-app.sh
)

completed=1
printf 'READEASE_SOURCE_INSTALL PASS target=%s/ReadEase.app\n' "$install_root"
