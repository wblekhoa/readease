---
id: readease-logic-home
type: logic
product: readease
title: "ReadEase — Read home (logic)"
status: active
updated: 2026-10-22
summary: "Default Read routing, five derived recents, shared path import and recovery without an additional content store."
tags: [area/reading, stack/react, stack/tauri, surface/macos]
reqPrefix: RE-HOME
relations:
  specifiedBy: [readease-ux-home]
  implements: [readease:app/src/ui/homeReading.ts, readease:app/src/ui/bookImport.ts, readease:app/src/ui/useShelf.ts, readease:app/src/App.tsx]
---
# ReadEase — Read home

## Purpose

Unify entry to document, Paste and selection reading. [App map](../systems/app/system.md) owns shared data lifetime; [library](library.md) owns managed imports.

## Inputs and outputs

| Action | Destination / effect |
|---|---|
| ordinary launch after setup | Read; no speech |
| Finder or Home picker/drop | import paths; open last successful readable book, no autoplay |
| Type/paste / Read a selection | existing draft / shortcut-permission guidance; no pretend webview capture |
| recent item | original book, current draft or saved paste, or focused capture by `at`; no autoplay |
| current reading → Open / Pause/Resume | return to origin / existing transport; never read-from-here |

Entering Read clears the document view/selection, retaining running audio/origin. Finder's specific-file request takes precedence over the ordinary launch destination.

## Rules

| REQ-ID | Rule | Status | Evidence |
|---|---|---|---|
| RE-HOME-001 | Read is the default entry. Open existing input workflows without autoplay; derive recent content without a separate history store. | live | [001](#evidence) |
| RE-HOME-002 | Read home is three entry points and one list of recent content: one line per item (kind glyph, title, progress for a started document, relative day), unfiltered; reading settings sit in a fixed footer whose panels open above it. | live | `app/tests/homeReading.test.ts` (`recent dates read as…`) |

## Recent-content contract

- Merge readable books, one nonblank current draft, nonblank saved pastes and nonblank captures with finite timestamps; sort newest first; take five. Skip saved pastes whose text exactly matches the current draft. Skip damaged books, retain original capture/translation/voice references.
- Book time is `listened_at`, fallback `imported_at` when absent. An invalid chosen date sorts as zero. Opening without hearing does not update heard time.
- Draft time changes when edited, not when Home opens. Saved pastes reopen their original text when available. Persistence and retention of pastes and captures follow the [history owner](history.md); Home derives its list without another store. This is distinct from the sidebar's five books with saved positions.
- Voice/rate and selection-translation open the existing panels; no Home preference copy. Openers are disabled during playback/export. [Translation](translation.md) owns target-voice scope.

## States and recovery

| State | Behavior / recovery |
|---|---|
| initial shelf load | loading; actions remain usable; no false empty claim |
| no book/draft/capture/active reading | three-action empty state |
| query fails | retain previous shelf and error; retry `library.list` |
| import running | serialize Home/Finder paths; also drain arrivals during refresh |
| some imports fail | continue others; return last error and open last successful listed/non-damaged result |
| import succeeds, refresh fails | do not guess a book; retry shelf load |
| unsupported drop / dialog failure | local error; choose supported file or retry picker |

Home/Finder share a queue, not the Library shelf's aggregate import-feedback owner. **Known limit:** successful-book navigation can hide a partial-import error; the next good refresh clears it. There is no durable per-file receipt.

## Evidence

- **001**: `app/tests/homeReading.test.ts`; `app/src/screens/Home.tsx`; `app/src/ui/useShelf.ts`; browser home entry/return flows

Additional queue coverage: `app/tests/bookImport.test.ts`. `home*` render recipes verify empty import, exact draft reopening, focused capture and preserved playback in both languages/themes. Native Finder/drop acceptance is still pending; mock routing does not prove it.

## Change log
- 2026-10-22: reviewed the render-audit changes adding Reader highlight recipes and real text-selection steps; Home recipes and routing are unchanged. Aligned the recent-content contract with existing saved-paste inputs and the shared history owner.
- 2026-10-21: audit 21/10: Home chips carry accessible names; the translation chip reads "Dịch · EN/Tắt" like the footer; "Recent" is an h2; Read tab has its own glyph. RE-HOME-002 evidence tagged in code.
- 2026-10-20: RE-HOME-002 simplified at the owner's request: no continue-reading card and no kind filter; recents only.

- 2026-10-20: condensed routing/recents/error contracts; rule and acceptance unchanged.
- 2026-10-19: introduced the unreleased Read entry and its derived recents.
