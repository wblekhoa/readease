---
id: readease-ux-home
type: ux
product: readease
title: "ReadEase — Read home (UX)"
status: active
updated: 2026-10-22
summary: "The default Read tab offers file, typed/pasted text and selection entry points, session recents, current playback and access to the existing voice and translation settings."
tags: [area/reading, stack/react, surface/macos]
relations:
  dependsOn: [readease-logic-home]
  specifies: [readease:app/src/screens/Home.tsx]
---
# ReadEase — Read home (UX)

## Entry
The first sidebar tab is **Đọc / Read**, the ordinary launch destination after voice setup. Opening a file from Finder goes directly to its document. Library remains a separate shelf, followed by Paste text and Read a selection; Move notes sits under Tools.

## Empty state
When the library, current draft and selection history are all empty, show “Bạn muốn đọc gì?” with three equally clear actions:
- Open a document: native picker or native PDF/EPUB drop. Import by path and open the last successful document.
- Type or paste text: open the existing editable Paste workspace, keeping its in-memory draft.
- Read a selection: open the shortcut/permission guidance in the selection workspace; do not pretend the ReadEase page itself is an external selection.
Loading has its own message. Library failures show retry, never a false empty-state claim. The actions remain available when recent content exists, without the empty-state heading.

## Content and settings
- A live reading or paused session offers pause/resume and an explicit Open content action. Navigation alone never starts or stops audio.
- Recent shows up to five items in time order: library books by heard time (fallback import time), the current pasted draft, and captured passages from this app session. Rows open their content; opening does not autoplay. Translated captures open the paired original/translation in the existing focused-passage view.
- Reading settings shows the current voice/rate and a separately scoped selection-translation summary. Both open the existing panels. Settings are disabled during playback/export to avoid changing a running job.
- Text and capture previews stay in memory. No new persistent history or content storage is introduced.

## Layout and interaction
Use the shared button/surface/notice/cover primitives and palette. Entry actions form three columns when the content area fits and stack otherwise. The body scrolls beneath the existing shell chrome; keep every action keyboard reachable. Labels and empty states support Vietnamese/English and both themes.

- 2026-10-20 (owner): minimal layout - the three entry points show an icon and a name (hint as tooltip); reading settings (voice, scan translation) sit in a fixed footer at the bottom of Read home, outside the scroll.
- 2026-10-22 (owner: "tạo trang riêng cho các menu này, giống với SpeakEase"): the side column's settings - Voice, Translate before reading, Pronunciations, Voices & models - open as pages of their own in the main area, under their name in the toolbar, one centred column that scrolls, with the item marked as the current page. As in SpeakEase, each group of rows is a card (soft fill, hairline edge, solid hairlines between rows) under a small-caps title, and a field's own label (Reading language, Translation voice) takes the same small caps. The footer's Voice and Translate buttons still open the same panels as popovers for a change made while reading. A link from one settings page to another (Voice → Translate before reading, Pronunciations, Voices & models) goes to that page. The dimming under the sheets that remain is a neutral dark, no longer navy.
- 2026-10-21 (owner: "bỏ đi divider, phân tích bằng spacing thôi"): the side column's groups (Tools, Settings) and the folded rail's settings group are set apart by space alone - no rules.
- 2026-10-20 (owner): the side column holds navigation and settings, like SpeakEase - Read, Library, Paste, Read a selection; Tools; Settings (Voice, Translate before reading, Pronunciations, Voices & models). The "Reading now" list is gone (Read home lists recent content). Opened from the column, each setting was a centred sheet over a scrim (pages since 22/10).
