---
id: readease-logic-reading
type: logic
product: readease
title: "ReadEase — Reading and playback (logic)"
status: active
updated: 2026-10-14
reqPrefix: RE-PLAY
relations:
  specifiedBy: [readease-ux-reading]
  implements: [readease:src/vieneu_reader/headless/server.py, readease:src/vieneu_reader/playback/coordinator.py, readease:src/vieneu_reader/domain/prosody.py, readease:src/vieneu_reader/domain/segmenter.py, readease:src/vieneu_reader/domain/markdown.py, readease:src/vieneu_reader/headless/export.py, readease:src/vieneu_reader/domain/pronunciation.py]
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
| RE-PLAY-010 | Paste text exports to a 48 kHz 16-bit mono WAV at the chosen path, with an `.srt` beside it, spoken with the same utterances, rests and speed as reading aloud; nothing goes to the speakers. | live | `tests/headless/test_export.py` (`test_export_writes_a_marked_wav_and_timed_subtitles`) |
| RE-PLAY-011 | An exported WAV states in its own metadata (RIFF INFO `ICMT`, `IKEY`, `ISFT`) that the speech is AI-generated, which voice made it, and the app version. | live | `tests/headless/test_export.py` (`test_export_writes_a_marked_wav_and_timed_subtitles`) |
| RE-PLAY-012 | An export is set to -14 LUFS integrated (BS.1770) with peaks at or under -1 dBFS; a limiter may take at most 6 dB off peaks, past that the file stays quieter. | live | `tests/headless/test_export.py` (`test_full_scale_997_hz_sine_reads_minus_3_01`, `test_peaky_speech_reaches_the_target_under_the_ceiling`, `test_the_limiter_never_takes_more_than_its_share`) |
| RE-PLAY-013 | Subtitles show the written words (Markdown read as meant), one cue per spoken sentence; a sentence over 84 characters becomes even whole-word cues timed by their share. | live | `tests/headless/test_export.py` (`CueTests`, `test_export_writes_a_marked_wav_and_timed_subtitles`) |
| RE-PLAY-015 | The reader's pronunciations (settings key `pronunciations`, up to 300 rows) replace a written word or phrase by how it should be said in every reading - books, pasted text, selection, export - before the text is made speakable: whole words only, any case, the longest written form first; the estimate counts and the audio cache keys on the replaced words; the page, `text.parts` and subtitles keep the written ones; malformed rows are skipped, a word written twice keeps its last spelling. | live | `tests/domain/test_pronunciation.py`; `tests/headless/test_export.py` (`PronunciationReadingTests`) |
| RE-PLAY-016 | A finished export is kept for review, by sentence, in a nameless temporary file: `export.play` streams one sentence as it is in the file (no synthesis), `export.retake` says one sentence again with the same speed and heading gain and replaces only that sentence, `export.save` rewrites WAV and SRT from the takes as they stand (later cues move by the change, the others keep their times); a retake is offered only for the local VieNeu voice; the review ends on `export.close`, a new export, or the engine's exit, and a request naming another session is refused. | live | `tests/headless/test_export.py` (`RetakeTests`) |
| RE-PLAY-014 | Export keeps nothing but the two files: no audio cache, no library row; the audio waits in a nameless temporary file (gone on close or crash) and is written a batch at a time, so memory does not grow with length; a stop cancels it and a cancelled export writes no file; a path that is not an absolute `.wav` in an existing folder, or a speed outside 0.5-2.0, is refused. | live | `tests/headless/test_export.py` (`test_a_stop_before_the_export_starts_writes_nothing`, `test_rejects_a_path_that_is_not_an_absolute_wav`, `test_rejects_a_rate_outside_the_reading_range`); a stop mid-export takes the reading's stop path (RE-PLAY-007) and `finish` returns before writing (`server.py` `_export_text`) |

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
