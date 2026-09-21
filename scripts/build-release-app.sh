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
# Signing, two ways. With a "Developer ID Application" identity in the login
# keychain (the owner's, since 15/09/2026) the bundle is signed inside-out
# with the hardened runtime and a trusted timestamp, sent to Apple's notary
# service through the keychain profile READEASE_NOTARY_PROFILE (default
# `readease-notary`, made once with `xcrun notarytool store-credentials`),
# stapled, and then REQUIRED to pass Gatekeeper before it is packaged. Without
# such an identity - a contributor's Mac - it falls back to the ad-hoc signing
# above, which is installable but not shareable without one Open Anyway.
# READEASE_ADHOC=1 forces the fallback on the owner's Mac too.
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

app="app/src-tauri/target/release/bundle/macos/ReadEase.app"
engine="app/src-tauri/engine/readease-engine"
version="$(sed -n 's/.*"version": "\(.*\)".*/\1/p' app/src-tauri/tauri.conf.json | head -1)"
# Which BUILD this is, not just which version. Two artifacts built an hour
# apart carried the same name and the same 0.1.0 while their contents
# differed, so "did my update take?" had no answer - for the person who
# installed it or for anyone checking afterwards. The commit answers it.
build="$(git rev-parse --short HEAD 2>/dev/null || echo nogit)"
dirty=""
if ! git diff --quiet HEAD 2>/dev/null; then dirty="-dirty"; fi
build="$build$dirty"
out_dir="dist/release"
artifact="$out_dir/ReadEase-$version+$build-arm64.zip"

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

# Everything that writes into the bundle happens BEFORE signing: touching
# Info.plist or Resources afterwards breaks the seal the sign step spends its
# whole existence earning.

# The licence and notices travel WITH the app. A binary handed to someone else
# carries the terms it is given under; leaving them only in the repository puts
# them where the person holding the app is not. The payload is generated from
# what this build actually contains - the frozen engine's PyInstaller TOC and
# the host's Cargo.lock - so the inventory cannot describe a different build,
# and the generator refuses to finish with a component that has no licence
# text to ship.
echo "==> writing the licence payload"
legal="$app/Contents/Resources/Legal"
rm -rf "$legal"
.venv/bin/python scripts/package-license-payload.py \
  --output "$legal" \
  --engine-build build/engine-build/readease-engine \
  --cargo-lock app/src-tauri/Cargo.lock

echo "==> writing the provenance record"
.venv/bin/python scripts/package-provenance.py --bundle "$app"

# 32 MB nothing loads. Measured on this layout, not assumed: a real read
# through the frozen engine gave the same 3 chunks and the same ok:true with
# the dylib deleted. The bundle contract re-proves the linkage claim after
# every build, so an ONNX Runtime that ever DOES link it fails the gate
# instead of shipping an app that cannot speak.
echo "==> dropping the ONNX Runtime dylib nothing links"
./scripts/deduplicate-runtime-libraries.sh "$app"

echo "==> stamping the build id ($build) into CFBundleVersion"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $version+$build" "$app/Contents/Info.plist"

