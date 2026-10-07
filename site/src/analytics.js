/* Simple GA4 page analytics for the landing page (owner, 07/10).
   Off until GA_ID holds the ReadEase web stream's measurement id; skipped on
   localhost and when the browser sends Do Not Track. Google signals and ad
   personalisation are switched off. The app itself sends nothing - this
   counts visits to the page, nothing more. */
export const GA_ID = '';

const EVENTS = [
  // [selector, event name, params from the element]
  ['[data-download]', 'download_click', el => ({ place: el.closest('.hero') ? 'hero' : 'closing' })],
  ['.nav-download', 'download_nav_click', () => ({})],
  ['.nav-github', 'github_click', () => ({})],
  ['.language', 'language_switch', el => ({ to: el.getAttribute('lang') })],
  ['.voice-play', 'voice_demo_play', el => ({ voice: (el.getAttribute('aria-label') || '').split(': ').pop() })],
  ['summary', 'faq_open', el => ({ question: el.textContent.trim().slice(0, 80) })],
];

export function startAnalytics(id = GA_ID) {
  if (!id || typeof window === 'undefined') return;
  if (/^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname) || navigator.doNotTrack === '1') return;
  window.dataLayer = window.dataLayer || [];
  window.gtag = function gtag() { window.dataLayer.push(arguments); };
  window.gtag('js', new Date());
  window.gtag('config', id, { allow_google_signals: false, allow_ad_personalization_signals: false });
  const script = document.createElement('script');
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
  document.head.append(script);
  // One listener for every tracked control; a voice demo counts only when it starts.
  document.addEventListener('click', event => {
    for (const [selector, name, params] of EVENTS) {
      const el = event.target.closest?.(selector);
      if (!el) continue;
      if (name === 'voice_demo_play' && el.getAttribute('aria-pressed') === 'true') return;
      if (name === 'faq_open' && el.parentElement?.open) return;
      window.gtag('event', name, { ...params(el), page_language: document.documentElement.lang });
      return;
    }
  }, { capture: true });
}
