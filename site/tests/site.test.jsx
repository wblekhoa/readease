import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import React from 'react';
import { renderToString } from 'react-dom/server';
import { App } from '../src/App.jsx';
import { content } from '../src/content.js';
import { resolveRelease, fetchRelease, fallback } from '../src/release.js';
import { createStory, keyboardIndex, progressIndex } from '../src/story.js';

const asset = (extension, overrides = {}) => ({ name: `ReadEase-1.2.3-arm64.${extension}`, size: 132000000,
  browser_download_url: `https://github.com/wblekhoa/readease/releases/download/v1.2.3/ReadEase-arm64.${extension}`, ...overrides });
const release = overrides => ({ tag_name: 'v1.2.3', assets: [asset('dmg'), asset('zip')], ...overrides });
test('trusted stable ARM64 release and optional archive', () => {
  assert.equal(resolveRelease(release()).version, '1.2.3');
  assert.equal(resolveRelease(release()).zip.size, 132000000);
  assert.equal(resolveRelease(release({ assets: [asset('dmg')] })).zip, undefined);
});
for (const [label, value] of Object.entries({ absent: null, draft: release({ draft: true }), prerelease: release({ prerelease: true }), noVersion: release({ tag_name: '' }), malformedVersion: release({ tag_name: {} }), noAssets: release({ assets: null }), noDmg: release({ assets: [asset('zip')] }) })) {
  test(`release fallback: ${label}`, () => assert.equal(resolveRelease(value), null));
}
for (const [label, patch] of Object.entries({ foreign: { browser_download_url: 'https://evil.example/a.dmg' }, wrongRepo: { browser_download_url: 'https://github.com/elsewhere/app/releases/download/a.dmg' }, http: { browser_download_url: 'http://github.com/wblekhoa/readease/releases/download/a.dmg' }, credentials: { browser_download_url: 'https://user:pass!@github.com/wblekhoa/readease/releases/download/a.dmg' }, badName: { name: 'intel.dmg' }, badSize: { size: -1 }, infiniteSize: { size: Infinity }, badUrl: { browser_download_url: 'broken' } })) {
  test(`reject unsafe asset: ${label}`, () => assert.equal(resolveRelease(release({ assets: [asset('dmg', patch)] })), null));
}
test('network/HTTP/JSON failure preserves fallback', async () => {
  for (const request of [async () => { throw Error('offline'); }, async () => ({ ok: false }), async () => ({ ok: true, json: async () => { throw Error('invalid'); } })]) assert.equal(await fetchRelease(undefined, request), null);
});
test('request has abort signal and validates successful response', async () => {
  const controller = new AbortController();
  const result = await fetchRelease(controller.signal, async (url, options) => {
    assert.equal(options.signal, controller.signal);
    assert.match(url, /^https:\/\/api.github.com\/repos\/wblekhoa\/readease/);
    return { ok: true, json: async () => release() };
  });
  assert.equal(result.version, '1.2.3');
});
test('keyboard wraps, Home/End jump, other keys do not intercept', () => {
  assert.equal(keyboardIndex('ArrowLeft', 0), 2);
  assert.equal(keyboardIndex('ArrowRight', 2), 0);
  assert.equal(keyboardIndex('ArrowUp', 0), 2);
  assert.equal(keyboardIndex('ArrowDown', 2), 0);
  assert.equal(keyboardIndex('Home', 2), 0);
  assert.equal(keyboardIndex('End', 0), 2);
  assert.equal(keyboardIndex('Tab', 0), undefined);
});
test('scroll progress advances and reverses, clamped at ends', () => {
  assert.deepEqual([-.1, 0, .26, .76, 1.2, .5, 0].map(progressIndex), [0, 0, 1, 2, 2, 1, 0]);
});

