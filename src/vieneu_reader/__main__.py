from __future__ import annotations

import os
from pathlib import Path
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from vieneu_reader.ui.theme import apply_theme
from vieneu_reader.identity import PRODUCT_NAME
from vieneu_reader.provenance import apply_provenance
from vieneu_reader.ui.app import build_runtime


def main() -> int:
    """Launch the native ReadEase application."""

    data_root = os.environ.get("VIENEU_READER_DATA_ROOT")
    resolved_data_root = Path(data_root) if data_root else None
    if os.environ.get("VIENEU_READER_TTS_SELF_CHECK") == "1":
        from vieneu_reader.speech.self_check import run_tts_self_check

        return run_tts_self_check(resolved_data_root)

    application = QApplication.instance() or QApplication(sys.argv)
    application.setApplicationDisplayName(PRODUCT_NAME)
    application.setApplicationName(PRODUCT_NAME)
    application.setOrganizationName("DOL English")
    apply_theme(application)
    apply_provenance(application)
    runtime = build_runtime(resolved_data_root)
    application.aboutToQuit.connect(runtime.close)
    runtime.window.show()
    smoke_quit_ms = os.environ.get("VIENEU_READER_SMOKE_QUIT_MS")
    if smoke_quit_ms:
        QTimer.singleShot(max(1, int(smoke_quit_ms)), application.quit)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
