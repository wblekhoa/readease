import React, { useEffect, useRef, useState } from 'react';
import { content } from './content.js';
import { fallback, fetchRelease, mb, repository } from './release.js';
import { createStory, keyboardIndex, viewIds } from './story.js';

const Arrow = () => <span aria-hidden="true">↗</span>;
const Lines = ({ value }) => <>{value[0]}<br />{value[1]}</>;
const doc = name => `${repository}/blob/main/${name}`;

/* One stroke set for every small glyph on the page (24px grid, 1.6 stroke). */
const glyphs = {
  reader: 'M12 5v15M12 5C9 3 6 3 3 4v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-3-1-6-1-9 1Z',
  shelf: 'M4 4h4v16H4zM10 4h4v16h-4zM16 5l4-1 3 15-4 1z',
  voices: 'M4 9v6M8 5v14M12 3v18M16 6v12M20 9v6',
  book: 'M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3zM5 17a3 3 0 0 1 3-3h11',
  paste: 'M9 4h6v3H9zM7 5H5v16h14V5h-2M8 12h8M8 16h5',
  cursor: 'M8 4h3M9.5 4v16M8 20h3M14 9h6M14 13h6M14 17h4',
  image: 'M4 5h16v14H4zM4 16l5-5 4 4 3-3 4 4M15 9h.01',
  bell: 'M6 16V11a6 6 0 1 1 12 0v5l2 2H4zM10 21h4',
  hash: 'M9 4 7 20M17 4l-2 16M4 9h16M3 15h16',
  follow: 'M4 18h16M4 13h10M4 8h16M17 11l3 2-3 2',
  clock: 'M12 7v5l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  menu: 'M3 6h18M7 6v-.5M12 11a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z',
  books: 'M4 5h5v15H4zM9 7h5v13H9zM15 6l4-1 3 14-4 1z',
  globe: 'M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  key: 'M14 10a4 4 0 1 0-3.5 4L9 16v2H7v2H4v-3l6.1-6.1M15 7h.01',
  speed: 'M12 14l4-5M4 18a9 9 0 1 1 16 0',
  pause: 'M8 6v12M16 6v12',
  heading: 'M5 5h14M12 5v14M9 19h6',
  caps: 'M3 18 7.5 6 12 18M4.7 14h5.6M15 18V6h3.5a3 3 0 0 1 0 6H15h4a3 3 0 0 1 0 6Z',
  quote: 'M5 11h4v6H5zM5 11c0-3 1-5 4-6M14 11h4v6h-4zM14 11c0-3 1-5 4-6',
  check: 'm5 12 4 4 10-10',
  plus: 'M12 5v14M5 12h14',
  down: 'M12 4v12M6 11l6 6 6-6M5 20h14',
};
/* The GitHub mark, filled (it is a logo, not a stroke glyph). */
const GITHUB = 'M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.52-1.33-1.28-1.68-1.28-1.68-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.84 1.19 3.1 0 4.42-2.7 5.4-5.26 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z';
const Glyph = ({ name, className = 'glyph' }) =>
  <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d={glyphs[name]} /></svg>;

function useEnhanced() {
  const [enhanced, setEnhanced] = useState(false);
  useEffect(() => { setEnhanced(true); }, []);
  return enhanced;
}
/* GSAP is loaded once, on demand, for the two scroll-linked sections. */
let motionEngine;
const loadMotion = () => (motionEngine ??= Promise.all([import('gsap'), import('gsap/ScrollTrigger')])
  .then(([{ gsap }, { ScrollTrigger }]) => { gsap.registerPlugin(ScrollTrigger); return { gsap, ScrollTrigger }; }));

