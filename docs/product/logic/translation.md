---
id: readease-logic-translation
type: logic
product: readease
title: "ReadEase — Translate before reading (logic)"
status: active
updated: 2026-10-21
summary: "Translate before reading for Read a selection and Paste text, each with its own switch: provider and target-voice eligibility, long-paste splitting, generation cancellation, bounded input/output and pending native acceptance."
tags: [area/translation, area/capture, area/voice, stack/react, stack/tauri, stack/swift, surface/macos]
reqPrefix: RE-PLAY
relations:
  partOf: [readease-system-app]
  specifiedBy: [readease-ux-reading]
  dependsOn: [readease-logic-reading, readease-logic-voices]
  implements: [readease:app/src/App.tsx, readease:app/src/ui/translation.ts, readease:app/src/ui/TranslationSettings.tsx, readease:app/src/ui/useTranslation.ts, readease:app/src-tauri/src/translation.rs, readease:native/macos/Translation.swift]
---
# ReadEase — Translate before reading

## Purpose

Read a captured passage, or pasted text, in the chosen target language - each source has its own switch under one master switch. Books and exports retain their own source language (books are a later phase). Presentation belongs to [translation UX](../ux/reading.md#translate-a-selection-before-reading); shared transport belongs to [playback](reading.md).

## Inputs and outputs

Native capture/clipboard restoration → snapshot preferences and generation → translate → target voice → `read_selection_text`/speech. Result: spoken text, original, target and voice in the existing capture entry; no persistent passage store.

## Rules

| REQ-ID | Rule | Status | Evidence |
|---|---|---|---|
| RE-PLAY-025 | Optionally translate captured text with an installed Apple/local provider and matching local voice; cancel stale generations and retain passages only in session memory. | blocked | [025](#evidence) |
| RE-PLAY-035 | Translation starts quickly: a translated book reading begins after the first three paragraphs are translated - the engine reads up to the first paragraph not yet translated, the host translates the rest of the chapter and the next one while it speaks, and the page carries on from where it stopped (inside the chapter that costs none of the press's chapter count). ReadEase's own translator is started as a screen that translates opens with it in use (Paste, Read a selection, a book), so the first translation does not wait for the server's cold start (~6 s). | blocked | `tests/headless/test_server_book_translation.py` (`test_the_reading_stops_at_the_first_paragraph_not_yet_translated`); `prewarm_translator` in `app/src-tauri/src/lib.rs`. Not run in the built app with a real translator. |
| RE-PLAY-033 | Exporting a translated paste saves what was heard: while the translation is shown on the paste sheet, the export is the translation in the translation voice (no price: a local voice); otherwise the pasted text in the chosen voice. The export's review still belongs to the pasted text - editing the box ends it. | live | `app/tests/translation.test.ts` (`a paste export saves what was heard`); harness run 21/10: `export_text` received the English translation and `af_heart` |
| RE-PLAY-032 | A library book can be read in translation. The unit is the paragraph (a block segment and its split pieces), never a 240-character piece. The host translates; the engine keeps each paragraph's translation in `translations.sqlite3` (0600, keyed book · paragraph · language, provider noted), answers which paragraphs a reading from here needs (`translation.paragraphs`, chapter by chapter, marking those already kept), stores (`translation.put`, only paragraphs of that book), lists and clears them, and removes a book's translations with the book. `read.book` with `translation: {target}` speaks the kept translations in the target language with the translation voice, saves progress with the book's own voice, and refuses by name (`translation:missing`) when a paragraph in scope has none. The host reads a chapter at a time: `read_book_translated` asks for this chapter and the next, translates this chapter's missing paragraphs (progress `reading:book_translating`), reads it, and translates the next in the background under the same generation; at the chapter's end the page calls again with the next chapter's first paragraph while the press's chapter count allows. The Library has its own switch under the master one (a setting saved before reads back off); a book already in the target language reads as it is. The Reader shows each kept translation under its paragraph. | blocked | [032](#evidence) |
| RE-PLAY-031 | ReadEase has its own translator: Tencent's Hy-MT2 1.8B (Q4_K_M GGUF, 1.1 GB, Apache-2.0), downloaded only on request from Voices & models from a pinned revision and checked against its published SHA-256, removable there. The bundled llama.cpp `llama-server` (MIT, built from a pinned commit without OpenSSL/libcurl) runs it on 127.0.0.1 at a free port, started on first use and stopped after 5 idle minutes, on removal and on quit. A new **Automatic** provider - the default, and what an `apple` saved before sources existed becomes - uses it once downloaded and Apple Translation until then. | blocked | [031](#evidence) |
| RE-PLAY-030 | Voices & models shows a Translation group: whether the chosen translator can translate now (Apple with both English↔Vietnamese packs, or a local server that has the chosen model) and, for each of Apple Translation, Ollama and LM Studio, what it found and how to fix it. It only asks; it downloads, installs and changes nothing. | live | `app/tests/translation.test.ts` (`the hub calls the chosen translator ready only when it can translate now`), render audit `hub`, harness `?translators=missing` |
| RE-PLAY-029 | One translation setting chooses its sources (Read a selection, Paste text), each switched separately under the master switch; a setting saved without sources reads back Selection-only. Paste with its switch on is translated whole - split into pieces of at most 5,000 characters at paragraph, then sentence, then word boundaries, rejoined by blank lines - then read with the target voice; Stop or a newer reading cancels it and nothing stale is spoken or kept. History keeps the translation with its original only once it is known. | blocked | [029](#evidence) |

## Eligibility and bounds

| Choice / boundary | Contract |
|---|---|
| source / target | Manual Auto/VI/EN source, VI/EN target. Auto may recognize another language; provider support decides availability. Equal source/target returns original text without a pack/model request. |
| target voice | Installed, non-paid voice declaring the target language. If saved voice is stale, use the first matching local voice; no candidate means visible refusal. Never replace the book/Paste voice or silently read original/paid speech. |
| Apple | macOS 26+ with already-installed packs; unsupported pairs/missing packs are refused. No automatic downloads. |
| ReadEase translator (031) | Loopback port chosen by the host, 1024-65535, never by the webview; Hy-MT2's own one-turn instruction, temperature 0, `finish_reason` must be `stop`; same output cleanup and bounds as local providers. Server: `-ngl 99 -c 8192 --parallel 1`, 90 s start deadline. |
| local providers | Fixed Ollama `127.0.0.1:11434` / LM Studio `127.0.0.1:1234`; no proxy, cookies, cache, redirect or remote URL setting. Reject cloud names and Ollama remote metadata. Third-party server logging/routing remains outside ReadEase's control. |
| request | ≤6,000 Swift `Character` values; model id ≤200 characters. Request/resource timeout 60/90 seconds, bridge deadline 95 seconds. |
| paste (029) | Any length up to the Paste limit; pieces ≤5,000 characters each, so every native request stays under the 6,000 bound. A paragraph or sentence longer than a piece is cut at word boundaries, then hard-cut only if a single word exceeds it. |
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
| paste, translation on (029) | pending generation; nothing in History and no voice switch until the translation returns; then read it and keep translation + original |

History holds at most 50 captures. Failed/cancelled translation creates no completed translated row. Only enabled/provider/model/source/target/voice preferences persist. Settings pair target and matching voice; enabling controls stay in the Translate panel, while Voice settings/hub show scoped status. Source/provider/model are disclosed on demand, with setup errors visible; the idle selection footer describes the effective voice. See the UX owner for dropdown/disclosure layout.

## Evidence

- **025**: `app/src-tauri/src/translation.rs`, `native/macos/Translation.swift`, `native/macos/TranslationTests.swift`, `app/tests/translation.test.ts`; `test_translation_preferences_round_trip_without_passage_data`. Implementation shipped in v0.1.23; complete native end-to-end owner acceptance remains pending, so the rule stays blocked rather than being promoted from source-only evidence.

- **029**: `app/tests/translation.test.ts` (legacy Selection-only default, per-source switches), `app/src-tauri/src/translation.rs` (`long_text_splits_at_paragraphs_and_never_over_the_limit`), `read_text_translated` in `app/src-tauri/src/lib.rs`, the harness `read_text_translated` mock (`?translation=vi-en&translation_sources=paste`). Checked in the browser harness only; native end-to-end acceptance with a real translator is pending, so the rule stays blocked like 025.

- **031**: `tests/translation/test_model.py` (pinned URL, hash mismatch never ready, remove only its folder), `tests/headless/test_server_translator.py` (status/prepare/remove on the wire), `app/src-tauri/src/local_translator.rs` tests (health probe; the ignored `starts_the_bundled_server_on_the_model_and_stops_it` run 20/10 against the real binary and model, at a path with spaces), `app/src-tauri/src/translation.rs` (`automatic_falling_back_to_apple_points_at_the_readease_translator`), `native/macos/TranslationTests.swift` (loopback-only port) plus an end-to-end run through the production bridge against the real server and model (`READEASE_TRANSLATOR_PORT=… scripts/test-native-translation.sh`: EN→VI and VI→EN, 0.25 s), `app/tests/translation.test.ts` (Automatic resolution, legacy Apple → Automatic). Probe 20/10: 0.2-0.4 s a paragraph, ~1.5 GB resident while loaded. Not yet run inside a signed, notarized build, and the owner's blind comparison with Apple Translation is pending - so blocked.

- **032**: `tests/storage/test_translations.py`, `tests/headless/test_server_book_translation.py` (paragraph join, translated reading keeps the book's voice, refusal by name, list/clear, removal with the book). Host: `read_book_translated` in `app/src-tauri/src/lib.rs`; shell: `app/tests/translation.test.ts` (library switch, legacy off), harness `read_book_translated` + `translation.list` mocks, render audit `reader/library_translated` (bilingual page), and a harness run 21/10: translating 0/6 → 3/6, read with the English voice, carried into the next part, Stop ended it with no continuation. Not yet run in the built app with a real translator, so blocked.

Configuration round-trip: `tests/headless/test_server.py::test_translation_preferences_round_trip_without_passage_data`. Fixtures establish protocol/cancellation/configuration, not real-model translation quality. Complete native end-to-end owner acceptance remains pending despite inclusion in v0.1.23; status is unchanged. See the [status convention](../systems/app/system.md#status-and-verification).

## Change log
- 2026-10-21: RE-PLAY-035 - translated reading starts after three paragraphs; translator prewarm.
- 2026-10-21: RE-PLAY-033 - translated paste export.
- 2026-10-21: RE-PLAY-032 host and shell - chapter-at-a-time translated reading, Library switch, bilingual Reader.
- 2026-10-21: RE-PLAY-032 (engine part) - per-book paragraph translations store and translated `read.book`.
- 2026-10-21: audit 21/10: hub/settings copy no longer points to macOS 15 workarounds or "Models and voices"; translator remove button named; panel titled "Dịch trước khi đọc".
- 2026-10-21: audit fixes - the paste splitter cuts after "…" at a character boundary (it panicked on the 3-byte ellipsis); the translator server starts without holding the lock, so quitting or removing the model mid-start returns at once (`a_stop_during_the_warm_up_does_not_wait_for_it`).
- 2026-10-20: RE-PLAY-031 - ReadEase translator (Hy-MT2 via bundled llama.cpp) and the Automatic provider.
- 2026-10-20: RE-PLAY-030 - translator status in Voices & models.
- 2026-10-20: RE-PLAY-029 - sources per switch; Paste translated whole before reading.

- 2026-10-19: moved the existing translation rule/details from `reading.md`; no new requirement or behavior.
