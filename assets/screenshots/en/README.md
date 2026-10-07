# Landing screenshots

Six 1600×1025 PNGs: `shelf`, `reader` and `voices`, Vietnamese in the parent
folder and English here. Captured 2026-10-07 from the actual React app UI in
its browser-only development harness, with the opt-in showcase fixture
(`?showcase=vi|en` in `app/src/dev/mockTauri.ts`). They are not AI-generated
mockups or a user's private library; the books, covers, chapter copy and
figure are synthetic fixtures, not proof of native playback.

They tell the landing page's three-step story:

- `shelf.png`: the Library with four showcase covers (four layouts, no label).
- `reader.png`: the first book, a reading under way from the second paragraph
  of chapter 3, the floating reading status above the transport. Vietnamese
  keeps the table of contents; English hides it, because the English fixture
  translates the chapter, not the contents.
- `voices.png`: the same book, reading stopped so every voice can be
  previewed, with the voice list open: Vietnamese shows all 26 voices, English
  filters to the six English ones.

Dark theme, 1152×738 CSS px at device scale 1600/1152, so the interface reads
a little larger than life inside the page's laptop frame.

Reproduce: start the app's dev server (`pnpm exec vite --port 1420 --strictPort`
in `app/`), then `node scripts-capture-landing.mjs` from `app/`. It writes all
six files here and checks, on the way, that the reading status steps aside
while the quick voice menu is open. No native app, model download, API call or
user book is needed; the dev module is excluded from production builds.
Vite emits only the six explicit screenshots, not this document.