function DownloadButton({ c, release, describedBy, className = 'button' }) {
  return <a className={className} href={release?.dmg.browser_download_url || fallback} data-download={c.cta} aria-describedby={describedBy}>
    <Glyph name="down" className="button-glyph" /><span data-label="">{c.cta}</span>
  </a>;
}
function Header({ c, prefix }) {
  return <header className="nav-shell"><div className="nav container">
    <a className="brand" href="./" aria-label={c.home}><img src={`${prefix}icon.png`} alt="" width="28" height="28" /><span>ReadEase</span></a>
    <nav className="nav-links" aria-label={c.nav}>
      {c.links.map(([id, label]) => <a key={id} href={`#${id}`}>{label}</a>)}
    </nav>
    <div className="nav-end">
      <a className="nav-github" href={repository} aria-label={c.github} title={c.github}><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d={GITHUB} /></svg><span>GitHub</span></a>
      <a className="language" href={c.other === 'en' ? 'en/' : '../'} lang={c.other} hrefLang={c.other} aria-label={c.switchLabel}><span aria-hidden="true">{c.flag}</span> {c.other.toUpperCase()}</a>
      <a className="nav-download" href={`#${c.downloadId}`}>{c.download}</a>
    </div>
  </div></header>;
}
function Hero({ c, prefix, release }) {
  // The second line is read aloud the way the app reads: a highlight moves word by word.
  return <section className="hero" aria-labelledby="hero-title">
    <div className="hero-aura" aria-hidden="true" />
    <p className="hero-chip"><img src={`${prefix}icon.png`} alt="" width="22" height="22" /><span>ReadEase</span><span className="chip-sub">{c.chip}</span>
      <span className="chip-wave" aria-hidden="true"><i /><i /><i /><i /></span></p>
    <h1 id="hero-title">{c.hero[0]}<br /><span className="hero-voice">{c.hero[1].split(' ').map((word, i) =>
      <React.Fragment key={i}>{i > 0 && ' '}<span className="hero-word" style={{ '--i': i }}>{word}</span></React.Fragment>)}</span></h1>
    <p className="description">{c.description}</p>
    <div className="actions"><DownloadButton c={c} release={release} describedBy="compatibility" /></div>
    <p className="compatibility" id="compatibility">{c.meta.map((item, i) => <React.Fragment key={item}>{i > 0 && <span className="meta-dot" aria-hidden="true">·</span>}<span>{item}</span></React.Fragment>)}</p>
  </section>;
}
/* A MacBook drawn in CSS: bezel, camera notch, screen, hinge and base. */
function Laptop({ children, className = '' }) {
  return <div className={`laptop ${className}`}>
    <div className="laptop-lid"><span className="laptop-notch" aria-hidden="true" /><div className="laptop-screen">{children}</div></div>
    <div className="laptop-base" aria-hidden="true"><span /></div>
  </div>;
}
function Showcase({ c, screenshots }) {
  const section = useRef(null);
  const story = useRef(null);
  const enhanced = useEnhanced();
  const [selected, setSelected] = useState(0);
  useEffect(() => {
    if (!enhanced) return;
    let disposed = false;
    loadMotion().then(({ ScrollTrigger }) => {
      if (!disposed) story.current = createStory(section.current, { ScrollTrigger, onSelect: setSelected });
    }).catch(() => { /* Manual, accessible tabs remain available if motion fails to load. */ });
    return () => { disposed = true; story.current?.destroy(); story.current = null; };
  }, [enhanced]);
  function navigate(index, focus = false) {
    if (story.current) story.current.navigate(index);
    else setSelected(index);
    if (focus) section.current.querySelector(`#tab-${viewIds[index]}`).focus();
  }
  return <section className="showcase" id="experience" aria-label={c.experience} data-showcase="" ref={section}>
    <div className="showcase-stage" data-stage="">
      <Laptop>
        {viewIds.map((id, i) => <figure key={id} className="preview" id={`panel-${id}`} data-preview="" data-on={selected === i ? '' : undefined}
          role={enhanced ? 'tabpanel' : undefined} aria-labelledby={enhanced ? `tab-${id}` : undefined} aria-hidden={enhanced && selected !== i ? true : undefined} tabIndex={enhanced && selected === i ? 0 : undefined}>
          <img src={`${screenshots}${id}.png`} width="1600" height="1025" fetchPriority={i === 0 ? 'high' : undefined} loading={i === 0 ? undefined : 'lazy'} alt={c.previews[i][1]} />
          <figcaption>{c.previews[i][2]}</figcaption>
        </figure>)}
      </Laptop>
      <p className="stage-caption" aria-hidden="true">{c.previews[selected][2]}</p>
      <div className="view-tabs" role="tablist" aria-label={c.screenshots} hidden={!enhanced}>
        {viewIds.map((id, i) => <button key={id} id={`tab-${id}`} type="button" role="tab" aria-controls={`panel-${id}`} aria-selected={selected === i} tabIndex={selected === i ? 0 : -1}
          onClick={() => navigate(i)} onKeyDown={event => { const next = keyboardIndex(event.key, i); if (next !== undefined) { event.preventDefault(); navigate(next, true); } }}>
          <span className="tab-step" aria-hidden="true">{i + 1}</span><Glyph name={id} className="tab-icon" /><span>{c.previews[i][0]}</span>
        </button>)}
      </div>
    </div>
  </section>;
}
/* The feature words drift sideways as the page scrolls past them: linked to
   the scroll, never a loop, and simply wrapped when motion is unwelcome. */
