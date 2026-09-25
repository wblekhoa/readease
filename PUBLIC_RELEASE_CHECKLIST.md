# Release checklist

What ships, per release, all built by `scripts/build-release-app.sh` and
published by `scripts/release.sh`: **a `.zip` of `ReadEase.app`**, **a `.dmg`**
(the app beside an Applications link on a backdrop that says to drag - laid
out by `dmgbuild` from `scripts/dmg-settings.py` and
`assets/branding/dmg-background*.png`, fetched through `uvx`; without `uvx`
the image is the plain pair), **`ReadEase-<v>-arm64.app.tar.gz`** with
its minisign signature for the in-app updater, and **`latest.json`**, the
manifest the running app fetches. Everything is Developer ID-signed and
notarized (since 0.1.2); the dmg is notarized in its own right.

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
.venv/bin/python scripts/audit-public-release.py --strict \
  --bundle app/src-tauri/target/release/bundle/macos/ReadEase.app
```

## What the recipient does

1. Download the `.dmg` (open it, drag `ReadEase.app` into Applications) or the
   `.zip` (unzip, drag).
2. Double-click. Notarized: no Control-click, no prompt beyond the first-open
   "downloaded from the internet" notice.
3. From 0.1.10 on, the app checks for the next release itself (ReadEase menu ›
   Kiểm tra bản mới…, and once, quietly, after launch).
4. Their library, progress, notes and downloaded voices live in
   `~/Library/Application Support/VieNeu Reader/`, outside the bundle, so
   dragging a new build over an old one is an upgrade and not a loss. The
   store migrates forward on open; a store from a NEWER build is refused with
   its own sentence rather than silently downgraded.

Requirements the app declares for itself: Apple Silicon, macOS 15+
(`LSMinimumSystemVersion`, so an older Mac is refused by macOS instead of
failing somewhere confusing).

## Publishing

- Bump the version in the seven files (`app/package.json`, `tauri.conf.json`,
  `Cargo.toml`, `Cargo.lock`, `pyproject.toml`, `uv.lock`, CHANGELOG head) and
  the README download links; commit "Release <v>" on a `release/<v>` branch,
  push it, and once CI is green push the same commit to `main` - `main`
  requires the CI checks (`app`, `engine`) on every commit, so a commit CI has
  not passed is refused. CI runs on every push, so no pull request is needed
  (owner, 25/09).
- Build with the updater key in the environment (`READEASE_UPDATER_KEY_PATH`,
  `TAURI_SIGNING_PRIVATE_KEY_PASSWORD_READEASE`, kept in `Apps/.env`): without
  them the build skips the updater archive and the release is invisible to
  every installed app.
- Write `dist/release/notes-<v>.md` (VI + EN, sha256 + build id).
- `./scripts/release.sh <v>`: tags the commit the bundle was built from (tag
  and `CFBundleVersion` name the same sha), publishes the four assets under
  their plain names, and proves each link's byte count.
- The landing page (`site/`, GitHub Pages) needs nothing per release: its
  download button asks GitHub for the newest release when the page is
  viewed, and falls back to the Releases page. It redeploys itself
  (`.github/workflows/pages.yml`) only when `site/` or the README
  screenshots change on `main`.

## Deliberately not done

- **Intel Macs.** The sidecar and the host are built for arm64 only.
- **Rotating the updater key.** Its public half is in every shipped app; a
  new key means one manual download for everyone. Back up
  `~/.tauri/readease.key` and its password instead.
