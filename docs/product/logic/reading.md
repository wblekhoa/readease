---
id: readease-logic-reading
type: logic
product: readease
title: "ReadEase — Reading and playback (logic)"
status: active
updated: 2026-10-16
summary: "Reading and playback rules (RE-PLAY): resume from heard progress, transient text never stored, Stop always wins, chapter chimes, pronunciations, Vietnamese abbreviations, Paste-text audio export and sentence review, and background M4B audiobook export with bounded batches and cancellation."
tags: [area/reading, area/audio, area/voice, stack/python, surface/macos]
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
| RE-PLAY-017 | A sentence of one to three words is generated whole (so the voice SDK can catch and redo a "said more" take) and sampled at temperature 0.3 or lower, while longer sentences keep the reading temperature; the change is part of the VieNeu engine identity so cached short sentences made the old way are not replayed. | live | `tests/speech/test_vieneu_contract.py` (`test_a_short_utterance_arrives_whole_so_the_sdk_can_catch_babble`, `test_a_sentence_keeps_the_readers_temperature`, `test_the_audio_cache_sees_the_new_way_short_sentences_are_made`) |
| RE-PLAY-018 | For the Vietnamese voice, abbreviations the voice SDK leaves half-read are written out before it: "ThS." → "Thạc sĩ", "TP."/"Tp." before a name → "Thành phố", "tr."/"Tr." before a number → "trang", "Q1/2025" → "quý 1 năm 2025", and in citations "Nxb."/"nxb" → "Nhà xuất bản", "Sđd" → "Sách đã dẫn", "Tlđd" → "Tài liệu đã dẫn", an imprint's "H.:" → "Hà Nội:"; the page and subtitles keep the written form. | live | `tests/domain/test_prosody.py` (`VietnameseAbbreviationTests`) |
| RE-PLAY-019 | For the Vietnamese voice, a standalone "OK"/"Ok" is said "ô kê" (the SDK spells it "ô ca"); words that only contain it ("OKR", "BOOK") and lowercase "ok" are left alone. | live | `tests/domain/test_prosody.py` (`test_ok_is_said_as_the_word_not_as_letters`) |
| RE-PLAY-020 | A chosen chapter range (including the whole book) exports as M4B with chapter marks, available JPEG/PNG cover, AI-speech metadata, the reading's voice, speed, pronunciation and chimes. On-device voices only; paid voices are refused before synthesis. Stopped/failed exports leave the destination unchanged; staging files are cleared on normal cancellation/failure. | live | `tests/headless/test_export.py` (`BookExportTests`), `tests/headless/test_m4b.py`; `BookExportPanel.tsx` and `useExport.ts` |
| RE-PLAY-021 | One export owns the voice until its receipt arrives: the native boundary rejects another reading/export and model restart. Navigation remains available during synthesis and finalisation; audio is staged on disk, loudness is processed in batches, AAC is copied 1 MB at a time, and synthesis progress emits at most four times per second. Normalisation and encoding are cancellable, including termination of the encoder child. | live | `BookExportTests.test_library_responds_during_finalisation_and_cancel_preserves_existing_file`; `CancelWriterTests`; `engine.rs` `is_exporting`; `scripts/measure-audiobook-export.py` |
| RE-PLAY-022 | Closing the window during export minimises it and keeps the job alive. Quit asks whether to keep exporting or cancel then quit; cancellation waits for the job's final receipt. Engine EOF ends the export with an error. Completion/error requests Dock attention when the window is unfocused. No notification permission or new dependency is needed. | live | `app/src-tauri/src/lib.rs` close/exit handlers; `engine.rs` `engine_exit_ends_an_export_instead_of_leaving_it_running`; `ExportQuitPanel.tsx`; native Dock/window behaviour still needs manual macOS smoke verification |

