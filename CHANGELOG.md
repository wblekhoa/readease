# Changelog

Notable changes to ReadEase — Thư Âm. Versions follow the app's own version;
each Release names the exact commit it was built from in `CFBundleVersion`
(`<version>+<git sha>`).

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