developer_id="$(security find-identity -v -p codesigning 2>/dev/null \
  | sed -n 's/.*"\(Developer ID Application: [^"]*\)".*/\1/p' | head -1)"
notary_profile="${READEASE_NOTARY_PROFILE:-readease-notary}"
if [[ "${READEASE_ADHOC:-0}" == "1" ]]; then developer_id=""; fi

if [[ -n "$developer_id" ]]; then
  echo "==> signing with \"$developer_id\" (hardened runtime, timestamp)"
  sign=(codesign --force --options runtime --timestamp --sign "$developer_id")
  # Inside-out, never --deep: every Mach-O the sidecar carries gets its own
  # signature first, then the sidecar executable with its entitlements, then
  # the bundle, which seals the host executable and everything under it.
  # Found by magic number rather than by suffix - PyInstaller ships
  # extension modules and dylibs under several names, and one missed file
  # is a notarization rejection twenty minutes later.
  engine_dir="$app/Contents/Resources/engine"
  signed=0
  while IFS= read -r -d '' file; do
    case "$(xxd -p -l 4 "$file" 2>/dev/null)" in
      cffaedfe|cefaedfe|feedface|feedfacf|cafebabe|bebafeca)
        "${sign[@]}" "$file" 2>/dev/null; signed=$((signed + 1)) ;;
    esac
  done < <(find "$engine_dir/_internal" -type f ! -name '*.py' ! -name '*.pyc' -print0)
  "${sign[@]}" --entitlements app/src-tauri/entitlements/engine.plist "$engine_dir/readease-engine"
  echo "    $((signed + 1)) Mach-O files in the sidecar"
  "${sign[@]}" "$app"
else
  echo "==> re-signing ad hoc (no Developer ID identity in the keychain)"
  codesign --force --deep --sign - "$app"
fi

echo "==> verifying the signature"
if ! codesign --verify --deep --strict "$app"; then
  echo "SIGN_FAILED: the bundle would be refused as damaged; not packaging" >&2
  exit 1
fi

# Submit one file to the notary service and wait for Apple's verdict.
# Submitted without `--wait`, then polled once a minute: Apple took over
# 30 minutes on the very first submission (15/09) and `--wait`'s timeout
# turned a still-pending review into a failed build, while the review went
# on to succeed. Only a verdict ends the wait, or the ceiling in
# READEASE_NOTARY_MAX_MINUTES (default six hours). A rejection prints
# Apple's own log - the file and the reason - and stops the build: a file
# that failed notarization must not be packaged as if it had passed.
notarize_wait() {
  local file="$1" submit_log submission max_minutes status last waited
  submit_log="$(mktemp)"
  xcrun notarytool submit "$file" --keychain-profile "$notary_profile" \
    2>&1 | tee "$submit_log" | sed 's/^/    /' || true
  submission="$(sed -n 's/^ *id: //p' "$submit_log" | head -1)"
  rm -f "$submit_log"
  if [[ -z "$submission" ]]; then
    echo "NOTARIZE_FAILED: the upload did not produce a submission id" >&2; exit 1
  fi
  max_minutes="${READEASE_NOTARY_MAX_MINUTES:-360}"
  status="In Progress"; last=""; waited=0
  while [[ "$status" == "In Progress" ]]; do
    if (( waited >= max_minutes )); then
      echo "NOTARIZE_FAILED: no verdict after $max_minutes minutes (submission $submission still pending)" >&2
      exit 1
    fi
    sleep 60; waited=$((waited + 1))
    status="$(xcrun notarytool info "$submission" --keychain-profile "$notary_profile" 2>/dev/null \
      | sed -n 's/^ *status: //p' | head -1)"
    [[ -n "$status" ]] || status="In Progress"
    if [[ "$status" != "$last" ]]; then echo "    $(date +%H:%M) $status ($submission)"; last="$status"; fi
  done
  if [[ "$status" != "Accepted" ]]; then
    xcrun notarytool log "$submission" --keychain-profile "$notary_profile" 2>&1 | sed 's/^/    /' || true
    echo "NOTARIZE_FAILED: Apple answered \"$status\" for $(basename "$file"); not packaging" >&2
    exit 1
  fi
}

if [[ -n "$developer_id" && "${READEASE_SKIP_NOTARY:-0}" == "1" ]]; then
  # A local iteration: Developer ID signature (so the Accessibility grant
  # keeps its anchor) without the half-hour at Apple. Not for anything that
  # leaves this machine - the artifact is written under a name that says so.
  echo "==> READEASE_SKIP_NOTARY=1: signed, NOT notarized - local install only"
  artifact="${artifact%.zip}-unnotarized.zip"
elif [[ -n "$developer_id" ]]; then
  # The notary service wants the bundle as an archive; ditto keeps the seal.
  # Submitted without `--wait`, then polled once a minute: Apple took over
  # 30 minutes on the very first submission (15/09) and `--wait`'s timeout
  # turned a still-pending review into a failed build, while the review
  # went on to succeed. Only a verdict ends the wait, or the ceiling in
  # READEASE_NOTARY_MAX_MINUTES (default six hours). A rejection prints
  # Apple's own log - the file and the reason - and stops here: an app that
  # failed notarization must not be packaged as if it had passed.
  echo "==> notarizing through profile \"$notary_profile\""
  notary_dir="$(mktemp -d)"
  ditto -c -k --keepParent "$app" "$notary_dir/ReadEase.zip"
  notarize_wait "$notary_dir/ReadEase.zip"
  rm -rf "$notary_dir"
  echo "==> stapling the notarization ticket"
  xcrun stapler staple "$app" | sed 's/^/    /'
  # The gate that used to be only a report: a Developer ID build has to be
  # accepted by Gatekeeper outright, or the whole point was missed.
  echo "==> Gatekeeper"
  # Read the verdict into a variable, then judge it. Piped through
  # `tee | grep -q`, the grep closed the pipe on its first match, tee lost
  # the race and died on the write, and pipefail turned an "accepted" into
  # GATEKEEPER_FAILED (0.1.5, 16/09/2026 - one build in three).
  verdict="$(spctl -a -t exec -vv "$app" 2>&1 || true)"
  printf '%s\n' "$verdict" | sed 's/^/    /'
  if ! grep -q "accepted" <<<"$verdict"; then
    echo "GATEKEEPER_FAILED: a notarized bundle should be accepted; not packaging" >&2
    exit 1
  fi
else
  # `spctl` rejects an app that is merely un-notarized, which is expected and
  # fine for the ad-hoc fallback. Reported, not gated.
  echo "==> Gatekeeper says (rejection here is normal, Open Anyway clears it):"
  spctl -a -t exec -vv "$app" 2>&1 | sed 's/^/    /' || true
fi

# Every Mach-O in the bundle must run on the macOS the plist claims. A single
# dylib built against a newer SDK floor turns "macOS 15+" into a launch
# failure on exactly the Macs the README invites - and the person sees a
# crash, not a requirement. The check existed and was reachable only from
# verify-app.sh, which went with the Qt lane.
echo "==> macOS floor"
.venv/bin/python scripts/audit-macos-compatibility.py "$app" || {
  echo "MACOS_FLOOR_FAILED: something in the bundle needs a newer macOS than the plist declares" >&2
  exit 1
}

# The bundle contract, run against the finished bundle rather than skipped.
# These eight assertions were written for exactly this moment and had never
# been pointed at a Tauri build: the first run found LSMinimumSystemVersion
# saying 10.13 while the README promised macOS 15, no licence payload, and the
# dead dylib above.
echo "==> bundle contract"
VIENEU_READER_BUNDLE_TEST=1 VIENEU_READER_BUNDLE_PATH="$project_root/$app" \
  .venv/bin/python -m unittest tests.packaging.test_bundle_contract -q || {
  echo "CONTRACT_FAILED: the bundle does not meet its own contract; not packaging" >&2
  exit 1
}

mkdir -p "$out_dir"
rm -f "$artifact"
echo "==> packaging"
ditto -c -k --keepParent "$app" "$artifact"

# The disk image (HIG 3.20 / README): the stapled app beside an Applications
# link, so installing is one drag. Made HERE, after notarization - the
# bundler's own dmg is written at `tauri build`, before this script signs
# and staples the app, and would carry the unstapled one. The image is
# signed, notarized and stapled in its own right; Gatekeeper judges it as
# an "open" target. Developer ID builds only: an ad-hoc dmg would be an
# ad-hoc app in a nicer box.
dmg=""
if [[ -n "$developer_id" ]]; then
  dmg="${artifact%.zip}.dmg"
  echo "==> disk image"
  staging="$(mktemp -d)"
  ditto "$app" "$staging/ReadEase.app"
  ln -s /Applications "$staging/Applications"
  rm -f "$dmg"
  hdiutil create -volname "ReadEase" -srcfolder "$staging" -ov -format UDZO -quiet "$dmg"
  rm -rf "$staging"
  codesign --sign "$developer_id" --timestamp "$dmg"
  if [[ "${READEASE_SKIP_NOTARY:-0}" != "1" ]]; then
    echo "==> notarizing the disk image"
    notarize_wait "$dmg"
    xcrun stapler staple "$dmg" | sed 's/^/    /'
    dmg_verdict="$(spctl -a -t open --context context:primary-signature -vv "$dmg" 2>&1 || true)"
    printf '%s\n' "$dmg_verdict" | sed 's/^/    /'
    if ! grep -q "accepted" <<<"$dmg_verdict"; then
      echo "GATEKEEPER_FAILED: the notarized disk image should be accepted" >&2
      exit 1
    fi
  fi
fi

# The in-app updater's archive (HIG 3.20): the STAPLED app as a tar.gz, a
# minisign signature over it with the updater's private key, and the
# manifest the running app fetches. Not the bundler's updater artifacts:
# those are made at `tauri build`, before signing and stapling, which is
# exactly the wrong bundle to hand an updater. The key lives outside the
# repository (READEASE_UPDATER_KEY_PATH, default ~/.tauri/readease.key) and
# its password only in the environment (TAURI_SIGNING_PRIVATE_KEY_PASSWORD_
# READEASE); neither is ever printed. Without them this step is skipped and
# says so - a release without a manifest is invisible to the updater.
updater_key="${READEASE_UPDATER_KEY_PATH:-$HOME/.tauri/readease.key}"
updater_password="${TAURI_SIGNING_PRIVATE_KEY_PASSWORD_READEASE:-}"
manifest=""
# READEASE_UPDATER_DRYRUN=1 runs the step on a skip-notary build too, to
# prove the tar/sign/manifest chain locally; the manifest it writes names
# an -unnotarized archive that release.sh will refuse.
if [[ -n "$developer_id" && -r "$updater_key" && -n "$updater_password" \
      && ( "${READEASE_SKIP_NOTARY:-0}" != "1" || "${READEASE_UPDATER_DRYRUN:-0}" == "1" ) ]]; then
  echo "==> updater archive"
  tarball="${artifact%.zip}.app.tar.gz"
  rm -f "$tarball" "$tarball.sig"
  COPYFILE_DISABLE=1 tar -czf "$tarball" -C "$(dirname "$app")" "$(basename "$app")"
  ( cd app && TAURI_SIGNING_PRIVATE_KEY_PATH="$updater_key" \
      TAURI_SIGNING_PRIVATE_KEY_PASSWORD="$updater_password" \
      npx tauri signer sign "$project_root/$tarball" >/dev/null )
  [[ -s "$tarball.sig" ]] || { echo "UPDATER_SIGN_FAILED: no signature was written" >&2; exit 1; }
  manifest="$out_dir/latest.json"
  # The release's asset carries the plain name (no build id); the release
  # step copies the tarball to it. Notes = this version's CHANGELOG entry.
  # This version's CHANGELOG entry, with its 72-column wraps undone: a line
  # that is not a bullet continues the one before it, so the updater's
  # sheet (and anything else reading the manifest) gets paragraphs.
  notes="$(awk -v v="## $version" '$0==v{f=1;next} /^## /{f=0} f' CHANGELOG.md \
    | awk 'NF==0{if(p!="")print p; p=""; next} /^- /{if(p!="")print p; p=$0; next} {sub(/^[ \t]+/, ""); p=(p==""?$0:p" "$0)} END{if(p!="")print p}' \
    | head -40)"
  python3 - "$version" "$tarball.sig" "$manifest" "$notes" <<'PY'
