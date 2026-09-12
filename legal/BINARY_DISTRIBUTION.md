# Binary distribution

What a ReadEase macOS bundle built from this repository is, and what a person
who receives one may rely on. An engineering receipt, not legal advice.

## The bundle

`ReadEase.app` is built by `scripts/build-release-app.sh`: a Tauri shell (Rust
host, WebKit view) with the Python speech engine frozen by PyInstaller as a
sidecar at `Contents/Resources/engine/`. It is signed ad hoc and is not
notarized; macOS asks once, on first launch, and the READMEs say how to
answer. It links no Qt, no PySide and no copyleft library that would reach
the binary.

## Licences travel with the app

`Contents/Resources/Legal/` carries, for every build:

| File | What it is |
| --- | --- |
| `LICENSE` | PolyForm-Noncommercial-1.0.0, ReadEase's own terms |
| `NOTICE.md` | The required notice and provenance ID |
| `THIRD_PARTY_NOTICES.md` | Human-readable attribution (this repository's copy) |
| `THIRD_PARTY_INVENTORY.md` | Every component in this build, with version, licence, source |
| `THIRD_PARTY_LICENSES.txt` | Every licence text, once, with the components it covers |
| `THIRD_PARTY_MANIFEST.json` | The inventory, machine-readable, bound to `uv.lock` and `Cargo.lock` by SHA-256 |
| `BINARY_DISTRIBUTION.md` | This file |

The inventory is generated from the artefact, not from a list somebody
maintains: the engine's components are read from PyInstaller's table of
contents for the frozen sidecar, the host's from `Cargo.lock`. A component
with no licence text to ship stops the build.

## Obligations this build meets, and how

- **MIT / BSD / ISC / Zlib** (most of the graph): the licence text and the
  copyright notice accompany the binary — `THIRD_PARTY_LICENSES.txt`, with the
  copyright holder named in each section header where the upstream text has
  none of its own.
- **Apache-2.0** (VieNeu SDK, tokenizers, the models, Tauri): the licence
  text is carried; no upstream NOTICE files apply to the components in this
  build.
- **MPL-2.0** (the `symphonia` crates, `certifi`, `tqdm`): the crates ship
  unmodified; the inventory records the repository each one's source is at,
  which is the notice §3.2 requires for an executable form.
- **PyInstaller bootloader** (GPL-2.0-or-later with the Bootloader
  exception): the exception grants that a program frozen with it may be
  distributed under its own terms. `COPYING.txt` is carried.
- **PolyForm-Noncommercial-1.0.0** (ReadEase): noncommercial use, with the
  required notice in `NOTICE.md`, `Info.plist` (`ReadEaseRequiredNotice`) and
  the provenance record.

## Rebuilding

The preferred form for rebuilding is this repository at the commit stamped
into the bundle's `CFBundleVersion` (`<version>+<git sha>`), with `uv.lock`
and `app/src-tauri/Cargo.lock` as the two locks. `scripts/build-release-app.sh`
is the whole path: sidecar, host, payload, provenance, signing, verification,
zip.

## Not done, on purpose

Developer ID signing and notarization. The owner accepted one Control-click →
Open on first launch as the cost of not buying a certificate. If that changes,
it is a separate lane with its own gates; nothing above depends on it.
