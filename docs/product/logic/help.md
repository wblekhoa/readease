---
id: readease-logic-help
type: logic
product: readease
title: "ReadEase — Help and feedback (logic)"
status: active
updated: 2026-10-22
summary: "Feedback metadata URL and fallback, issue-submission boundary and local diagnostic-log ownership."
tags: [area/security, stack/tauri, stack/rust, surface/macos]
reqPrefix: RE-HELP
relations:
  implements: [readease:app/src/ui/feedback.ts, readease:app/src-tauri/src/log.rs]
---
# ReadEase — Help and feedback

## Purpose

Open a useful bug form without including document, library, preference or provider-key content.

## Inputs and outputs

`feedback_facts` → build id, macOS version, architecture → encoded GitHub URL. Facts failure uses the plain issue form; `+hash` and other metadata survive URL encoding.

## Rules

| REQ-ID | Rule | Status | Evidence |
|---|---|---|---|
| RE-HELP-001 | Open feedback with build/macOS/chip metadata only; fall back to a plain form if facts are unavailable. | live | [001](#evidence) |

## States and recovery

| Event | Boundary |
|---|---|
| choose Report a Problem | read facts; open prefilled or fallback URL |
| browser opens URL | metadata query already reaches GitHub |
| user reviews/submits form | creates the issue; opening alone does not |

[Privacy](../../../PRIVACY.md) owns network disclosure. Local stderr may be captured at `~/Library/Logs/ReadEase/readease.log`; on startup, >2 MiB rotates to one `.1` generation. Logs are not auto-uploaded/attached, and are not guaranteed free of user text.

## Evidence

- **001**: `app/tests/feedback.test.ts`; `app/src-tauri/src/log.rs` (`the_macos_version_is_read_out_of_the_system_plist`)

## Change log

- 2026-10-22: reviewed d2dedf4 mockTauri edits (annotations add/restyle, copy_text belong to RE-NOTE); no feedback or log change.
- 2026-10-21: audit 21/10: no rule change; App.tsx/mock edits are copy, headings and confirms reviewed against this doc.
- 2026-10-20: condensed feedback/transmission boundary; no payload change.
- 2026-10-19: corrected URL-open versus issue-submit timing and documented local logs.
- 2026-10-15: introduced prefilled feedback.
