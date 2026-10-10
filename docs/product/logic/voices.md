---
id: readease-logic-voices
type: logic
product: readease
title: "ReadEase — Voices and models (logic)"
status: active
updated: 2026-10-10
reqPrefix: RE-VOICE
relations:
  specifiedBy: [readease-ux-voices]
  implements: [readease:src/vieneu_reader/speech/vieneu.py, readease:src/vieneu_reader/speech/kokoro.py, readease:src/vieneu_reader/speech/external/route.py, readease:src/vieneu_reader/speech/external/spend.py, readease:src/vieneu_reader/speech/external/secrets.py, readease:app/src/ui/readingSources.ts, readease:app/src/ui/ModelPanel.tsx]
---
# ReadEase — Voices and models (logic)

## Purpose
- Let the reader decide what to download and what to pay for; refuse by name rather than fall back silently; keep a
  paid key local and a paid reading within the figure shown.
- Success signal: no surprise download, no surprise bill, no key ever shown or logged.

## Rules
| REQ-ID | Rule (behaviour-changing) | Status (live / not built) | Evidence (code path or test) |
|---|---|---|---|
| RE-VOICE-001 | The first-run screen is shown only while nothing can read (no ready model and no key); a key counts before its voices are listed. | live | `app/tests/readingSources.test.ts` ("the first-run screen is due only while nothing at all can read") |
| RE-VOICE-002 | Preparing the Vietnamese model downloads only the chosen build (Standard or Highest). | live | `tests/speech/test_precision.py` (`test_preparing_downloads_only_the_chosen_build`) |
| RE-VOICE-003 | The build in use cannot be removed; a build not in use can. | live | `tests/speech/test_precision.py` (`test_the_build_in_use_is_refused`) |
| RE-VOICE-004 | A model download can be cancelled from the interface. | live | `tests/headless/test_server.py` (`test_a_download_can_be_abandoned_from_the_shell`) |
| RE-VOICE-005 | A local model unused for 300 s releases its memory and loads again on the next sentence. | live | `src/vieneu_reader/headless/server.py` (`IDLE_RELEASE_SECONDS`); `tests/speech/test_vieneu_contract.py`, `tests/speech/test_kokoro.py` (`test_an_idle_model_is_released…`) |
| RE-VOICE-006 | On a Mac with about 8 GB of memory or less, Voices & models suggests the Standard build. | live | `app/src/ui/ModelPanel.tsx` (`LOW_MEMORY_BYTES`) |
| RE-VOICE-007 | A voice is never refused for the language of the text; the app only suggests a fitting voice or the download. | live | `app/tests/readingSources.test.ts` ("the hint: a voice on text it was not made for…") |
| RE-VOICE-008 | A paid voice without a key is refused by name (`no_key`), never silently replaced by a local voice. | live | `tests/speech/test_external_route.py` (`test_no_key_is_a_named_refusal_not_a_silent_fallback`) |
| RE-VOICE-009 | A key the provider refuses is not saved. | live | `tests/speech/test_external_reading.py` (`test_a_key_the_service_refuses_is_NOT_saved`) |
| RE-VOICE-010 | A saved key never comes back out through the engine's replies. | live | `tests/speech/test_external_reading.py` (`test_the_key_never_comes_back_out`) |
| RE-VOICE-011 | When the session budget would be exceeded, the reading stops before any text is sent to the provider. | live | `tests/speech/test_external_reading.py` (`test_the_budget_stops_it_before_the_characters_leave`) |
| RE-VOICE-012 | A paid voice whose model this build cannot price locks the Read button instead of reading unpriced. | live | `tests/speech/test_external_reading.py` (`test_a_model_this_build_cannot_price_locks_the_button_rather_than_reading_free`) |
| RE-VOICE-013 | Any provider error text that quotes the key is scrubbed before it reaches the screen. | live | `src/vieneu_reader/speech/external/secrets.py`; `tests/speech/test_external_secrets.py` (`test_a_provider_error_that_quotes_the_key_is_scrubbed`) |

## States and transitions
| State | Trigger | Next state | Edge case |
|---|---|---|---|
| model not downloaded | Download and use | downloading | only the chosen build is fetched |
| downloading | Cancel | model not downloaded | a cancel with nothing downloading says so |
| downloading | complete | ready | |
| ready (in memory) | 300 s unused | ready (released) | next sentence reloads it |
| ready | switch build | downloading new build | asks first, states the download size; old build removable once not in use |
| no key | Add key → provider accepts | key saved | offline does not wipe a key that already worked |
| no key | Add key → provider refuses | no key | reason shown with what to do |
| paid reading | budget reached | stopped | stopped before characters leave the Mac |

## Fixed vs flexible
- Fixed (logic the UI must not change): one route decision (`pick_voice_route`) for local / paid / blocked; refusals are
  named, never silent fallbacks; the key is write-only across the engine pipe; cost is known before Read.
- Flexible (UI may explore): how models, voices, favourites and the cost figure are presented; wording of hints.

## Open questions
- None recorded.

## Change log
- 2026-10-10: created; REQ-IDs added as comments next to the evidence (tests, and `LOW_MEMORY_BYTES`) in the same commit.
