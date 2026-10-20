---
id: readease-decisions
type: decision
product: readease
title: "ReadEase — Decisions"
status: active
updated: 2026-10-20
summary: "Append-only record of why ReadEase is built as it is: noncommercial licence, Tauri shell over a Python engine, own-key paid voices, signing, on-device voices and memory, bundle id, audio export, pronunciations and the default voice."
tags: [area/voice, area/audio, area/release, area/signing, stack/tauri, stack/python, surface/macos]
---
# ReadEase — Decisions (append-only, newest first)

Entries before 2026-10-10 are reconstructed from commits, the CHANGELOG and docs in this repo; each cites its source.

## 2026-10-20 · Separate logic owners and shorten retrieval

- **Context**: The owner approved the proposed documentation optimization: separate playback/translation/export, shorten rules and link shared policy instead of repeating it.
- **Decision**: Keep the app map for ownership, data lifetime and operation precedence. Move translation/export rules into their owning logic files without changing IDs, status or test annotations. Keep operational detail and evidence below short rule tables; leave presentation with UX.
- **Compatibility**: Existing rule IDs remain valid across files. Historical decisions/releases are retained. Native acceptance holds and the chapter-scope bridge gap stay explicit; no runtime change or new release is implied.
- **Verification**: Compare the original rule/evidence inventory, validate links/relations and confirm non-document files are unchanged.
- **Reversal**: Regroup files only if retrieval becomes worse; keep one definition per rule and stable IDs.

## 2026-10-19 · Make logic documentation traceable to the current app

- **Context**: The owner asked to focus on completing app logic documentation after reviewing Read home.
- **Decision**: One app logic map links feature owners and records data lifetime, shared transport/concurrency, release status and verification gaps. Keep implementation evidence separate from native/manual acceptance; no new runtime behavior is authorized by a documentation status change.
- **Identity repair**: Preserve RE-VOICE-009 for the default voice; the previously colliding rejected-key rule is RE-VOICE-014. Retag only its test comment, retain historical decision/release records and add missing existing export evidence annotations.
- **Known source mismatch**: UI chapter scope is not forwarded by native `read_book`. Document it as an open contract gap, not a guaranteed playback bound. No fix is claimed in this pass.
- **Evidence**: `systems/app/system.md`, feature logic documents and the cited source/tests. Feedback privacy distinguishes URL metadata transmission from issue submission; Apple Books mirroring differs from explicit Move notes writes.
- **Reversal**: Update the owning contract after behavior or acceptance actually changes; do not erase open checks based only on a new build or screenshot.

## 2026-10-19 · Name the shared reading home Đọc

- **Context**: The owner wants an overall home rather than Library as the app's starting page, with recent work and reading settings, then specified: “tab sẽ có tên là đọc” and an empty state suggesting file, typed/pasted content and selection capture.
- **Decision**: Read is the first/default tab. Keep Library/Paste/Selection as existing workspaces and group Move notes under Tools. Empty Read offers three entry actions; a populated Read derives up to five recent items and exposes existing voice/selection-translation settings.
- **Privacy**: Keep the current draft and captures transient. No persistent recent-text archive, automatic clipboard read, upload or new dependency.
- **Interactions**: Picking/dropping files opens the last successful import. Recent opens without autoplay. The current reading remains active across navigation.
- **Evidence**: `app/tests/homeReading.test.ts`, UI build and browser/render checks. Native file/drag acceptance remains separate.
- **Reversal**: Restore the launch route and remove the derived surface without migrating stored user content.

## 2026-10-19 · Prepare updates without blocking reading

- **Context**: The owner reported the update dialog prevents continued use, and chose the proposed sidebar notice plus detail popover ("theo đề xuất của bạn nhé").
- **Decision**: Keep a quiet status above the sidebar footer, with an icon in the folded rail. Details are dismissible and non-modal. Download only prepares the signed archive; install only on explicit restart or armed quit. Keep the opt-in auto preference and menu entry.
- **Safety**: Check export state again before apply, serialize duplicate operations, show recoverable failures, and invalidate cancelled quit timeouts. Warn about clearing temporary reading content on restart; do not persist it to solve an update UI issue.
- **Evidence**: `app/tests/updateFlow.test.ts`, native quit-timeout test, build and browser preview checks. Signed old-to-new replacement remains a release-candidate check.
- **Reversal**: Presentation can change after owner review; retain preparation/apply separation and export guards.

