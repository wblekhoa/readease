import React, { useEffect, useRef, useState } from 'react';
import { content } from './content.js';
import { directDmg, directZip, fallback, fetchRelease, mb, repository } from './release.js';
import { glyphs } from './icons.js';
import { voiceBars } from './voiceBars.js';
import { createStory, keyboardIndex, viewIds } from './story.js';

const Arrow = () => <span aria-hidden="true">↗</span>;
const Lines = ({ value }) => <>{value[0]}<br />{value[1]}</>;
const doc = name => `${repository}/blob/main/${name}`;

/* One stroke set for every small glyph on the page (24px grid, 1.6 stroke). */
/* The GitHub mark, filled (it is a logo, not a stroke glyph). */
const GITHUB = 'M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.52-1.33-1.28-1.68-1.28-1.68-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.84 1.19 3.1 0 4.42-2.7 5.4-5.26 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z';
const Glyph = ({ name, className = 'glyph' }) =>
  <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
    {glyphs[name].map(([d, extra], i) => <path key={i} d={d} {...extra} />)}</svg>;

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
  return <a className={className} href={release?.dmg.browser_download_url || directDmg} data-download={c.cta} aria-describedby={describedBy}>
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
/* The brand's mark behind the headline: the icon's ring of light, drawn as
   six closed strands that ripple at different counts and phases, the way
   the icon's ribbons cross. Pure geometry, so it is SVG, not an image. */
/* The brand's mark behind the headline: the icon's ring of light, drawn as
   closed strands that ripple at different counts and phases, the way the
   icon's ribbons cross. Pure geometry, so it is SVG, not an image.
   In three depths (owner, 10/10: "create depth ... one less blurred than the
   ones behind it"): far strands sit a little outside, wide, soft and deep
   blue; near strands a little inside, fine, sharp and light. */
const DEPTHS = [
  { name: 'far', radius: 322, width: 7, strands: [[5, .4, 22], [6, 2.1, 18], [4, 4.0, 24]] },
  { name: 'mid', radius: 302, width: 3, strands: [[6, 0, 15], [7, 2.3, 12], [5, 4.6, 13]] },
  { name: 'near', radius: 286, width: 1.3, strands: [[6, 3.4, 16], [7, 5.5, 17], [5, 1.1, 18]] },
];
function strand(waves, phase, amplitude, radius = 300) {
  const points = Array.from({ length: 181 }, (_, i) => {
    const t = (i / 180) * Math.PI * 2;
    const r = radius + amplitude * Math.sin(waves * t + phase) + amplitude * .45 * Math.sin((waves - 2) * t - phase * 1.7);
    return `${(r * Math.cos(t)).toFixed(1)} ${(r * Math.sin(t)).toFixed(1)}`;
  });
  return `M${points.join('L')}Z`;
}
const LAYERS = DEPTHS.map((depth, layer) => ({
  ...depth,
  paths: depth.strands.map(([waves, phase, amplitude]) => strand(waves, phase, amplitude, depth.radius)),
  /* Each strand swells and settles like a level meter under a voice, on its
     own beat (owner, 10/10: "motion như sound wave") - louder and further
     along, quieter, back where it began, a closed loop that never jumps.
     Nearer strands beat faster and wider: what is close moves more. The far
     layer only turns. SMIL, not CSS `d`, because Safari animates only SMIL
     path data. */
  beats: layer === 0 ? null : depth.strands.map(([waves, phase, amplitude], i) => ({
    dur: `${(layer === 2 ? 3.1 : 4.4) + i * .53}s`,
    values: [strand(waves, phase, amplitude, depth.radius), strand(waves, phase + .8, amplitude * (layer === 2 ? 1.9 : 1.5), depth.radius),
      strand(waves, phase + 1.5, amplitude * .55, depth.radius), strand(waves, phase, amplitude, depth.radius)].join(';'),
  })),
}));
const GLOW_PATHS = LAYERS[1].paths;
const RING_STOPS = {
  glow: ['var(--ring-hi)', 'var(--brand)', 'var(--ring-deep)'],
  far: ['var(--brand)', 'var(--ring-deep)', 'var(--ring-deep)'],
  mid: ['var(--ring-hi)', 'var(--brand)', 'var(--ring-deep)'],
  near: ['var(--ring-near)', 'var(--ring-hi)', 'var(--brand)'],
};
/* Ribbons, not wires (owner, 10/10: "chưa hài hoà"): light runs along each
   strand and dies away, the way the icon's ribbons glow in places and sink
   into the dark in others. The bright reaches sit at a different angle in
   each depth, so as the layers turn, light travels round the ring. */
