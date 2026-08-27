#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
source_png="${1:-$project_root/assets/branding/readease-icon-master.png}"
output_icns="${2:-$project_root/assets/branding/readease.icns}"

if [[ ! -f "$source_png" ]]; then
  echo "ICON_BUILD RED missing_source=$source_png" >&2
  exit 1
fi

icon_workspace="$(mktemp -d -t readease-icon)"
iconset="$icon_workspace/ReadEase.iconset"
mkdir -p "$iconset" "$(dirname "$output_icns")"

cleanup_icon_workspace() {
  rm -rf -- "$icon_workspace"
}
trap cleanup_icon_workspace EXIT

make_icon() {
  size="$1"
  filename="$2"
  sips -z "$size" "$size" "$source_png" --out "$iconset/$filename" >/dev/null
}

make_icon 16 icon_16x16.png
make_icon 32 icon_16x16@2x.png
make_icon 32 icon_32x32.png
make_icon 64 icon_32x32@2x.png
make_icon 128 icon_128x128.png
make_icon 256 icon_128x128@2x.png
make_icon 256 icon_256x256.png
make_icon 512 icon_256x256@2x.png
make_icon 512 icon_512x512.png
make_icon 1024 icon_512x512@2x.png

iconutil -c icns "$iconset" -o "$output_icns"
echo "ICON_BUILD PASS output=$output_icns"
