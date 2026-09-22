import React from 'react';
import { renderToString } from 'react-dom/server';
import { defineConfig } from 'vite';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { App } from './src/App.jsx';

const root = fileURLToPath(new URL('.', import.meta.url));
const assets = new Map([
  ['icon.png', new URL('./icon.png', import.meta.url)],
  ...['', 'en/'].flatMap(locale => ['reader', 'shelf', 'voices'].map(id =>
    [`screenshots/${locale}${id}.png`, new URL(`../assets/screenshots/${locale}${id}.png`, import.meta.url)])),
]);

export default defineConfig({
  root, base: './', publicDir: false,
  build: { rollupOptions: { input: { vi: `${root}index.html`, en: `${root}en/index.html` } } },
  plugins: [{
    name: 'readease-static-content',
    transformIndexHtml: {
      order: 'post',
      handler(html) {
        const locale = /<html\s+lang="en"/.test(html) ? 'en' : 'vi';
        return html.replace('<!--app-html-->', renderToString(React.createElement(App, { locale })));
      },
    },
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const name = req.url?.split('?')[0].replace(/^\//, '');
        const file = assets.get(name);
        if (!file) return next();
        res.setHeader('Content-Type', 'image/png');
        res.end(readFileSync(file));
      });
    },
    generateBundle() {
      for (const [fileName, file] of assets) this.emitFile({ type: 'asset', fileName, source: readFileSync(file) });
      // Preserve notices alongside the minified runtime, independently of minifier comments.
      const licenses = ['react', 'react-dom', 'scheduler'].map(name =>
        `${name}\n${readFileSync(new URL(`./node_modules/${name}/LICENSE`, import.meta.url), 'utf8')}`);
      for (const name of ['gsap-core.js', 'ScrollTrigger.js', 'Observer.js', 'CSSPlugin.js']) {
        const source = readFileSync(new URL(`./node_modules/gsap/${name}`, import.meta.url), 'utf8');
        licenses.push(source.match(/\/\*![\s\S]*?\*\//)?.[0] || source.slice(0, source.indexOf('*/') + 2));
      }
      this.emitFile({ type: 'asset', fileName: 'THIRD_PARTY_LICENSES.txt', source: licenses.join('\n\n') });
    },
  }],
});
