import test from 'node:test';
import assert from 'node:assert/strict';
import { scenarios, matrix, previewUrl, fixtureCopy } from '../src/dev/playgroundScenarios.ts';
import registry from '../src/dev/playgroundStates.json' with { type: 'json' };

test('RE-PG-001 eight product states generate 64 unique locale/theme/viewport cells', () => {
  assert.deepEqual(scenarios.map(s => s.id), ['library/empty', 'library/ready', 'library/error', 'reader/ready', 'reader/preparing', 'reader/playing', 'reader/paused', 'reader/error']);
  const cells = matrix(); assert.equal(cells.length, 64);
  assert.equal(new Set(cells.map(c => c.id)).size, 64);
  assert.equal(new Set(cells.map(c => previewUrl(c))).size, 64);
  assert.ok(cells.every(c => c.width >= 960 && c.height >= 600));
});

test('RE-PG-004 the JSON registry owns flow order, arrows and state IDs', () => {
  assert.equal(registry.version, 1);
  const screens = registry.flow.map(f => f.screen);
  assert.deepEqual(screens, ['library', 'reader']);
  for (const f of registry.flow) for (const n of f.next) assert.ok(screens.includes(n), `unknown flow target ${n}`);
  for (const s of registry.states) assert.ok(screens.includes(s.id.split('/')[0]), `state ${s.id} is on no flow screen`);
  assert.deepEqual(scenarios.map(s => s.id), registry.states.map(s => s.id));
  assert.equal(matrix().length, 64);
});
