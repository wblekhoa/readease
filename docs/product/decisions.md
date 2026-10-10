---
id: readease-decisions
type: decision
product: readease
title: "ReadEase — Decisions"
status: active
updated: 2026-10-10
---
# ReadEase — Decisions (append-only, newest first)

Entries before 2026-10-10 are reconstructed from commits, the CHANGELOG and docs in this repo; each cites its source.

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
