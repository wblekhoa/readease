---
id: readease-logic-history
type: logic
product: readease
title: "ReadEase — Paste and scan history"
status: active
updated: 2026-10-22
summary: "What pasted and scanned text is kept on this Mac, for how long, how it is deduplicated and deleted, and the switch that stops it."
tags: [area/storage, area/security, stack/python, stack/react, surface/macos]
reqPrefix: RE-HIST
relations:
  partOf: [readease-system-app]
  implements: [readease:src/vieneu_reader/storage/history.py, readease:app/src/ui/readingHistory.ts, readease:app/src/ui/HistoryPanel.tsx]
---
# ReadEase — Paste and scan history

## Purpose
- Reopen and read again what the reader pasted or scanned, after the app has quit, without adding it to the library.
- Owner's decision (2026-10-20): on by default and switchable off; kept for a chosen number of days; text and
  translation only, never audio.

## Rules

| REQ-ID | Rule (behaviour-changing) | Status (live / not built / blocked) | Evidence (code path or test) |
|---|---|---|---|
| RE-HIST-001 | Pasted text is kept when it is read, and a scanned selection when it is captured (with its original and target language when translated), in `history.sqlite3` beside the library (owner-only file, never sent anywhere); switched off, nothing new is written. The Paste and Scan screens and Read home list it after a relaunch. | live | `tests/storage/test_history.py`, `tests/headless/test_history_protocol.py`, `app/tests/readingHistory.test.ts` |
| RE-HIST-002 | The same words of the same kind (and same original) move to the top instead of being kept twice; the latest wording is kept. | live | `tests/storage/test_history.py` (`test_reading_the_same_text_again_moves_it_up_instead_of_adding_a_copy`), `app/tests/readingHistory.test.ts` |
| RE-HIST-003 | Retention is 7, 30 (default), 90 or 365 days, or until deleted; entries past it are deleted from the file, not hidden. | live | `tests/storage/test_history.py` (`test_entries_older_than_the_chosen_days_are_deleted_not_just_hidden`), `tests/headless/test_history_protocol.py` |
| RE-HIST-004 | One entry, a whole kind (Scan's "Clear history") or everything ("Delete all history") can be deleted; deleted rows are overwritten on disk (`secure_delete`, `VACUUM` after a clear). | live | `tests/storage/test_history.py` (`test_one_entry_or_everything_can_be_deleted`), `tests/headless/test_history_protocol.py` |

## States and recovery
| State | Trigger | Next state | Edge case |
|---|---|---|---|
| on (default) | Read pasted text / capture a selection | entry saved or moved up | save failure is dropped; reading never waits on it |
| on | switch off | off | existing entries stay until deleted or past retention |
| any | change retention | entries past it deleted | "until deleted" keeps everything |

## Fixed vs flexible
- Fixed: no audio is stored; nothing leaves the Mac; off writes nothing; delete is a real delete.
- Flexible: where the History panel opens, how many rows it shows, labels.

## Change log
- 2026-10-22: reviewed against d2dedf4 (highlights made in the Reader: `mockTauri.ts`, `i18n.ts`, `headless/server.py`) — no history behaviour changed; RE-HIST-001…004 still match.
- 2026-10-21: audit 21/10: clearing history asks first; a translated scan with line breaks is one entry (RE-HIST-002); copy that said history was session-only corrected.
- 2026-10-21: a translated scan whose original has line breaks is matched as the same entry (RE-HIST-002); deleting all history and clearing the scan list ask first.
- 2026-10-20: created (RE-HIST-001…004).
