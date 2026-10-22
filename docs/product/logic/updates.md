---
id: readease-logic-updates
type: logic
product: readease
title: "ReadEase — Software updates (logic)"
status: active
updated: 2026-10-22
summary: "Prepare signed updates in the background and apply only on explicit restart or an armed quit, with export guards, retry and duplicate-operation protection."
tags: [area/release, stack/tauri, surface/macos]
reqPrefix: RE-UPDATE
relations:
  specifiedBy: [readease-ux-updates]
  implements: [readease:app/src/ui/updateFlow.ts, readease:app/src/ui/updates.ts, readease:app/src-tauri/src/lib.rs]
---
# ReadEase — Software updates

## Purpose

Separate background preparation from installation/exit. One app-wide `UpdateFlow` serves sidebar, menu and non-modal details; closing details changes visibility, not the job.

## Inputs and outputs

- Signed feed/archive → available, progress, ready or recoverable error. The session owns the archive; relaunch rechecks without promising download resume.
- Explicit Install and Relaunch / armed Install when quitting → guarded installation, then relaunch / exit. No reading-content snapshot.
- [UX](../ux/updates.md) owns the one-line, version-free sidebar notice and detail presentation. Tauri verifies the configured updater key; Apple Developer ID/notarization remain separate release checks.

## Rules

| REQ-ID | Rule | Status | Evidence |
|---|---|---|---|
| RE-UPDATE-001 | Prepare updates without blocking app use; apply only at an explicit safe boundary, with export guards, retry and duplicate-operation protection. | live | [001](#evidence) |

## States and recovery

| Phase / event | Result / guard |
|---|---|
| idle → manual or quiet check | checking; coalesce duplicate checks |
| check returns | available / current / failed-check / idle for legacy skipped version |
| available → Download | one shared download promise; counted or indeterminate progress |
| download succeeds | ready; no install or deferred surprise restart |
| ready → Install when quitting | download if needed, native arm acknowledgement; keep using app |
| ready → Install and Relaunch | require prepared archive; guard → disarm → guard → install → guard before relaunch |
| install succeeds | installed; explicit relaunch attempt |
| relaunch fails | retain installed state/error; retry relaunch only |
| armed native close/quit | recheck export guard, apply; exit on success without relaunch |
| failed check/download/install/schedule | retry that step; retain accepted/prepared archive where applicable |
| failed quit install | acknowledged disarm invalidates timeout generation and keeps app open |

Apply and schedule are serialized; repeated clicks cannot double-install/relaunch. Export beginning during a guard await prevents apply and requires explicit retry. The native [export exit contract](export.md#states-and-recovery) takes precedence; `exit_now` also refuses exit during export. Explicit restart ends ordinary reading/translation sessions.

A current armed/busy quit generation has a 60-second fallback if the webview hangs. Disarmed/superseded timeouts cannot exit a newer generation; timeout is not an installation-success receipt.

## Preferences and limits

- Quiet check runs about five seconds after native-host startup. Opt-in `readease.update.auto` may download and arm quit installation after that check, never auto-relaunch.
- Auto toggle persists policy only: it does not itself check, cancel a transfer or disarm the current scheduled update.
- Skip UI was removed; legacy `readease.update.skipped`/controller compatibility remains. Quiet checks honor it, manual checks omit it.
- Downloading permits navigation, speech, translation and export. Prepared update/current text are session state; [app data lifetime](../systems/app/system.md#data-lifetime) applies at restart.

## Evidence

- **001**: `app/tests/updateFlow.test.ts`; `app/src-tauri/src/lib.rs` (`cancelled_or_superseded_quit_cannot_trigger_an_old_timeout`)

Mock download/install checks do not establish signed old-to-new replacement. That real upgrade and owner acceptance remain pending; this flow is unreleased in [releases](../releases.md).

## Change log

- 2026-10-22: audit 22/10: no rule change; the render audit gained Reader highlight steps (`select-words`, `reader_highlight*`), none touch the update flow.
- 2026-10-21: audit 21/10: no rule change; the restart warning no longer says scans and pastes are lost; render audit reads the folded update notice by its accessible name.
- 2026-10-20: condensed phases/recovery and linked the export exit owner; behavior unchanged.
- 2026-10-19: implemented/documented unreleased background preparation and explicit apply.
