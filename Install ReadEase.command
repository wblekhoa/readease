#!/bin/bash
set -u

project_root="$(cd "$(dirname "$0")" && pwd)"
installer="$project_root/scripts/install-from-source.sh"

printf '\nReadEase - Thu Am\n'

# Fail in two seconds, not in twenty-five minutes. This path compiles the file
# pysidedeploy.spec names, and that file left with the Qt shell (2026-09-08).
# Finding that out from a compiler trace after a long build is the worst way to
# find it out, so the check happens before anything is downloaded or installed.
entry_point="$(sed -n 's/^input_file = //p' "$project_root/pysidedeploy.spec" | head -1)"
if [[ -n "$entry_point" && ! -f "$project_root/$entry_point" ]]; then
  printf '\nDuong cai tu ma nguon hien khong dung duoc.\n' >&2
  printf 'The install-from-source path cannot build right now.\n\n' >&2
  printf 'Hay tai ban .zip dung san o README.md - do la ban day du va moi nhat.\n' >&2
  printf 'Download the prebuilt .zip from README.md instead.\n\n' >&2
  if [[ -t 0 ]]; then
    printf 'Press Enter to close this window...'
    read -r _answer
  fi
  exit 1
fi

printf 'Checking this Mac and preparing a local build. The first run usually takes 10-25 minutes.\n\n'

status=0
"$installer" "$@" || status=$?

if [[ "$status" -eq 0 && "${1:-}" == "--check" ]]; then
  printf '\nThis Mac is supported. Open this file again to start the install.\n'
elif [[ "$status" -eq 0 ]]; then
  printf '\nDone. ReadEase has been opened from your Applications folder.\n'
else
  printf '\nThe install did not finish. You can paste this whole window to an AI assistant for help.\n' >&2
fi

if [[ -t 0 ]]; then
  printf '\nPress Enter to close this window...'
  read -r _answer
fi

exit "$status"
