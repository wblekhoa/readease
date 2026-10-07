# ReadEase landing page

React + Vite. Vietnamese at `/`, English at `/en/`. Both entries are
prerendered at build time and hydrated in the browser. No server runtime,
tracking or storage. The macOS application is unchanged.

## Develop and verify

Requires Node.js 22.12+ and npm. From the repository root:

```sh
npm ci --prefix site
npm run dev --prefix site
```

Development uses http://127.0.0.1:4173/ with a strict port. Stop an existing
preview before starting another. For a production-build preview:

```sh
npm run verify --prefix site
python3 scripts/preview-site.py
```

The Python helper now serves `site/dist`, not source files; rebuild after
edits. Alternatively use `npm run preview --prefix site`.

`verify` runs behavior/SSR tests, builds both entries, then checks the actual
output for matching locales, prerendered content, portable URLs and notices.
Additional checks: `git diff --check`, `npm audit --prefix site`, and
`python3 scripts/audit-public-release.py --strict`. The last audits tracked
files only; it does not cover untracked changes or certify deployment.

## Owners

- `src/content.js`: VI/EN copy, alt text and FAQs. Every claim is one the
  repository README makes about the app.
- `src/App.jsx`: Header (floating pill), Hero, Laptop, Showcase, Ticker, Ways
  (card scroller), Craft, Voices, More, Privacy, FAQ, Closing and Footer. React
  owns selection and release state; GSAP loads once, on demand.
- `src/story.js`: scoped GSAP ScrollTrigger lifecycle and navigation helpers.
- `src/release.js`: trusted GitHub asset validation and cancellable fetch.
- `site.js`: browser hydration entry.
- `style.css`: the visual design, responsive rules and light/dark tokens.
- `index.html`, `en/index.html`: localized SEO metadata, entry shells and the
  one-line script that marks `<html class="js">` before first paint.
- `vite.config.mjs`: static rendering, icon and six explicitly allowed screenshots.
- `tests/`: behavior/SSR tests and independent built-output checks.

The Pages workflow installs the lockfile, verifies, and uploads `site/dist`
on every push to `main` that touches `site/**`: a push to main IS a deploy.

## Design contract (layout rebuilt 07/10/2026, after tryonenotch.com/vi)

The owner asked for this layout on 07/10. Structure follows the reference;
assets and copy are ReadEase's own. Do not move it back to the 22/09 design.

- A floating glass pill nav, sticky at the top: brand, four section links
  (hidden under 960px), a GitHub link (icon only on phones), language switch
  and a dark Download pill. The repository is never only in the footer.
- A centred hero: product chip, two-line headline, one-sentence description,
  one dark download button and a Free · macOS 15+ · Apple Silicon line. No
  install link: installing is one drag (owner, 07/10); the guide is in the FAQ
  and the footer.
- A MacBook drawn in CSS (bezel, notch, screen, hinge) holding the three real
  screenshots as a three-step story (owner, 07/10): Library → Reader → Voices,
  open a document, read it, change the voice. Its width is bound to the viewport
  height so the pinned stage always fits. Numbered tabs sit under it.
- A band of the big features only (owner, 07/10: pauses, chimes, figures and
  Markdown are one entry, "natural reading") that drifts with the scroll, then sections in this
  order: card scroller (library, paste, selection, EPUB figures), craft (pauses,
  chapter chimes, Markdown), voices (VieNeu, Kokoro), a 6-item grid, free and
  private (stands where a pricing table would), FAQ, closing, column footer.
- Few words (owner, 07/10): headings and visuals carry each section; no
  supporting paragraphs under headings or cards, grid items are titles only.
- Dark ink CTA, cobalt accent, DS blue ramp, Be Vietnam Pro / Plus Jakarta Sans,
  system light/dark. Diagrams and glyphs are CSS/SVG; no generated art, no
  private books, no reference-site assets.
- Vietnamese via VieNeu and English via Kokoro. Offline listening requires
  initial model setup. Optional external providers receive passages.
  Selection uses Accessibility and selected digital text, not monitoring/OCR.
- Noncommercial/source-available, not OSI open source. Native FAQ disclosures
  and language-specific installation guides remain intact.

## Interaction and motion contract

- Without JavaScript the three previews stack inside the laptop with their
  captions, the card scroller scrolls natively and fallback Releases links work.
  Hydration enables ARIA tabs (roving focus, arrows wrap, Home/End), the card
  arrows and dots. No timer autoplay and no `infinite` animation.
- `.js` (set before paint) layers the screens in one grid cell and cross-fades
  the one marked `data-on`; captions become a shared line under the laptop.
- The showcase pins only at 720px+ wide and 600px+ tall with motion allowed;
  GSAP observes two scroll steps (70% of viewport each, minimum 320px) and CSS
  owns stickiness. Scroll down advances Library → Reader → Voices; up reverses.
  Elsewhere the tabs alone switch the screen.
- The hero reads its second line once on load, CSS only: the app's reading
  highlight passes word by word behind always-visible words, and the chip's
  level meter moves for those few beats then rests still. A dotted-paper aura
  (the DMG's) and a brand glow under the laptop set the light.
- The feature band translates with the scroll (scrub), never loops; with
  reduced motion or no JS its words wrap, centred, and the duplicate set used
  for the drift is hidden.
- Effects dispose owned triggers, listeners, frames and animation contexts.
  Failed motion loading leaves manual tabs usable. Failed/invalid GitHub
  responses preserve fallback links. Only HTTPS ARM64 assets under this
  repository's release-download path can replace the fallback.

## Dependencies and storage

Runtime: React/React DOM 19.3.0 and GSAP 3.15.0. Build tools: Vite 8.3.0,
tsx 4.23.15. Versions/integrity are pinned in `package-lock.json`.
No private DOL packages or skill documents are copied. DOL's React/GSAP
guidance informed lifecycle cleanup and accessibility, not visual identity.

React is MIT. GSAP uses its own [Standard No Charge License](https://gsap.com/standard-license/),
not MIT. The build emits installed notices in `THIRD_PARTY_LICENSES.txt`;
ReadEase's noncommercial license does not relicense dependencies.

Generated directories: `site/node_modules` (~57 MB locally, including dev cache) and `site/dist`
(~2 MB including both screenshot sets), both ignored. No model downloads. Initial app JS is
~76 KB gzip; separate GSAP/ScrollTrigger chunks total ~45 KB gzip. This is
larger than vanilla HTML, traded for shared components and explicit lifecycle.
Prerendering preserves first content.

## Local verification — 2026-10-07

28 behavior/SSR tests + 3 built-output tests; public-release audit PASS.
Browser (Chromium): 1440×900 light and dark through every section, the pinned
showcase forward through Reader and Library, 390×844 with no horizontal
overflow. No claim of Safari/Firefox or a physical iPhone. The screenshots are
still the 22/09 captures.

## Local verification — 2026-09-22

28 behavior/SSR tests + 3 built-output tests. Browser: desktop forward/reverse
scroll and keyboard tabs, VI 390px / EN 320px light/reduced-motion, desktop dark.
No claim of Safari/Firefox, field-performance testing or production deployment.
Screenshots and functional checks supplement, not replace, automated tests.

Screenshot refresh: routes `/` and `/en/` now use synthetic Vietnamese and
English chapter copy for Reader and Voices, while Shelf captures remain
unchanged. See `assets/screenshots/en/README.md` in the repository for capture
provenance; locale routing and 1600×1025 dimensions are build-tested.
