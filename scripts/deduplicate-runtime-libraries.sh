#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
bundle="${1:-$project_root/dist/ReadEase.app}"
macos="$bundle/Contents/MacOS"
compatibility_name="$macos/libonnxruntime.1.dylib"
versioned_library=""
versioned_count=0

for candidate in "$macos"/libonnxruntime.*.dylib; do
  if [[ ! -e "$candidate" || "$candidate" == "$compatibility_name" ]]; then
    continue
  fi
  versioned_library="$candidate"
  versioned_count=$((versioned_count + 1))
done

if [[ "$versioned_count" -ne 1 || ! -f "$versioned_library" ]]; then
  echo "RUNTIME_DEDUP RED expected_one_versioned_onnxruntime count=$versioned_count" >&2
  exit 1
fi

if [[ -L "$compatibility_name" ]]; then
  if [[ "$(readlink "$compatibility_name")" != "$(basename "$versioned_library")" ]]; then
    echo "RUNTIME_DEDUP RED unexpected_compatibility_symlink=$compatibility_name" >&2
    exit 1
  fi
elif [[ -f "$compatibility_name" ]]; then
  library_id="$(otool -D "$versioned_library" | tail -n 1)"
  if [[ "$library_id" != "@rpath/libonnxruntime.1.dylib" ]]; then
    echo "RUNTIME_DEDUP RED unexpected_versioned_library_id=$library_id" >&2
    exit 1
  fi
  case "$(file "$versioned_library")" in
    *Mach-O*arm64*) ;;
    *)
    echo "RUNTIME_DEDUP RED versioned_library_is_not_arm64=$versioned_library" >&2
    exit 1
      ;;
  esac
  rm -f -- "$compatibility_name"
  ln -s "$(basename "$versioned_library")" "$compatibility_name"
else
  echo "RUNTIME_DEDUP RED missing_compatibility_name=$compatibility_name" >&2
  exit 1
fi

echo "RUNTIME_DEDUP PASS compatibility=$(basename "$compatibility_name") target=$(basename "$versioned_library")"
