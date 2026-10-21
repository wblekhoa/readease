---
id: readease-logic-notes
type: logic
product: readease
title: "ReadEase — Annotations and note transfer (logic)"
status: active
updated: 2026-10-21
summary: "Saved annotation ownership, highlights and notes made in the Reader, Apple Books projection modes and explicit backup-before-write note transfer between editions."
tags: [area/sync, area/storage, area/book, stack/python, surface/macos]
reqPrefix: RE-NOTE
relations:
  partOf: [readease-system-app]
  implements: [readease:src/vieneu_reader/headless/server.py, readease:src/vieneu_reader/storage/repository.py, readease:app/src/ui/HighlightBar.tsx, readease:app/src/ui/highlightSelection.ts, readease:src/vieneu_reader/integrations/apple_books_sync.py, readease:app/src/screens/Transfer.tsx]
---
# ReadEase — Annotations and note transfer

## Purpose

Keep saved highlights/notes consistent, and let the Reader make its own. Ordinary Apple Books import/sync reads its source; the separate Move notes utility explicitly writes the selected Apple Books destination. Spoken footnotes/citations belong to [reading](reading.md).

## Inputs and outputs

| Operation | Input → result |
|---|---|
| add (`annotations.add`) | `book_id + pieces[{segment_id, selected_text}] + note? + style?` → the kept rows, source `readease` |
| restyle (`annotations.restyle`) | `book_id + annotation_id + style` → `restyled` (only rows made here) |
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
| RE-NOTE-005 | Words selected in the Reader can be kept as a highlight in one of five colours (yellow by default). A selection over several paragraphs is kept as one row per paragraph. Each piece must name a paragraph of that book and words it holds (folded: quotes, spaces, case), or nothing is kept (`annotations:not_in_book`). The rows carry source `readease`, so the Apple Books sync, which replaces only its own rows, never removes them; removing the book removes them. | live | [005](#evidence) |
| RE-NOTE-006 | The bar's Note keeps the highlight, then opens the note on it. A note made with a highlight goes on its first piece. Notes on highlights made here are edited and removed like Books' (RE-NOTE-001). | live | [006](#evidence) |
| RE-NOTE-007 | Pressing a highlight offers its bar: its note, Remove, and - only for one made here - the five colours (`annotations.restyle` answers `restyled: false` for a Books highlight, whose colour the next sync would paint back). A colour change shows at once, and is put back and said if the engine refuses. | live | [007](#evidence) |
| RE-NOTE-008 | The Notes tab copies the book's highlights and notes as Markdown: title, a heading per chapter, each highlight quoted, its note under it, in reading order. The text goes to the pasteboard through the host (`copy_text`, `/usr/bin/pbcopy`); nothing is written to disk. | blocked | [008](#evidence). Not yet run in the built app. |

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

- **005**: `tests/headless/test_server_highlights.py`: `test_a_selection_over_two_paragraphs_is_kept_with_its_note_on_the_first`, `test_the_books_sync_never_takes_a_highlight_made_here`, `test_words_the_paragraph_does_not_hold_are_refused_and_nothing_is_kept`, `test_curled_quotes_and_case_still_find_the_words`. Render audit cell `reader_highlight` selects words with a real drag and draws the bar.
- **006**: `test_a_selection_over_two_paragraphs_is_kept_with_its_note_on_the_first`, `test_a_highlight_made_here_is_removed_and_edited_like_any_other`. Harness run 21/10: Note → editor → Save drew the note icon.
- **007**: `test_only_a_highlight_made_here_changes_colour`. Render audit cell `reader_highlight_mark` keeps a green highlight and presses it. Harness run 21/10: green → pink restyled; a Books highlight's bar showed only Edit note and Remove.
- **008**: `app/tests/annotationsList.test.ts` (`ghi chú ra Markdown theo thứ tự đọc…`). `copy_text` in `app/src-tauri/src/lib.rs`. The browser harness refuses clipboard writes, so the pasteboard path is unverified until the built app runs it.

- **001**: `tests/headless/test_server.py`: `test_a_note_written_here_is_not_overwritten_by_the_next_sync`, `test_a_deleted_highlight_does_not_come_back_on_the_next_sync`, `test_deleting_a_highlight_that_is_not_there_says_so`; `tests/storage/test_annotations.py::test_a_note_can_be_taken_back_and_stays_taken_back`
- **002**: `tests/headless/test_server.py`: `test_apple_books_note_sync_modes_keep_what_was_asked_for`, `test_a_narrower_sync_mode_also_drops_what_it_no_longer_covers`
- **003**: `tests/headless/test_server.py`: `test_notes_transfer_backs_up_then_copies_only_the_copyable`, `test_notes_transfer_reports_all_already_there`; `app/src/screens/Transfer.tsx`; headless `_notes_transfer`
- **004**: `tests/headless/test_server.py`: `test_notes_transfer_refuses_while_books_is_open`, `test_notes_transfer_writes_nothing_when_backup_fails`

Matching coverage: `tests/integrations/test_apple_books_sync.py`. No user database is read/changed by this documentation work.

## Change log
- 2026-10-21: no rule change; `tests/headless/test_server.py` now closes every repository and pipe it opens (test hygiene).

- 2026-10-20: condensed annotation/sync/transfer boundaries; moved document search to its reading owner.
- 2026-10-19: documented existing behavior and narrower-mode replacement semantics.
