# Changelog

Notable changes to ReadEase — Thư Âm. Versions follow the app's own version;
each Release names the exact commit it was built from in `CFBundleVersion`
(`<version>+<git sha>`).

## Unreleased

- Resuming after a break of 30 seconds or more starts again from the
  beginning of the sentence the voice was in - and from the sentence
  before it when the pause fell mid-sentence - so the ear picks the
  thread back up. A short pause resumes exactly where it stopped.
- How long is left: while a document is read, the corner of the bar
  says "Chương này · còn ~52 phút" (or the hours and minutes to the end
  of the document, when that is how far the reading goes), and the ⓘ
  tooltip says it before the reading starts. The engine forecasts it
  from what it still has to say and the pace it has actually been heard
  at, so the number settles as the reading goes on.

## 0.1.12

Updates with a Mac's manners - skip this version, later, install when
quitting, automatic download if you want it - and release notes that read
as paragraphs. Installs over 0.1.11, or lets 0.1.11 install it.

- The update sheet shows the release notes as paragraphs, not as the
  CHANGELOG's wrapped lines; the manifest is written that way too.
- Updates behave the way a Mac expects of Sparkle: **Skip This
  Version**, **Later** (quiet until the next launch), **Install When
  Quitting** (downloaded now, installed as the app quits - nothing
  interrupts a reading), **Install and Relaunch**, and an optional
  **automatic download** (off unless you turn it on) that leaves the
  update ready to install. The menu item under About says what is known
  - "ReadEase 0.1.12 is available · Update…", "…is ready · Install…" -
  and the floating notice is gone. The sheet shows the release date.

## 0.1.11

The first release the app fetches by itself: a log file for bug reports,
and the bundle's own category and copyright. Installs over 0.1.10 - or
lets 0.1.10 install it (ReadEase › Kiểm tra bản mới…).

- A log file: with the app opened from Finder, what the host and the
  engine report goes to `~/Library/Logs/ReadEase/readease.log` (kept to
  one previous generation) instead of nowhere. Help › Show Log File
  reveals it, and the bug-report form asks for its last lines. The app
  writes no document names or text there.
- The bundle names its category (Education), its copyright and a short
  description, the way the Finder's Get Info and the App Store's tools
  expect.

## 0.1.10

A Mac app of its own: a menu bar with every command, documents that open
from Finder and the Dock, a window that remembers itself, a reading that
Control Center and the media keys know about, and an updater that will
bring the next release by itself. Ships as a disk image beside the zip.
Installs over 0.1.9.

- A menu bar of the app's own, in the app's language: File (Add to
  Library ⇧⌘O, From Apple Books, Close Document ⌘W), Edit (the system's
  seven, then Find in Document ⌘F), View (Show/Hide Side Column ⌥⌘S, the
  four places ⌘1-⌘4 - the document's three lists inside one - text size
  ⌘= ⌘− ⌘0, Appearance, Full Screen), Reading (Resume/Pause, Stop ⌘.,
  Read Selection, Voice Settings, Voices & Models ⌘,), Window and Help
  (guide, feedback, latest release on GitHub). Every shortcut the app
  had is now found where a Mac shows them; items disable rather than
  disappear, and the words follow the language switch.
- ReadEase opens EPUB and PDF files from the Mac: double-click a file
  and choose it under "Open With", drop one on its Dock icon, or launch
  the app with a file - it is added to the library (a file already there
  is recognised, not duplicated) and opened. The app does not take the
  place of Books or Preview as the default; that stays your choice.
- The window opens where you left it, at the size you left it.
- A reading is a Now Playing item of the Mac: Control Center and the
  menu bar's Now Playing show the document and chapter, and F8, an
  AirPod's stem and Control Center's play/pause/stop control the reading
  - even with the window behind others. It withdraws when the reading
  ends.
- **Check for Updates…** under the ReadEase menu: the app asks GitHub for
  a newer release, shows its notes, downloads and installs it, and offers
  the relaunch. It also looks once, quietly, a few seconds after launch,
  and only speaks up when there is something new. Updates are signed;
  the public key ships in the app. (This release is the first with the
  updater, so the first update it performs will be to the release after
  it.)
- Releases now ship a disk image (`.dmg`, drag to Applications) beside
  the zip, both notarized.
- Tooltips wait a beat before appearing, like the Mac's own help tags,
  and then follow the pointer along a row at once; sweeping the toolbar
  no longer flashes a name under every button.
