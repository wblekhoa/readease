---
id: readease-logic-voices
type: logic
product: readease
title: "ReadEase — Voices and models (logic)"
status: active
updated: 2026-10-20
summary: "Voice/model eligibility, explicit download lifecycle, key verification, pricing/session-budget guards and language preference ownership."
tags: [area/voice, area/security, area/performance, stack/python, surface/macos]
reqPrefix: RE-VOICE
relations:
  specifiedBy: [readease-ux-voices]
  implements: [readease:src/vieneu_reader/speech/vieneu.py, readease:src/vieneu_reader/speech/kokoro.py, readease:src/vieneu_reader/speech/external/route.py, readease:src/vieneu_reader/speech/external/spend.py, readease:src/vieneu_reader/speech/external/secrets.py, readease:app/src/ui/readingSources.ts, readease:app/src/ui/ModelPanel.tsx]
---
# ReadEase — Voices and models

## Purpose

Make model downloads and paid speech explicit choices. Resolve one local/paid/blocked route, without silent substitution or key disclosure.

## Inputs and outputs

| Input | Output / scope |
|---|---|
| model/key status | first-run readiness and available catalogue |
| chosen voice/rate/language, shortlist/favorites | persistent preferences; language tabs may choose a remembered fitting voice, book-open only suggests |
| source text + voice/model/scope | estimate or named refusal before paid action |
| provider key | verification result and set/unset status; never key readback |

[Selection translation](translation.md#eligibility-and-bounds) separately owns target-voice eligibility; it does not replace the book/Paste choice. [Speech preparation](reading.md#speech-preparation) owns pronunciation changes shared by reading, cache and estimates.

## Rules

| REQ-ID | Rule | Status | Evidence |
|---|---|---|---|
| RE-VOICE-001 | Show first-run setup only while no model or configured key can read; a key counts before its catalogue arrives. | live | [001](#evidence) |
| RE-VOICE-002 | Download only the chosen Vietnamese model build. | live | [002](#evidence) |
| RE-VOICE-003 | Refuse removal of the build in use; allow another build to be removed. | live | [003](#evidence) |
| RE-VOICE-004 | Allow model-download cancellation. | live | [004](#evidence) |
| RE-VOICE-005 | Release a local model after 300 seconds idle; reload on the next sentence. | live | [005](#evidence) |
| RE-VOICE-006 | Suggest Standard on Macs with about 8 GB RAM or less. | live | [006](#evidence) |
| RE-VOICE-007 | Suggest a language-fitting voice/download instead of refusing ordinary text for voice-language mismatch. | live | [007](#evidence) |
| RE-VOICE-008 | Refuse a keyless paid voice by name; never silently substitute local speech. | live | [008](#evidence) |
| RE-VOICE-009 | Default to Đức Trí within the initial five-voice shortlist; preserve existing and per-book choices. | live | [009](#evidence) |
| RE-VOICE-010 | Never return a stored provider key through engine replies. | live | [010](#evidence) |
| RE-VOICE-011 | Stop before sending billable text that would exceed the session ceiling. | live | [011](#evidence) |
| RE-VOICE-012 | Lock paid reading when this build cannot price the model. | live | [012](#evidence) |
| RE-VOICE-013 | Scrub provider-key content from displayed provider errors. | live | [013](#evidence) |
| RE-VOICE-014 | Do not save a key rejected by its provider. | live | [014](#evidence) |

## States and recovery

| State / action | Result / boundary |
|---|---|
| setup with no model/key | user may enter Read without downloading; engine-status failure still leaves a recoverable app |
| catalogue arrives | retain saved/user-touched voice choice |
| Download chosen build | app-wide job shared by setup/hub/settings; another Vietnamese precision restarts the engine |
| close panel | job continues; no second download owner |
| cancel/failure/completion | expose outcome, refresh actual installed status/catalogue; percentage alone is not successful load |
| unused model | release memory after idle interval, not downloaded weights |
| verify new key | save only on provider acceptance; empty value removes it; network failure does not wipe an existing working key |
| paid request | require known price and check ceiling before more text leaves |

A model restart respects the [export lock](export.md#states-and-recovery). Download failure never chooses paid speech automatically.

## Pricing and identity limits

- Counted characters/credits differ from time/token estimates; an estimate is not a provider receipt. Auditions spend against the ceiling; cached app-authored sample audio does not charge again. Superseding playback never subtracts money already spent.
- The native [chapter-scope gap](reading.md#known-limits) affects the UI's chapter quote/bound; session-budget refusal is independent.
- Default voice keeps the established code. The rejected-key rule was previously mislabeled with that same code; its repaired identity below preserves the old test assertions. Historical decision/release records remain intact.
- Compatibility/installed status does not establish real-model speed or translation quality.

## Evidence

- **001**: `app/tests/readingSources.test.ts` ("the first-run screen is due only while nothing at all can read")
- **002**: `tests/speech/test_precision.py` (`test_preparing_downloads_only_the_chosen_build`)
- **003**: `tests/speech/test_precision.py` (`test_the_build_in_use_is_refused`)
- **004**: `tests/headless/test_server.py` (`test_a_download_can_be_abandoned_from_the_shell`)
- **005**: `src/vieneu_reader/headless/server.py` (`IDLE_RELEASE_SECONDS`); `tests/speech/test_vieneu_contract.py`, `tests/speech/test_kokoro.py` (`test_an_idle_model_is_released…`)
- **006**: `app/src/ui/ModelPanel.tsx` (`LOW_MEMORY_BYTES`)
- **007**: `app/tests/readingSources.test.ts` ("the hint: a voice on text it was not made for…")
- **008**: `tests/speech/test_external_route.py` (`test_no_key_is_a_named_refusal_not_a_silent_fallback`)
- **009**: `tests/playback/test_preferences.py` (`test_the_default_voice_is_one_the_switcher_starts_with`, `test_nothing_stored_yet_reads_as_the_shipped_default`)
- **010**: `tests/speech/test_external_reading.py` (`test_the_key_never_comes_back_out`)
- **011**: `tests/speech/test_external_reading.py` (`test_the_budget_stops_it_before_the_characters_leave`)
- **012**: `tests/speech/test_external_reading.py` (`test_a_model_this_build_cannot_price_locks_the_button_rather_than_reading_free`)
- **013**: `src/vieneu_reader/speech/external/secrets.py`; `tests/speech/test_external_secrets.py` (`test_a_provider_error_that_quotes_the_key_is_scrubbed`)
- **014**: `tests/speech/test_external_reading.py` (`test_a_key_the_service_refuses_is_NOT_saved`)

Catalogue/language/startup policy: `app/tests/readingSources.test.ts`, `app/tests/voiceShortlist.test.ts`; downloads use `app/src/ui/useModels.ts`. Real-model memory/quality targets need separate measured acceptance.

## Change log

- 2026-10-20: condensed voice/model states and linked translation/export owners; identities unchanged.
- 2026-10-19: repaired the duplicate default/rejected-key identifier.
- 2026-10-15: measured default Adam → Đức Trí; see `../decisions.md`.
- 2026-10-10: introduced requirement evidence annotations.
