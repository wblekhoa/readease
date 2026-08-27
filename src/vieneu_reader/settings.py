"""One local settings document shared by the small preference stores."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any


def _read_document(path: Path) -> tuple[dict[str, Any], str | None]:
    """Return the stored settings, plus the raw text if it could not be read."""

    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return {}, None
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        return {}, raw
    if not isinstance(payload, dict):
        return {}, raw
    return payload, None


def load_settings(path: Path) -> dict[str, Any]:
    """Read the settings document, treating any damage as "no settings yet"."""

    return _read_document(path)[0]


def update_settings(path: Path, changes: dict[str, Any]) -> bool:
    """Merge changes into the document so the stores in one app never erase
    each other's keys.

    This is not a cross-process lock. Two copies of ReadEase running at once
    can still overwrite one another's last write, and the loser is not told.
    """

    document, damaged = _read_document(path)
    document.update(changes)
    target = Path(path)
    temp_path: Path | None = None
    try:
        if damaged is not None:
            # Something is in there that this build cannot parse. It may be
            # settings from a newer version; saving one preference must not be
            # what destroys it.
            salvage = target.with_name(target.name + ".damaged")
            salvage.write_text(damaged, encoding="utf-8")
            salvage.chmod(0o600)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, raw_path = tempfile.mkstemp(
            prefix=f".{target.name}.",
            dir=target.parent,
        )
        temp_path = Path(raw_path)
        with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
            json.dump(document, destination)
            destination.write("\n")
            destination.flush()
            os.fsync(destination.fileno())
        temp_path.chmod(0o600)
        os.replace(temp_path, target)
        target.chmod(0o600)
        return True
    except OSError:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        return False
