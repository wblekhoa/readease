import test from 'node:test';
import assert from 'node:assert/strict';
import { scenarios, matrix, previewUrl, fixtureCopy } from '../src/dev/playgroundScenarios.ts';

test('RE-PG-001 eight product states generate 64 unique locale/theme/viewport cells', () => {
  assert.deepEqual(scenarios.map(s => s.id), ['library/empty', 'library/ready', 'library/error', 'reader/ready', 'reader/preparing', 'reader/playing', 'reader/paused', 'reader/error']);
  const cells = matrix(); assert.equal(cells.length, 64);
  assert.equal(new Set(cells.map(c => c.id)).size, 64);
  assert.equal(new Set(cells.map(c => previewUrl(c))).size, 64);
  assert.ok(cells.every(c => c.width >= 960 && c.height >= 600));
});
