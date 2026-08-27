# Binary distribution and LGPL compliance

This document describes the intended compliance path for a ReadEase macOS
binary built from this repository. It is an engineering receipt, not legal
advice and not a statement that an unsigned local build has been published.

## Selected license path

ReadEase first-party source and scaffold use
PolyForm-Noncommercial-1.0.0. The supported macOS bundle dynamically links
Qt 6.11.2 through PySide6 under the LGPL-3.0 option. QtPdf is used under its
LGPL-3.0 option. The complete GPL-3.0 and LGPL-3.0 texts are included in the
generated `Legal/THIRD_PARTY_LICENSES.txt` payload because LGPL-3.0 supplements
GPL-3.0.

The app does not use or intentionally package Qt Virtual Keyboard. The bundle
audit fails if `QtVirtualKeyboard`, `QtVirtualKeyboardQml`, or the virtual
keyboard platform plugin appears. Voice cloning is not a ReadEase feature;
optional VieNeu cloning dependencies such as soxr, SoundFile, and
kaldi-native-fbank are excluded from the supported bundle. Reintroducing one of
them requires a new license and relinking audit.

## Replacement, relink, and reverse engineering

Qt dynamic libraries are emitted beside the executable under
`ReadEase.app/Contents/MacOS`. A recipient may replace compatible LGPL
libraries, rebuild or relink the application from the corresponding source and
locked build scripts, and reverse engineer the binary when necessary to debug
such modifications. The ReadEase license and provenance marker do not restrict
those LGPL rights. Replacing a library invalidates an Apple code signature; a
locally modified bundle can be signed ad-hoc by its recipient.

The source code, `uv.lock`, `pysidedeploy.spec`, and scripts in this repository
are the preferred form for rebuilding ReadEase. Exact component versions,
license receipts, source locations, and the Nuitka compilation-report digest
are recorded in `Legal/THIRD_PARTY_MANIFEST.json` for each build.

## Corresponding source code

- Qt/PySide 6.11.2 source: <https://code.qt.io/cgit/pyside/pyside-setup.git/> and
  <https://code.qt.io/cgit/qt/>.
- QtPdf/PDFium licensing: <https://doc.qt.io/qt-6/qtpdf-licensing.html>.
- VieNeu SDK and runtime model sources are identified at exact revisions in
  `THIRD_PARTY_NOTICES.md` and the generated manifest.
- Python distribution sources and license receipts are derived from the locked
  environment and fresh Nuitka report by `scripts/package-license-payload.py`.

Anyone distributing a ReadEase binary must make the corresponding source code
and relink instructions available for at least the period required by the
applicable license. Developer ID signing and Apple notarization do not replace
these obligations.

## Release boundary

The local ad-hoc bundle is for verification. A public binary remains held until
the strict public-release audit passes against a fresh bundle and compilation
report, Developer ID signing/notarization is completed, and the publisher has
reviewed trademark, voice/model provenance, and LGPL source-offer obligations.