import json, sys, datetime
version, sig_path, manifest, notes = sys.argv[1:5]
signature = open(sig_path, encoding="utf-8").read().strip()
json.dump({
    "version": version,
    "notes": notes,
    "pub_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "platforms": {
        "darwin-aarch64": {
            "signature": signature,
            "url": f"https://github.com/wblekhoa/readease/releases/download/v{version}/ReadEase-{version}-arm64.app.tar.gz",
        }
    },
}, open(manifest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
PY
elif [[ -n "$developer_id" && "${READEASE_SKIP_NOTARY:-0}" != "1" ]]; then
  echo "==> updater archive SKIPPED: no updater key/password in the environment (READEASE_UPDATER_KEY_PATH, TAURI_SIGNING_PRIVATE_KEY_PASSWORD_READEASE)"
fi

echo
echo "READY  $artifact"
echo "size   $(du -h "$artifact" | cut -f1)"
echo "sha256 $(shasum -a 256 "$artifact" | cut -d' ' -f1)"
if [[ -n "$dmg" && -s "$dmg" ]]; then echo "dmg    $dmg ($(du -h "$dmg" | cut -f1))"; fi
if [[ -n "$manifest" ]]; then echo "update ${artifact%.zip}.app.tar.gz + .sig + $manifest"; fi
echo
echo "Which build is installed, at any time:"
echo "  /usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' ~/Applications/ReadEase.app/Contents/Info.plist"
echo
echo "Not published by this script: ./scripts/release.sh $version publishes the zip,"
echo "the dmg, the updater archive and latest.json to the GitHub release and checks"
echo "the README links; write dist/release/notes-$version.md first."
