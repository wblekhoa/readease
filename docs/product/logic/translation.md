---
id: readease-logic-translation
type: logic
product: readease
title: "ReadEase — Selection translation (logic)"
status: active
updated: 2026-10-20
summary: "Selection-only translation: provider and target-voice eligibility, generation cancellation, bounded input/output, transient history and pending native acceptance."
tags: [area/translation, area/capture, area/voice, stack/react, stack/tauri, stack/swift, surface/macos]
reqPrefix: RE-PLAY
relations:
  partOf: [readease-system-app]
  specifiedBy: [readease-ux-reading]
  dependsOn: [readease-logic-reading, readease-logic-voices]
  implements: [readease:app/src/ui/translation.ts, readease:app/src/ui/useTranslation.ts, readease:app/src-tauri/src/translation.rs, readease:native/macos/Translation.swift]
---
# ReadEase — Selection translation

## Purpose

Read a captured passage in the chosen target language. Books, Paste and exports retain their own source language. Presentation belongs to [translation UX](../ux/reading.md#translate-a-selection-before-reading); shared transport belongs to [playback](reading.md).

## Inputs and outputs

Native capture/clipboard restoration → snapshot preferences and generation → translate → target voice → `read_selection_text`/speech. Result: spoken text, original, target and voice in the existing capture entry; no persistent passage store.

## Rules

| REQ-ID | Rule | Status | Evidence |
|---|---|---|---|
| RE-PLAY-025 | Optionally translate captured text with an installed Apple/local provider and matching local voice; cancel stale generations and retain passages only in session memory. | blocked | [025](#evidence) |

## Eligibility and bounds

| Choice / boundary | Contract |
|---|---|
| source / target | Manual Auto/VI/EN source, VI/EN target. Auto may recognize another language; provider support decides availability. Equal source/target returns original text without a pack/model request. |
| target voice | Installed, non-paid voice declaring the target language. If saved voice is stale, use the first matching local voice; no candidate means visible refusal. Never replace the book/Paste voice or silently read original/paid speech. |
| Apple | macOS 26+ with already-installed packs; unsupported pairs/missing packs are refused. No automatic downloads. |
| local providers | Fixed Ollama `127.0.0.1:11434` / LM Studio `127.0.0.1:1234`; no proxy, cookies, cache, redirect or remote URL setting. Reject cloud names and Ollama remote metadata. Third-party server logging/routing remains outside ReadEase's control. |
| request | ≤6,000 Swift `Character` values; model id ≤200 characters. Request/resource timeout 60/90 seconds, bridge deadline 95 seconds. |
| output | Nonempty, ≤24,000 characters. Local completion must finish with `stop`, without refusal/truncation. Strip a closed leading `<think>` block; reject malformed output. |

## States and recovery

| Event | Result |
|---|---|
| preferences unavailable / no target voice | stop with visible setup error |
| capture, translation off | record text immediately and read normally |
| capture, translation on | pending generation; record translated entry only after successful native result |
| Stop/new capture/playback/export | advance generation; cancel older Swift jobs; ignore stale App completion before speech/history update |
| provider failure | bounded translated error; never expose raw model output as an error label |
| replay/from-here | use stored spoken text and voice; do not translate again |

History holds at most 50 captures. Failed/cancelled translation creates no completed translated row. Only enabled/provider/model/source/target/voice preferences persist. Settings pair target and matching voice; enabling controls stay in the Translate panel, while Voice settings/hub show scoped status. Source/provider/model are disclosed on demand, with setup errors visible; the idle selection footer describes the effective voice. See the UX owner for dropdown/disclosure layout.

## Evidence

- **025**: `app/src-tauri/src/translation.rs`, `native/macos/Translation.swift`, `native/macos/TranslationTests.swift`, `app/tests/translation.test.ts`; `test_translation_preferences_round_trip_without_passage_data`. Implementation shipped in v0.1.23; complete native end-to-end owner acceptance remains pending, so the rule stays blocked rather than being promoted from source-only evidence.

Configuration round-trip: `tests/headless/test_server.py::test_translation_preferences_round_trip_without_passage_data`. Fixtures establish protocol/cancellation/configuration, not real-model translation quality. Complete native end-to-end owner acceptance remains pending despite inclusion in v0.1.23; status is unchanged. See the [status convention](../systems/app/system.md#status-and-verification).

## Change log

- 2026-10-19: moved the existing translation rule/details from `reading.md`; no new requirement or behavior.
