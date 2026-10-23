---
id: readease-releases
type: release
product: readease
title: "ReadEase — Releases"
status: active
updated: 2026-10-23
summary: "User-facing changes, shipped REQ-IDs and channel of each ReadEase GitHub release from v0.1.0 to v0.1.26, newest first."
tags: [area/release, area/updater, surface/macos]
relations:
  presentedBy: [website:/projects/readease]
---
# ReadEase — Releases (newest first)

Source of truth for details: `CHANGELOG.md` (repo root) and `gh release list -R wblekhoa/readease`. One line per release
here; REQ-IDs were introduced on 2026-10-10, so only releases whose shipped behaviour maps to a current rule are traced.
The landing page `wblekhoa.github.io/readease` links the newest release at view time, and the author's portfolio presents the
product at `website:/projects/readease`.

## v0.1.26 · 2026-10-23
- **What changed for users**:
  - A click on a paragraph no longer starts reading. Hover a paragraph, or a part in Read a selection, and press the ▶ in its left margin.
  - Panels opened while the highlight bar is up sit on top of it.
  - Documents without a cover of their own (Markdown, Word and other text files) get a paper cover: format, title and first chapter names on tinted paper with a folded corner. The colour is stable per document and never shared with a neighbour on the shelf.
- **REQ-IDs shipped**: no rule changed; UX recorded in `ux/reading.md` (▶ on hover) and `ux/library.md` (paper covers).
- **Verification**: 1039 Python tests (7 skipped), 277 UI tests, 48 Rust tests. Render audit: 25 groups plus 91 keyboard/pointer checks, each group run on its own.
- **Channel**: GitHub release with Developer ID signature, notarization and in-app updater.
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.25 · 2026-10-23
- **What changed for users**:
  - Settings have pages of their own. Voice, Translate before reading, Pronunciations and Voices & models open from the side column in the main window, like SpeakEase.
  - Each settings group is a light grey card without an edge, with dotted rules between rows and small-caps titles. The footer's buttons still open the same panels as popovers while reading.
  - A download in Voices & models shows at the top of the page.
  - The dimming behind sheets is a neutral dark instead of a blue one.
  - The switch-mode button beside a screen's title is gone.
