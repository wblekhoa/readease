# Release checklist

What ships: **a `.zip` of `ReadEase.app`**, built by
`scripts/build-release-app.sh`, ad-hoc signed, published on GitHub Releases,
installed by dragging into Applications.

## Build the candidate

```bash
./scripts/build-release-app.sh
```

One command, and it refuses to hand over a broken artefact. In order it:

1. rebuilds the engine sidecar if any Python source is newer than the frozen
   binary (a stale sidecar ships silently otherwise);
2. runs `pnpm tauri build`;
3. generates the licence payload into `Contents/Resources/Legal` from the
   frozen engine's table of contents and `Cargo.lock`
   (`scripts/package-license-payload.py`), and the provenance record into
   `Contents/Resources/Provenance`, plus the `ReadEase*` keys in `Info.plist`;
4. drops the ONNX Runtime dylib nothing links - 32 MB the recipient would
   download for nothing;
5. stamps `CFBundleVersion` as `<version>+<git sha>` so "did my update take?"
   has an answer;
6. re-signs ad hoc, then **verifies** - `tauri build` leaves a signature that
   does not verify, and a downloaded copy of that is "damaged and can't be
   opened", with no Open Anyway;
7. runs the bundle contract (`tests/packaging/test_bundle_contract.py`)
   against the finished bundle, including that every crate in `Cargo.lock`
   is in the shipped inventory;
8. packs with `ditto`, which preserves the signature and symlinks that
   `zip` can lose.

Any of 3, 6 or 7 failing stops the script before it packages anything.

Then, against the finished bundle:

```bash
.venv/bin/python scripts/audit-public-release.py --strict --bundle dist/ReadEase.app
```

## What the recipient does

1. Download the `.zip` from the Release and unzip it.
2. Drag `ReadEase.app` into Applications.
3. First launch: Control-click the app → **Open** → **Open**. One prompt, once.
   This is the ordinary un-notarized dialog, not the "damaged" one.
4. Their library, progress, notes and downloaded voices live in
   `~/Library/Application Support/VieNeu Reader/`, outside the bundle, so
   dragging a new build over an old one is an upgrade and not a loss. The
   store migrates forward on open; a store from a NEWER build is refused with
   its own sentence rather than silently downgraded.

Requirements the app declares for itself: Apple Silicon, macOS 15+
(`LSMinimumSystemVersion`, so an older Mac is refused by macOS instead of
failing somewhere confusing).

## Publishing

- Tag the commit the bundle was built from; the tag and `CFBundleVersion`
  must name the same sha.
- Create the GitHub Release with the `.zip` and the sha256 the build printed.
- Fast-forward `main` to that commit: the default branch is what a stranger
  reads.

## Deliberately not done

- **Developer ID signing and notarization.** The owner accepted one
  Control-click → Open as the cost. If that ever changes, it is a separate
  lane with its own gates.
- **Intel Macs.** The sidecar and the host are built for arm64 only.
