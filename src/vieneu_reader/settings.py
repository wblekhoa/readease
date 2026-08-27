"""One local settings document shared by the small preference stores."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any


def load_settings(path: Path) -> dict[str, Any]:
    """Read the settings document, treating any damage as "no settings yet"."""

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def update_settings(path: Path, changes: dict[str, Any]) -> bool:
    """Merge changes into the document so stores never erase each other."""

    document = load_settings(path)
    document.update(changes)
    target = Path(path)
    temp_path: Path | None = None
    try:
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
