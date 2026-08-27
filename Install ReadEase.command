#!/bin/bash
set -u

project_root="$(cd "$(dirname "$0")" && pwd)"
installer="$project_root/scripts/install-from-source.sh"

printf '\nReadEase - Thu Am\n'
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
