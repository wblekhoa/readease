# Release checklist

What we actually ship, as of 2026-09-04: **a `.zip` of `ReadEase.app`**, built by
`scripts/build-release-app.sh`, ad-hoc signed, published by hand on GitHub
Releases, installed by dragging into `/Applications`.

Everything below describes THAT path. The Qt/Nuitka checklist this file used to
carry described a build we no longer make - it asked for a Nuitka compilation
report, QtPdf, and `Install ReadEase.command`, none of which exist in the
shipped app. Following it would have meant doing the wrong work carefully.

## Build the candidate

```bash
./scripts/build-release-app.sh
```

One command, and it refuses to hand over a broken artifact. In order it:

1. rebuilds the engine sidecar if any Python source is newer than the frozen
   binary (a stale sidecar ships silently otherwise);
2. runs `pnpm tauri build`;
3. writes the licence payload into `Contents/Resources/Legal` and the
   provenance record into `Contents/Resources/Provenance`, plus the
   `ReadEase*` keys in `Info.plist`;
4. drops the ONNX Runtime dylib nothing links - 32 MB the recipient would
   download for nothing;
5. stamps `CFBundleVersion` as `<version>+<git sha>` so "did my update take?"
   has an answer;
6. re-signs ad hoc, then **verifies** - `tauri build` leaves a signature that
   does not verify, and a downloaded copy of that is "damaged and can't be
   opened", with no Open Anyway;
7. runs the bundle contract (`tests/packaging/test_bundle_contract.py`)
   against the finished bundle;
8. packs with `ditto`, which preserves the signature and symlinks that
   `zip` can lose.

Any of 6-7 failing stops the script before it packages anything.

## What the recipient does

1. Download the `.zip` from the Release and unzip it.
2. Drag `ReadEase.app` into `/Applications`.
3. First launch: Control-click the app → **Open** → **Open**. One prompt, once.
   This is the ordinary un-notarized dialog, not the "damaged" one.
4. Their library, progress, notes and downloaded voices live in
   `~/Library/Application Support/VieNeu Reader/`, outside the bundle, so
   dragging a new build over an old one is an upgrade and not a loss. The
   store migrates forward on open; a store from a NEWER build is refused with
   its own sentence rather than silently downgraded.

Requirements the app now declares for itself: Apple Silicon, macOS 15+
(`LSMinimumSystemVersion`, so an older Mac is refused by macOS instead of
failing somewhere confusing).

## Needs the owner - never done automatically

- **Creating the GitHub Release and uploading the `.zip`.** The build script
  prints the path, size and sha256 and stops there.
- **Developer ID signing and notarization.** Deliberately not done: the owner
  accepted one Control-click → Open as the cost. If that ever changes, it is a
  separate lane with its own gates.
- **Merging the release branch** into `main`.

## Known gaps, named rather than forgotten

- **The machine-auditable components manifest is not regenerated for this
  build.** `scripts/package-license-payload.py` derives its component list from
  a Nuitka compilation report, and the sidecar is PyInstaller now. The bundle
  carries the three static, always-true documents (`LICENSE`, `NOTICE.md`,
  `THIRD_PARTY_NOTICES.md`) plus the provenance record; the generated
  `THIRD_PARTY_MANIFEST.json` and its receipts are still Qt-era work. The
  bundle contract says so out loud rather than passing quietly.
- **No notarization**, as above.
- The legacy source-sharing path (`scripts/export-public-source.py`,
  `Install ReadEase.command`) still exists and still builds the OLD Qt shell.
  It is superseded by this document and goes away with the rest of the Qt
  shell in P6.
