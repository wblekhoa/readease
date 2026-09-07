from __future__ import annotations

import unittest
from unittest.mock import patch

from vieneu_reader.integrations.macos_settings import (
    ACCESSIBILITY_SETTINGS_URL,
    open_accessibility_settings,
)


class MacOSSettingsTests(unittest.TestCase):
    def test_accessibility_action_opens_the_exact_system_settings_pane(self) -> None:
        with patch(
            "vieneu_reader.integrations.macos_settings.QDesktopServices.openUrl",
            return_value=True,
        ) as open_url:
            opened = open_accessibility_settings()

        self.assertTrue(opened)
        self.assertEqual(
            open_url.call_args.args[0].toString(),
            ACCESSIBILITY_SETTINGS_URL,
        )


if __name__ == "__main__":
    unittest.main()