## 2026-10-18 · Finalize shared reading controls and release 0.1.23

- **Context**: The owner approved the revised selection blocks and requested commit, push and release.
- **Decision**: Keep the white light-theme ground, quiet borders and diffuse card shadows. Use a solid 1px reading underline with an 18px blue Pause/Resume button and 9px white icon, 12px left of the text and 10px below the paragraph top. Share the component across selection history and document detail.
- **Interaction**: The control toggles the existing transport without starting a sentence again. The expanded pagination clip is centered, and its empty padding passes clicks to Next/Previous. Text width and paragraph height remain unchanged.
- **Evidence**: 236 UI tests; browser pause/resume and keyboard checks, geometry measurements, and direct page-arrow clicks at wide/narrow viewport sizes. Apple translation bridge passed VI→EN and EN→VI; local-model fixture passed protocol and cancellation checks. Native focus/fullscreen/accessibility and total-process performance acceptance remain separate from these checks.
- **Reversal**: Revisit visuals with options approved by the owner before implementation; retain the shared playback semantics.

## 2026-10-18 · Group selection history into readable blocks
- **Owner direction**: optimize the other UI areas shown in the selection screenshots; try blocks like SpeakEase.
- **Decision**: one paper Surface per capture, with summary/time and existing actions in its header. Put translated
  speech first and the original in a separate collapsed disclosure below. Group setup controls in their own block.
- **Scope**: selection history and focused-passage view. Reuse existing tokens and Surface; no new stats, search,
  storage, polling or dependency. Engine sentence IDs and playback/follow behavior remain authoritative.
- **Reversal**: presentation only; no history schema or persisted preference migration.

## 2026-10-18 · Simplify translation controls and reuse the voice picker
- **Owner direction**: use the same quality dropdowns as elsewhere, show translation status in general voice
  settings, and simplify the three footer targets.
- **Decision**: two footer openers: Translate (label plus chevron in one hit area) and Voice. Move the toggle
  inside Translation settings. This supersedes the split-toggle decision below; toggling takes one extra click.
- **Consistency**: reuse VoicePicker for installed target voices, including sample, favorites and keyboard
  navigation; keep shared Select for simple choices. No new UI dependency or background polling.
- **Visibility**: Voice settings and Voices & models show a compact On/Off + target status/link, explicitly scoped
  to selection capture. Book and pasted-text voices remain independent.
- **Reversal**: UI-only arrangement; saved translation and voice preferences require no migration.

## 2026-10-18 · Give translation its own footer control
- **Owner direction**: add a translation toggle and settings beside Voice settings.
- **Decision**: the Translate label toggles on/off and shows the target when on; a separate arrow opens Translation
  settings. Voice settings retains the effective voice and speed. Target and matching local voice remain together
  in Translation settings; provider options stay disclosed. Opening either panel closes the other.
- **Scope**: selection capture only; no change to saved book voice, engine translation or downloads. Toggle is locked
  while reading/exporting/saving. Load/save failures expose the retry path in Translation settings.
- **Reversal**: move the same persisted preference back into Voice settings without a data migration.

## 2026-10-17 · Settings follow the reading task
- **Owner direction**: when translation is on, pair the target language with its voice and avoid unrelated settings.
- **Decision**: Selection settings shows target, matching local voice and speed together; source/provider/model
  move into Translation options. Errors remain visible when folded. Original-reading controls return when translation
  is off; book-only controls stay in book settings. The selection footer names the effective target voice.
- **Implementation default**: keep the existing shared speech rate and separate translation voice preference;
  no new model downloads, provider calls on disclosure, or changes to book voice persistence.
- **Evidence**: target-voice regression test and interactive selection settings checks; native acceptance remains
  separate from automated checks. RE-PLAY-025 remains candidate.
- **Reversal**: rearrange the controls without migrating saved voice or translation preferences.

