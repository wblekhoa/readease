---
id: readease-logic-playground
type: logic
product: readease
title: "ReadEase — Browser preview scenarios"
status: active
updated: 2026-11-09
summary: "Eight deterministic Library/Reader scenarios share one registry across preview and audit; synthetic data and native-service simulation stay out of production and native sessions."
tags: [area/testing, area/components, area/layout, stack/react, surface/web]
reqPrefix: RE-PG
relations:
  specifiedBy: [readease-ux-playground]
  dependsOn: [readease-logic-library, readease-logic-reading]
  implements: [app/src/dev/playgroundStates.json, app/src/dev/playgroundScenarios.ts, app/src/dev/playgroundDriver.ts, app/src/dev/mockTauri.ts, app/src/main.tsx, app/tests/playgroundScenarios.test.ts]
---
# Browser preview scenarios

| REQ-ID | Rule | Status | Evidence |
|---|---|---|---|
| RE-PG-001 | One registry defines Library empty/ready/error and Reader ready/preparing/playing/paused/error; VI/EN × light/dark × 960×600/1280×820 generates 64 unique stable cells and URLs. | live | `app/tests/playgroundScenarios.test.ts`; `app/src/dev/playgroundScenarios.ts`; state:library/empty state:library/ready state:library/error state:reader/ready state:reader/preparing state:reader/playing state:reader/paused state:reader/error |
| RE-PG-002 | Opt-in pilot fixtures replace reading content with short synthetic copy, clear annotations/history/figures and supply a stable two-book shelf. Preparing holds before voice events; playing holds after a real mock started/position event; the first reading error is recoverable on retry. All changes are in the browser mock, not native data. | live | `app/src/dev/mockTauri.ts`; `app/src/dev/playgroundScenarios.ts`; browser checkpoint audit; state:library/error state:reader/preparing state:reader/playing state:reader/error |
| RE-PG-003 | The dev-browser driver waits for listeners, navigates through connected product controls and reports the exact cell only after its visible checkpoint; a registry state with an unknown checkpoint or step, or without both labels, reports failed. It never runs in native Tauri or production; ordinary text click does not start playback. | live | `app/src/main.tsx`; `app/src/dev/playgroundDriver.ts`; production build/mock audit and browser checks |
| RE-PG-004 | `app/src/dev/playgroundStates.json` owns the state IDs, how each is reached, the screen order and the arrows between screens. Every arrow and state names a known screen; docs cite these IDs. | live | `app/tests/playgroundScenarios.test.ts`; [app-states contract](../contracts/app-states.md) |

The registry is source data, not a second renderer. Scenario steps use existing Library/Reader controls and service events. The native reading/library rules remain owned by their existing documents. A hold is a declared fixture checkpoint; it does not certify timing or audio delivery on macOS.

`pilot`, `locale`, `theme` and `viewport` select the fixture. Existing `empty`, `fail` and `warm` query seams continue to drive empty/error/preparation behavior. Unknown pilot IDs do not activate the new fixture or driver. A driver failure remains failed with its step; it is not counted as a rendered state.

Production uses the unchanged app entry/build pipeline; both mock and driver imports are dev gated. No user books, database, voice model or generated audio is fixture data.

## Change log
- 2026-11-09: RE-PG-003: the driver refuses a registry state it cannot run.
- 2026-11-09: RE-PG-004: registry moved to JSON with flow order and arrows; REQ rows cite state IDs.
- 2026-10-24: Added the eight-state public browser preview registry and synthetic fixture checkpoints.
