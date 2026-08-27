"""Application-owned filesystem locations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vieneu_reader.identity import LEGACY_DATA_DIRECTORY_NAME


def default_app_root() -> Path:
    # Keep the original directory name so the ReadEase rebrand reopens every
    # existing book, model download, cached clip, and saved reading position.
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / LEGACY_DATA_DIRECTORY_NAME
    )


@dataclass(frozen=True, slots=True)
class AppPaths:
    root: Path
    books: Path
    cache: Path
    models: Path
    database: Path

    @classmethod
    def create(cls, root: Path) -> "AppPaths":
        resolved_root = Path(root).expanduser()
        books = resolved_root / "Books"
        cache = resolved_root / "Cache"
        models = resolved_root / "Models"
        for directory in (resolved_root, books, cache, models):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)
        return cls(
            root=resolved_root,
            books=books,
            cache=cache,
            models=models,
            database=resolved_root / "reader.sqlite3",
        )
