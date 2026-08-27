#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

bundle="${1:-$project_root/dist/ReadEase.app}"
if [[ ! -d "$bundle/Contents/MacOS" ]]; then
  echo "ASSET_PACKAGE RED missing_bundle=$bundle" >&2
  exit 1
fi

resolve_package_asset() {
  uv run --frozen python - "$1" "$2" <<'PY'
from importlib.util import find_spec
from pathlib import Path
import sys

package, relative_name = sys.argv[1:]
spec = find_spec(package)
if spec is None or not spec.submodule_search_locations:
    raise SystemExit(f"package not found: {package}")
package_root = Path(next(iter(spec.submodule_search_locations))).resolve()
asset = (package_root / relative_name).resolve()
if package_root not in asset.parents or not asset.is_file():
    raise SystemExit(f"package asset not found: {package}/{relative_name}")
print(asset)
PY
}

copy_package_asset() {
  package="$1"
  relative_name="$2"
  minimum_bytes="$3"
  source_path="$(resolve_package_asset "$package" "$relative_name")"
  actual_bytes="$(stat -f '%z' "$source_path")"
  if (( actual_bytes < minimum_bytes )); then
    echo "ASSET_PACKAGE RED undersized=$source_path bytes=$actual_bytes" >&2
    exit 1
  fi
  destination="$bundle/Contents/MacOS/$package/$relative_name"
  mkdir -p "$(dirname "$destination")"
  /usr/bin/install -m 0644 "$source_path" "$destination"
}

copy_package_asset "vieneu" "assets/voices_v3_turbo.json" 1000
copy_package_asset "sea_g2p" "sea_g2p.bin" 10000000
uv run --frozen python "$project_root/scripts/package-license-payload.py" \
  --output "$bundle/Contents/Resources/Legal" \
  --report "$project_root/dist/nuitka-compilation-report.xml"
uv run --frozen python "$project_root/scripts/package-provenance.py" \
  --bundle "$bundle"

echo "ASSET_PACKAGE PASS voices=1 phonemes=1 legal=1 provenance=1"
