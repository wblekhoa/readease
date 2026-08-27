#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

uv sync --locked --managed-python --python 3.13
"$project_root/scripts/build-icon.sh"

if ! uv run python - <<'PY'
from importlib import metadata

try:
    version = metadata.version("Nuitka")
except metadata.PackageNotFoundError:
    raise SystemExit(1)
raise SystemExit(0 if version == "4.1.1" else 1)
PY
then
  echo "BUILD_PARKED: Nuitka 4.1.1 is not locked and installed." >&2
  echo "Approve the build dependency before running this script again." >&2
  exit 2
fi

bundle="$project_root/dist/ReadEase.app"
temp_root="${TMPDIR:-/tmp}"
temp_root="${temp_root%/}"
rollback_root="$(mktemp -d "$temp_root/readease-build-rollback.XXXXXX")"
previous_bundle="$rollback_root/ReadEase.app"
onnxruntime_alias=""
onnxruntime_alias_created=0

cleanup_build() {
  local status=$?
  trap - EXIT

  if [[ "$onnxruntime_alias_created" == 1 && -L "$onnxruntime_alias" ]]; then
    rm -f -- "$onnxruntime_alias"
  fi

  if [[ "$status" -ne 0 ]]; then
    if [[ -e "$bundle" ]]; then
      mv "$bundle" "$rollback_root/failed-ReadEase.app"
    fi
    if [[ -d "$previous_bundle" ]]; then
      mv "$previous_bundle" "$bundle"
      echo "Restored previous bundle after failed build: $bundle" >&2
    fi
  fi

  case "$rollback_root" in
    "$temp_root"/readease-build-rollback.*)
      rm -R -- "$rollback_root"
      ;;
    *)
      echo "BUILD_CLEANUP_REFUSED: unexpected rollback path $rollback_root" >&2
      exit 1
      ;;
  esac
  exit "$status"
}
trap cleanup_build EXIT

if [[ -e "$bundle" ]]; then
  mv "$bundle" "$previous_bundle"
  echo "Saved previous bundle in a transactional rollback directory."
fi

# ONNX Runtime 1.29 ships the versioned dylib with an install name ending in
# libonnxruntime.1.dylib, but its macOS wheel omits that compatibility symlink.
# Nuitka 4.1.1 resolves install names while collecting native libraries and
# therefore needs the alias during compilation. Keep the workaround transient
# so uv remains the sole owner of the virtual environment.
onnxruntime_capi="$(uv run python - <<'PY'
from importlib.util import find_spec
from pathlib import Path

spec = find_spec("onnxruntime")
if spec is None or spec.origin is None:
    raise SystemExit("onnxruntime package not found")
print(Path(spec.origin).resolve().parent / "capi")
PY
)"
onnxruntime_target="$(find "$onnxruntime_capi" -maxdepth 1 -type f -name 'libonnxruntime.[0-9]*.dylib' -print -quit)"
onnxruntime_alias="$onnxruntime_capi/libonnxruntime.1.dylib"

if [[ -z "$onnxruntime_target" ]]; then
  echo "BUILD_FAILED: versioned ONNX Runtime dylib not found in $onnxruntime_capi" >&2
  exit 1
fi
if [[ -e "$onnxruntime_alias" || -L "$onnxruntime_alias" ]]; then
  if [[ ! -L "$onnxruntime_alias" || "$(readlink "$onnxruntime_alias")" != "$(basename "$onnxruntime_target")" ]]; then
    echo "BUILD_FAILED: unexpected ONNX Runtime compatibility alias at $onnxruntime_alias" >&2
    exit 1
  fi
else
  ln -s "$(basename "$onnxruntime_target")" "$onnxruntime_alias"
  onnxruntime_alias_created=1
fi

mkdir -p "$project_root/dist"
runtime_spec="$project_root/build/pysidedeploy.runtime.spec"
mkdir -p "$project_root/build"
cp "$project_root/pysidedeploy.spec" "$runtime_spec"
uv run pyside6-deploy -c "$runtime_spec" --force

if [[ ! -d "$bundle" ]]; then
  echo "BUILD_FAILED: expected bundle was not produced at $bundle" >&2
  exit 1
fi

"$project_root/scripts/package-runtime-assets.sh" "$bundle"
"$project_root/scripts/build-native-selection-bridge.sh" "$bundle"
"$project_root/scripts/deduplicate-runtime-libraries.sh" "$bundle"

plist="$bundle/Contents/Info.plist"
if /usr/libexec/PlistBuddy -c "Print :LSMinimumSystemVersion" "$plist" >/dev/null 2>&1; then
  /usr/libexec/PlistBuddy -c "Set :LSMinimumSystemVersion 15.0" "$plist"
else
  /usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string 15.0" "$plist"
fi
plutil -lint "$plist"
codesign --force --deep --sign - "$bundle"
echo "BUILD_APP PASS bundle=$bundle"
