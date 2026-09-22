import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const dist = resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
for (const route of ['index.html', 'en/index.html']) test(`built ${route}: prerendered HTML and portable URLs`, () => {
  const html = readFileSync(resolve(dist, route), 'utf8');
  assert.doesNotMatch(html, /<!--app-html-->|\/src\/|src="\/site.js"/);
  assert.match(html, /<h1 /); assert.match(html, /role="tablist"[^>]*hidden/);
  assert.ok(html.includes(route.startsWith('en/') ? 'Let words' : 'Để chữ'));
  const imageBase = route.startsWith('en/') ? '../screenshots/en/' : 'screenshots/';
  for (const id of ['reader', 'shelf', 'voices']) {
    assert.ok(html.includes(`src="${imageBase}${id}.png"`));
    const png = readFileSync(resolve(dirname(resolve(dist, route)), `${imageBase}${id}.png`));
    assert.equal(png.readUInt32BE(16), 1600);
    assert.equal(png.readUInt32BE(20), 1025);
  }
  assert.equal((html.match(/class="preview"/g) || []).length, 3);
  assert.doesNotMatch(html, /<figure[^>]*hidden/);
  const assets = [...html.matchAll(/(?:src|href)="([^"#]+)"/g)].map(m => m[1]).filter(p => !/^https?:/.test(p));
  for (const asset of assets) {
    assert.ok(!asset.startsWith('/'), `absolute URL breaks project-prefix hosting: ${asset}`);
    const target = resolve(dirname(resolve(dist, route)), asset);
    assert.ok(target === dist || target.startsWith(`${dist}/`), `asset outside site: ${asset}`);
    assert.ok(existsSync(target), `missing built asset or route: ${asset}`);
  }
});
test('deployed runtime carries third-party notices', () => {
  const notices = readFileSync(resolve(dist, 'THIRD_PARTY_LICENSES.txt'), 'utf8');
  assert.match(notices, /MIT License/); assert.match(notices, /GreenSock/); assert.match(notices, /gsap.com\/standard-license/);
});
