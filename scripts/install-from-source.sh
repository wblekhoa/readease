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

human_kib() {
  local kib="$1"
  if [[ "$kib" -ge 1048576 ]]; then
    printf '%s GB' "$((kib / 1048576))"
  else
    printf '%s MB' "$((kib / 1024))"
  fi
}

if [[ "$#" -gt 1 ]]; then
  fail "invalid_arguments" "Chỉ hỗ trợ --check hoặc không truyền tham số."
fi
case "$mode" in
  install|--check) ;;
  *) fail "invalid_arguments" "Dùng: ./Install ReadEase.command [--check]" ;;
esac

step 1 "Kiểm tra máy và nguồn cài"

for required_file in \
  "$project_root/pyproject.toml" \
  "$project_root/uv.lock" \
  "$project_root/scripts/export-public-source.py" \
  "$project_root/scripts/build-app.sh" \
  "$project_root/scripts/install-app.sh"
do
  [[ -f "$required_file" ]] || fail "incomplete_source" "Thiếu file: $required_file"
done

temp_root_probe="${TMPDIR:-/tmp}"
temp_root_probe="${temp_root_probe%/}"

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

install_root="${READEASE_INSTALL_ROOT:-$HOME/Applications}"
if [[ -d "$install_root" ]]; then
  [[ -w "$install_root" ]] || fail "install_not_writable" "Không thể ghi vào $install_root."
else
  [[ -w "$HOME" ]] || fail "install_not_writable" "Không thể tạo $install_root."
fi

# What is already on this machine, so nobody has to guess what will change.
installed_app="$install_root/ReadEase.app"
legacy_app="$install_root/VieNeu Reader.app"
if [[ -d "$installed_app" ]]; then
  installed_version="$(/usr/libexec/PlistBuddy \
    -c 'Print :CFBundleShortVersionString' \
    "$installed_app/Contents/Info.plist" 2>/dev/null || true)"
  [[ -n "$installed_version" ]] || installed_version="không đọc được"
  printf 'READEASE_EXISTING installed version=%s\n' "$installed_version"
  printf '  Đã có ReadEase %s. Bản mới sẽ thay thế nó; bản cũ được giữ nguyên cho tới khi cài xong.\n' \
    "$installed_version"
else
  printf 'READEASE_EXISTING none\n'
  printf '  Chưa có ReadEase trên máy — đây là lần cài đầu tiên.\n'
fi

if [[ -d "$legacy_app" ]]; then
  printf 'READEASE_LEGACY present\n'
  printf '  Tìm thấy bản cũ tên "VieNeu Reader" — sẽ được gỡ sau khi cài xong. Sách và tiến độ đọc giữ nguyên.\n'
fi

# Gatekeeper quarantine: set when the source arrived as a browser download.
# It does not block this script (Terminal execution is unaffected), but it is
# exactly what blocks double-clicking "Install ReadEase.command" in Finder.
if xattr -p com.apple.quarantine "$project_root" >/dev/null 2>&1 \
  || xattr -p com.apple.quarantine "$project_root/Install ReadEase.command" >/dev/null 2>&1
then
  printf 'READEASE_QUARANTINE present\n'
  printf '  Nguồn cài này được tải qua trình duyệt nên macOS gắn cờ kiểm dịch (Gatekeeper).\n'
  printf '  Chạy từ Terminal như hiện tại thì KHÔNG sao. Chỉ double-click trong Finder mới bị chặn.\n'
  printf '  Muốn double-click được, gỡ cờ bằng:\n'
  printf '    xattr -d com.apple.quarantine %s\n' "$(printf '%q' "$project_root")"
  printf '  Hoặc lần sau lấy nguồn bằng git clone — cách này không bao giờ bị gắn cờ:\n'
  printf '    git clone https://github.com/wblekhoa/readease.git\n'
else
  printf 'READEASE_QUARANTINE none\n'
fi

# Failed builds deliberately keep their workspace. Report it; never delete it here.
stale_total_kib=0
stale_count=0
for stale_dir in "$temp_root_probe"/readease-source-install.*; do
  [[ -d "$stale_dir" ]] || continue
  stale_count=$((stale_count + 1))
  stale_kib="$(du -sk "$stale_dir" 2>/dev/null | awk '{ print $1 }')"
  stale_total_kib=$((stale_total_kib + ${stale_kib:-0}))
done
if [[ "$stale_count" -gt 0 ]]; then
  printf 'READEASE_STALE_BUILD count=%s size_kib=%s\n' "$stale_count" "$stale_total_kib"
  printf '  Có %s thư mục build dở từ lần cài hỏng trước, chiếm khoảng %s.\n' \
    "$stale_count" "$(human_kib "$stale_total_kib")"
  printf '  Xoá bằng lệnh sau (chạy khi bạn muốn, bộ cài không tự xoá):\n'
  printf '    rm -R %s/readease-source-install.*\n' "$temp_root_probe"
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

step 2 "Chuẩn bị công cụ build (uv $UV_VERSION)"

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
    printf 'Thư mục build dở được giữ lại để chẩn đoán (khoảng %s).\n' \
      "$(human_kib "${kept_kib:-0}")" >&2
    printf 'Khi không cần nữa, xoá bằng:\n    rm -R %s\n' "$work_root" >&2
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

step 3 "Tạo bản nguồn sạch để build"

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
step 4 "Biên dịch ứng dụng — bước lâu nhất, thường 10–20 phút"
(
  cd "$export_root"
  ./scripts/build-app.sh
)
step 5 "Cài vào $install_root"
(
  cd "$export_root"
  ./scripts/install-app.sh
)

completed=1
printf 'READEASE_SOURCE_INSTALL PASS target=%s/ReadEase.app\n' "$install_root"
