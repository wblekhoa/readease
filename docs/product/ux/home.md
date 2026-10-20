---
id: readease-ux-home
type: ux
product: readease
title: "ReadEase — Read home (UX)"
status: active
updated: 2026-10-19
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