- The voice plays through the Mac's default output, opened by name; if
  that device will not open, the app says so instead of quietly picking
  another. Voice settings now shows which output the voice goes to, and
  whether it is the system's default - the line that makes a
  Multi-Output setup diagnosable.

## 0.1.9

The side column's states become alphas of the ink on the Mac's sidebar
material, and the whole app moves on one scale, in Apple's manner - layers
that grow out of their control and fade away instead of popping. Installs
over 0.1.8.

- The side column paints its states as alphas of the ink, the way the
  Mac's own sidebar does, so its material shows through them: the open
  list's tab, the chapter you are at, the chosen search hit and the
  navigation entry on show are a light tint in the dark theme and a grey
  one in the light theme instead of opaque blocks; the tab track and the
  search box are recessed wells; the column's hairlines are alpha too;
  the chosen tab no longer carries a drop shadow and runs to the edge of
  its track. Hover stays one step under "chosen", so the open entry and a
  hovered neighbour are no longer the same colour.
- Motion, on one scale and in Apple's manner: a popover grows out of the
  control that opened it (200 ms) and shrinks back faster than it came
  (150 ms); a sheet and the dimmed window under it fade in together and
  out together; a menu appears at once and fades on the way out; tooltips,
  peeks and callouts fade in; the side column, the text-size fold and a
  page turn share one 240 ms move; a hover changes colour in 120 ms. A
  jump the reader asks for - a chapter, a search hit, a note, "Back to
  reading position" - scrolls instead of cutting. With the Mac's Reduce
  Motion on, movement goes and only the fades stay; nothing waits on a
  window that is off screen.

## 0.1.8

Voice samples that play without a stutter, a reading of a selection that
says so only while it reads and offers the way back, and a permission
card that goes the moment the grant is seen. Installs over 0.1.7.

- Read a selection: "Reading your selection…" now ends when the reading
  ends - it used to stay on the screen after the voice fell silent - and
  carries a **Back to reading position** button that opens the passage
  being read and brings the part the voice is at to the middle. The page
  follows the voice until you scroll by hand; the button starts the
  following again.
- The voice samples no longer stutter: a reading's first sound waits
  until 0.6 s of it is in the speakers (the model's first chunks arrive
  about as fast as they play, and a device that started on the first one
  ran dry between them), a short sample plays the moment it is whole,
  and the player keeps twice as much audio ahead of the ear.
- Accessibility: the permission card disappears the moment the grant is
  seen - the app asks again whenever its window comes back and every
  1.5 s while the card is up - instead of staying until you left the
  screen. No relaunch is needed.

## 0.1.7

The side column on the Mac's own sidebar material, glass panels, search
that marks the page, and a day of small corrections to the reading page,
the lists and the keys. Installs over 0.1.6.

- The side column shows the Mac's own sidebar material behind it - the
  desktop and windows behind ReadEase, blurred - dark when the app is,
  and stays paper-solid nowhere else.
- "Đang đọc" in the column: each document carries its cover with a
  progress strip, two lines of its name and "42% · Chương 3", in two
  ranks; the group's label is set in small caps.
- Panels over the page (voice settings, reading settings, the cost panel,
  menus, the chapter tooltip) are glass: the page shows through, blurred.
  A sheet in the middle of the window (Voices & models, the Apple Books
  list) stands on a strongly blurred, dimmed window and is centred on the
  window rather than on the page.
- Search marks its matches on the page while the Tìm tab holds a query,
  the hit just chosen stronger; the search box is the taller one with
  the lens inside.