## 2026-10-17 · Translate selected text before reading, on device
- **Owner direction**: “Apple và các model local giống speakease”. The owner wants a translation setting so a
  Vietnamese selection can be translated and spoken in English (and vice versa).
- **Decision**: opt-in translation for external selection capture; Apple Translation or a local Ollama/LM Studio
  server. SpeakEase's custom local-provider pattern is the reference, not its speech-recognition models. No paid
  translation fallback, API key, automatic model download or persisted passage. Use an installed local voice for
  the target language without replacing the user's saved book voice.
- **Compatibility**: the installed-language headless Apple API requires macOS 26. The app retains its macOS 15
  floor; local-server translation works there. Missing Apple language packs have an explicit setup message.
- **Scope**: source auto-detection or explicit Vietnamese/English; target Vietnamese/English, matching the local
  speech models. Books, audiobook exports and pasted text are unchanged. Selections are limited to 6,000 characters.
- **Failure rule**: Stop and superseding playback invalidate translation; a failed translation never silently
  speaks the original. History holds the original plus the spoken translation in memory for this session.

## 2026-10-17 · Start with a roomier main window
- **Context**: the owner requested a larger default after the Library toolbar and shelf appeared cramped.
- **Decision**: change the initial window from 1060×720 to 1280×820 logical pixels, using Tauri's work-area overflow
  prevention. Keep the 960×600 minimum and the existing saved size/position restoration.
- **Evidence**: `app/src-tauri/tauri.conf.json` owns the initial geometry; `app/src-tauri/src/lib.rs` registers size and
  position persistence. Existing saved frames take precedence over the initial size.
- **Reversal**: adjust the initial dimensions after desktop feedback without resetting readers' saved layouts.

## 2026-10-17 · Give floating controls a generous hover surface
- **Context**: the owner found the small hover disks cramped around the Pause/Resume and Stop symbols.
- **Decision**: expand both hover/press disks from 24pt to 36pt inside the existing 40pt targets, retaining the capsule
  geometry. Paint the hit-test-transparent progress ring above the wash so feedback does not dull its stroke.
- **Evidence**: the native pixel check fails on the small disk and passes on both expanded disks in light/dark
  appearances; the existing action, transparent-corner and surface-opacity checks remain passing.
- **Reversal**: tune the disk inset without enlarging the capsule or adding motion.

## 2026-10-17 · Give the reading controller SpeakEase's flat silhouette
- **Context**: the owner reported that the controller's shadow looks cropped inside a rectangle and supplied the
  SpeakEase recording pill as the visual reference.
- **Decision**: remove the AppKit window shadow and visual-effect backdrop; draw only an opaque, rounded system
  surface with a thin separator border and transparent corners. Reduce height from 64pt to 48pt and width to 96pt, with equal 4pt outer insets,
  preserve 40pt native hit targets, and reduce the progress ring and symbols. This supersedes the earlier controller geometry.
- **Owner correction**: the initial 120pt-wide refinement left excessive padding at both ends. The owner rejected
  that layout; the revised width follows the two 40pt targets, 8pt gap and two 4pt insets.
- **Evidence**: the previous implementation enabled the window shadow with a masked visual-effect view filling its
  bounds. SpeakEase's current overlay explicitly disables native shadows and uses a flat surface without blur.
  Native view checks cover geometry, transparent corners and the disabled shadow; real desktop appearance still
  needs owner review. This change does not establish focus, accessibility or performance acceptance.
- **Delivery audit**: a subsequent screenshot still showed the original large, blurred controller. The installed
  build was confirmed as the previous candidate; source previews had not updated the running application.
  `bash scripts/test-native-reading-panel.sh` now exercises the production views at 1×/2× in both appearances,
  checking corner alpha, surface opacity, balanced insets and button actions across six states without opening a window.
  A signed build and explicit installed-build verification are required before asking for another desktop review.
- **Contrast correction**: the native render over adjacent white/dark backdrops exposed a faint seam through the
  initial 98% surface. Use a fully opaque interior while preserving transparent corners; the pixel regression check
  fails on the translucent surface and passes on the solid one.
