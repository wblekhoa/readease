---
id: readease-logic-reading
type: logic
product: readease
title: "ReadEase — Reading and playback (logic)"
status: active
updated: 2026-10-21
summary: "Playback, heard progress, speech preparation and native controls; translation and export have separate rule owners with unchanged requirement IDs."
tags: [area/reading, area/audio, area/voice, stack/python, surface/macos]
reqPrefix: RE-PLAY
relations:
  partOf: [readease-system-app]
  specifiedBy: [readease-ux-reading]
  implements: [readease:src/vieneu_reader/headless/server.py, readease:src/vieneu_reader/playback/coordinator.py, readease:src/vieneu_reader/domain/prosody.py, readease:src/vieneu_reader/domain/segmenter.py, readease:src/vieneu_reader/domain/markdown.py, readease:src/vieneu_reader/domain/pronunciation.py]
---
# ReadEase — Reading and playback

## Purpose

Read each source through one transport, preserve the heard position, and keep speech transformations separate from written content. [Translation](translation.md) and [audio export](export.md) own their separate pipelines; [app map](../systems/app/system.md) owns shared data lifetime and status conventions.

## Inputs and outputs

| Input | Native → engine request | Position / result |
|---|---|---|
| imported book | `read_book` → `read.book` | book segment; heard progress may persist |
| Paste, capture or selection inside a book | `read_text` / `read_selection_text` → `read` | transient `part-*`; no book progress |
| app-authored voice sample | `read_text`, `appText: true` | preview; sample cache allowed |

`origin` is return-navigation context; `current` identifies the actual speech request; `readingAt` identifies the capture owning a `part-*` position. A book origin does not make selected-text speech a book reading. Navigation, search and displayed-page changes do not acknowledge listening.

## Rules

