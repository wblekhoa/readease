---
id: readease-decisions
type: decision
product: readease
title: "ReadEase — Decisions"
status: active
updated: 2026-10-15
---
# ReadEase — Decisions (append-only, newest first)

Entries before 2026-10-10 are reconstructed from commits, the CHANGELOG and docs in this repo; each cites its source.

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