- **Local delivery**: rebuilt the solid-surface candidate through the canonical release script with Developer ID
  signing (local, unnotarized). After verifying ReadEase was no longer running, installed it with a rollback copy;
  the installed executable hash matches the verified bundle. Desktop visual acceptance remains pending.
- **Reversal**: adjust the native flat surface if desktop review fails; keep the shared controls and playback path.

## 2026-10-16 · Build the floating controller in regular ReadEase for owner testing
- **Context**: the owner asked to stop separate test apps and continue in the regular app, with manual testing by the owner.
- **Decision**: integrate B as an AppKit non-activating NSPanel with native buttons and progress, using the existing Cocoa
  bridge and dependencies. This avoids an extra webview, JavaScript renderer and controller polling loop. Menu and panel
  share playback state, and the external-reading screen has the default-on switch.
- **Evidence**: owner's instruction, 2026-10-16: "làm trên app chuẩn rồi để tôi tự test". The owner subsequently confirmed
  the controller is visible and "các nút hoạt động tốt nhé", then requested UI refinement. This confirms the visible
  controls and button actions only; focus/selection, fullscreen, accessibility and performance acceptance remain pending.
  The earlier diagnostic's timing/focus results belong to its second-webview experiment only.
- **UI refinement**: owner confirmed the scope: "Viên điều khiển nổi: cân lại nút, vòng tiến độ, padding và hover".
  Use equal 48pt targets, 8pt inset/gap, 16pt symbols and the HIG's native 10%/20% hover/press feedback.
  The compact size and existing actions stay the same; appearance changes redraw on pointer events without timers.
- **Reversal**: disable the floating controller and retain the menu if focus, selection, fullscreen, accessibility or
  performance checks fail on the real build. This is a local candidate, not public-release acceptance.

## 2026-10-16 · External reading uses menu controls first, floating controller B after a native spike
- **Context**: selection reading gives no immediate visible response and its menu-bar icon stops on click.
- **Decision**: the owner chose B: the smallest immediately visible controller that still offers Pause/Resume
  (sentence-progress ring) and Stop. Open ReadEase belongs in the menu-bar menu, keeping the pill to two buttons
  and revealing no document text. First implement the localised native menu and preparation feedback (RE-PLAY-023).
- **Evidence**: owner's approved handover, 2026-10-16. B remains unbuilt (RE-PLAY-024) pending a second-webview
  non-activating NSPanel spike using existing dependencies: TextEdit remains frontmost with its test selection,
  fullscreen/Spaces visibility, ≤150 ms appearance, <40 MB added RSS. Test on the secondary display only.
- **Reversal**: if focus is stolen, stop at the menu implementation; do not ship the floating controller.

## 2026-10-16 · Short sentences stay at temperature 0.3 after the blind listening test
- **Context**: RE-PLAY-017 shipped 0.3 for sentences of three words or fewer on a machine measure (heard exactly 61 % →
  71 %) while its blind listening test was still open; the reversal was "back to 0.8 if the owner hears it worse".
- **Decision**: keep 0.3.
- **Evidence**: owner's blind ratings, Adam, 10 phrases × 2 takes, labels shuffled: 0.3 preferred 8, 0.8 preferred 7,
  equal 5 - to the ear a draw, so the machine-measured accuracy decides. Ngọc Linh's rows were not rated.
  `docs/local-voice-model-survey-2026-10.md` §9.
- **Reversal**: `SHORT_UTTERANCE_TEMPERATURE` back to 0.8 and `SYNTHESIS_REVISION` bumped, in
  `src/vieneu_reader/speech/vieneu.py`.

## 2026-10-15 · Background audiobook export shares one voice lane
- **Context**: the owner asked to continue audiobook development, protect app performance, and let a reader export in
  the background with understandable status. This authorises the chapter/book export scope previously a non-goal.
- **Decision**: one local voice job at a time; navigation continues, playback waits. Reuse the book utterances and the
  existing on-disk sink. Finalise loudness/AAC on one worker while the request thread answers quick navigation calls;
  cancellation reaches both batched audio processing and the encoder process. Keep a global receipt and use Dock
  attention when unfocused. Closing the window minimises during an export; quitting requires keep/cancel-and-quit.
  No new dependency, extra model process, automatic relaunch resume or paid book synthesis.
