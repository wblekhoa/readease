# Qt and embedded third-party notices

ReadEase's supported bundle uses Qt/PySide 6.11.2 under LGPL-3.0. GNU GPL-3.0
and LGPL-3.0 license texts are preserved in this repository and copied into the
binary license payload.

QtPdf incorporates third-party code from the Chromium/PDFium project. PDFium
and its bundled third-party components retain their upstream copyright and
license notices. The authoritative Qt 6.11.2 module attribution is the
[Qt PDF licensing page](https://doc.qt.io/qt-6/qtpdf-licensing.html); source is
available through the [Qt repositories](https://code.qt.io/cgit/qt/).

Qt Multimedia can load Qt's FFmpeg backend for local audio playback. FFmpeg and
its third-party components retain their upstream notices and are governed by
the configuration shipped in the official Qt/PySide 6.11.2 wheel. ReadEase
does not enable an additional codec or change that binary. See the
[Qt Multimedia licensing documentation](https://doc.qt.io/qt-6/qtmultimedia-index.html)
and [FFmpeg legal page](https://ffmpeg.org/legal.html).

This notice supplements, and does not replace, the complete component license
texts and manifest generated from the actual locked environment. A fresh
bundle audit is required because the applicable third-party set is determined
by the frameworks and plugins that enter that particular binary.
