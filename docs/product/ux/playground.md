---
id: readease-ux-playground
type: ux
product: readease
title: "ReadEase — Browser preview"
status: active
updated: 2026-11-09
summary: "Browser previews expose Library and Reader states with synthetic content in Vietnamese/English, light/dark and the two desktop sizes, preserving real product interaction."
tags: [area/testing, area/layout, area/reading, surface/web]
figma: []
relations:
  partOf: [readease-goal]
  dependsOn: [readease-ux-library, readease-ux-reading]
  implements: [app/src/dev/playgroundScenarios.ts, app/src/dev/playgroundDriver.ts]
---
# Browser preview

The preview follows Library → open a synthetic book → Reader. Its native bridge is simulated and it produces no real audio. Supported checkpoints cover an empty shelf, populated shelf, library failure, idle Reader, voice preparation, playback, pause and a recoverable read failure.

Each state can be inspected in VI/EN and light/dark at 960×600 or 1280×820. Content and chapters agree with the small synthetic fixture. The product's real controls still pause, resume, stop and return to the library. Clicking ordinary text does not start reading.

This is a browser development surface. Production and native sessions use their existing paths; no local library content or saved native settings are used by the fixture. A scenario that cannot reach its checkpoint reports failure rather than presenting a replacement mockup.

State IDs come from the registry in `app/src/dev/playgroundStates.json` ([contract](../contracts/app-states.md)), RE-PG-004.