- **Evidence**: RE-PLAY-020…022, `BookExportTests`, `CancelWriterTests`, Rust EOF test and the synthetic benchmark
  `scripts/measure-audiobook-export.py`. Native window/Dock smoke remains unverified; synthetic timings exclude model cost.
- **Reversal**: remove the book entry point; keep the shared sink and Paste-text export intact.

## 2026-10-15 · Audiobook export (.m4b): macOS encodes, the engine writes the chapter track itself
- **Context**: roadmap P2 asks for chapter-marked audiobooks without a new dependency (no ffmpeg, no mutagen).
- **Decision**: the WAV the export already makes is encoded by `/usr/bin/afconvert` (AAC 64 kbit/s, on every Mac);
  `headless/m4b.py` (stdlib only) lays the file out as ftyp · mdat · moov and adds a QuickTime chapter track - the
  layout AVFoundation itself wrote in the spike: a disabled 'text' track, one UTF-8 sample per chapter with an 'encd'
  atom, the audio track pointing at it through tref/chap - plus iTunes tags (title, artist, comment, cover, stik =
  audiobook). Rejected: AVFoundation from Rust (needs a new `objc2-core-media` crate) and a timed-metadata chapter
  track (AVAssetWriter refuses metadata tracks in .m4a).
- **Evidence**: a Swift probe reading the Python-written file through AVFoundation (`scripts/check-m4b-chapters.swift`):
  playable, 3 chapters at 0/4/8 s with Vietnamese titles, title/artist tags; `afinfo` reports file type m4bf;
  decoded back, each chapter's tone is intact (440/550/660 Hz, same level). 8 tests in `tests/headless/test_m4b.py`,
  including a real encode on macOS. Not yet opened in Apple Books by hand.
- **Reversal**: delete `headless/m4b.py`; nothing else uses it yet.

## 2026-10-15 · No ready-made pronunciation pack; only "OK" is rewritten
- **Context**: roadmap P1 step 7 proposed an optional pack of tech terms and common names to import into the
  reader's pronunciation list.
- **Decision**: no pack ships. The voice SDK already reads English tech words and acronyms well; respelling them the
  Vietnamese way made them worse. The one clear failure, "OK" read as letters, is fixed in the Vietnamese normaliser
  (RE-PLAY-019) for everyone instead of behind an import.
- **Evidence**: 20 terms × raw vs respelled × 3 renders (Đức Trí, int8), Whisper large-v3-turbo: heard right 54/60
  raw vs 49/60 respelled; KPI 3/3 → 0/3, online 3/3 → 1/3, ChatGPT 3/3 → 1/3; OK 0/3 → 3/3.
  `docs/local-voice-model-survey-2026-10.md` §8.
- **Reversal**: a pack can still be added later from words readers actually add (needs the feedback channel, P0).

## 2026-10-15 · Default voice: Đức Trí instead of Adam, on measurement
- **Context**: the roadmap (P1) asked for the default voice to be chosen on evidence. Adam, the default since the
  start, missed short headings and replies most often (e.g. "Vâng." heard as "Văng"/"Văn" in 3 of 3 takes). The owner
  asked for the roadmap to run without stopping for questions (15/10), so this is decided here and reported.
- **Decision**: `DEFAULT_VOICE_ID` = "Đức Trí" (male, Southern, storytelling - same gender and region as Adam). In the
  switcher's starting five, Đức Trí takes the male storytelling slot from Thái Sơn; Adam stays as the familiar natural
  voice. Only readers who never chose a voice are affected; saved choices and each book's voice stay.
- **Evidence**: Whisper large-v3-turbo listening back, VieNeu 3.6.3 int8, short sentences at temperature 0.3.
  Short headings heard exactly: Mai Anh 98 %, Đức Trí 96 %, Trúc Ly 96 %, Ngọc Linh 71 %, Adam 64 %, Thái Sơn 31 %.
  Six passages × 3 takes, mean word error: Đức Trí 5.7 %, Mai Anh 8.9 %, Trúc Ly 12.3 %, Ngọc Linh 23.6 %, Adam 24.5 %
  (long passages only: 8.6 / 9.2 / 10.2 / 10.5 / 11.8 % - close; the gap is mostly short sentences). Caveat: Whisper
  favours Northern speech, and Đức Trí is Southern, so the ranking leans against him and he still leads.
  `docs/local-voice-model-survey-2026-10.md` §7.
