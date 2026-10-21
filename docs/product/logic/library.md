---
id: readease-logic-library
type: logic
product: readease
title: "ReadEase — Library (logic)"
status: active
updated: 2026-10-21
summary: "Managed PDF/EPUB import, duplicate and failure handling, language/progress ownership, schema boundaries and the Apple Books import boundary."
tags: [area/data-import, area/storage, area/book, stack/python, surface/macos]
reqPrefix: RE-LIB
relations:
  specifiedBy: [readease-ux-library]
  implements: [readease:src/vieneu_reader/importers/service.py, readease:src/vieneu_reader/importers/pdf.py, readease:src/vieneu_reader/importers/epub.py, readease:src/vieneu_reader/storage/repository.py, readease:src/vieneu_reader/integrations/apple_books.py]
---
# ReadEase — Library

## Purpose

Import/remove documents safely, preserving originals and durable book state. [Home](home.md) owns entry routing; [reading](reading.md) owns heard acknowledgements; [notes](notes.md) owns annotation mirroring and explicit Apple Books writes.

## Inputs and outputs

`library.import(path)` returns `book_id`, title, format and `was_existing`. The caller chooses navigation: Home/Finder opens the result; Library shows aggregate added/existing/refused feedback. Import never implies autoplay.

| Stored item | Owner / behavior |
|---|---|
| source file → managed copy + SQLite row | service validates format, size and readability before commit |
| progress | segment/rate/voice per book; last-heard changes only with heard progress |
| book language | explicit supported override or withdrawal to detected answer; opening does not force a voice change |
| Apple Books link | asset → ReadEase book id; temporary packing for unpacked EPUB; source book unchanged |

## Rules

