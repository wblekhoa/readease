#!/bin/bash
# Đưa bản vừa build vào ~/Applications, và ký nó bằng chứng chỉ CỐ ĐỊNH của máy
# này để quyền Trợ năng không rụng sau mỗi lần build.
#
# Đây là đường CÀI CỤC BỘ, không phải đường phát hành. Từ 15/09/2026 bản build
# đã mang chữ ký Developer ID + vé notarize; script này giữ nguyên chữ ký đó.
# Chứng chỉ máy "ReadEase Dev" chỉ còn dùng cho bản build ad-hoc (không có
# Developer ID trong keychain, hoặc READEASE_ADHOC=1).
#
# Không có chứng chỉ thì vẫn cài được, chỉ là ad-hoc như cũ (và quyền lại rụng
# sau mỗi build) — chạy ./scripts/make-dev-cert.sh một lần để hết chuyện đó.
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
src="$project_root/app/src-tauri/target/release/bundle/macos/ReadEase.app"
dst="$HOME/Applications/ReadEase.app"
identity="${READEASE_SIGN_IDENTITY:-ReadEase Dev}"
bundle_id="$(sed -n 's/.*"identifier": "\(.*\)".*/\1/p' "$project_root/app/src-tauri/tauri.conf.json" | head -1)"

[[ -d "$src" ]] || { echo "NO_BUILD at $src" >&2; exit 1; }

if pgrep -fq "ReadEase.app/Contents/MacOS"; then
  osascript -e 'tell application "ReadEase" to quit' >/dev/null 2>&1 || true
  sleep 2
fi

want="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$src/Contents/Info.plist")"
if [[ -d "$dst" ]]; then
  had="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$dst/Contents/Info.plist")"
  mv "$dst" "$HOME/.Trash/ReadEase-$had-$(date +%H%M%S).app"
  echo "bản cũ $had đã vào Thùng rác"
fi
ditto "$src" "$dst"

# Bản build đã ký Developer ID (và notarize) thì giữ nguyên chữ ký: designated
# requirement của nó đã bám chứng chỉ Apple, ổn định qua mọi lần build, và ký
# đè bằng chứng chỉ máy sẽ xoá mất vé notarize. Chỉ bản ad-hoc mới cần ký lại.
if codesign -dv "$dst" 2>&1 | grep -q "Authority=Developer ID Application"; then
  echo "giữ chữ ký Developer ID của bản build (không ký lại)"
# Ký SAU khi chép, vì ditto giữ nguyên chữ ký nguồn (ad-hoc). `--identifier` ghim
# định danh bundle để designated requirement không phụ thuộc vào tên file.
elif security find-identity -v -p codesigning 2>/dev/null | grep -q "\"$identity\""; then
  codesign --force --deep --sign "$identity" --identifier "$bundle_id" "$dst"
  echo "ký bằng \"$identity\""
else
  codesign --force --deep --sign - "$dst"
  echo "ký ad-hoc — chưa có chứng chỉ \"$identity\"; chạy ./scripts/make-dev-cert.sh"
  echo "một lần để build lại không rụng quyền Trợ năng."
fi

codesign --verify --deep --strict "$dst" || { echo "SIGN_FAILED" >&2; exit 1; }

# Điều thật sự quan trọng, kiểm bằng chính nó: yêu cầu định danh phải nói tới
# CHỨNG CHỈ, không phải cdhash. Còn cdhash nghĩa là quyền sẽ lại rụng.
requirement="$(codesign -d -r- "$dst" 2>&1 | sed -n 's/^designated => //p')"
echo "yêu cầu định danh: $requirement"
case "$requirement" in
  *cdhash*) echo "! vẫn bám cdhash — quyền Trợ năng sẽ rụng ở lần build sau" >&2 ;;
  *certificate*) echo "✔ bám chứng chỉ — quyền Trợ năng giữ qua các lần build" ;;
esac

got="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$dst/Contents/Info.plist")"
[[ "$got" == "$want" ]] || { echo "VERSION_MISMATCH built=$want installed=$got" >&2; exit 1; }
echo "ĐÃ CÀI $got · $(du -sh "$dst" | cut -f1)"
