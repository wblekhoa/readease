---
id: readease-logic-notes
type: logic
product: readease
title: "ReadEase — Annotations and note transfer (logic)"
status: active
updated: 2026-10-20
summary: "Saved annotation ownership, Apple Books projection modes and explicit backup-before-write note transfer between editions."
tags: [area/sync, area/storage, area/book, stack/python, surface/macos]
reqPrefix: RE-NOTE
relations:
  partOf: [readease-system-app]
  implements: [readease:src/vieneu_reader/headless/server.py, readease:src/vieneu_reader/storage/repository.py, readease:src/vieneu_reader/integrations/apple_books_sync.py, readease:app/src/screens/Transfer.tsx]
---
# ReadEase — Annotations and note transfer

## Purpose

Keep saved highlights/notes consistent. Ordinary Apple Books import/sync reads its source; the separate Move notes utility explicitly writes the selected Apple Books destination. Spoken footnotes/citations belong to [reading](reading.md).

## Inputs and outputs

| Operation | Input → result |
|---|---|
| edit/delete | `book_id + annotation_id` → persistent local override/tombstone |
| sync linked/imported book | matched Apple annotations → replacement projection; report unmatched/skipped |
| transfer | source/destination editions → plan, confirmed backup/copy, outcome |

## Rules

| REQ-ID | Rule | Status | Evidence |
|---|---|---|---|
| RE-NOTE-001 | Persist local note overrides and deletion tombstones across sync; report absent annotations explicitly. | live | [001](#evidence) |
| RE-NOTE-002 | Replace the linked Apple Books annotation projection according to the chosen sync mode, preserving local overrides/tombstones. | live | [002](#evidence) |
| RE-NOTE-003 | Confirm, recompute and back up before copying eligible notes between Apple Books editions; preserve source and deduplicate destination. | live | [003](#evidence) |
| RE-NOTE-004 | Write no transferred item while Apple Books is open or backup creation fails. | live | [004](#evidence) |

## States and recovery

| Action | Result / boundary |
|---|---|
| edit note, including empty | local override survives sync; missing id returns `updated: false`, failure stays visible |
| delete | tombstone prevents resurrection; absent id returns `removed: false` |
| sync `both` / `highlights` / `notes` | matched passages+notes / passages without note text / only passages carrying notes |
| narrower sync mode | remove previously mirrored rows outside mode; not append-only; preserve local overrides/tombstones |
| invalid mode/unlinked book | refuse; never guess an import |
| Preview transfer | plan only; non-copyable items excluded |
| confirm | recompute → backup → deduplicated copy; all-already-present is successful no-op; never delete source |
| Books open / backup failure | zero writes; resolve condition then retry |

Matching uses normalized selected text and chapter/CFI evidence, with stable source IDs. Unmatched words/bookmarks are reported, never placed on arbitrary segments. Live Apple Books permission/database compatibility remains separate from injected-fixture tests.

## Evidence

- **001**: `tests/headless/test_server.py`: `test_a_note_written_here_is_not_overwritten_by_the_next_sync`, `test_a_deleted_highlight_does_not_come_back_on_the_next_sync`, `test_deleting_a_highlight_that_is_not_there_says_so`; `tests/storage/test_annotations.py::test_a_note_can_be_taken_back_and_stays_taken_back`
- **002**: `tests/headless/test_server.py`: `test_apple_books_note_sync_modes_keep_what_was_asked_for`, `test_a_narrower_sync_mode_also_drops_what_it_no_longer_covers`
- **003**: `tests/headless/test_server.py`: `test_notes_transfer_backs_up_then_copies_only_the_copyable`, `test_notes_transfer_reports_all_already_there`; `app/src/screens/Transfer.tsx`; headless `_notes_transfer`
- **004**: `tests/headless/test_server.py`: `test_notes_transfer_refuses_while_books_is_open`, `test_notes_transfer_writes_nothing_when_backup_fails`

Matching coverage: `tests/integrations/test_apple_books_sync.py`. No user database is read/changed by this documentation work.

## Change log

- 2026-10-20: condensed annotation/sync/transfer boundaries; moved document search to its reading owner.
- 2026-10-19: documented existing behavior and narrower-mode replacement semantics.
