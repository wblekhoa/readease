# English landing screenshots

Captured 2026-09-22 from the actual React app UI in its existing browser-only
development harness, at `http://127.0.0.1:1420/?showcase=en`. These are not
AI-generated mockups or screenshots of a user's private library. The book,
cover and figure content are synthetic fixtures, not proof of native playback.

- `shelf.png`: Library, English interface and English sample titles.
- `reader.png`: first sample book, chapter 3, contents hidden, dark theme,
  text size level 6/8, pages layout, Heart at 1.25×.
- `voices.png`: same reader, Voice settings → Manage voices → English filter.
- All three are 1600×1025 PNG viewport captures. No text painted over an image.

Reproduce with `npm run dev --prefix app -- --host 127.0.0.1`, open the URL
above, then operate the normal UI. The opt-in `showcase=en` fixture lives in
`app/src/dev/mockTauri.ts`; default fixtures and production app are unchanged.
The dev module is removed from production builds by the existing DEV gate.
No native app installation, model download, API call or user book is needed.

Landing `/en/` uses this set for Reader/Library/Voices and the library story;
the English Open Graph image also points here. Vietnamese assets remain in
the parent folder. Reader and Voices in both locales now include the authored
three-perspective illustration from `app/src/dev/showcaseFigure.ts`, recaptured
2026-09-22. The Vietnamese capture uses `?showcase=vi`, text size 6/8 and the
Phạm Tuyên voice; English uses Heart. The same fixture owns polished chapter
copy for both locales, while default stress fixtures remain unchanged. Shelf
captures are unchanged.
Vite emits only the six explicit screenshots,
not this provenance document or other files under assets.