- **Reversal**: set `DEFAULT_VOICE_ID` back to "Adam" and restore "Thái Sơn" in `STARTING_VOICES`.

## 2026-10-14 · Review sentences: re-takes kept by sentence until the file is saved
- **Context**: VieNeu samples (temperature 0.8), so a sentence never comes out the same way twice - the short-utterance
  weakness measured on 13/10 is worst on titles. A creator needs to keep the take they like.
- **Decision**: the export's audio is tagged by sentence; a finished export stays reviewable in the engine (nameless
  temp file) until Done / text changed / new export / quit, stated in PRIVACY. Play = the stored take, never a new one;
  Say again = VieNeu only (Kokoro is deterministic; paid voices would spend unquoted); the file is rewritten only on
  Save, since a rewrite measures the whole file. In export mode the stretcher drains per sentence so a take is exactly
  one sentence. The temperature change for short sentences stays out (its listening test is unanswered).
- **Evidence**: RE-PLAY-016 tests (incl. rate 1.5); real-voice probe: "Mở đầu." 0.56 s → 0.72 s new take in 0.09 s,
  later cue moved 160 ms, file re-saved at -14.0 LUFS.
- **Reversal**: drop `export.play/retake/save/close` and close the sink in `_export_text` as before.

## 2026-10-14 · Pronunciations: the reader's own, applied before the text is made speakable
- **Context**: a voice reads a brand, an acronym or an English word inside Vietnamese by its own guess - the error a
  creator hears most (14/10 analysis). The owner asked to proceed with the proposed steps.
- **Decision**: one list in settings (`pronunciations`), applied in both utterance builders to the written words before
  `speakable_text`, so the voice, the estimate and the cache key move together and display/subtitles never change.
  Whole-word, case-insensitive, longest first; no per-language or per-voice lists in v1. Edited in a panel opened from
  Voice settings; each change saves at once and re-counts a paid price.
- **Evidence**: RE-PLAY-015 tests; real-voice A/B export of one sentence with and without three entries, sent to the
  owner for listening (14/10).
- **Reversal**: remove the key from `_CONFIG_KEYS` and the `say`/`pronounce` calls; stored rows are then ignored.

## 2026-10-14 · Paste text can be exported as audio with subtitles (non-goal lifted)
- **Context**: creators asked to use ReadEase's voices for video narration. The goal listed "no audio export" as a
  non-goal. The owner's position (14/10): ReadEase is a tool; where a user publishes its output (YouTube or anywhere) and
  that platform's rules are the user's responsibility, so the app adds no platform checks or warnings.
- **Decision**: export Paste text only, as WAV (48 kHz, 16-bit) + SRT, normalised to -14 LUFS with a gentle limiter, and a
  machine-readable AI-speech mark in the WAV's RIFF INFO chunk. The mark is the one duty that falls on the tool, not the
  user: Vietnam's Law on AI (134/2025/QH15, in force 2026-03-01, implementing decree pending) and EU AI Act Art. 50(2)
  (from 2026-08-02) ask providers of synthetic-audio tools for machine-readable marking (read from law-firm summaries,
  not the official texts, 14/10). Metadata, not an audible watermark: it restricts nobody. Books, chapters, re-takes per
  sentence and a pronunciation dictionary are later steps. `LICENSE` (PolyForm Noncommercial) is unchanged; whether a
  commercial licence is offered is still the owner's call.
- **Evidence**: VieNeu-TTS v3 Turbo model card (fetched 2026-10-14): preset voices are Apache-2.0 with the speakers'
  consent, and generated audio "may be used in commercial and monetized content". Real-voice probe on a model copy:
  14.6 s of Ngọc Linh exported in 3.9 s, -14.06 LUFS, peak -1.0 dBFS, 6 cues. A 90-minute export (test voice, 92 489
  characters) peaked at 213 MB resident: audio is staged in a temporary file and processed in batches. RE-PLAY-010…014.
