"""The look of the app, written once, in the design system's own values.

Qt Widgets inherit the macOS palette by default. That gives free light/dark
switching, but it also means the app cannot have its own neutral ramp and
cannot round anything: a native control draws its own corners. Taking the paint
over is all-or-nothing - a half-styled Qt app reads worse than either extreme -
so this module owns every surface, control and state, in both appearances.

Values come from the DOL DS token file (`DOL-DS-token/studio/public/tokens.css`,
`--light-neutral-*` / `--dark-neutral-*`). They are copied rather than fetched
because the app ships without the design repo; `NEUTRAL` is the one place to
edit when the ramp moves.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

# DS neutral ramp, verbatim. Light is cool-tinted; macOS's own window grey is
# warmer and brighter, which is what made the app look washed out.
NEUTRAL: dict[str, dict[str, str]] = {
    "light": {
        "n00": "#FFFFFF",
        "n05": "#F6F7F9",
        "n10": "#F0F2F5",
        "n20": "#E1E5EA",
        "n40": "#C8CFD6",
        "n60": "#AAB4BF",
        "n80": "#8997A5",
        "n100": "#6C7885",
        "n120": "#55606B",
        "n140": "#444C56",
        "n200": "#21262D",
    },
    "dark": {
        "n00": "#1C1D1E",
        "n05": "#212222",
        "n10": "#262727",
        "n20": "#2D2E2E",
        "n40": "#363637",
        "n60": "#444546",
        "n80": "#6F7173",
        "n100": "#8D8F91",
        "n120": "#AAABAC",
        "n140": "#CCCDCD",
        "n200": "#FFFFFF",
    },
}

# DS brand red. Already the app's one accent, on figure labels.
BRAND = "#D42525"
BRAND_PRESSED = "#B31F1F"

# Radius is stepped, never flat: surfaces read rounder than the controls
# sitting inside them (DS direction: 24 > 16 > 8-12).
RADIUS_SURFACE = 12
RADIUS_CONTROL = 8
RADIUS_SMALL = 6

# One height for every control on a row, so a toolbar reads as a single line
# instead of a row of differently sized boxes.
CONTROL_HEIGHT = 30


def _roles(mode: str) -> dict[str, str]:
    ramp = NEUTRAL[mode]
    dark = mode == "dark"
    return {
        # The desk the paper sits on. Deeper than macOS grey on purpose: white
        # content needs something to sit against or the screen reads as one
        # flat bright field.
        "desk": ramp["n20"] if not dark else ramp["n00"],
        "paper": ramp["n00"] if not dark else ramp["n05"],
        "raised": ramp["n05"] if not dark else ramp["n10"],
        "control": ramp["n00"] if not dark else ramp["n20"],
        "control_hover": ramp["n05"] if not dark else ramp["n40"],
        "control_pressed": ramp["n10"] if not dark else ramp["n60"],
        "line": ramp["n40"] if not dark else ramp["n40"],
        "line_soft": ramp["n20"] if not dark else ramp["n20"],
        "text": ramp["n200"],
        # Measured against the desk, not chosen by eye: n100 gave secondary text
        # only 3.56:1 in light, under the 4.5 a label needs.
        "text_muted": ramp["n120"] if not dark else ramp["n100"],
        "text_disabled": ramp["n80"],
        "selection": BRAND,
        "on_selection": "#FFFFFF",
        # Must differ from the desk it sits on: n20 IS the light desk, so a
        # selected row painted with it disappeared.
        "selected_row": ramp["n40"] if not dark else ramp["n40"],
        # The segmented track behind the tabs, following the DS
        # ToggleButtonGroup: a tinted rail with the active item raised out of it.
        "track": ramp["n10"],
        "text_inactive": ramp["n140"],
        # The band on the sentence being read. It rides on paper, so it has to
        # differ from paper without becoming a second surface.
        "reading_band": ramp["n10"] if not dark else ramp["n20"],
        "danger": "#C34116" if not dark else "#E16B44",
    }


def stylesheet(mode: str) -> str:
    """The whole app's paint, for one appearance."""
    c = _roles(mode)
    return f"""
/* ---- page ---------------------------------------------------------- */
QWidget {{
    background: {c['desk']};
    color: {c['text']};
}}
QLabel {{ background: transparent; }}
QLabel:disabled {{ color: {c['text_disabled']}; }}
QStackedWidget, QSplitter {{ background: transparent; }}
QSplitter::handle {{ background: transparent; }}

/* ---- reading surface ----------------------------------------------- */
QTextBrowser#readerText {{
    background: {c['paper']};
    border: 1px solid {c['line_soft']};
    border-radius: {RADIUS_SURFACE}px;
}}
QPlainTextEdit, QTextEdit {{
    background: {c['paper']};
    border: 1px solid {c['line']};
    border-radius: {RADIUS_CONTROL}px;
    padding: 8px;
    selection-background-color: {c['selection']};
    selection-color: {c['on_selection']};
}}
QPlainTextEdit:focus, QTextEdit:focus {{ border-color: {c['selection']}; }}

/* ---- lists --------------------------------------------------------- */
QListWidget {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{
    padding: 7px 10px;
    border-radius: {RADIUS_SMALL}px;
    color: {c['text']};
}}
QListWidget::item:hover {{ background: {c['raised']}; }}
QListWidget::item:selected {{
    /* Brand red is the identity and the primary action, not a row cursor.
       A filled neutral plus weight says "you are here" without shouting. */
    background: {c['selected_row']};
    color: {c['text']};
    font-weight: 600;
}}

/* ---- buttons ------------------------------------------------------- */
QPushButton, QToolButton {{
    background: {c['control']};
    border: 1px solid {c['line']};
    border-radius: {RADIUS_CONTROL}px;
    padding: 0 12px;
    min-height: {CONTROL_HEIGHT}px;
    color: {c['text']};
}}
QToolButton {{ padding: 0 8px; }}
QPushButton:hover, QToolButton:hover {{ background: {c['control_hover']}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {c['control_pressed']}; }}
QPushButton:disabled, QToolButton:disabled {{
    color: {c['text_disabled']};
    border-color: {c['line_soft']};
    background: transparent;
}}
QPushButton:focus, QToolButton:focus {{ border-color: {c['selection']}; }}
QPushButton#prepareModelButton {{
    background: {BRAND};
    border-color: {BRAND};
    color: #FFFFFF;
    font-weight: 600;
    padding: 0 20px;
}}
QPushButton#prepareModelButton:hover {{ background: {BRAND_PRESSED}; }}
QPushButton#prepareModelButton:pressed {{ background: {BRAND_PRESSED}; }}
QToolButton::menu-indicator {{ image: none; width: 0; }}

/* ---- dropdowns ----------------------------------------------------- */
QComboBox {{
    background: {c['control']};
    border: 1px solid {c['line']};
    border-radius: {RADIUS_CONTROL}px;
    padding: 0 8px;
    min-height: {CONTROL_HEIGHT}px;
    color: {c['text']};
}}
QComboBox:hover {{ background: {c['control_hover']}; }}
QComboBox:focus {{ border-color: {c['selection']}; }}
QComboBox:disabled {{ color: {c['text_disabled']}; border-color: {c['line_soft']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {c['paper']};
    border: 1px solid {c['line']};
    border-radius: {RADIUS_CONTROL}px;
    padding: 4px;
    selection-background-color: {c['selection']};
    selection-color: {c['on_selection']};
}}

/* ---- tabs: DS ToggleButtonGroup, style-1 --------------------------- */
/* Tinted rail, active item raised out of it as a bordered pill. Radius is
   nested (track 12, item 9 inside 3px of padding) so the corners sit
   concentric instead of fighting each other. The rail is exactly as tall as
   the buttons beside it, so the whole row reads on one line. */
QTabBar {{
    background: {c['track']};
    border-radius: {RADIUS_SURFACE}px;
    padding: 3px;
}}
QTabBar::tab {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {RADIUS_CONTROL - 2}px;
    padding: 0 12px;
    min-height: 24px;
    margin: 0 1px;
    color: {c['text_inactive']};
    font-weight: 600;
}}
QTabBar::tab:hover {{ background: {c['control_hover']}; color: {c['text']}; }}
QTabBar::tab:selected {{
    background: {c['paper']};
    border-color: {c['line']};
    color: {c['text']};
}}

/* ---- menus --------------------------------------------------------- */
QMenu {{
    background: {c['paper']};
    border: 1px solid {c['line']};
    border-radius: {RADIUS_CONTROL}px;
    padding: 4px;
}}
QMenu::item {{ padding: 6px 12px; border-radius: {RADIUS_SMALL}px; }}
QMenu::item:selected {{ background: {c['selection']}; color: {c['on_selection']}; }}

/* ---- progress ------------------------------------------------------ */
QProgressBar {{
    background: {c['line_soft']};
    border: none;
    border-radius: {RADIUS_SMALL}px;
    min-height: 12px;
    max-height: 12px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {BRAND};
    border-radius: {RADIUS_SMALL}px;
}}

/* ---- rules --------------------------------------------------------- */
QFrame#playerRule {{ background: {c['line_soft']}; border: none; }}

/* ---- scrollbars ---------------------------------------------------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background: {c['line']};
    border-radius: 5px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: {c['text_muted']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollBar:horizontal {{ height: 0; }}
"""