function RingGradient({ id, stops, angle = 45, ribbon = false }) {
  const a = (angle * Math.PI) / 180;
  const [x, y] = [Math.cos(a) * 340, Math.sin(a) * 340];
  const shine = ribbon ? [.12, 1, .18, .95, .1] : [1, 1, 1, 1, 1];
  const at = [0, .24, .48, .74, 1];
  const color = [stops[0], stops[0], stops[1], stops[2], stops[2]];
  return <defs><linearGradient id={id} gradientUnits="userSpaceOnUse" x1={-x} y1={-y} x2={x} y2={y}>
    {at.map((offset, i) => <stop key={i} offset={offset} style={{ stopColor: color[i], stopOpacity: shine[i] }} />)}
  </linearGradient></defs>;
}
const RING_ANGLES = { glow: 45, far: 110, mid: 20, near: -40 };
/* One SVG per depth so each turns on the compositor at its own speed - the
   parallax that sells the depth. The wide glow and the far strands never
   change shape, so they are painted once; only the mid and near strands
   ripple. Everything stops while the hero is out of sight, and nothing
   moves under Reduce Motion. */
function HeroRing() {
  const box = useRef(null);
  const [moving, setMoving] = useState(false);
  useEffect(() => {
    const quiet = window.matchMedia('(prefers-reduced-motion: reduce)');
    const follow = () => setMoving(!quiet.matches);
    follow();
    quiet.addEventListener('change', follow);
    return () => quiet.removeEventListener('change', follow);
  }, []);
  useEffect(() => {
    if (!moving || !box.current || !('IntersectionObserver' in window)) return;
    const watch = new IntersectionObserver(([entry]) => {
      box.current?.classList.toggle('ring-paused', !entry.isIntersecting);
      box.current?.querySelectorAll('svg').forEach(svg => entry.isIntersecting ? svg.unpauseAnimations?.() : svg.pauseAnimations?.());
    });
    watch.observe(box.current);
    return () => watch.disconnect();
  }, [moving]);
  return <div className="hero-backdrop" aria-hidden="true" ref={box}><div className="ring-stage">
    <svg className="hero-ring ring-glow" viewBox="-500 -500 1000 1000" focusable="false">
      <RingGradient id="ring-glow" stops={RING_STOPS.glow} angle={RING_ANGLES.glow} />
      <g fill="none" stroke="url(#ring-glow)" strokeWidth="34">{GLOW_PATHS.map((d, i) => <path key={i} d={d} />)}</g>
    </svg>
    {LAYERS.map(layer => <svg key={layer.name} className={`hero-ring ring-${layer.name}`} viewBox="-500 -500 1000 1000" focusable="false">
      <RingGradient id={`ring-${layer.name}-light`} stops={RING_STOPS[layer.name]} angle={RING_ANGLES[layer.name]} ribbon />
      <g fill="none" stroke={`url(#ring-${layer.name}-light)`} strokeWidth={layer.width} strokeLinejoin="round">{layer.paths.map((d, i) => <path key={i} d={d}>
        {moving && layer.beats && <animate attributeName="d" dur={layer.beats[i].dur} values={layer.beats[i].values} repeatCount="indefinite"
          calcMode="spline" keyTimes="0;.35;.7;1" keySplines=".45 0 .55 1;.45 0 .55 1;.45 0 .55 1" />}
      </path>)}</g>
    </svg>)}
  </div></div>;
}
function Hero({ c, prefix, release }) {
  // The second line is read aloud the way the app reads: a highlight moves word by word.
  return <section className="hero" aria-labelledby="hero-title">
    <div className="hero-aura" aria-hidden="true" />
    <HeroRing />
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
    <ul className="ticker-row" data-drift="">{[...c.ticker, ...c.ticker].map(([icon, word], i) =>
      <li key={i} aria-hidden={i >= c.ticker.length ? true : undefined}><Glyph name={icon} />{word}</li>)}</ul>
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
/* A real sample from each local model (scripts/render-voice-demos.py). Plays on
   request only; starting one stops the other; the bars are the clip's own peaks. */
function VoicePlayer({ src, bars, name, labels, compact = false }) {
  const audio = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    const element = audio.current;
    let frame = 0;
    const draw = () => { setProgress(element.duration ? element.currentTime / element.duration : 0); frame = requestAnimationFrame(draw); };
    const onPlay = () => { setPlaying(true); frame = requestAnimationFrame(draw); };
    const onStop = () => { setPlaying(false); cancelAnimationFrame(frame); };
    const onEnd = () => { onStop(); setProgress(0); };
    element.addEventListener('play', onPlay); element.addEventListener('pause', onStop); element.addEventListener('ended', onEnd);
    return () => { cancelAnimationFrame(frame); element.removeEventListener('play', onPlay); element.removeEventListener('pause', onStop); element.removeEventListener('ended', onEnd); };
  }, []);
  function toggle() {
    const element = audio.current;
    if (!element.paused) { element.pause(); return; }
    for (const other of document.querySelectorAll('audio[data-voice-demo]')) if (other !== element) other.pause();
    element.play().catch(() => setPlaying(false));
  }
  const lit = Math.round(progress * bars.length);
  if (compact) return <span className={`voice-mini${playing ? ' is-playing' : ''}`} style={{ '--p': progress }}>
    <button type="button" className="voice-play" onClick={toggle} aria-pressed={playing} aria-label={`${playing ? labels[1] : labels[0]}: ${name}`}><Glyph name={playing ? 'pause' : 'play'} /></button>
    <audio ref={audio} src={src} preload="none" data-voice-demo="" /></span>;
  return <div className="voice-player">
    <button type="button" className="voice-play" onClick={toggle} aria-pressed={playing} aria-label={`${playing ? labels[1] : labels[0]}: ${name}`}><Glyph name={playing ? 'pause' : 'play'} /></button>
    <span className="voice-wave" aria-hidden="true">{bars.map((height, i) => <i key={i} className={i < lit ? 'is-played' : undefined} style={{ '--h': `${height}%` }} />)}</span>
    <audio ref={audio} src={src} preload="none" data-voice-demo="" />
  </div>;
}
function Voices({ c, prefix, locale }) {
  return <section className="voices section container" id="voices" aria-labelledby="voices-title">
    <div className="center-heading"><p className="label">{c.voicesLabel}</p><h2 id="voices-title"><Lines value={c.voicesTitle} /></h2></div>
    <div className="voice-grid">{c.voices.map(([flag, language, model, facts], i) => {
      const demo = ['vi', 'en'][i];
      return <article key={model} className="voice-card">
        <p className="voice-lang"><span aria-hidden="true">{flag}</span>{language}</p><h3>{model}</h3>
        <p className="fact-list">{facts.map((fact, j) => <React.Fragment key={fact}>{j > 0 && <span className="meta-dot" aria-hidden="true">·</span>}<span>{fact}</span></React.Fragment>)}</p>
        <VoicePlayer src={`${prefix}voice-demos/${demo}.m4a`} bars={voiceBars[demo]} name={model} labels={c.listen} />
      </article>;
    })}</div>
    {/* The paid-voice option, drawn as the app's key settings: keys stay masked, a session cap,
        and the price shown on the read button before anything is sent (example figures). */}
    <article className="api-card">
      <div className="api-copy"><span className="tile-icon"><Glyph name="key" /></span><h3>{c.apiTitle}</h3></div>
      {/* The app's key settings, each saved provider with a real sample of its stock voice
          (same text as the local demos), then the per-session spending cap. */}
      <div className="api-panel">
        {[['openai', 'OpenAI', { vi: 'Marin', en: 'Marin' }, 'sk-••••••••••••3f9a'], ['elevenlabs', 'ElevenLabs', { vi: 'Nguyễn Ngân', en: 'Sarah' }, '••••••••••••b21c']].map(([id, provider, voices, key]) => { const voice = voices[locale]; return (
          <div key={id} className="api-row api-provider">
            <VoicePlayer compact src={`${prefix}voice-demos/${id}-${locale}.m4a`} bars={voiceBars[`${id}-${locale}`]} name={`${provider} ${voice}`} labels={c.listen} />
            <b>{provider}<span> · {voice}</span></b><code aria-hidden="true">{key}</code><span className="api-saved"><Glyph name="check" />{c.apiRows[0]}</span>
          </div>); })}
        <p className="api-row api-cap-row" aria-hidden="true"><b>{c.apiRows[1]}</b><span className="api-cap">$1.00</span></p>
      </div>
    </article>
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
      <p className="download-detail">{release ? <span data-download-detail="">{`${release.version} · ${mb(release.dmg.size)} MB · .dmg`}</span> : <a data-download-detail="" href={fallback}>{c.latest}</a>}<span aria-hidden="true"> · </span><a href={release?.zip?.browser_download_url || directZip} data-zip=".zip ({size} MB)">{release?.zip ? `.zip (${mb(release.zip.size)} MB)` : '.zip'}</a></p>
    </div>
  </section>;
}
function Footer({ c, prefix, release }) {
  const targets = {
    download: release?.dmg.browser_download_url || directDmg, install: doc(c.installFile), releases: `${repository}/releases`,
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
      <Ways c={c} screenshots={screenshots} /><Craft c={c} /><Voices c={c} prefix={prefix} locale={locale} /><More c={c} /><Privacy c={c} /><FAQ c={c} /><Closing c={c} prefix={prefix} release={release} /></main>
    <Footer c={c} prefix={prefix} release={release} /></>;
}