| REQ-ID | Rule | Status | Evidence |
|---|---|---|---|
| RE-PLAY-001 | Read a book from its saved position unless an explicit segment is requested. | live | [001](#evidence) |
| RE-PLAY-002 | Save progress from heard acknowledgements, never synthesized-ahead audio. | live | [002](#evidence) |
| RE-PLAY-003 | Transient text playback never changes book progress. | live | [003](#evidence) |
| RE-PLAY-004 | Never persist pasted-text audio in the document cache. | live | [004](#evidence) |
| RE-PLAY-005 | Accept pasted text through 100,000 characters; refuse larger input. | live | [005](#evidence) |
| RE-PLAY-006 | Chime before later chapters; omit the first; Off uses the plain rest. | live | [006](#evidence) |
| RE-PLAY-007 | Stop interrupts playback; stale audio cannot revive it. | live | [007](#evidence) |
| RE-PLAY-008 | Remove bold markers from speech/cost, retaining the displayed text. | live | [008](#evidence) |
| RE-PLAY-009 | Scale sentence pauses proportionally with reading speed. | live | [009](#evidence) |
| RE-PLAY-015 | Apply validated pronunciation replacements consistently; keep written text in the page, parts and subtitles. | live | [015](#evidence) |
| RE-PLAY-017 | Generate short utterances whole at lower temperature; invalidate incompatible cached audio. | live | [017](#evidence) |
| RE-PLAY-018 | Expand supported Vietnamese abbreviations for speech only. | live | [018](#evidence) |
| RE-PLAY-019 | Say standalone OK/Ok as “ô kê”; leave lowercase and longer words unchanged. | live | [019](#evidence) |
| RE-PLAY-023 | Provide localized, text-free native reading status/actions; Stop also cancels capture. | blocked | [023](#evidence) |
| RE-PLAY-024 | Provide a non-activating external-reading controller with shared transport and safe selection replacement. | blocked | [024](#evidence) |
| RE-PLAY-026 | Share the current-reading Pause/Resume control without restarting speech or changing text geometry. | live | [026](#evidence) |
| RE-PLAY-027 | A book reading stops at the end of the chapter scope the page quoted ("this chapter", N chapters, or the whole book); the page, the native command and the engine carry the same `chapters` value. | live | [027](#evidence) |
| RE-PLAY-028 | For the Vietnamese voice, everyday forms the SDK misreads are rewritten before it, in spellings it reads right: "100m²"/"2,5m³" keep "vuông"/"khối" (converted before footnote marks are dropped), "8h-17h30" says "đến", a weekday run "T2-T6, T7, CN" says "thứ hai đến thứ sáu, thứ bảy, chủ nhật", and "$20"/"3,5 tỷ USD" say "đô la"/"đô la Mỹ"; a lone "T2", "USD" or "x²" is left alone. | live | `tests/domain/test_prosody.py` (`test_square_and_cubic_units_keep_their_power`, `test_an_hour_range_says_den`, `test_a_weekday_range_or_list_says_the_days`, `test_dollars_are_said_as_do_la`) |

## States and recovery

Preparation is `reading + warming: true`, not a fourth reducer enum. Error is a separate value. Native reading epochs filter stale events before they reach the UI reducer.

| Current / event | Next state | Boundary |
|---|---|---|
| any playback state → Start | reading + warming; clear error | supersede old audio/translation |
| reading/paused → first voice | same state; clear warming | late voice cannot revive idle |
| reading → Pause / paused → Resume | paused / reading | preserve request and queued audio |
| idle → Pause/Resume | idle | no-op |
| active → Stop | idle immediately; clear warming | native cancellation follows; repeat is safe |
| current request → Done/Failed | idle; optional error | synthesis completion alone is insufficient |

Python may synthesize ahead. Native `audio.credit` bounds queued frames; `progress.reached` records when a book segment reaches the ear. Both carry reading identity, receive no reply, and work during streaming/idle. Ignore another reading's acknowledgement; accept a valid final acknowledgement after synthesis replies. `reading:done` waits for audio to drain.

Document search stays local: at least two folded query characters, at most 200 hits, case/diacritic-insensitive matches and original-text snippets. A hit only navigates; it creates no note or heard progress (`app/src/ui/textSearch.ts`, `app/tests/textSearch.test.ts`).

## Speech preparation

| Rule detail | Contract |
|---|---|
| pronunciations | At most 300 `pronunciations` rows. Whole words, case-insensitive, longest match first; skip malformed rows; duplicate written forms keep the last spelling. Reading/export, estimates and cache keys use replacements; page, `text.parts` and subtitles retain written words. |
| short utterances | Generate 1–3 words whole so the SDK can detect/retry babble; temperature ≤0.3. Longer sentences retain the chosen temperature. Engine identity changes prevent old short-sentence cache reuse. |
| Vietnamese expansions | `ThS.` → Thạc sĩ; `TP.`/`Tp.` before a name → Thành phố; `tr.`/`Tr.` before a number → trang; `Q1/2025` → quý 1 năm 2025; citation `Nxb.`/`nxb`, `Sđd`, `Tlđd`, imprint `H.:` expand to Nhà xuất bản, Sách đã dẫn, Tài liệu đã dẫn, Hà Nội:. |
| standalone OK | Only `OK`/`Ok` → ô kê; preserve `ok`, `OKR`, `BOOK`. |

## Native controls and acceptance

- Menu status is disabled Preparing / current sentence n/N / Paused; actions are Pause/Resume, Stop, Open ReadEase. Use `ui_language`, English fallback, counts updated on heard sentences without selected text. Stop cancels acquisition; capture cannot overlap clipboard restoration.
- The floating NSPanel is non-activating, text-free, draggable with remembered per-screen position, default-on, and only for external or hidden/minimized playback. Preparing is indeterminate; completion hides after 3 seconds, Stop immediately. Repeating the same live selection toggles pause; a different selection replaces it.
- Geometry, appearance, Reduce Motion, VoiceOver and the shared inline marker are owned by the [reading UX contract](../ux/reading.md#current-truth) and [selection-history presentation](../ux/reading.md#selection-history-blocks). Inline Pause/Resume uses the existing transport; it never invokes read-from-here. Centered pagination keeps both page-turn hit zones usable and text height unchanged.
- Menu smoke on the secondary screen is pending. Controller focus/selection, fullscreen, accessibility, ≤150 ms appearance and <40 MB additional total RSS remain unverified. Owner-confirmed buttons do not clear these holds.

## Known limits

None open for chapter scope: the bridge gap noted on 2026-10-19 is closed by RE-PLAY-027 (2026-10-20).

## Evidence

- **001**: `tests/headless/test_server.py` (`test_read_book_resumes_from_saved_progress`)
- **002**: `tests/headless/test_server.py` (`test_the_shell_reporting_the_ear_writes_progress_for_that_reading`, `test_read_book_does_not_persist_listening_progress_during_production`)
- **003**: `tests/playback/test_coordinator.py` (`test_selection_playback_never_changes_book_progress`)
- **004**: `tests/speech/test_headless_audio_cache.py` (`test_pasted_text_is_never_written_to_the_audio_cache`)
- **005**: `src/vieneu_reader/domain/segmenter.py` (`MAX_PASTED_TEXT_CHARS`); `tests/domain/test_segmenter.py` (`test_pasted_text_accepts_the_limit_and_rejects_larger_input`)
- **006**: `tests/headless/test_server.py` (`test_a_chime_opens_each_later_chapter_unless_turned_off`)
- **007**: `tests/headless/test_server.py` (`test_stop_interrupts_a_reading_mid_stream`)
- **008**: `tests/headless/test_server.py` (`test_markdown_bold_is_removed_only_from_speech_and_its_estimate`)
- **009**: `tests/headless/test_server.py` (`test_a_faster_rate_shortens_the_rest_exactly`)
- **015**: `tests/domain/test_pronunciation.py`; `tests/headless/test_export.py` (`PronunciationReadingTests`)
- **017**: `tests/speech/test_vieneu_contract.py` (`test_a_short_utterance_arrives_whole_so_the_sdk_can_catch_babble`, `test_a_sentence_keeps_the_readers_temperature`, `test_the_audio_cache_sees_the_new_way_short_sentences_are_made`)
- **018**: `tests/domain/test_prosody.py` (`VietnameseAbbreviationTests`)
- **019**: `tests/domain/test_prosody.py` (`test_ok_is_said_as_the_word_not_as_letters`)
- **023**: `app/src-tauri/src/reading_tray.rs` (`preparing_progress_pause_and_languages`); `app/src-tauri/src/engine.rs` (`sentence_progress_waits_for_audio_and_drops_stale_readings`); `tests/headless/test_server.py` (`test_sentence_progress_counts_sentences_inside_a_paragraph`)
- **024**: `native/macos/ReadingPanel.m`, `app/src-tauri/src/reading_panel.rs`, shared `reading_tray.rs`; `bash scripts/test-native-reading-panel.sh` checks native state/action/alpha/geometry; Rust `the_same_live_external_selection_toggles_but_a_new_selection_replaces_it`. Owner confirmed visibility and working buttons in regular ReadEase on 2026-10-16 and requested UI refinement; real focus/selection, fullscreen, accessibility, ≤150 ms appearance and <40 MB added total RSS remain unverified.
- **027**: `tests/headless/test_shell_contract.py` (`PageShellEngineBookContractTests`: every argument the page passes to `read_book` is declared by the Rust command, `chapters` is forwarded to `read.book`, and `_read_book` reads it); engine bound in `tests/speech/test_external_reading.py` (`"chapters": 1` cases).
- **026**: `app/src/ui/ReadingPositionControl.tsx`, `app/src/ui/ScanEntry.tsx`, `app/src/screens/Reader.tsx`, `app/src/screens/PageFlow.tsx`; shared player state tests in `app/tests/playback.test.ts`; browser pause/resume, page-turn and geometry checks on 2026-10-18.

Protocol checks: `app/tests/playback.test.ts`, `tests/headless/test_shell_contract.py`, native `engine.rs`/`audio.rs` tests. Reducer checks alone do not establish speaker cancellation.

## Change log

- 2026-10-21: audit 21/10: no rule change; translation-coverage allowlist gained the new chapter-line matchers.
- 2026-10-20: RE-PLAY-028 - probed 44 everyday forms through the SDK normaliser; four misread families rewritten (unit powers, hour ranges, weekday runs, dollars).
- 2026-10-20: RE-PLAY-027 - `read_book` now declares and forwards `chapters`; cross-layer contract test added; the chapter-scope known limit is closed.
- 2026-10-19: separated translation/export ownership without renumbering rules; retained native holds and the chapter-scope gap.
- 2026-10-19: documented request identity, actual reducer states and heard acknowledgements.
- 2026-10-15: citation abbreviations, standalone OK and short-utterance handling; pronunciation replacements were introduced earlier.
- 2026-10-10: introduced requirement IDs beside code/test evidence.
