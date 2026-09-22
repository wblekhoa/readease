export const viewIds = ['reader', 'shelf', 'voices'];
// The list is vertical beside the screen on desktop and horizontal above it
// on narrow screens, so both arrow axes move through it (WAI-ARIA tabs).
export function keyboardIndex(key, index) {
  const next = (index + 1) % 3, previous = (index + 2) % 3;
  return ({ ArrowRight: next, ArrowDown: next, ArrowLeft: previous, ArrowUp: previous, Home: 0, End: 2 })[key];
}
export const progressIndex = progress => Math.max(0, Math.min(2, Math.round(progress * 2)));

// Own only this section's trigger/listeners. Safe to dispose during React unmount/HMR.
// CSS handles stickiness; GSAP measures the two bounded scroll steps, not wheel input.
export function createStory(section, { ScrollTrigger, onSelect, win = window }) {
  const stage = section.querySelector('[data-stage]');
  const panels = [...section.querySelectorAll('[data-preview]')];
  const motion = win.matchMedia('(prefers-reduced-motion: no-preference) and (min-height: 600px)');
  let trigger;
  let disposed = false;
  let step = 1;
  let focusFrame;
  const start = () => section.getBoundingClientRect().top + win.scrollY +
    (parseFloat(win.getComputedStyle(section).paddingTop) || 0) - 24;
  const sync = progress => {
    if (!panels.some(panel => panel.contains(section.ownerDocument.activeElement))) onSelect(progressIndex(progress));
  };
  function configure() {
    if (disposed) return;
    trigger?.kill();
    trigger = undefined;
    section.classList.toggle('scroll-showcase', motion.matches);
    step = Math.max(320, win.innerHeight * .7);
    section.style.setProperty('--story-travel', `${step * 2}px`);
    if (!motion.matches || stage.getBoundingClientRect().height > win.innerHeight - 48) {
      section.classList.remove('scroll-showcase');
      return;
    }
    trigger = ScrollTrigger.create({
      trigger: section, start, end: () => start() + step * 2,
      invalidateOnRefresh: true,
      onUpdate: self => sync(self.progress),
      onRefresh: self => sync(self.progress),
    });
    sync(trigger.progress);
  }
  const focusout = () => {
    win.cancelAnimationFrame(focusFrame);
    focusFrame = win.requestAnimationFrame(() => { if (!disposed && trigger) sync(trigger.progress); });
  };
  win.addEventListener('resize', configure);
  motion.addEventListener('change', configure);
  stage.addEventListener('focusout', focusout);
  section.ownerDocument.fonts?.ready.then(configure);
  configure();
  return {
    navigate(index) {
      onSelect(index);
      if (trigger) win.scrollTo({ top: start() + step * index, behavior: 'instant' });
    },
    destroy() {
      disposed = true;
      win.cancelAnimationFrame(focusFrame);
      trigger?.kill();
      win.removeEventListener('resize', configure);
      motion.removeEventListener('change', configure);
      stage.removeEventListener('focusout', focusout);
      section.classList.remove('scroll-showcase');
      section.style.removeProperty('--story-travel');
    },
  };
}