- Keys: ⌥⌘S folds and unfolds the column (was ⌃⌘S - the ⌃⌘ layer is the
  system's); ⌘1-⌘4 go to the four screens, and inside a document to
  Contents, Notes and Search; ⌘F puts the cursor in the search and keeps
  it there.
- The window's buttons, the column's switch and the toolbar sit on one
  line, 16 px of air after the zoom button; the toolbar row is 4 px
  higher. The line under the paragraph being read is a step darker; the
  hairline darkens while the pointer is on the column's resize grip; the
  delete control in the notes list is a button-sized chip; a chapter's
  name over its notes is written as its author wrote it; menus are as
  round as their rows; hints that say something are no longer faint.

## 0.1.6

A side column that folds like Codex's, headings and chapters you can hear,
footnotes that stop being long-winded, and an app that calls your files
what they are. Installs over 0.1.5.

- ReadEase describes itself as what it is: a reader of your EPUB and PDF
  files. Every sentence the app shows - in both languages, from the shell
  and from the engine - now says document, file or copy where it used to
  say book; the sample shelf in the developer preview names invented
  documents rather than real titles. Apple Books keeps its name, being
  a product, and the feature that moves notes between two copies of the
  same document is unchanged.
- A side column, the way Codex has one: a real column of the layout on the
  left, from the window's own buttons down, with the content beside it -
  not a layer over the page. It carries the navigation (Library, Paste,
  Read a selection, Move notes) and the documents being read; inside a
  document it turns into its contents, notes and search, which were
  floating sidebars in 0.1.5 and are tabs of the column now. Fold and unfold it with
  the switch at its top or ⌃⌘S; it remembers your choice, folds itself
  when the window is narrower than 1100 px until you say otherwise, and
  opens on the right tab when you ask for a list (▤, the notes button, ⌘F).
  The appearance switch, the language and Voices & models live at its
  foot, and move to the toolbar while it is folded.
- The app opens on the Library. An empty shelf still offers the paste
  screen with one button.
- A heading sounds like one: read 8 % slower and 2 dB louder than the
  paragraphs around it, with a longer breath before (1.0 s) and after
  (0.85 s). The text on the page does not change.
- A short chime opens each chapter after the first - marimba by default,
  harp or piano instead, or off - under Voice settings › Chapter chime.
  The chime is a sound the app carries, never fetched and never billed to
  an API voice.
- Footnotes are read short by default: a bibliographic note ("Sđd., tr.
  45", "Trần, Nhịp của thị trường, 2019") is not read at all, a remark
  keeps its first two sentences, and an in-text citation - "(Trần,
  2019)", "[12]" - is skipped. Voice settings › Footnotes switches to
  reading them whole, or to none. The cost estimate under a paid voice
  counts what is actually read.

## 0.1.5

The contents, notes and search in a book stand beside the page on glass.
Installs over 0.1.4.

- The contents, the notes and the search in a book are sidebars now: one
  layer each, the whole height between the two bars, on glass the page shows
  through - where each was a card capped to a fraction of the window (at a
  600 px window the contents showed fourteen rows). Contents and notes on
  the left, search on the right; Escape, a click outside or the close button
  leaves; the button that opened one closes it again.

## 0.1.4

Two fixes: the voice no longer goes silent until a relaunch, and long voice
names stay inside the settings panel. Installs over 0.1.3.

- The voice no longer goes silent until a relaunch after a model download
  or two quick presses. A reading asked for while a model was downloading
  (or while another reading ran) and then stopped - Dừng, or Đọc pressed
  again - used to start anyway, after the download, for a player that had
  already let it go; the engine then waited for room that never came, with
  every later reading queued behind it. A stop now covers every reading
  asked for before it, queued or playing. Cancelling a download is its own
  action: Dừng stops the voice and leaves the download running.
- The voice settings panel no longer grows scrollbars when the chosen
  voice has a long name. The name is clipped inside its control, with an
  ellipsis; the panel scrolls down when the window is shorter than it, and
  never sideways.

## 0.1.3

English books read by a voice on this Mac, and the choice of what to
download is yours. Installs over 0.1.2.

- A second local model, for English: Kokoro-82M (Apache-2.0), six American
  voices, no API key and no network once downloaded. One model per
  language, each optional: the first-run screen and **Voices & models**
  (the gear on the home screen) show what this Mac can read, with which
  model or key, and let either model be fetched or removed - nobody is made
  to download any one of them, and the library opens either way. A model's
  voices are listed only while it is on the Mac.
- No voice is refused for the language it is handed any more. The voice
  settings ask which language you read in first, then show that language's
  voices and models; switching the language brings back the voice you last
  used for it. When the text in front of you is in the other language, the
  panel and the footer chip carry a suggestion - one sentence, one button -
  and nothing changes until you press it.
- Pronunciation comes from the same lexicon the model was trained with
  (misaki, ported without torch), a part-of-speech tagger for the words
  that change with their role (*read*, *lead*, *used to*), and a small
  network for names and terms the lexicon lacks, so nothing is skipped.
  Numbers, years, ordinals, decimals and prices are read as words.
- The voice last used for Vietnamese and the one last used for English are
  remembered separately, so moving between languages does not mean picking
  a voice again.
- Cancelling a model download is reported as a cancellation, not as a
  network failure; what had landed whole stays for the next attempt, and
  the model's row says so, with a way to resume and a way to remove it.
- The frozen engine grows by about 45 MB (spaCy and its small English
  pipeline); the app bundle grows accordingly.
- Only the model of the voice you use is loaded when the app starts; the
  other one loads the moment you choose a voice of it. With both models on
  the Mac, the engine sits at about 1.1 GB for a Vietnamese reader and
  0.6 GB for an English one, instead of 1.7 GB for both. The first sentence
  after switching models may wait up to about three seconds, once - less
  when the play button comes a few seconds after the choice.
- An EPUB whose chapters open with a document type declaration - the plain
  `<!DOCTYPE html>` of every EPUB 3 chapter, or the XHTML public doctype
  of an EPUB 2 one - imports again. The importer refused every doctype as
  "unsafe XML declarations", where only a doctype with an internal subset
  (the one place a chapter can declare entities) is; that one is still
  refused, before anything inside it is read.

## 0.1.2

Signed and notarized: the app opens like any other. Installs over 0.1.1.

- Releases are signed with an Apple Developer ID certificate (hardened
  runtime, trusted timestamp on every binary) and notarized by Apple, and
  the build refuses to package anything Gatekeeper would not accept. No
  more right-click → Open; upgrading from 0.1.1 asks for the Accessibility
  permission once more, then it survives updates.
- Import by dropping PDF or EPUB files from Finder onto the window: the
  whole window becomes the target, says how many books are in hand, and
  turns red when nothing dragged is a book. The open panel takes several
  files at once. A dropped batch reports what was added, what was already
  there, and what failed.
- Books are imported by path: the file no longer travels through the
  interface (a 46 MB EPUB froze it for about a second), and the engine's
  200 MiB limit is reachable.
- The window opens in about a tenth of a second instead of three: the
  voice list no longer loads the model, the model warms in the background,
  and paid-voice catalogues are fetched off the request path and cached.
- Two glyphs from the design system's AI set: the voice-settings button
  and the read button.

## 0.1.1

Installs over 0.1.0; the library is carried forward on first launch.

- A book removed from the library no longer takes the reader's decisions
  about its highlights with it: a highlight deleted for good stays deleted
  and a rewritten note keeps the reader's words when the same file is
  imported again and notes are synced. This is the library's first schema
  migration (v1 → v2); it runs once, in a single transaction, and a library
  upgraded this way is not opened by 0.1.0 again.
- A book whose stored data the app can no longer decode stays on the shelf,
  marked, instead of taking the whole library down with it. It cannot be
  opened; it can be removed, or healed by importing the original file again.
- Every error the app can show names the next step; voice regions read as
  places in the interface language; a book's language can no longer be
  forced to English when its own words are Vietnamese.
- Public repository: security audit over every tracked file, macOS floor
  gated at build time, screenshots in the READMEs, a render audit any
  contributor can run. Two modules nothing shipped were retired.

## 0.1.0 — first public release

The first build shared outside the author's Mac.

- Reads text-based PDFs, reflowable EPUBs and pasted text aloud in Vietnamese
  with VieNeu-TTS running on the Mac. No account, no key, no server; reading
  works offline once the voice is prepared.
- Library with reading progress, chapters, highlights and notes; figures in
  EPUBs announced in reading order; pauses that follow the text's structure.
- Read a selection from any app with a global shortcut (needs Accessibility);
  pick up notes and highlights from Apple Books.
- Optional paid AI voices (OpenAI, ElevenLabs) on the reader's own key, with
  the price shown in the read button before pressing it and a spending
  ceiling the reader sets. Off by default; nothing leaves the Mac otherwise.
- Bilingual interface (Vietnamese, English). A book's language is read off its
  own text; a reader may say a scanned book is Vietnamese when the scan lost
  its diacritics.
- macOS bundle: Tauri shell with the Python engine frozen as a sidecar, Apple
  Silicon, macOS 15+, ad-hoc signed (one Control-click → Open on first
  launch). Licence payload generated from what the bundle contains.
- Licence: PolyForm Noncommercial 1.0.0 - free for personal and other
  noncommercial use; the source is public so anyone can verify the privacy
  claims.
