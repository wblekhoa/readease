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

- `src/content.js`: VI/EN copy, alt text and FAQs.
- `src/App.jsx`: shared Header, Hero, DownloadButton, Showcase, FeatureStory,
  FAQ, Closing and Footer. React owns selection and release state.
- `src/story.js`: scoped GSAP ScrollTrigger lifecycle and navigation helpers.
- `src/release.js`: trusted GitHub asset validation and cancellable fetch.
- `site.js`: browser hydration entry, replacing the legacy DOM controller.
- `style.css`: existing approved visual design and responsive/theme tokens.
- `index.html`, `en/index.html`: localized SEO metadata and entry shells.
- `vite.config.mjs`: static rendering, icon and six explicitly allowed screenshots.
- `tests/`: behavior/SSR tests and independent built-output checks.

The Pages workflow installs the lockfile, verifies, and uploads `site/dist`.
This local update does not publish or enable Pages. Commit/push/deploy require
separate approval.

## Preserved design and product contract

- Quiet asymmetric hero, sparse bilingual description, cobalt glass CTA,
  compatibility note and small installation link beneath it.
- Full-width header/footer; 1280px main-content maximum. Existing typography,
  system light/dark theme, icon and spacing. No extra slogans or eyebrows.
- Full-width, natural-aspect previews. Separate VI/EN sets of three screenshots
  from `assets/screenshots` and `assets/screenshots/en`; no private books or generated art.
  Paste/selection figures are labeled illustrations, not fake controls.
- Vietnamese via VieNeu and English via Kokoro. Offline listening requires
  initial model setup. Optional external providers receive passages.
  Selection uses Accessibility and selected digital text, not monitoring/OCR.
- Noncommercial/source-available, not OSI open source. Native FAQ disclosures
  and language-specific installation guides remain intact.

## Interaction and motion contract

- Without JavaScript, all three previews and fallback Releases links work in
  the built HTML. Hydration enables ARIA tabs, roving focus, Left/Right and
  Up/Down wrap, Home/End. No timer autoplay.
- The stage is two columns above 960px - title and the vertical tab list on
  the left, the screen on the right (`aria-orientation="vertical"`); one
  column with a horizontal list below that. Pinned, the stage takes the
  viewport height and centres its columns; in scroll mode the screen yields
  height (`max-height: calc(100svh - 240px)`) so the stage fits and the
  story engages on laptop viewports, not only tall ones.
- GSAP/ScrollTrigger loads separately. It observes two scroll steps (70% of
  viewport each, minimum 320px); CSS owns stickiness. Scroll down advances
  Reader → Library → Voices; scrolling up reverses it. No wheel interception,
  forced snap or scroll-smoother dependency.
- Manual selection aligns scroll immediately only when the entire stage fits.
  Short/tall-content layouts and reduced motion retain manual tabs.
  Scroll never moves keyboard focus or hides a focused panel.
- Effects dispose owned triggers, listeners, pending focus frames, animation
  contexts and requests. Live reduced-motion changes cancel animation; rapid
  tab changes revert the prior animation before starting the next.
- Entrances use GSAP for 420ms directional opacity/translation. Existing CSS
  view-timeline chapter accents keep their reduced-motion overrides.
- Failed motion loading leaves manual tabs usable. Failed/invalid GitHub
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

## Local verification — 2026-09-22

28 behavior/SSR tests + 3 built-output tests. Browser: desktop forward/reverse
scroll and keyboard tabs, VI 390px / EN 320px light/reduced-motion, desktop dark.
No claim of Safari/Firefox, field-performance testing or production deployment.
Screenshots and functional checks supplement, not replace, automated tests.

Screenshot refresh: routes `/` and `/en/` now use synthetic Vietnamese and
English chapter copy for Reader and Voices, while Shelf captures remain
unchanged. See `assets/screenshots/en/README.md` in the repository for capture
provenance; locale routing and 1600×1025 dimensions are build-tested.
