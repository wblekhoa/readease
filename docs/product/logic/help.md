---
id: readease-logic-help
type: logic
product: readease
title: "ReadEase — Help and feedback (logic)"
status: active
updated: 2026-10-15
reqPrefix: RE-HELP
relations:
  implements: [readease:app/src/ui/feedback.ts, readease:app/src-tauri/src/log.rs]
---
# ReadEase — Help and feedback (logic)

## Purpose
- Let a reader report a problem without first hunting for the facts a report needs, and without anything from
  their documents leaving the Mac.
- Success signal: bug reports arrive with a build id and a macOS version filled in.

## Rules

| REQ-ID | Rule (behaviour-changing) | Status (live / not built / blocked) | Evidence (code path or test) |
|---|---|---|---|
| RE-HELP-001 | "Report a Problem or Suggest…" opens GitHub's bug form with only the build id, the macOS version and the chip family in the address; if those cannot be read, the plain form opens instead of nothing. | live | `app/tests/feedback.test.ts`; `app/src-tauri/src/log.rs` (`the_macos_version_is_read_out_of_the_system_plist`) |

## States and transitions
| State | Trigger | Next state | Edge case |
|---|---|---|---|
| Menu item chosen | facts read | browser opens the prefilled form | the facts call fails → the plain form |

## Fixed vs flexible
- Fixed (logic the UI must not change): nothing from a document, the library or a setting goes into the address;
  nothing is sent until the reader submits the form on GitHub.
- Flexible (UI may explore): the menu wording, adding a separate form for ideas.

## Change log
- 2026-10-15: created with RE-HELP-001 (prefilled bug form).