- **Reversal**: drop the export button and `export.text`; nothing else depends on them.

## 2026-10-11 · Design tokens re-synced from WAVE (snapshot of 2026-08-31 replaced)
- **Context**: `app/src/styles/ds-tokens.css` is a verbatim, locked copy of the design system's token bundle. The design
  system moved to WAVE; the copy was still the 2026-08-31 bundle. The re-sync waited until the owner settled which
  colour ramps (success / warning / purple) are canonical: the ramps in use were kept.
- **Decision**: replace the whole snapshot with WAVE's bundle (`npm run tokens:build` output, `wave@e69471c`), header
  records the source, hash and date; no partial copy, no local edit. Every DS variable the app references still exists
  (no renames needed). Resolved changes, of the 42 DS variables the app uses (12 light, 6 dark):

  | Variable | Used for | Light | Dark |
  |---|---|---|---|
  | `--border-color-info-secondary` | focus ring | `#6f8ae2` → `#839ff9` | `#4159a6` → `#3456ae` |
  | `--fill-info-haze`, `--border-color-info-haze` | blue highlight, info edge | `#002dca58` → `#003dee4e` | `#5881fd6d` → `#447afd73` |
  | `--fill-info-wash` | info wash | = | `#4c6efa29` → `#3268f82d` |
  | `--fill-warning-bold` | favourite star | `#b07e0f` → `#5f3a00` | = |
  | `--text-color-warning-stress` | warning text | `#996d0d` → `#4c2f00` | = |
  | `--fill-warning-haze` | yellow highlight (default) | `#dd99007b` → `#b97d0093` | = |
  | `--yellow-alpha-ya50`, `--yellow-y100` | mark backgrounds | `#dd9a00c5` → `#9d6c00`; `#e0a011` → `#855300` | = |
  | `--fill-success-primary`, `--fill-success-haze` | OK state, green highlight | `#329546` → `#006e25`; `#007a1659` → `#00a1278e` | = |
  | `--fill-purple-haze` | purple highlight | `#2e00c652` → `#2f00cd4f` | = |
  | `--fill-pink-haze` | pink highlight | `#c9052d4d` → `#d800515e` | `#fe5a7765` → `#fe5a7666` |
  | `--border-color-neutral-soft` | input and secondary borders | = | `#444546` → `#363637` |

  Info values follow the design system's new blue-violet brand ramp; warning/success/purple are the darker ramps the
  design system now uses (more contrast on white). The app's own brand (`--blue-b100`) is unchanged.
- **Evidence**: `app/src/styles/ds-tokens.css` header; Python `unittest` 915 OK (7 skipped) before and after; app
  `node --test tests/*.test.ts` 218/218 before and after; `pnpm build` passes; CI on the temporary branch.
- **Reversal**: restore the previous snapshot from git history; a new entry here.

## 2026-10-09 · Bundle id moves to `com.wblekhoa.readease`
- **Context**: the previous bundle id referenced an organisation the app has nothing to do with.
- **Decision**: ship 0.1.20 under `com.wblekhoa.readease`; keep the data folder (`VieNeu Reader`) so the library,
  notes, voices and settings stay; copy window state and interface storage on first launch. Accepted cost: macOS asks
  once more for the Accessibility permission (it is tied to the id).
- **Evidence**: commit `82ce4de`; CHANGELOG 0.1.20; `app/src-tauri/src/identity.rs`.
- **Reversal**: not practical - a second id change would cost the permission again; a new entry would be needed.

## 2026-10-08 · Release a local model after five quiet minutes; suggest Standard on 8 GB Macs
- **Context**: holding the Vietnamese and English models in memory left an 8 GB Mac short of room.
- **Decision**: a local model unused for 300 s releases its memory and reloads on the next sentence; at about 8 GB or
  less, Voices & models suggests the Standard build (measured: ~0.44 GB less memory, same speed).
