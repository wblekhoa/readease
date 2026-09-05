#!/usr/bin/env python3
"""Count the content patterns a book's markup leaves for the voice to trip on.

    uv run python scripts/audit-book-content.py path/to/book.epub
    uv run python scripts/audit-book-content.py "~/Library/Application Support/VieNeu Reader/Books"
    … --json          # machine-readable, one object per book

Read-only: the EPUB is parsed the way import does, nothing is written and the
library database is never opened. This is the measuring half of the
content-pattern work (Apps/ai-memory/plans/readease-content-patterns.md):
a pattern becomes a voice RULE only once these counts say it is common and
its fix is safe. Detectors: vieneu_reader.domain.content_patterns.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vieneu_reader.domain.content_patterns import RULES, Finding, audit_book  # noqa: E402
from vieneu_reader.importers.epub import import_epub  # noqa: E402
from vieneu_reader.importers.epub_presentation import load_epub_presentation  # noqa: E402


def audit_path(path: Path) -> dict:
    book = import_epub(path)
    presentation = load_epub_presentation(path, book)
    findings = audit_book(book, presentation)
    figures = sum(
        len(presentation.chapter(chapter.id).figures)
        for chapter in book.chapters
        if presentation.chapter(chapter.id) is not None
    )
    counts = Counter(finding.kind for finding in findings)
    examples: dict[str, list[str]] = defaultdict(list)
    for finding in findings:
        if len(examples[finding.kind]) < 3 and finding.detail:
            examples[finding.kind].append(finding.detail)
    return {
        "file": path.name,
        "title": book.title,
        "segments": sum(len(chapter.segments) for chapter in book.chapters),
        "figures": figures,
        "counts": dict(sorted(counts.items())),
        "examples": dict(examples),
    }


def print_report(report: dict) -> None:
    print(f"## {report['title']}  ({report['file'][:12]}…)")
    print(f"   segments={report['segments']} figures={report['figures']}")
    for kind, count in report["counts"].items():
        tag = "RULE  " if kind in RULES else "report"
        print(f"   {tag} {kind:<28} {count:>5}")
        for example in report["examples"].get(kind, []):
            print(f"          · {example}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("paths", nargs="+", type=Path, help="EPUB files or folders of them")
    parser.add_argument("--json", action="store_true", help="one JSON object per book")
    arguments = parser.parse_args()

    books: list[Path] = []
    for given in arguments.paths:
        given = given.expanduser()
        books.extend(sorted(given.glob("*.epub")) if given.is_dir() else [given])
    if not books:
        print("no EPUB found", file=sys.stderr)
        return 2

    failures = 0
    for path in books:
        try:
            report = audit_path(path)
        except Exception as error:  # noqa: BLE001 - one bad book, one line
            failures += 1
            print(f"## {path.name}: could not audit ({type(error).__name__}: {error})", file=sys.stderr)
            continue
        if arguments.json:
            print(json.dumps(report, ensure_ascii=False))
        else:
            print_report(report)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
