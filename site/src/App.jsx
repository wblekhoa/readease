import React, { useEffect, useRef, useState } from 'react';
import { content } from './content.js';
import { fallback, fetchRelease, mb, repository } from './release.js';
import { createStory, keyboardIndex, viewIds } from './story.js';

const Arrow = () => <span aria-hidden="true">↗</span>;
const Lines = ({ value }) => <>{value[0]}<br />{value[1]}</>;
const doc = name => `${repository}/blob/main/${name}`;

function DownloadButton({ c, release, describedBy }) {
  return <a className="button" href={release?.dmg.browser_download_url || fallback} data-download={c.cta} aria-describedby={describedBy}><span data-label="">{c.cta}</span><Arrow /></a>;
}
function Header({ c, prefix }) {
  return <header className="nav container">
    <a className="brand" href="./" aria-label={c.home}><img src={`${prefix}icon.png`} alt="" width="36" height="36" /><span>ReadEase<span className="brand-sub">Thư Âm</span></span></a>
    <nav className="nav-links" aria-label={c.nav}>
      <a className="source-link" href={repository}>GitHub</a>
      <a className="language" href={c.other === 'en' ? 'en/' : '../'} lang={c.other} hrefLang={c.other} aria-label={c.switchLabel}><span aria-hidden="true">{c.flag}</span> {c.other.toUpperCase()}</a>
      <a className="nav-download" href={`#${c.downloadId}`}>{c.download} <Arrow /></a>
    </nav>
  </header>;
}
function Hero({ c, release }) {
  return <section className="hero" aria-labelledby="hero-title">
    <div className="hero-heading"><h1 id="hero-title">{c.hero[0]}<br /><span>{c.hero[1]}</span></h1></div>
    <div className="hero-copy">
      <p className="description">{c.description}</p>
      <div className="actions"><DownloadButton c={c} release={release} describedBy="compatibility" /></div>
      <p className="compatibility" id="compatibility">macOS 15+ · Apple Silicon</p>
      <a className="install-link" href={doc(c.installFile)}>{c.install}</a>
    </div>
  </section>;
}
const iconPaths = [
  'M12 5v15M12 5C9 3 6 3 3 4v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-3-1-6-1-9 1Z',
  'M4 4h4v16H4zM10 4h4v16h-4zM16 5l4-1 3 15-4 1z',
  'M4 9v6M8 5v14M12 3v18M16 6v12M20 9v6',
];
function Showcase({ c, screenshots }) {
  const section = useRef(null);
  const story = useRef(null);
  const engine = useRef(null);
  const previous = useRef(0);
  const [enhanced, setEnhanced] = useState(false);
  const [selected, setSelected] = useState(0);
  // Beside the screen the tab list stands vertical (style.css, > 960px);
  // above it on narrow screens it lies horizontal. Assistive tech is told
  // which, so the arrow keys it announces match the axis on screen.
  const [vertical, setVertical] = useState(false);
  useEffect(() => { setEnhanced(true); }, []);
  useEffect(() => {
    const media = window.matchMedia('(min-width: 961px)');
    const follow = () => setVertical(media.matches);
    follow();
    media.addEventListener('change', follow);
    return () => media.removeEventListener('change', follow);
  }, []);
  useEffect(() => {
    if (!enhanced) return;
    let disposed = false;
    Promise.all([import('gsap'), import('gsap/ScrollTrigger')]).then(([{ gsap }, { ScrollTrigger }]) => {
      if (disposed) return;
      gsap.registerPlugin(ScrollTrigger);
      engine.current = gsap;
      story.current = createStory(section.current, { ScrollTrigger, onSelect: setSelected });
    }).catch(() => { /* Manual, accessible tabs remain available if motion fails to load. */ });
    return () => { disposed = true; story.current?.destroy(); story.current = null; engine.current = null; };
  }, [enhanced]);
  useEffect(() => {
    const old = previous.current;
    previous.current = selected;
    const gsap = engine.current;
    if (!gsap || old === selected) return;
    const media = window.matchMedia('(prefers-reduced-motion: no-preference)');
    const ctx = gsap.context(() => {
      if (media.matches) gsap.fromTo(section.current.querySelector(`#panel-${viewIds[selected]}`),
        { opacity: .65, y: selected > old ? 14 : -14, scale: .99 },
        { opacity: 1, y: 0, scale: 1, duration: .42, ease: 'power3.out', clearProps: 'opacity,transform' });
    }, section);
    const cancel = () => ctx.revert();
    media.addEventListener('change', cancel);
    return () => { media.removeEventListener('change', cancel); ctx.revert(); };
  }, [selected]);
  function navigate(index, focus = false) {
    if (story.current) story.current.navigate(index);
    else setSelected(index);
    if (focus) section.current.querySelector(`#tab-${viewIds[index]}`).focus();
  }
  return <section className="showcase" id="experience" aria-label={c.experience} data-showcase="" ref={section}>
    <div className="showcase-stage" data-stage="">
      <div className="showcase-side">
        <div className="section-heading"><h2><Lines value={c.showcase} /></h2></div>
        <div className="view-tabs" role="tablist" aria-label={c.screenshots} aria-orientation={vertical ? 'vertical' : undefined} hidden={!enhanced}>
          {viewIds.map((id, i) => <button key={id} id={`tab-${id}`} type="button" role="tab" aria-controls={`panel-${id}`} aria-selected={selected === i} tabIndex={selected === i ? 0 : -1}
            onClick={() => navigate(i)} onKeyDown={event => { const next = keyboardIndex(event.key, i); if (next !== undefined) { event.preventDefault(); navigate(next, true); } }}>
            <svg className="tab-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d={iconPaths[i]} /></svg><span>{c.previews[i][0]}</span>
          </button>)}
        </div>
      </div>
      <div className="showcase-screen">
        {viewIds.map((id, i) => <figure key={id} className="preview" id={`panel-${id}`} data-preview="" hidden={enhanced && selected !== i} role={enhanced ? 'tabpanel' : undefined} aria-labelledby={enhanced ? `tab-${id}` : undefined} tabIndex={enhanced ? 0 : undefined}>
          <img src={`${screenshots}${id}.png`} width="1600" height="1025" fetchPriority={i === 0 ? 'high' : undefined} loading={i === 0 ? undefined : 'lazy'} alt={c.previews[i][1]} />
          <figcaption>{c.previews[i][2]}</figcaption>
        </figure>)}
      </div>
    </div>
  </section>;
}
function FeatureStory({ title, children }) {
  return <article><p className="way-type">{title[0]} <span>{title[1]}</span></p><h3><Lines value={title.slice(2)} /></h3>{children}</article>;
}
function Ways({ c, screenshots }) {
  return <section className="ways section" aria-labelledby="ways-title">
    <div className="section-heading story-intro"><h2 id="ways-title"><Lines value={c.ways} /></h2><p className="story-description"><Lines value={c.waysDescription} /></p><a className="text-link" href={`#${c.downloadId}`}>{c.start} <Arrow /></a></div>
    <div className="ways-grid">
      <FeatureStory title={c.library}><figure className="library-visual"><img src={`${screenshots}shelf.png`} width="1600" height="1025" loading="lazy" alt={c.libraryAlt} /></figure></FeatureStory>
      <FeatureStory title={c.paste}><figure className="reading-visual paste-visual" aria-label={c.pasteLabel}>
        <div className="passage-sheet"><p className="sample-label">{c.sampleTitle}</p><ol className="sample-passages">{c.passages.map(p => <li key={p}>{p}</li>)}</ol></div><figcaption>{c.pasteCaption}</figcaption>
      </figure></FeatureStory>
      <FeatureStory title={c.selection}><figure className="reading-visual selection-visual" aria-label={c.selectionLabel}>
        <div className="selection-sheet"><p className="sample-label">{c.page}</p><p className="sample-excerpt">{c.excerpt[0]}<br /><mark>{c.excerpt[1]}</mark></p><div className="shortcut-legend"><span>{c.shortcut}</span><span><kbd>⌥</kbd> <kbd>⌘</kbd> <kbd>R</kbd></span></div></div><figcaption>{c.selectionCaption}</figcaption>
      </figure></FeatureStory>
    </div>
  </section>;
}
function FAQ({ c }) {
  return <div className="questions">{c.faq.map(([question, answer, link]) => <details key={question}><summary>{question}</summary><p>{answer}{link && <> <a href={doc(c.installFile)}>{link}</a>.</>}</p></details>)}</div>;
}
function Closing({ c, prefix, release }) {
  return <section className="closing section" id={c.downloadId} aria-labelledby="download-title">
    <div className="download-block">
      <img className="app-icon" src={`${prefix}icon.png`} width="64" height="64" alt="" loading="lazy" />
      <h2 id="download-title"><Lines value={c.closing} /></h2><p>{c.license}</p><DownloadButton c={c} release={release} />
      <p className="download-detail"><span data-download-detail="">{release ? `${release.version} · ${mb(release.dmg.size)} MB · .dmg` : c.latest}</span><span aria-hidden="true"> · </span><a href={release?.zip?.browser_download_url || fallback} data-zip=".zip ({size} MB)">{release?.zip ? `.zip (${mb(release.zip.size)} MB)` : '.zip'}</a></p>
    </div>
    <div className="practical"><h3><Lines value={c.privacyTitle} /></h3><p>{c.privacy}</p><a className="text-link" href={doc('PRIVACY.md')}>{c.privacyLink} <Arrow /></a><FAQ c={c} /></div>
  </section>;
}
function Footer({ c }) {
  const links = [repository, `${repository}/releases`, `${repository}/issues/new/choose`, doc('LICENSE')];
  return <footer className="footer container"><div><span className="footer-name">ReadEase <span>Thư Âm</span></span><p>{c.made}</p></div><nav aria-label={c.support}>{links.map((href, i) => <a key={href} href={href}>{c.footer[i]}</a>)}</nav></footer>;
}
export function App({ locale = 'vi' }) {
  const c = content[locale];
  const prefix = locale === 'en' ? '../' : '';
  const screenshots = `${prefix}screenshots/${locale === 'en' ? 'en/' : ''}`;
  const [release, setRelease] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    fetchRelease(controller.signal).then(value => { if (!controller.signal.aborted) setRelease(value); });
    return () => controller.abort();
  }, []);
  return <><a className="skip-link" href="#main">{c.skip}</a><Header c={c} prefix={prefix} /><main id="main" className="container"><Hero c={c} release={release} /><Showcase c={c} screenshots={screenshots} /><Ways c={c} screenshots={screenshots} /><Closing c={c} prefix={prefix} release={release} /></main><Footer c={c} /></>;
}
