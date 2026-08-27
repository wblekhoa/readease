#!/bin/bash
set -u

project_root="$(cd "$(dirname "$0")" && pwd)"
installer="$project_root/scripts/install-from-source.sh"

printf '\nReadEase — Thư Âm\n'
printf 'Đang kiểm tra máy và chuẩn bị bản cài cục bộ. Quá trình đầu tiên có thể mất 10–25 phút.\n\n'

status=0
"$installer" "$@" || status=$?

if [[ "$status" -eq 0 && "${1:-}" == "--check" ]]; then
  printf '\nMáy này tương thích. Bạn có thể bấm lại file này để bắt đầu cài.\n'
elif [[ "$status" -eq 0 ]]; then
  printf '\nHoàn tất. ReadEase đã được mở từ thư mục Applications của bạn.\n'
else
  printf '\nCài đặt chưa hoàn tất. Bạn có thể gửi toàn bộ nội dung cửa sổ này cho một trợ lý AI để được hỗ trợ.\n' >&2
fi

if [[ -t 0 ]]; then
  printf '\nNhấn Enter để đóng cửa sổ này...'
  read -r _answer
fi

exit "$status"