function Ticker({ c }) {
  const band = useRef(null);
  const enhanced = useEnhanced();
  useEffect(() => {
    if (!enhanced) return;
    const media = window.matchMedia('(prefers-reduced-motion: no-preference)');
    let ctx, disposed = false;
    const setup = () => {
      ctx?.revert(); ctx = undefined;
      band.current.classList.toggle('is-drifting', media.matches);
      if (!media.matches) return;
      loadMotion().then(({ gsap }) => {
        if (disposed || !media.matches) return;
        ctx = gsap.context(() => {
          gsap.fromTo('[data-drift]', { xPercent: 0 }, { xPercent: -22, ease: 'none',
            scrollTrigger: { trigger: band.current, start: 'top bottom', end: 'bottom top', scrub: .6 } });
        }, band);
      }).catch(() => band.current?.classList.remove('is-drifting'));
    };
    setup();
    media.addEventListener('change', setup);
    return () => { disposed = true; media.removeEventListener('change', setup); ctx?.revert(); };
  }, [enhanced]);
  return <section className="ticker" aria-label={c.tickerLabel} ref={band}>
    <ul className="ticker-row" data-drift="">{[...c.ticker, ...c.ticker].map((word, i) =>
      <li key={i} aria-hidden={i >= c.ticker.length ? true : undefined}>{word}</li>)}</ul>
  </section>;
}
function Card({ title, children }) {
  // Every card: a fixed-height illustration, then the title, so titles line up across cards.
  return <article className="way-card"><div className="way-visual"><div className="way-art">{children}</div></div>
    <div className="way-text"><p className="way-type">{title[0]} <span>{title[1]}</span></p><h3><Lines value={title.slice(2)} /></h3></div></article>;
}
function Ways({ c, screenshots }) {
  const track = useRef(null);
  const enhanced = useEnhanced();
  const [current, setCurrent] = useState(0);
  const count = 4;
  const step = direction => {
    const el = track.current; const card = el.querySelector('.way-card');
    el.scrollBy({ left: direction * (card.offsetWidth + 24), behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  };
  const onScroll = () => {
    const el = track.current; const card = el.querySelector('.way-card');
    setCurrent(Math.max(0, Math.min(count - 1, Math.round(el.scrollLeft / (card.offsetWidth + 24)))));
  };
  return <section className="ways section" id="features" aria-labelledby="ways-title">
    <div className="split-heading container"><h2 id="ways-title"><Lines value={c.ways} /></h2></div>
    <div className="way-track" ref={track} onScroll={enhanced ? onScroll : undefined} role="group" aria-label={c.carousel} tabIndex={0}>
      <Card title={c.library}><figure className="library-visual"><img src={`${screenshots}shelf.png`} width="1600" height="1025" loading="lazy" alt={c.libraryAlt} /></figure></Card>
      <Card title={c.paste}><figure className="reading-visual paste-visual" aria-label={c.pasteLabel}>
        <div className="passage-sheet"><p className="sample-label">{c.sampleTitle}</p><ol className="sample-passages">{c.passages.map(p => <li key={p}>{p}</li>)}</ol></div>
      </figure></Card>
      <Card title={c.selection}><figure className="reading-visual selection-visual" aria-label={c.selectionLabel}>
        <div className="selection-sheet"><p className="sample-label">{c.page}</p><p className="sample-excerpt">{c.excerpt[0]}<br /><mark>{c.excerpt[1]}</mark></p><div className="shortcut-legend"><span>{c.shortcut}</span><span><kbd>⌥</kbd> <kbd>⌘</kbd> <kbd>R</kbd></span></div></div>
      </figure></Card>
      <Card title={c.figures}><figure className="reading-visual figure-visual" aria-label={c.figuresLabel}>
        <div className="figure-sheet"><div className="figure-art" aria-hidden="true"><span /><span /><span /></div><p className="sample-label">{c.figureName}</p><p className="figure-cue"><Glyph name="voices" />{c.figureCue}</p></div>
      </figure></Card>
    </div>
    <div className="way-controls container" hidden={!enhanced}>
      <div className="way-dots" aria-hidden="true">{Array.from({ length: count }, (_, i) => <span key={i} className={i === current ? 'is-on' : undefined} />)}</div>
      <div className="way-arrows">
        <button type="button" aria-label={c.previous} onClick={() => step(-1)} disabled={current === 0}>←</button>
        <button type="button" aria-label={c.next} onClick={() => step(1)} disabled={current === count - 1}>→</button>
      </div>
    </div>
  </section>;
}
function Craft({ c }) {
  // A plain list of what makes listening feel natural (owner, 07/10: simple, many items).
  return <section className="craft section container" aria-labelledby="craft-title">
    <div className="center-heading"><p className="label">{c.craftLabel}</p><h2 id="craft-title"><Lines value={c.craft} /></h2></div>
    <ul className="tile-grid craft-list">{c.craftItems.map(([icon, title]) => <li key={title}><span className="tile-icon"><Glyph name={icon} /></span><h3>{title}</h3></li>)}</ul>
  </section>;
}
function Voices({ c }) {
  return <section className="voices section container" id="voices" aria-labelledby="voices-title">
    <div className="split-heading"><div><p className="label">{c.voicesLabel}</p><h2 id="voices-title"><Lines value={c.voicesTitle} /></h2></div></div>
    <div className="voice-grid">{c.voices.map(([language, model, facts]) =>
      <article key={model} className="voice-card"><p className="card-label">{language}</p><h3>{model}</h3>
        <ul className="fact-list">{facts.map(fact => <li key={fact}>{fact}</li>)}</ul><span className="voice-wave" aria-hidden="true">{Array.from({ length: 28 }, (_, i) => <i key={i} style={{ '--h': `${30 + Math.round(60 * Math.abs(Math.sin(i * .9 + model.length)))}%` }} />)}</span></article>)}
    </div>
    <p className="voices-note">{c.voicesNote}</p>
  </section>;
}
function More({ c }) {
  return <section className="more section container" aria-labelledby="more-title">
    <div className="center-heading"><p className="label">{c.moreLabel}</p><h2 id="more-title"><Lines value={c.moreTitle} /></h2></div>
    <ul className="tile-grid more-grid">{c.more.map(([icon, title]) => <li key={title}><span className={`tile-icon more-${icon}`}><Glyph name={icon} /></span><h3>{title}</h3></li>)}</ul>
  </section>;
}
function Privacy({ c }) {
  return <section className="privacy section container" id="privacy" aria-labelledby="privacy-title">
    <div className="center-heading"><p className="label">{c.privacyLabel}</p><h2 id="privacy-title">{c.privacyTitle[0]}<br /><span className="accent">{c.privacyTitle[1]}</span></h2>
      <p>{c.privacy}</p><ul className="pill-checks">{c.checks.map(item => <li key={item}><Glyph name="check" />{item}</li>)}</ul></div>
    <p className="privacy-foot">{c.license} <a className="text-link" href={doc('PRIVACY.md')}>{c.privacyLink} <Arrow /></a></p>
  </section>;
}
function FAQ({ c }) {
  return <section className="faq section container" id="faq" aria-labelledby="faq-title">
    <div className="center-heading"><p className="label">{c.faqLabel}</p><h2 id="faq-title">{c.faqTitle}</h2></div>
    <div className="questions">{c.faq.map(([question, answer, link]) => <details key={question}><summary>{question}<Glyph name="plus" className="summary-glyph" /></summary>
      <p>{answer}{link && <> <a href={doc(c.installFile)}>{link}</a>.</>}</p></details>)}</div>
  </section>;
}
function Closing({ c, prefix, release }) {
  return <section className="closing" id={c.downloadId} aria-labelledby="download-title">
    <div className="closing-tiles" aria-hidden="true">{['book', 'voices', 'paste', 'cursor', 'image', 'bell', 'hash', 'globe'].map(name => <span key={name}><Glyph name={name} /></span>)}</div>
    <div className="download-block">
      <img className="app-icon" src={`${prefix}icon.png`} width="84" height="84" alt="" loading="lazy" />
      <h2 id="download-title"><Lines value={c.closing} /></h2><p>{c.license}</p><DownloadButton c={c} release={release} />
      <p className="download-detail"><span data-download-detail="">{release ? `${release.version} · ${mb(release.dmg.size)} MB · .dmg` : c.latest}</span><span aria-hidden="true"> · </span><a href={release?.zip?.browser_download_url || fallback} data-zip=".zip ({size} MB)">{release?.zip ? `.zip (${mb(release.zip.size)} MB)` : '.zip'}</a></p>
    </div>
  </section>;
}
function Footer({ c, prefix, release }) {
  const targets = {
    download: release?.dmg.browser_download_url || fallback, install: doc(c.installFile), releases: `${repository}/releases`,
    source: repository, issues: `${repository}/issues/new/choose`, privacy: doc('PRIVACY.md'), license: doc('LICENSE'),
  };
  return <footer className="footer container">
    <div className="footer-about"><span className="footer-name"><img src={`${prefix}icon.png`} alt="" width="24" height="24" loading="lazy" />ReadEase <span>Thư Âm</span></span><p>{c.made}</p></div>
    <nav className="footer-groups" aria-label={c.support}>{c.footerGroups.map(([title, links]) => <div key={title}><p>{title}</p>
      <ul>{links.map(([key, label]) => <li key={key}><a href={key.startsWith('#') ? key : targets[key]}>{label}</a></li>)}</ul></div>)}</nav>
    <p className="footer-rights">© ReadEase · {c.rights}</p>
  </footer>;
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
  return <><a className="skip-link" href="#main">{c.skip}</a><Header c={c} prefix={prefix} />
    <main id="main"><div className="container"><Hero c={c} prefix={prefix} release={release} /></div><Showcase c={c} screenshots={screenshots} /><Ticker c={c} />
      <Ways c={c} screenshots={screenshots} /><Craft c={c} /><Voices c={c} /><More c={c} /><Privacy c={c} /><FAQ c={c} /><Closing c={c} prefix={prefix} release={release} /></main>
    <Footer c={c} prefix={prefix} release={release} /></>;
}
