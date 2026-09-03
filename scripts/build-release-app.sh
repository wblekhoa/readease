#!/usr/bin/env bash
# Build the downloadable ReadEase, and refuse to hand over one that macOS
# would call damaged.
#
# The whole reason this script exists is one measured fact (2026-09-04): what
# `tauri build` leaves behind is `adhoc, linker-signed`, and its signature
# does NOT verify -
#
#     ReadEase.app: code has no resources but signature indicates they must
#     be present
#
# On a Mac that downloaded it, that is not the friendly "unidentified
# developer" dialog with an Open Anyway button. It is "ReadEase is damaged
# and can't be opened", which offers nothing but Move to Trash - so the app
# is not installable at all. Re-signing ad hoc seals the resources properly;
# `codesign --verify` then passes, and Gatekeeper falls back to the ordinary
# not-notarized refusal that Open Anyway clears.
#
# So: sign, then VERIFY, and stop if the verify fails. An artifact whose
# signature is broken must never leave this machine looking finished.
#
# Zipped with ditto, not zip(1): ditto is what preserves a bundle's
# signature and its symlinks. A plain zip round-trip can invalidate the
# signature it just took a script to earn.
#
# This does not sign with a Developer ID and does not notarize - the owner
# decided against both. One Open Anyway is the accepted cost.
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

app="app/src-tauri/target/release/bundle/macos/ReadEase.app"
engine="app/src-tauri/engine/readease-engine"
version="$(sed -n 's/.*"version": "\(.*\)".*/\1/p' app/src-tauri/tauri.conf.json | head -1)"
out_dir="dist/release"
artifact="$out_dir/ReadEase-$version-arm64.zip"

# The sidecar is bundled as a resource, so a stale one ships silently. Build
# it first unless it is already newer than every Python source.
newer="$(find src -name '*.py' -newer "$engine" 2>/dev/null | head -1 || true)"
if [[ ! -x "$engine" || -n "$newer" ]]; then
  echo "==> engine is missing or stale; building the sidecar"
  ./scripts/build-sidecar.sh
fi

echo "==> building the app"
(cd app && pnpm tauri build)

[[ -d "$app" ]] || { echo "BUILD_FAILED: no bundle at $app" >&2; exit 1; }

echo "==> re-signing ad hoc"
codesign --force --deep --sign - "$app"

echo "==> verifying the signature"
if ! codesign --verify --deep --strict "$app"; then
  echo "SIGN_FAILED: the bundle would be refused as damaged; not packaging" >&2
  exit 1
fi

# `spctl` rejects an app that is merely un-notarized, which is expected and
# fine. It is reported, not gated: gating on it would demand notarization.
echo "==> Gatekeeper says (rejection here is normal, Open Anyway clears it):"
spctl -a -t exec -vv "$app" 2>&1 | sed 's/^/    /' || true

mkdir -p "$out_dir"
rm -f "$artifact"
echo "==> packaging"
ditto -c -k --keepParent "$app" "$artifact"

echo
echo "READY  $artifact"
echo "size   $(du -h "$artifact" | cut -f1)"
echo "sha256 $(shasum -a 256 "$artifact" | cut -d' ' -f1)"
echo
echo "Not published by this script - upload it to a GitHub release yourself."