def current_mode() -> str:
    """Which appearance macOS is in right now."""
    hints = QGuiApplication.styleHints()
    scheme = getattr(hints, "colorScheme", None)
    if scheme is not None and scheme() == Qt.ColorScheme.Dark:
        return "dark"
    return "light"


def palette(mode: str) -> QPalette:
    """The same values, for code that asks the palette instead of the sheet.

    The reader draws the sentence it is speaking with `AlternateBase` and its
    figure placeholders with `PlaceholderText`. Styling only the sheet left
    those roles on the system defaults, which in dark mode painted a white band
    under white text.
    """
    c = _roles(mode)
    result = QPalette()
    pairs = (
        (QPalette.ColorRole.Window, c["desk"]),
        (QPalette.ColorRole.WindowText, c["text"]),
        (QPalette.ColorRole.Base, c["paper"]),
        (QPalette.ColorRole.AlternateBase, c["reading_band"]),
        (QPalette.ColorRole.Text, c["text"]),
        (QPalette.ColorRole.Button, c["control"]),
        (QPalette.ColorRole.ButtonText, c["text"]),
        (QPalette.ColorRole.Highlight, c["selection"]),
        (QPalette.ColorRole.HighlightedText, c["on_selection"]),
        (QPalette.ColorRole.PlaceholderText, c["text_muted"]),
        (QPalette.ColorRole.ToolTipBase, c["paper"]),
        (QPalette.ColorRole.ToolTipText, c["text"]),
        # The error label reads its colour from LinkVisited, so that role has
        # to carry the danger tone rather than a link tone.
        (QPalette.ColorRole.Link, c["selection"]),
        (QPalette.ColorRole.LinkVisited, c["danger"]),
    )
    for role, value in pairs:
        result.setColor(role, QColor(value))
    for role, value in (
        (QPalette.ColorRole.WindowText, c["text_disabled"]),
        (QPalette.ColorRole.Text, c["text_disabled"]),
        (QPalette.ColorRole.ButtonText, c["text_disabled"]),
    ):
        result.setColor(QPalette.ColorGroup.Disabled, role, QColor(value))
    return result


def apply_theme(application: QApplication) -> None:
    """Paint the app, and repaint it when macOS switches appearance.

    Set `READEASE_NATIVE_STYLE=1` to skip all of this and let Qt draw with the
    macOS style instead. That is the honest A/B for "should we follow Apple's
    look?": one run each, same build, same window.
    """
    if os.environ.get("READEASE_NATIVE_STYLE") == "1":
        return
    # QSS is only fully honoured by a style that defers to it. The macOS style
    # draws several controls itself and would ignore half of the rules above,
    # which is exactly the half-styled result this module exists to avoid.
    application.setStyle(QStyleFactory.create("Fusion"))
    application.setPalette(palette(current_mode()))
    application.setStyleSheet(stylesheet(current_mode()))

    hints = QGuiApplication.styleHints()
    changed = getattr(hints, "colorSchemeChanged", None)
    if changed is not None:
        changed.connect(lambda _scheme: _repaint(application))


def _repaint(application: QApplication) -> None:
    mode = current_mode()
    application.setPalette(palette(mode))
    application.setStyleSheet(stylesheet(mode))
