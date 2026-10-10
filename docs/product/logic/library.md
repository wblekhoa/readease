---
id: readease-logic-library
type: logic
product: readease
title: "ReadEase — Library (logic)"
status: active
updated: 2026-10-10
reqPrefix: RE-LIB
relations:
  specifiedBy: [readease-ux-library]
  implements: [readease:src/vieneu_reader/importers/service.py, readease:src/vieneu_reader/importers/pdf.py, readease:src/vieneu_reader/importers/epub.py, readease:src/vieneu_reader/storage/repository.py, readease:src/vieneu_reader/integrations/apple_books.py]
---
# ReadEase — Library (logic)

## Purpose
- Turn the reader's own files into readable books safely: never damage or delete the original, never half-import,
  refuse what cannot be read with a reason the reader can act on.
- Success signal: every refused file names its reason; no import leaves a partial copy or a broken entry.

## Rules
| REQ-ID | Rule (behaviour-changing) | Status (live / not built) | Evidence (code path or test) |
|---|---|---|---|
| RE-LIB-001 | Only `.pdf` and `.epub` are accepted; any other file is refused before anything is copied. | live | `tests/importers/test_service.py` (`test_unsupported_extension_is_rejected_without_copying`) |
| RE-LIB-002 | An import copies the file into the app's own library folder; the source file stays where it was, unchanged. | live | `tests/importers/test_service.py` (`test_import_copies_source_into_managed_library`) |
| RE-LIB-003 | A file over 200 MiB is refused before the managed copy is made (`MAX_MANAGED_SOURCE_BYTES`). | live | `src/vieneu_reader/importers/service.py`; `tests/importers/test_service.py` (`test_oversized_source_is_rejected_before_managed_copy`) |
| RE-LIB-004 | Importing a file whose content is already in the library returns the existing book (`was_existing`) and adds no second copy. | live | `tests/importers/test_service.py` (`test_duplicate_import_focuses_existing_managed_book`) |
| RE-LIB-005 | A PDF without a text layer (a scan) is refused with "no text layer; OCR not supported". | live | `src/vieneu_reader/importers/pdf.py`; `tests/importers/test_pdf.py` (`test_textless_pdf_reports_that_ocr_is_not_supported`) |
| RE-LIB-006 | An EPUB whose archive members are encrypted is refused with a named reason. | live | `src/vieneu_reader/importers/epub.py` (`_validate_archive`) |
| RE-LIB-007 | Removing a book deletes its library rows and the app's own copy only; a file outside the library folder is never deleted. | live | `src/vieneu_reader/importers/service.py` (`remove_book`); `tests/headless/test_server.py` (`test_import_and_remove_walk_through_the_real_service`) |
| RE-LIB-008 | Reading progress (position, rate, voice) is stored per book, independently, and updated in place. | live | `tests/storage/test_repository.py` (`test_progress_is_independent_per_book_and_updates_in_place`) |
| RE-LIB-009 | From Apple Books, a book whose reading content is encrypted (DRM) cannot be imported; font obfuscation alone is not treated as DRM. | live | `tests/integrations/test_apple_books_sync.py` (`test_font_obfuscation_is_not_drm_but_encrypted_content_is`) |
| RE-LIB-010 | Scanned PDFs are run through OCR so they can be imported. | not built | README "Limits": no OCR today |

## States and transitions
| State | Trigger | Next state | Edge case |
|---|---|---|---|
| not in library | Open PDF or EPUB / drop / From Apple Books | importing | several files at once are imported one by one under one lock |
| importing | file accepted and copied, row written | in library | database failure removes only the new copy (`test_database_failure_removes_only_the_new_managed_copy`) |
| importing | file refused (type, size, no text, encrypted, damaged) | not in library | the source and library stay unchanged (`test_corrupt_import_leaves_source_and_library_unchanged`) |
| in library | same content imported again | in library (focused) | a damaged row is healed by importing the same file again |
| in library | Remove → confirm | not in library | a damaged row can still be removed |

## Fixed vs flexible
- Fixed (logic the UI must not change): the source file is never modified or deleted; refusals carry a reason; duplicate
  imports never create a second book; limits are enforced in the engine, not only in the interface.
- Flexible (UI may explore): shelf layout, ordering and filtering, how import feedback and the remove confirmation look.

## Open questions
- None recorded.

## Change log
- 2026-10-10: created; REQ-IDs added as comments next to the evidence tests in the same commit.
