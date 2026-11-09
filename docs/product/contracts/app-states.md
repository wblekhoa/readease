---
id: readease-contract-app-states
type: contract
product: readease
title: "ReadEase — App states registry (contract)"
status: active
updated: 2026-11-09
summary: "The JSON registry that owns ReadEase's screens, flow arrows and eight preview states; docs cite these IDs and the index checks both ways."
tags: [area/testing, area/layout, stack/react, surface/web]
artifact: app/src/dev/playgroundStates.json
stateRegistry: true
relations:
  dependsOn: [readease-logic-playground]
  implements: [app/src/dev/playgroundStates.json]
---
# ReadEase — App states registry (contract)

`app/src/dev/playgroundStates.json` is the one list of ReadEase's screens and preview states.

| Field | Meaning |
|---|---|
| `flow[].screen`, `label`, `next` | left-to-right screen order, display name, arrows |
| `states[].id` | `<screen>/<state>`; never reused |
| `states[].label` | display name, Vietnamese and English |
| `states[].query`, `steps`, `checkpoint` | how the preview reaches the state and what proves it arrived (RE-PG-003) |

Docs cite an ID in a REQ row, a UX "Screens and states" row or a flow diagram comment (`%% node A` followed by the citation).

Adding a state adds 8 preview cells. Update the `RE-PG-001` test and any consumer that fixes the cell count.

## Consumers
| Consumer | Uses | Breaks if |
|---|---|---|
| `app/src/dev/playgroundScenarios.ts`, the preview driver and mock | `states` | a state's `query`, `steps` or `checkpoint` changes meaning |
| The doc index | `flow`, `states[].id`, `label`, `checkpoint` | `id` changes form |
| The JAK Hub flow page | `flow`, `states` | a field is renamed |

## Change log
- 2026-11-09: created (RE-PG-004).