| REQ-ID | Rule | Status | Evidence |
|---|---|---|---|
| RE-LIB-001 | Accept only the supported formats (PDF, EPUB, and since RE-LIB-011 the text documents); reject other extensions before copying. | live | [001](#evidence) |
| RE-LIB-002 | Copy imports into managed storage without changing the original. | live | [002](#evidence) |
| RE-LIB-003 | Reject files over 200 MiB before making a managed copy. | live | [003](#evidence) |
| RE-LIB-004 | Deduplicate identical content, returning the existing book id. | live | [004](#evidence) |
| RE-LIB-005 | Refuse PDFs without a text layer; no OCR fallback. | live | [005](#evidence) |
| RE-LIB-006 | Refuse encrypted EPUB archive members with a named reason. | live | [006](#evidence) |
| RE-LIB-007 | Remove only the library entry and managed copy; never an external source file. | live | [007](#evidence) |
| RE-LIB-008 | Persist position, rate and voice independently per book. | live | [008](#evidence) |
| RE-LIB-009 | Refuse Apple Books DRM content; font obfuscation alone is permitted. | live | [009](#evidence) |
| RE-LIB-010 | Support OCR-based import of scanned PDFs. | not built | [010](#evidence) |
| RE-LIB-011 | Import text documents as books: `.txt`, `.md`, `.html` and `.docx` with the standard library, `.doc`, `.rtf` and `.odt` through macOS `textutil` (to HTML, so text and paragraphs survive). Headings become chapters (Markdown `#`/`##`, HTML `h1`/`h2`, Word `Heading 1/2` and `Title`); a document without marked headings splits at short lines of their own like "Chương 3" / "Part II" - the keyword must be followed by a number (digits, roman, or a number word), so a sentence like "Hồi đó…" or "Chương trình…" stays text, and a chapter line with no body (a contents list) is kept as text rather than dropped. HTML marked `hidden`/`aria-hidden` is not read. A first heading that is itself a chapter line ("# Chương 1", `<h1>Chương 1</h1>`) is the first chapter, not the book's title; the title then comes from the file name. A title may follow after a separator ("Chương 1: Hà Nội") or, when the number is a numeral, after a space if it opens with a capital and the line does not end like a sentence ("Chương 1 Hà Nội", "Part II The Road"); "Hồi 5 giờ sáng tôi dậy." and "Hồi năm ngoái…" stay text. UTF-8 (BOM or not) and UTF-16 with a BOM are read; any other encoding is refused in words, never guessed. Text sources are capped at 20 MB; Word's main part at 100 MB with an element bound and no XML entity declarations. Each format is its own `source_format`, equal to its canonical suffix; `.markdown`, `.htm`/`.xhtml` and `.text` are read as `.md`, `.html` and `.txt` and kept under that suffix. | live | [011](#evidence) |

## States and recovery

| Event | Result / safety boundary |
|---|---|
| supported readable import | commit managed file/row; deduplicate or heal damaged existing entry |
| per-file import failure | preserve original/existing good import; remove only new partial work |
| multi-file gesture | attempt serially/independently; one refusal does not roll back other successes |
| missing/DRM/oversized Apple Books content | named refusal; never bypass protection |
| older supported schema | ordered migration; failed step leaves original store unchanged |
| future/malformed schema | refuse rather than guess a rewrite |
| remove damaged or readable book | delete own row/copy; never the external source |

No OCR, DRM bypass or fixed-layout EPUB support. Home queue recovery is documented only in its [owner](home.md#states-and-recovery).

## Evidence

- **001**: `tests/importers/test_service.py` (`test_unsupported_extension_is_rejected_without_copying`)
- **002**: `tests/importers/test_service.py` (`test_import_copies_source_into_managed_library`)
- **003**: `src/vieneu_reader/importers/service.py`; `tests/importers/test_service.py` (`test_oversized_source_is_rejected_before_managed_copy`)
- **004**: `tests/importers/test_service.py` (`test_duplicate_import_focuses_existing_managed_book`)
- **005**: `src/vieneu_reader/importers/pdf.py`; `tests/importers/test_pdf.py` (`test_textless_pdf_reports_that_ocr_is_not_supported`)
- **006**: `src/vieneu_reader/importers/epub.py` (`_validate_archive`)
- **007**: `src/vieneu_reader/importers/service.py` (`remove_book`); `tests/headless/test_server.py` (`test_import_and_remove_walk_through_the_real_service`)
- **008**: `tests/storage/test_repository.py` (`test_progress_is_independent_per_book_and_updates_in_place`)
- **009**: `tests/integrations/test_apple_books_sync.py` (`test_font_obfuscation_is_not_drm_but_encrypted_content_is`)
- **010**: README "Limits": no OCR today
- **011**: `src/vieneu_reader/importers/text.py`; `tests/importers/test_text.py` (every format, encodings, empty refusal, unsafe docx, damaged rtf, and the managed round trip `test_a_markdown_book_is_managed_reopened_and_reimported_as_the_same_book`); `app/tests/bookPaths.test.ts`. Probe 20/10: `.docx`/`.doc`/`.rtf`/`.odt` written by macOS itself import with their "Chương N" chapters. Frozen sidecar 21/10: the built `readease-engine`, driven over the protocol with a temp data root, imported `.docx`, `.doc`, `.rtf`, `.odt`, `.htm`, `.markdown` and `.txt` with their chapters, and reported the translator block.

Schema/progress/language: `tests/storage/test_repository.py` (`UpgradingOverAnOlderInstallTests`, `TheFirstRealMigrationTests`). Import rollback: `tests/importers/test_service.py`, `tests/importers/test_pdf.py`, `tests/importers/test_epub.py`. Headless tests use temporary managed files/Apple Books fixtures; live permissions and new Home Finder/drop remain manual acceptance.

## Change log

- 2026-10-21: a chapter-line first heading is a chapter, not the title; frozen-sidecar evidence added.
- 2026-10-21: RE-LIB-011 audit fixes - chapter lines need a number; bodiless chapter lines kept as text; hidden HTML skipped; a document with no title of its own names its chapter after the file, not the temp copy.
- 2026-10-21: RE-LIB-011 - text documents (TXT, Markdown, HTML, Word, RTF, ODT) import as books; RE-LIB-001 widened to match.

- 2026-10-20: no rule change; `tests/headless/test_server.py` gained a `selection_translation` settings round-trip and sentence-progress frames (RE-PLAY-023 in reading.md); RE-LIB-007 evidence (`test_import_and_remove_walk_through_the_real_service`) is unchanged.
- 2026-10-20: condensed import/state contract and linked adjacent owners; no behavior change.
- 2026-10-19: reviewed service/storage evidence and schema/language boundaries.
- 2026-10-10: introduced stable requirement IDs.
