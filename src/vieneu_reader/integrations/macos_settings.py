"""Narrow links into macOS System Settings."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


ACCESSIBILITY_SETTINGS_URL = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
)


def open_accessibility_settings() -> bool:
    """Open Privacy & Security > Accessibility in macOS System Settings."""

    return QDesktopServices.openUrl(QUrl(ACCESSIBILITY_SETTINGS_URL))
