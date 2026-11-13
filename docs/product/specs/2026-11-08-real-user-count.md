---
id: readease-spec-2026-11-08-real-user-count
type: spec
product: readease
title: "ReadEase — Counting real users without telemetry"
status: draft
updated: 2026-11-08
summary: "How to tell how many people really use ReadEase while keeping the no-telemetry promise: read the updater-feed hits that already exist, then four options that differ in privacy cost, for the owner to choose."
tags: [area/reading, surface/macos]
relations:
  derivedFrom: [readease-goal, readease-logic-updates]
  changes: []
---

# ReadEase — Counting real users (draft)

## Why now
- The owner's app-revenue goal waits until the app has users. Today nobody can say whether ReadEase has users:
  the goal table shows downloads only, and "Active readers / retention" is "not measured" (`goal.md`).
- Downloads overcount (owner test installs) and say nothing about who keeps using the app.
- Asked by the maintainer's planning campaign of 2026-11-08. Nothing ships from this
  draft: any change to what leaves the Mac needs the owner's yes and a `PRIVACY.md` update in the same release.

## A signal that already exists (no code change)
The app checks `https://github.com/wblekhoa/readease/releases/latest/download/latest.json` about five seconds after each
start (`app/src-tauri/tauri.conf.json` `plugins.updater.endpoints`; RE-UPDATE-001). The `/latest/` URL redirects to the
newest release, so GitHub counts every check on that release's `latest.json` asset while it is the newest.

| Release | Newest from | `latest.json` hits | Installers (`.dmg` + `.zip`) |
|---|---|---|---|
| v0.1.27 | 2026-11-04 | 10 | 6 |
| v0.1.26 | 2026-10-23 | 14 | 9 |
| v0.1.22 | 2026-10-15 | 14 | 8 |
| v0.1.19 | 2026-09-26 | 13 | 9 |

Read on 2026-11-08 with:
`gh api repos/wblekhoa/readease/releases --paginate --jq '.[] | [.tag_name, ([.assets[]|select(.name=="latest.json")|.download_count]|add // 0)] | @tsv'`

What it means: **app starts per period, all installs together** (about 10 starts in 4 days for v0.1.27). It cannot tell
one person starting 10 times from 10 people, and it includes the owner's own Mac. It is an upper bound on activity and a
trend line, not a user count.

## Options for the owner (choose one or combine)
| # | Option | What leaves the Mac | Effort | Accuracy | Risk |
|---|---|---|---|---|---|
| A | **Track the feed hits weekly** (recommended): a script stores `latest.json` hits per release with dates; "starts per week" goes into `goal.md` and the maintainer's scoreboard | nothing new | small (script + scoreboard row) | trend only; owner Mac inside | none; keeps the promise word for word |
| B | Ask readers: a one-question link in Help ("How often do you use ReadEase each week?") to a form | only what a reader chooses to send | small | few answers; real people | needs a form host (cost/privacy choice) |
| C | Opt-in anonymous ping: off by default; when on, one request per day with app version only, no ID | version + IP to the endpoint | medium (endpoint + toggle + `PRIVACY.md`) | counts opted-in starts | breaks the "no telemetry" non-goal unless the owner rewrites it; needs a server (Cloudflare) |
| D | Distribution store (Mac App Store / Setapp) gives install and active-device numbers | handled by the store | large (sandboxing, review, fees) | good | money and review; sandbox may block local model servers |

Not proposed: any always-on telemetry or per-install ID — it contradicts `goal.md` Non-goals and `PRIVACY.md`.

## Questions for the owner
1. Keep "no telemetry inside the app" as an absolute rule? (yes → only A and B are allowed)
2. Is "starts per week from the feed, owner Mac included" good enough to say the app has users, and what number counts
   (for example ≥ 20 starts/week for 4 weeks)?
3. If B: where should answers go (GitHub Discussions, Google Form, Tally)? Each sends data to a third party.
4. Should the same method apply to SpeakEase, Spotkey and AutoType (they have their own updater feeds)?

## If A is chosen (build notes, not started)
- Script stores a dated snapshot outside this repo (no counts committed) and prints starts in the last 7 days as the
  difference between two snapshots of the newest release's `latest.json` count (a new release resets the base).
- Maintainer scoreboard row `readease-starts-7d` (`kind: leading`, UNKNOWN when the snapshot is older than 26 h).
- `goal.md` Success measures gets a row "App starts per week (updater feed)" with this method and its limits.

## Change log
- 2026-11-08: created as draft by the maintainer's 2026-11-08 planning campaign; feed counts read from the GitHub API on this date.