- **REQ-IDs shipped**: no rule changed; UX recorded in `ux/home.md` (settings pages, 22/10) and `readease-hig.md`.
- **Verification**: 1038 Python tests (7 skipped), 273 UI tests, 48 Rust tests. Render audit: 25 groups plus 89 keyboard checks, each group run on its own.
- **Channel**: GitHub release with Developer ID signature, notarization and in-app updater.
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.24 · 2026-10-22
- **What changed for users**: Highlights and notes made in the Reader: select words for a five-colour bar with Note; press a highlight to edit its note, remove it or recolour it (ReadEase's own); Copy as Markdown in the Notes tab. Paste text as a visible sheet with Export audio beside Read text. A quieter History dialog, re-laid Translation options and a side column without rules. It also ships everything listed under the 2026-10-20 entry below: Read home, background updates, the side column, translation for pasted text and Library books, ReadEase's own translator, more file formats, history and the performance work.
- **REQ-IDs shipped**: RE-NOTE-005, RE-NOTE-006, RE-NOTE-007 (live); RE-NOTE-008 (blocked until Copy as Markdown is run in the built app); RE-HOME-001, RE-UPDATE-001 and RE-PLAY-029…035, each at the status its logic doc records.
- **Verification**: 1038 Python tests (7 skipped), 273 UI tests, 48 Rust tests. Render audit: 24 groups plus 89 keyboard checks, each group run on its own. The Developer ID build `0.1.23+d2dedf4` of the same code was notarized, accepted by Gatekeeper and installed on the owner's Mac.
- **Channel**: GitHub release with Developer ID signature, notarization and in-app updater.
- **Shown in**: CHANGELOG.md; GitHub release notes.

## Work shipped in v0.1.24 · recorded 2026-10-20
- **Documentation organization**: separate playback, translation and export owners; compact rule tables and linked shared policy. All 57 existing rule IDs/statuses and native holds remain; runtime behavior is unchanged.
- **Logic documentation audit**: app state/data/concurrency map, note-sync/transfer rules (RE-NOTE-001…004), repaired RE-VOICE-009/014 identity, explicit native chapter-scope gap and corrected feedback/update privacy wording. Documentation/evidence annotations only; no runtime change from this audit.
- **Read home**: First/default Đọc tab with an actionable empty state, shared file import, derived session recents and existing reading settings (RE-HOME-001).
- **Prepared for review**: Non-blocking update notice in the expanded/folded sidebar, dismissible detail popover, background download and explicit safe apply boundary (RE-UPDATE-001).
- **Status**: Shipped in v0.1.24 (2026-10-22).

## v0.1.23 · 2026-10-18
- **What changed for users**: Optional Apple/local translation before reading a selection, target-language local voices and compact translation settings. Capture history uses separate blocks with original/translation sections. Selection and document detail share a solid reading underline and a small blue Pause/Resume button without changing text geometry. Page margins and Next/Previous hit areas are balanced. Refined native floating controls, localized menu-bar reading controls and a larger default window.
- **REQ-IDs shipped**: RE-PLAY-024 (native floating controller), RE-PLAY-025 (selection translation), RE-PLAY-026 (shared reading position control).
- **Verification**: 236 UI tests, 43 Rust tests, 976 Python tests (7 skipped), native selection bridge and floating-panel geometry/actions. Production Apple bridge passed both VI→EN and EN→VI with installed packs; local-provider fixture passed cancellation/protocol checks. Browser checks covered selection blocks, pause/resume, page turns, balanced margins and unchanged paragraph geometry. Focus/fullscreen/assistive-technology and whole-app native performance limits in RE-PLAY-024 remain unverified.
- **Channel**: GitHub release with Developer ID signature, notarization and in-app updater.
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.22 · 2026-10-16
- **What changed for users**: Export a chapter range or whole book as an M4B audiobook while browsing or minimising. Progress shows synthesis, normalisation and encoding; cancelling preserves an existing file. Reader and Library share the folded sidebar; hovering Contents, Notes or Search opens an interactive preview. Panel gaps and scrolling are consistent, and moving the pointer into a preview keeps it open.
- **REQ-IDs shipped**: RE-PLAY-020/021/022 (audiobook export and background lifecycle); shared Reader sidebar and panel interaction contract in `ux/reading.md`.
- **Release performance check**: The optimised native app with its frozen local voice engine measured 59.92 FPS at idle and 59.99 FPS while exporting, using a temporary requestAnimationFrame probe. 697/653 visible, focused samples within 600ms of preview changes; p95 19/18ms, p99 26/24ms, max 35/30ms, no frames over 50ms. Nine direct panel switches per mode, plus opening tests. This measures WebKit callback cadence, not whole-display composited FPS. The probe is absent from the distributable.
- **Channel**: GitHub release with Developer ID signature, notarization and in-app updater.
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.21 · 2026-10-10
- **What changed for users**: The folded side column names its icons on hover and opens from the top; dragging its edge eases between the rail and the column; the open column carries the ReadEase mark; the interface starts in the Mac's language.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.20 · 2026-10-09
- **What changed for users**: The side column folds to a rail of icons and its edge folds and unfolds it; the reading status floats above the control bar; pasted Markdown reads as meant; voices can be previewed and starred from the Voice list; a local voice gives its memory back after five quiet minutes, so an 8 GB Mac has room; ElevenLabs reads with eleven_v4_turbo. The app has a new bundle id: installs over 0.1.19, or lets 0.1.19 install it, and asks once for Accessibility again.
- **REQ-IDs shipped**: RE-VOICE-005, RE-VOICE-006 (idle release, low-memory hint); RE-PLAY-008 (Markdown read as meant).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.19 · 2026-09-26
- **What changed for users**: Hear where a chapter starts and where a section does; search results and notes no longer pull the page back; favourite voices come first.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.18 · 2026-09-25
- **What changed for users**: Two things that were in the way while listening: the Speaker row now names the device the voice is on, and the Change voice menu in the reading bar opens where it can be seen.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.17 · 2026-09-25
- **What changed for users**: Clearer seams for the ear: a breath around the chapter chime, a sound of its own for a part, one sound for one arrival, and no printed contents read aloud; pictures that show on the dark page and open from the keyboard.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.16 · 2026-09-24
- **What changed for users**: The voice follows the text: it breathes where the text does, chimes where the contents open a chapter or a part, and falls silent at a change of scene; the contents show the document's own numbered tree.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.15 · 2026-09-23
- **What changed for users**: For the ear and the keyboard: VoiceOver hears what ReadEase is doing, panels and menus work without a mouse, and the interface speaks its own language.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.14 · 2026-09-22
- **What changed for users**: The new face: the soundwave-ring icon, a disk image that shows you where to drag it, and a website to point people at.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: the landing page (wblekhoa.github.io/readease) launched with this release; author's portfolio case study `website:/projects/readease`.

## v0.1.13 · 2026-09-21
- **What changed for users**: The listening release: the voice picks the thread back up after a break, the bar says how long is left, Now Playing shows the cover - and the brand is blue.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.12 · 2026-09-21
- **What changed for users**: Updates with a Mac's manners - skip this version, later, install when quitting, automatic download if you want it - and release notes that read as paragraphs.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.11 · 2026-09-21
- **What changed for users**: The first release the app fetches by itself: a log file for bug reports, and the bundle's own category and copyright.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.10 · 2026-09-21
- **What changed for users**: A Mac app of its own: a menu bar with every command, documents that open from Finder and the Dock, a window that remembers itself, a reading that Control Center and the media keys know about, and an updater that will bring the next release by itself. Ships as a disk image beside the zip.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.9 · 2026-09-20
- **What changed for users**: The side column's states become alphas of the ink on the Mac's sidebar material, and the whole app moves on one scale, in Apple's manner - layers that grow out of their control and fade away instead of popping.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.8 · 2026-09-19
- **What changed for users**: Voice samples that play without a stutter, a reading of a selection that says so only while it reads and offers the way back, and a permission card that goes the moment the grant is seen.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.7 · 2026-09-17
- **What changed for users**: The side column on the Mac's own sidebar material, glass panels, search that marks the page, and a day of small corrections to the reading page, the lists and the keys.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.6 · 2026-09-17
- **What changed for users**: A side column that folds like Codex's, headings and chapters you can hear, footnotes that stop being long-winded, and an app that calls your files what they are.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.5 · 2026-09-16
- **What changed for users**: The contents, notes and search in a book stand beside the page on glass.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.4 · 2026-09-16
- **What changed for users**: Two fixes: the voice no longer goes silent until a relaunch, and long voice names stay inside the settings panel.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.3 · 2026-09-15
- **What changed for users**: English books read by a voice on this Mac, and the choice of what to download is yours.
- **REQ-IDs shipped**: RE-VOICE-001, RE-VOICE-007 (no model required; suggest, never refuse, by language).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.2 · 2026-09-14
- **What changed for users**: Signed and notarized: the app opens like any other.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.1 · 2026-09-14
- **What changed for users**: Installs over 0.1.0; the library is carried forward on first launch.
- **REQ-IDs shipped**: not traced (REQ-IDs introduced 2026-10-10).
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.

## v0.1.0 · 2026-09-12
- **What changed for users**: The first build shared outside the author's Mac.
- **REQ-IDs shipped**: Paid-voice foundations later traced as RE-VOICE-008…013 shipped from this release; the rest not traced.
- **Channel**: GitHub release (signed and notarized from v0.1.2; in-app updater from v0.1.10).
- **Shown in**: CHANGELOG.md; GitHub release notes.
