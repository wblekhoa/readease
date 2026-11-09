import { scenarios, validateScenario } from './playgroundScenarios';

declare global { interface Window { __playgroundState?: { scenario: string; cell?: string; status: string; error?: string } } }
const label = (element: Element) => (element.getAttribute('aria-label') || element.textContent || '').trim();
const button = (pattern: RegExp) => [...document.querySelectorAll<HTMLButtonElement>('button')].find(b => !b.disabled && pattern.test(label(b)));
async function until<T>(find: () => T | undefined | null | false): Promise<T> {
  const deadline = performance.now() + 12000;
  while (performance.now() < deadline) {
    const value = find(); if (value) return value;
    await new Promise(resolve => setTimeout(resolve, 40));
  }
  throw new Error('Scenario checkpoint timed out');
}
async function press(pattern: RegExp) {
  // Lookup and dispatch in one task: unfolding can replace its buttons.
  await until(() => { const target = button(pattern); if (!target?.isConnected) return false; target.click(); return true; });
}
function announce(state: NonNullable<Window['__playgroundState']>) {
  const query = new URLSearchParams(location.search);
  state.cell = `${state.scenario}/${query.get('locale') ?? 'vi'}/${query.get('theme') ?? 'light'}/${query.get('viewport') ?? `${innerWidth}x${innerHeight}`}`;
  window.__playgroundState = state;
  if (parent !== window && document.referrer) parent.postMessage({ type: 'readease-scenario', ...state }, new URL(document.referrer).origin);
}

// RE-PG-003: reach checkpoints through product actions, never synthetic UI markup.
export async function runPlaygroundScenario() {
  const scenario = scenarios.find(s => s.id === new URLSearchParams(location.search).get('pilot'));
  if (!scenario) return;
  announce({ scenario: scenario.id, status: 'loading' });
  let step = 'startup';
  try {
    validateScenario(scenario);
    await until(() => window.__mockReady?.());
    for (const action of scenario.steps) {
      step = action;
      if (action === 'library') {
        const unfold = button(/^(Mở cột bên|Show the side column)/); unfold?.click();
        await press(/^(Thư viện|Library)$/);
      }
      if (action === 'open') await press(/^(Mở|Open) (Một buổi sáng|A quiet morning)/);
      if (action === 'read') await press(/^(Đọc tiếp|Continue)/);
      if (action === 'pause') {
        await until(() => /Đang đọc:|Reading:/.test(document.querySelector('[data-reading-status]')?.textContent ?? ''));
        await press(/^(Tạm dừng|Pause)$/);
      }
    }
    if (scenario.checkpoint === 'preparing') await until(() => /Đang chuẩn bị giọng đọc|Preparing the voice/.test(document.body.textContent ?? ''));
    if (scenario.checkpoint === 'playing') await until(() => /Đang đọc:|Reading:/.test(document.querySelector('[data-reading-status]')?.textContent ?? ''));
    if (scenario.checkpoint === 'paused') await until(() => button(/^(Tiếp tục|Resume)$/));
    if (scenario.checkpoint === 'reader') await until(() => button(/^(Quay lại thư viện|Back to library)$/));
    if (scenario.checkpoint.endsWith('error')) await until(() => document.querySelector('[role="alert"]'));
    if (scenario.checkpoint === 'shelf') await until(() => button(/^(Mở|Open) (Một buổi sáng|A quiet morning)/));
    if (scenario.checkpoint === 'empty') await until(() => /Hoặc kéo sách, tài liệu từ Finder|Or drag books and documents from Finder/.test(document.body.textContent ?? ''));
    announce({ scenario: scenario.id, status: 'ready' });
  } catch { announce({ scenario: scenario.id, status: 'failed', error: `Scenario checkpoint not reached at ${step}` }); }
}
