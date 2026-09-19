# Changelog

Notable changes to ReadEase — Thư Âm. Versions follow the app's own version;
each Release names the exact commit it was built from in `CFBundleVersion`
(`<version>+<git sha>`).

## Unreleased

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