| RE-PLAY-023 | During preparation and playback, including pause, the menu-bar icon opens a native menu: disabled status (preparing or current spoken sentence/total), Pause/Resume, Stop and Open ReadEase. Labels and tooltip follow `ui_language` (English fallback); counts contain no text and update when the ear reaches the sentence. Stop also cancels a selection still being captured; captures never overlap clipboard restore. Native menu smoke on the secondary screen is still pending. | blocked | `app/src-tauri/src/reading_tray.rs` (`preparing_progress_pause_and_languages`); `app/src-tauri/src/engine.rs` (`sentence_progress_waits_for_audio_and_drops_stale_readings`); `tests/headless/test_server.py` (`test_sentence_progress_counts_sentences_inside_a_paragraph`) |
| RE-PLAY-024 | Floating controller B uses a native non-activating NSPanel: Pause/Resume with sentence-progress ring and Stop; preparation, completion (3 seconds) and immediate stop; external or hidden/minimised readings only; no selected text; draggable position per screen, system appearance, Reduce Motion, VoiceOver labels and default-on switch. Repeating the shortcut toggles the same live external selection; a different selection replaces it. | blocked | `native/macos/ReadingPanel.m`, `app/src-tauri/src/reading_panel.rs`, shared `reading_tray.rs`; Rust `the_same_live_external_selection_toggles_but_a_new_selection_replaces_it`. Owner confirmed visibility and working buttons in regular ReadEase on 2026-10-16 and requested UI refinement; real focus/selection, fullscreen, accessibility, ≤150 ms appearance and <40 MB added total RSS remain unverified. |

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

## Export performance verification
- Reproduce without a model, network or user library: `PYTHONPATH=src:. uv run --frozen python scripts/measure-audiobook-export.py`.
  The script uses a 300-chapter / 6,000-paragraph fixture and real loudness processing plus macOS AAC encoding; temporary
  files are removed when it exits. This measures export overhead, **not voice-model speed or its memory**.
- Implementation bounds: a single voice job; selecting the next voice does not warm another model during export; progress at most 4 Hz; timer ticks only inside the status component;
  32 loudness blocks per FFT batch, 262,144 samples per WAV write; limiter interpolation uses only nearby blocks.
- Measured on macOS 27.0 arm64, 2026-10-15: 300 chapters / 6,000 paragraphs → 95.0 minutes of synthetic audio,
  23.30 s wall time, -14.0 LUFS, 342.6 MiB peak RSS / +276.7 MiB over the fixture baseline. Library-response p95:
  77.8 ms during synthesis, 41.3 ms during normalisation, 41.9 ms during encoding; maximum during finalisation 55.3 ms.
  The earlier 128-block / 1,048,576-sample batches measured +299.6 MiB. These figures exclude voice-model costs and
  do not establish the roadmap's memory target against a real reading on an 8 GB Mac.
- Verification: Python full suite 968 tests OK (8 skipped; existing SQLite ResourceWarnings remain), app `pnpm build`
  with 229 tests plus UI/mock audits, Rust `cargo test --offline --lib` 36 passed, native selection bridge PASS.
  Browser audit: 48 cases passed, axe-watch=0, VI/EN × light/dark at 960×600; native window/Dock behaviour remains source/test-only.
- Pending: model-inclusive CPU/RAM on an 8 GB Mac; native close/quit/Dock smoke; opening the final file by hand in
  Apple Books; pre-export time/size forecasts and paid-voice whole-book pricing. No accuracy target for forecasts is claimed.

## Open questions
- None recorded.

## Change log
- 2026-10-15: RE-PLAY-020 connected to the app; RE-PLAY-021/022 cover background export, cancellation, resource bounds and lifecycle.
- 2026-10-15: RE-PLAY-018 extended to citation words (Nxb., Sđd, Tlđd, "H.:"), found by probing the SDK normaliser on 34 common forms.
- 2026-10-15: RE-PLAY-020 engine method `export.book` (range by chapter, marks timed from the audio, audio streamed to disk).
- 2026-10-15: RE-PLAY-020 added (not built): the .m4b writer and its tests; spike result in decisions.md.
- 2026-10-15: RE-PLAY-019 ("OK" said "ô kê"; a general tech-term pack measured worse and was not shipped - survey §8).
- 2026-10-15: RE-PLAY-018 (abbreviations written out for the Vietnamese voice).
- 2026-10-15: RE-PLAY-017 (short sentences sampled at 0.3; measured in `docs/local-voice-model-survey-2026-10.md` §6).
- 2026-10-10: created; REQ-IDs added as comments next to the evidence tests in the same commit.
