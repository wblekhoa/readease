#!/bin/bash
# Publish one built release to GitHub (HIG 3.20): the zip, the disk image,
# the updater archive and its manifest, under the plain asset names the
# README and `latest.json` point at - then prove every link answers with
# the right size. Run after ./scripts/build-release-app.sh, with
# dist/release/notes-<version>.md written.
#
#   ./scripts/release.sh 0.1.10
#
# Refuses to publish over an existing tag, and stops before the release if
# any artifact for the version is missing: a release without its updater
# manifest is invisible to every installed app, silently.
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"
version="${1:?usage: release.sh <version>}"
out="dist/release"
notes="$out/notes-$version.md"
tag="v$version"
repo="wblekhoa/readease"

[[ -f "$notes" ]] || { echo "NO_NOTES: write $notes first" >&2; exit 1; }
conf_version="$(sed -n 's/.*"version": "\(.*\)".*/\1/p' app/src-tauri/tauri.conf.json | head -1)"
[[ "$conf_version" == "$version" ]] || { echo "VERSION_MISMATCH: tauri.conf.json says $conf_version" >&2; exit 1; }
if git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
  echo "TAG_EXISTS: $tag is already tagged; bump the version instead of republishing" >&2; exit 1
fi

# The build's artifacts carry the build id; exactly one build of this version
# may be waiting, or the wrong one could ship.
pick() {
  local pattern="$1" found
  found="$(ls -1 $pattern 2>/dev/null | grep -v unnotarized || true)"
  [[ -n "$found" ]] || { echo "MISSING: no $pattern (run build-release-app.sh)" >&2; exit 1; }
  [[ "$(wc -l <<<"$found")" -eq 1 ]] || { echo "AMBIGUOUS: more than one build of $version in $out - trash the stale ones" >&2; exit 1; }
  printf '%s' "$found"
}
zip_built="$(pick "$out/ReadEase-$version+*-arm64.zip")"
dmg_built="$(pick "$out/ReadEase-$version+*-arm64.dmg")"
tar_built="$(pick "$out/ReadEase-$version+*-arm64.app.tar.gz")"
manifest="$out/latest.json"
[[ -s "$manifest" ]] || { echo "MISSING: $manifest (updater key not in the environment at build time?)" >&2; exit 1; }
grep -q "\"version\": \"$version\"" "$manifest" || { echo "STALE_MANIFEST: $manifest is not for $version" >&2; exit 1; }

zip_out="$out/ReadEase-$version-arm64.zip"
dmg_out="$out/ReadEase-$version-arm64.dmg"
tar_out="$out/ReadEase-$version-arm64.app.tar.gz"
cp "$zip_built" "$zip_out"; cp "$dmg_built" "$dmg_out"; cp "$tar_built" "$tar_out"

build="$(git rev-parse --short HEAD)"
echo "==> tagging $tag at $build"
git tag -a "$tag" -m "ReadEase $version"
git push -q origin "$tag"

echo "==> release $tag"
gh release create "$tag" "$zip_out" "$dmg_out" "$tar_out" "$manifest" \
  --repo "$repo" --title "ReadEase — Thư Âm $version" --notes-file "$notes"

# Every link the README and the updater will follow, answered with the
# exact byte count of the file uploaded - the check that caught nothing so
# far and is kept because a wrong link is the one release bug users meet
# first.
echo "==> links"
sleep 5
check() {
  local file="$1" name url head size length
  name="$(basename "$file")"
  url="https://github.com/$repo/releases/download/$tag/$name"
  size="$(stat -f%z "$file")"
  head="$(curl -sIL "$url")"
  length="$(printf '%s' "$head" | tr -d '\r' | awk 'tolower($1)=="content-length:"{v=$2} END{print v}')"
  if grep -q "^HTTP/[0-9.]* 200" <<<"$head" && [[ "$length" == "$size" ]]; then
    echo "    ok   $name ($size B)"
  else
    echo "LINK_FAILED: $url (expected $size B, got '$length')" >&2; exit 1
  fi
}
check "$zip_out"; check "$dmg_out"; check "$tar_out"; check "$manifest"

echo
echo "PUBLISHED https://github.com/$repo/releases/tag/$tag"
echo "sha256 $(shasum -a 256 "$zip_out" | cut -d' ' -f1)  $(basename "$zip_out")"
echo "Now: point README.md / README.en.md at $version if not already, and trash"
echo "the build-id artifacts in $out."
