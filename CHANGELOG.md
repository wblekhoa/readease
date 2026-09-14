# Changelog

Notable changes to ReadEase — Thư Âm. Versions follow the app's own version;
each Release names the exact commit it was built from in `CFBundleVersion`
(`<version>+<git sha>`).

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
