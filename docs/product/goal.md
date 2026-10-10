---
id: readease-goal
type: goal
product: readease
title: "ReadEase — Product goal"
status: active
updated: 2026-10-10
relations:
  servesGoal: [hq:app-revenue]
---
# ReadEase — Product goal

## Problem
- People who read long Vietnamese (and English) text on a Mac - books, papers, reports, web pages - have no simple way
  to *listen* to it in a natural Vietnamese voice without uploading their documents to a cloud service. Reading on screen
  for hours is tiring; cloud text-to-speech bills per character and sends private documents away.

## Audience
- Primary: a Vietnamese-speaking reader on an Apple Silicon Mac (macOS 15+) with EPUB/PDF books and documents.
- Secondary: a bilingual reader who also listens to English; anyone who wants selected text in any app read aloud.
- Who pays: nobody today - the app is free under PolyForm Noncommercial 1.0.0. Paid voices bill the reader's own
  OpenAI/ElevenLabs account directly; ReadEase is not in that payment path.

## Promise
- ReadEase reads your EPUB, PDF and pasted text aloud in a natural voice on your Mac - and with the on-device voice,
  nothing leaves the Mac.

## Success measures
| Measure | Today | Target | How it is measured (command, dashboard, store data) |
|---|---|---|---|
| Installer downloads (`.dmg` + `.zip` assets, all versions) | 52 (GitHub API, 2026-10-10) | not set | `gh api repos/wblekhoa/readease/releases --paginate --jq '[.[].assets[] \| select(.name\|test("\\.(dmg\|zip)$")) \| .download_count] \| add'` |
| Release assets downloaded, excluding the updater feed | 72 (GitHub API, 2026-10-10) | not set | same command with `select(.name!="latest.json")`; `latest.json` hits (37) are update checks, not installs |
| Public releases shipped | 22 (v0.1.0 2026-09-12 → v0.1.21 2026-10-10) | not set | `gh release list -R wblekhoa/readease` |
| GitHub stars / forks | 0 / 0 (GitHub API, 2026-10-10) | not set | `gh api repos/wblekhoa/readease --jq '{stars:.stargazers_count,forks:.forks_count}'` |
| Active readers / retention | not measured | not set | no method: the app has no telemetry by design (`PRIVACY.md`) |
| Landing-page visits | not measured here | not set | GA4 on the landing page (`site/src/analytics.js`); figures are not copied into this repo |
| Revenue | not measured | not set | no method yet: the app is free for noncommercial use |

Download counts include the maintainer's own test downloads; read them as an upper bound.

## Non-goals
- No ReadEase account, no ReadEase server, no telemetry inside the app.
- No OCR for scanned PDFs, no DRM- or password-protected books, no fixed-layout EPUB rendering.
- No Intel Macs, Windows, Linux or iOS today.
- No audio export today: generated audio stays in the app's on-device cache for re-listening (`README.en.md`, `PRIVACY.md`).

## Links
- UX: `ux/library.md` · `ux/reading.md` · `ux/voices.md`
- Logic: `logic/library.md` · `logic/reading.md` · `logic/voices.md`
- Decisions: `decisions.md` · Releases: `releases.md`
- Public context: `README.en.md`, `PRIVACY.md`, `CHANGELOG.md` at the repo root

## Change log
- 2026-10-10: created (doc-engine pilot); measures read from the GitHub API on this date.
