---
id: readease-logic-export
type: logic
product: readease
title: "ReadEase — Audio export (logic)"
status: active
updated: 2026-10-21
summary: "WAV/SRT and M4B export, temporary sentence review, exclusive job ownership, cancellation/exit recovery and dated performance evidence."
tags: [area/audio, area/performance, area/storage, stack/python, stack/tauri, surface/macos]
reqPrefix: RE-PLAY
relations:
  partOf: [readease-system-app]
  specifiedBy: [readease-ux-reading]
  dependsOn: [readease-logic-reading, readease-logic-voices]
  implements: [readease:src/vieneu_reader/headless/export.py, readease:src/vieneu_reader/headless/m4b.py, readease:app/src/ui/useExport.ts, readease:app/src/ui/BookExportPanel.tsx, readease:app/src-tauri/src/engine.rs]
---
# ReadEase — Audio export

## Purpose

Write audio only at a user-chosen destination, with one app-wide job that survives tab changes. Shared pronunciation/prosody follows [speech preparation](reading.md#speech-preparation); source/voice eligibility follows [voices](voices.md).

## Inputs and outputs

| Source | Result | Eligibility / persistence |
|---|---|---|
| Paste draft | absolute `.wav` + adjacent `.srt` | chosen local or priced API voice; existing destination folder; speed 0.5–2.0 |
| imported book + chapter range (including whole book) | absolute `.m4b` with chapter marks | on-device voice only; include available JPEG/PNG cover and AI metadata |
| last WAV session id + sentence index | play, retake, Save | retake only local VieNeu; never a new library item |

## Rules

| REQ-ID | Rule | Status | Evidence |
|---|---|---|---|
| RE-PLAY-010 | Export Paste as 48 kHz, 16-bit mono WAV plus SRT with reading-equivalent speech/rest/speed and no speaker output. | live | [010](#evidence) |
| RE-PLAY-011 | Mark exported WAV metadata with AI provenance, voice and app version. | live | [011](#evidence) |
| RE-PLAY-012 | Normalize toward −14 LUFS and ≤−1 dBFS peaks; limit peak reduction to 6 dB. | live | [012](#evidence) |
| RE-PLAY-013 | Keep written words in sentence subtitles; split cues over 84 characters by whole-word timing shares. | live | [013](#evidence) |
| RE-PLAY-014 | Stage text-export audio without cache/library writes; validate path/rate and honor cancellation before final writing. | live | [014](#evidence) |
| RE-PLAY-016 | Review/play/retake individual WAV sentences in a scoped temporary session; retake only the selected sentence and rewrite outputs with adjusted timings. | live | [016](#evidence) |
| RE-PLAY-020 | Export a local-voice chapter range as M4B; replace the destination only after success. | live | [020](#evidence) |
| RE-PLAY-021 | Keep exclusive voice ownership through final receipt; allow browsing and bounded, cancellable M4B finalization. | live | [021](#evidence) |
| RE-PLAY-022 | Keep exports alive when closing/minimizing; confirm quit, await cancellation and settle engine EOF as failure. | live | [022](#evidence) |

## Output and review details

- WAV uses the same utterances, rests, rate and pronunciation rules as playback. RIFF INFO `ICMT`/`IKEY`/`ISFT` identify AI generation, voice and software. Loudness may remain quieter when the peak limiter has used its 6 dB allowance.
- SRT keeps written text with Markdown read as meant, one cue per spoken sentence. Split long sentences evenly at whole words and distribute time by text share.
- Keep audio in a nameless temporary file (released on close/crash), write in batches so memory does not grow with text length, and bypass library/audio cache. Stop acknowledged before final output writes leaves no new file; invalid path/rate is refused.
- Review `export.play` streams the existing take. `export.retake` preserves speed/heading gain, replaces one sentence and shifts only later cue times. `export.save` rewrites WAV/SRT from current takes. Reject foreign session ids; close/new export/engine exit ends review. Final WAV/SRT writes and review re-save cannot service mid-write cancellation; they do not share M4B's atomic destination replacement.
- M4B preserves voice, rate, pronunciation and chimes. Copy AAC in 1 MB chunks; stage WAV/AAC/M4B in the output folder and atomically replace only when ready. Normal failure/cancel clears staging and preserves an existing destination; force quit/power loss may leave staging. No export resumes on relaunch.

## States and recovery

Register listeners before starting; match progress/completion by job id, including a completion received before the start reply.

| State / event | Result / boundary |
|---|---|
| idle → valid start | app-wide job owns speech; invalidate pending translation |
| synthesis | counted part progress, at most 4 Hz |
| M4B normalization → encoding | indeterminate stages; elapsed time is not an ETA |
| competing playback/export/model restart | refused by native export guard; navigation/configuration queries remain available |
| Cancel | mark cancelling; Stop requests cancellation; normalization/encoder are cancellable, including encoder-child termination |
| Stop timeout/failure | show cancel error; retain active job/id until receipt or EOF |
| final receipt / engine EOF | release ownership; success/error/cancel remains visible; EOF produces failed receipt |
| window close/minimize | keep job alive; close minimizes rather than quits |
| Quit | Keep exporting or Cancel export and quit; latter waits for final receipt |
| completion/error while unfocused | request Dock attention; no notification permission/dependency |

[Updater apply](updates.md#states-and-recovery) respects this export/quit boundary. Closing a panel or changing selected voice does not end a job or warm another model.

## Evidence

- **010**: `tests/headless/test_export.py` (`test_export_writes_a_marked_wav_and_timed_subtitles`)
- **011**: `tests/headless/test_export.py` (`test_export_writes_a_marked_wav_and_timed_subtitles`)
- **012**: `tests/headless/test_export.py` (`test_full_scale_997_hz_sine_reads_minus_3_01`, `test_peaky_speech_reaches_the_target_under_the_ceiling`, `test_the_limiter_never_takes_more_than_its_share`)
- **013**: `tests/headless/test_export.py` (`CueTests`, `test_export_writes_a_marked_wav_and_timed_subtitles`)
- **014**: `tests/headless/test_export.py` (`test_a_stop_before_the_export_starts_writes_nothing`, `test_rejects_a_path_that_is_not_an_absolute_wav`, `test_rejects_a_rate_outside_the_reading_range`); a stop mid-export takes the reading's stop path ([Stop contract](reading.md#states-and-recovery)) and `finish` returns before writing (`server.py` `_export_text`)
- **016**: `tests/headless/test_export.py` (`RetakeTests`)
- **020**: `tests/headless/test_export.py` (`BookExportTests`), `tests/headless/test_m4b.py`; `app/src/ui/BookExportPanel.tsx` and `app/src/ui/useExport.ts`
- **021**: `tests/headless/test_export.py::BookExportTests.test_library_responds_during_finalisation_and_cancel_preserves_existing_file`; `tests/headless/test_m4b.py::CancelWriterTests`; `app/src-tauri/src/engine.rs` `is_exporting`; `scripts/measure-audiobook-export.py`
- **022**: `app/src-tauri/src/lib.rs` close/exit handlers; `app/src-tauri/src/engine.rs` `engine_exit_ends_an_export_instead_of_leaving_it_running`; `app/src/ui/ExportQuitPanel.tsx`; native Dock/window behaviour still needs manual macOS smoke verification

## Known limits

Native close/quit/Dock smoke, opening final M4B in Apple Books, real-model CPU/RAM on 8 GB hardware and time/size forecasts remain unverified. A successful fixture or synthetic benchmark does not establish these acceptance results.

## Historical benchmark (2026-10-15)

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


## Change log
- 2026-10-21: no export rule change; the engine's speak loop gained a progress-voice override for translated book readings (RE-PLAY-032), and a translated paste exports its translation (RE-PLAY-033, in translation.md).

- 2026-10-19: moved existing export rules and dated benchmark from `reading.md`; requirement IDs, evidence and acceptance limits retained.
- 2026-10-15: connected M4B range export, background lifecycle and cancellation to the app; the earlier writer-only spike is recorded in `../decisions.md`.