function harness({ reduced = false, tall = false } = {}) {
  const handlers = new Map();
  const selections = [], triggers = [], classes = new Set(), properties = new Map();
  const stage = { getBoundingClientRect: () => ({ height: tall ? 2000 : 700 }), addEventListener: (k, fn) => handlers.set(`stage:${k}`, fn), removeEventListener: k => handlers.delete(`stage:${k}`) };
  const document = { activeElement: null };
  const panel = { contains: el => el === panel };
  const section = { ownerDocument: document, querySelector: () => stage, querySelectorAll: () => [panel], getBoundingClientRect: () => ({ top: 100 }),
    classList: { toggle(k, on) { on ? classes.add(k) : classes.delete(k); }, remove: k => classes.delete(k) },
    style: { setProperty: (k, v) => properties.set(k, v), removeProperty: k => properties.delete(k) } };
  const media = { matches: !reduced, addEventListener: (k, fn) => handlers.set(`media:${k}`, fn), removeEventListener: k => handlers.delete(`media:${k}`) };
  const win = { innerHeight: 1000, scrollY: 0, getComputedStyle: () => ({ paddingTop: '0px' }), matchMedia: () => media,
    requestAnimationFrame: fn => { handlers.set('frame', fn); return 1; }, cancelAnimationFrame: () => handlers.delete('frame'),
    addEventListener: (k, fn) => handlers.set(k, fn), removeEventListener: k => handlers.delete(k), scrollTo: value => { win.lastScroll = value; } };
  const ScrollTrigger = { create(options) { const trigger = { options, progress: 0, killed: false, kill() { this.killed = true; } }; triggers.push(trigger); return trigger; } };
  const story = createStory(section, { ScrollTrigger, onSelect: i => selections.push(i), win });
  return { story, win, document, panel, media, handlers, selections, triggers, classes, properties };
}
test('GSAP trigger maps forward/reverse progress and manual navigation aligns scroll', () => {
  const h = harness();
  const trigger = h.triggers[0];
  assert.equal(trigger.options.start(), 76);
  assert.equal(trigger.options.end(), 1476);
  for (const progress of [.5, 1, .5, 0]) trigger.options.onUpdate({ progress });
  assert.deepEqual(h.selections, [0, 1, 2, 1, 0]);
  h.story.navigate(2);
  assert.deepEqual(h.win.lastScroll, { top: 1476, behavior: 'instant' });
  h.story.destroy();
});
for (const mode of ['reduced', 'tall']) test(`${mode} view keeps manual tabs without pinning`, () => {
  const h = harness({ [mode]: true });
  assert.equal(h.triggers.length, 0);
  assert.equal(h.classes.size, 0);
  h.story.navigate(2);
  assert.deepEqual(h.selections, [2]);
  assert.equal(h.win.lastScroll, undefined);
  h.story.destroy();
});
test('scroll does not hide a focused panel; focusout resynchronizes', () => {
  const h = harness(); h.document.activeElement = h.panel;
  h.triggers[0].options.onUpdate({ progress: 1 });
  assert.deepEqual(h.selections, [0]);
  h.document.activeElement = null; h.triggers[0].progress = 1;
  h.handlers.get('stage:focusout')();
  h.handlers.get('frame')();
  assert.deepEqual(h.selections, [0, 2]); h.story.destroy();
});
test('live preference and resize recreate only owned trigger; destroy removes all listeners', () => {
  const h = harness();
  h.handlers.get('resize')();
  assert.equal(h.triggers[0].killed, true);
  h.media.matches = false; h.handlers.get('media:change')();
  assert.equal(h.triggers[1].killed, true);
  assert.equal(h.classes.size, 0);
  h.media.matches = true; h.handlers.get('media:change')();
  h.story.destroy();
  assert.equal(h.triggers.at(-1).killed, true);
  assert.equal(h.handlers.size, 0);
  assert.equal(h.properties.size, 0);
});
for (const locale of ['vi', 'en']) test(`${locale}: SSR keeps content, links, illustrations and no-JS access`, () => {
  const html = renderToString(<App locale={locale} />);
  const c = content[locale];
  assert.equal((html.match(/<h1 /g) || []).length, 1);
  assert.equal((html.match(/data-download=/g) || []).length, 2);
  assert.equal((html.match(/<details>/g) || []).length, 3);
  assert.equal((html.match(/class="preview"/g) || []).length, 3);
  assert.equal((html.match(/class="tab-icon"/g) || []).length, 3);
  assert.equal((html.match(/<li>/g) || []).length, 3);
  assert.equal((html.match(/<mark>/g) || []).length, 1);
  assert.equal((html.match(/<kbd>/g) || []).length, 3);
  assert.match(html, /role="tablist"[^>]+hidden=""/);
  assert.doesNotMatch(html, /<figure[^>]*hidden|eyebrow|story-link|scroll-hint/);
  assert.ok(html.includes(c.description));
  assert.ok(html.includes(fallback));
  assert.ok(html.includes(c.installFile));
  assert.match(html, /VieNeu/); assert.match(html, /Kokoro/); assert.match(html, /OpenAI/); assert.match(html, /OCR/);
  assert.ok(html.indexOf('id="compatibility"') < html.indexOf('class="install-link"'));
  assert.match(html, new RegExp(`id="${c.downloadId}"`));
  assert.match(html, /class="nav container"/); assert.match(html, /class="footer container"/);
  const imageSources = [...html.matchAll(/<img[^>]+src="([^"]+)"/g)].map(match => match[1]).filter(src => src.includes('screenshots/'));
  const base = locale === 'en' ? '../screenshots/en/' : 'screenshots/';
  assert.deepEqual(imageSources, ['reader', 'shelf', 'voices', 'shelf'].map(id => `${base}${id}.png`));
});
test('CSS retains full-width chrome, aligned images and reduced-motion fallback', () => {
  const css = readFileSync(new URL('../style.css', import.meta.url), 'utf8');
  assert.match(css, /\.nav\.container, \.footer\.container \{ max-width: none/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /\.preview img \{ width: 100%/);
  assert.doesNotMatch(css, /infinite/);
});
