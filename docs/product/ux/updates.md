---
id: readease-ux-updates
type: ux
product: readease
title: "ReadEase — Software updates (UX)"
status: active
updated: 2026-10-19
summary: "A quiet sidebar notice and dismissible update detail popover let readers prepare updates while using ReadEase and choose a safe time to restart."
tags: [area/release, stack/react, surface/macos]
relations:
  dependsOn: [readease-logic-updates]
  specifies: [readease:app/src/ui/UpdateNotice.tsx, readease:app/src/ui/UpdatePanel.tsx]
---
# ReadEase — Software updates (UX)

## Entry and layout
A single-line notice with a soft brand-tinted background sits above the sidebar settings footer on every screen. Its ready label is just “Sẵn sàng cập nhật” / “Ready to Update”; the version number belongs in details. Folded sidebar shows an accessible icon with the same status. Clicking toggles a detail popover beside the column; the menu's Check for Updates opens the same details. There is no dimming scrim, modal focus trap or automatic window activation.

## Interaction states
- Available: notice shows a new version; details offer Download and Later, notes/date and the existing automatic-download preference.
- Downloading: sidebar shows percentage/progress, or an indeterminate label if size is unknown. Details may close via Escape, close button, outside click or Continue Using ReadEase. Reading/navigation remain usable.
- Ready: notice says Ready to Update. Details place Install When Quitting and Install and Relaunch side by side in one row, with no Skip This Version action. Scheduling closes details and changes the notice to Installs When Quitting.
- Export in progress: preparing remains allowed; applying/restarting is disabled with an explanation. Completion enables the action; it does not trigger restart.
- Install/restart: explicit action applies the archive then relaunches. The details warn that restart ends reading and clears transient pasted/selection content; saved book progress is retained.
- Failure: persistent quiet notice, error detail and Try Again. No unsolicited modal. A failed restart has its own retry, without downloading/installing again.
- Keyboard: focus can leave the popover; Escape returns to its opener. Pointer outside dismisses while allowing the underlying action. Labels are in Vietnamese and English.

## Scope
Use existing Surface, Button, IconButton and palette tokens. Status survives navigation and sidebar folding within the current app session. A prepared archive is not promised to survive an app crash. No redesign to the reading surface or voice controls.