- **Evidence**: commits `291ff17`, `d335131`, `6aefe2a`; `IDLE_RELEASE_SECONDS` in `headless/server.py`;
  `LOW_MEMORY_BYTES` in `app/src/ui/ModelPanel.tsx`; REQ RE-VOICE-005, RE-VOICE-006.
- **Reversal**: raise or remove `IDLE_RELEASE_SECONDS`; a new entry here.

## 2026-09-15 · The reader chooses what to download; no voice is refused for a language
- **Context**: the first-run gate made the Vietnamese model the price of entry, and a voice could be refused for the
  language of the text.
- **Decision**: no model is required - first run offers each model, an API key, or nothing; the voice panel asks the
  language first; a voice is refused only when its model is missing, and for a language mismatch the app suggests,
  never blocks. Rejected: a `wrong_language` refusal.
- **Evidence**: commits `967ff83`, `f0ff3f0`; `app/src/screens/Setup.tsx` header comment;
  `src/vieneu_reader/speech/external/route.py`; REQ RE-VOICE-001, RE-VOICE-007.
- **Reversal**: reintroduce a gate in `firstRunNeeded` / a refusal reason in `route.py`; a new entry here.

## 2026-09-15 · Kokoro-82M as the on-device English voice
- **Context**: English books needed a local voice with the same privacy promise as Vietnamese.
- **Decision**: after a survey and measurements of local English voices, add Kokoro-82M (Apache-2.0, six American
  voices, ~330 MB) as a second, optional model.
- **Evidence**: commits `7d2236d`, `73508cb`; `docs/english-voice-research-2026-09-15.md`,
  `docs/local-voice-model-survey-2026-09.md`; CHANGELOG 0.1.3.
- **Reversal**: remove the English engine (`speech/kokoro.py`); a new entry here.

## 2026-09-15 · Sign with Developer ID and notarize every release
- **Context**: the first builds (0.1.0, 0.1.1) were blocked by Gatekeeper and needed manual steps.
- **Decision**: from 0.1.2, releases are signed with an Apple Developer ID certificate (hardened runtime) and notarized.
- **Evidence**: commits `ba7b9d5`, `228f7b1`; CHANGELOG 0.1.2; `PUBLIC_RELEASE_CHECKLIST.md`.
- **Reversal**: none planned.

## 2026-09-04 · Paid voices only on the reader's own key, capped and priced up front
- **Context**: some readers want cloud voices; the on-device promise must survive that.
- **Decision**: OpenAI and ElevenLabs voices run on the reader's own key, sent directly from the Mac (no ReadEase
  server); the key stays local and write-only; cost is shown before Read; scope and session budget caps stop a reading
  before text is sent. Off unless the reader adds a key.
- **Evidence**: commits `1268e26`, `2df6b84`; `PRIVACY.md`; `src/vieneu_reader/speech/external/`; REQ RE-VOICE-008…013.
- **Reversal**: remove the external providers; a new entry here.

## 2026-08-31 · Tauri shell over a Python engine (Qt shell retired)
- **Context**: the speech engine is Python and cannot be ported (Vietnamese phonetics, ONNX voice runtime, time
  stretching); the owner's design system is web-based (Tailwind/CSS variables, see `app/src/styles/ds-tokens.css`).
- **Decision**: a thin Tauri v2 shell with a web interface, the Python engine as a sidecar process; SwiftUI and the
  existing Qt shell were rejected. Migration finished 2026-09-12 with the Qt lane removed.
- **Evidence**: `docs/tauri-migration-plan.md`; commits `90327db` (Tauri shell), `0fe6895` (Qt/Nuitka lane retired).
- **Reversal**: would need a new shell; a new entry here.

## 2026-08-27 · Source-available under PolyForm Noncommercial 1.0.0
- **Context**: the privacy promise should be checkable by anyone, while commercial reuse stays reserved.
- **Decision**: publish the source under PolyForm Noncommercial 1.0.0; free for personal and other noncommercial use.
- **Evidence**: commit `efc6ae5` (initial release), `94595bf`; `LICENSE`; `CONTRIBUTING.md`.
- **Reversal**: relicensing requires a new entry and contributor review (see `CONTRIBUTING.md`).
