---
id: readease-logic-library
type: logic
product: readease
title: "ReadEase — Library (logic)"
status: active
updated: 2026-10-20
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
| RE-LIB-001 | Accept only PDF/EPUB; reject other extensions before copying. | live | [001](#evidence) |
| RE-LIB-002 | Copy imports into managed storage without changing the original. | live | [002](#evidence) |
| RE-LIB-003 | Reject files over 200 MiB before making a managed copy. | live | [003](#evidence) |
| RE-LIB-004 | Deduplicate identical content, returning the existing book id. | live | [004](#evidence) |
| RE-LIB-005 | Refuse PDFs without a text layer; no OCR fallback. | live | [005](#evidence) |
| RE-LIB-006 | Refuse encrypted EPUB archive members with a named reason. | live | [006](#evidence) |
| RE-LIB-007 | Remove only the library entry and managed copy; never an external source file. | live | [007](#evidence) |
| RE-LIB-008 | Persist position, rate and voice independently per book. | live | [008](#evidence) |
| RE-LIB-009 | Refuse Apple Books DRM content; font obfuscation alone is permitted. | live | [009](#evidence) |
| RE-LIB-010 | Support OCR-based import of scanned PDFs. | not built | [010](#evidence) |

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

Schema/progress/language: `tests/storage/test_repository.py` (`UpgradingOverAnOlderInstallTests`, `TheFirstRealMigrationTests`). Import rollback: `tests/importers/test_service.py`, `tests/importers/test_pdf.py`, `tests/importers/test_epub.py`. Headless tests use temporary managed files/Apple Books fixtures; live permissions and new Home Finder/drop remain manual acceptance.

## Change log

- 2026-10-20: no rule change; `tests/headless/test_server.py` gained a `selection_translation` settings round-trip and sentence-progress frames (RE-PLAY-023 in reading.md); RE-LIB-007 evidence (`test_import_and_remove_walk_through_the_real_service`) is unchanged.
- 2026-10-20: condensed import/state contract and linked adjacent owners; no behavior change.
- 2026-10-19: reviewed service/storage evidence and schema/language boundaries.
- 2026-10-10: introduced stable requirement IDs.
