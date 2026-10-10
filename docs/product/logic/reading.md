---
id: readease-logic-reading
type: logic
product: readease
title: "ReadEase — Reading and playback (logic)"
status: active
updated: 2026-10-10
reqPrefix: RE-PLAY
relations:
  specifiedBy: [readease-ux-reading]
  implements: [readease:src/vieneu_reader/headless/server.py, readease:src/vieneu_reader/playback/coordinator.py, readease:src/vieneu_reader/domain/prosody.py, readease:src/vieneu_reader/domain/segmenter.py, readease:src/vieneu_reader/domain/markdown.py]
---
# ReadEase — Reading and playback (logic)

## Purpose
- Read text aloud in an order and rhythm that follows the text's structure, keep the reader's place truthfully, and keep
  transient text (paste, selection) out of persistent storage.
- Success signal: resume lands where the ear stopped; Stop is immediate; nothing pasted is kept.

## Rules
| REQ-ID | Rule (behaviour-changing) | Status (live / not built) | Evidence (code path or test) |
|---|---|---|---|
| RE-PLAY-001 | Reading a book without a start position resumes from its saved progress. | live | `tests/headless/test_server.py` (`test_read_book_resumes_from_saved_progress`) |
| RE-PLAY-002 | Progress is written from what the shell reports as heard, not from what the engine has synthesized ahead. | live | `tests/headless/test_server.py` (`test_the_shell_reporting_the_ear_writes_progress_for_that_reading`, `test_read_book_does_not_persist_listening_progress_during_production`) |
| RE-PLAY-003 | Reading a selection or pasted text never changes any book's progress. | live | `tests/playback/test_coordinator.py` (`test_selection_playback_never_changes_book_progress`) |
| RE-PLAY-004 | Pasted text is never written to the audio cache. | live | `tests/speech/test_headless_audio_cache.py` (`test_pasted_text_is_never_written_to_the_audio_cache`) |
| RE-PLAY-005 | Pasted text is accepted up to 100,000 characters and refused above it. | live | `src/vieneu_reader/domain/segmenter.py` (`MAX_PASTED_TEXT_CHARS`); `tests/domain/test_segmenter.py` (`test_pasted_text_accepts_the_limit_and_rejects_larger_input`) |
| RE-PLAY-006 | Each later chapter of a reading opens with the chosen chime; the first chapter gets none; "off" restores the plain rest. | live | `tests/headless/test_server.py` (`test_a_chime_opens_each_later_chapter_unless_turned_off`) |
| RE-PLAY-007 | Stop interrupts a reading mid-stream. | live | `tests/headless/test_server.py` (`test_stop_interrupts_a_reading_mid_stream`) |
| RE-PLAY-008 | Markdown bold markers are removed from speech and its cost estimate only; the displayed text is unchanged. | live | `tests/headless/test_server.py` (`test_markdown_bold_is_removed_only_from_speech_and_its_estimate`) |
| RE-PLAY-009 | A faster speed shortens the pauses between sentences in proportion. | live | `tests/headless/test_server.py` (`test_a_faster_rate_shortens_the_rest_exactly`) |

## States and transitions
| State | Trigger | Next state | Edge case |
|---|---|---|---|
| idle | Read / Continue / click paragraph | preparing | voice blocked (no model, no key, budget) → error with reason, then idle |
| preparing | first audio arrives | reading | warming notice clears; reading content does not change |
| reading | Pause | paused | pause does nothing while idle |
| paused | Resume | reading | |
| reading | Stop | idle | pressing Stop several times stays idle; late audio from a stopped reading cannot restart it |
| reading | end of text | idle | progress saved up to the last heard position |
| reading | generation failure | idle (error) | progress is not saved past the failure |

## Fixed vs flexible
- Fixed (logic the UI must not change): progress follows the ear; transient text never persists; Stop always wins;
  the displayed text is never altered by speech rules.
- Flexible (UI may explore): the control bar layout, the status capsule, how chapters and figures are presented, chime
  choice and pause lengths within the prosody rules.

## Open questions
- None recorded.

## Change log
- 2026-10-10: created; REQ-IDs added as comments next to the evidence tests in the same commit.
