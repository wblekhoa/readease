// RE-PG-001, RE-PG-004: the preview, its audit and the docs consume this one registry.
import registry from './playgroundStates.json' with { type: 'json' };

export type Scenario = { id: string; label: { vi: string; en: string }; query: Record<string, string | undefined>; steps: string[]; checkpoint: string };
export const scenarios: Scenario[] = registry.states;
export const locales = ['vi', 'en'] as const;
export const themes = ['light', 'dark'] as const;
export const viewports = [{ width: 960, height: 600 }, { width: 1280, height: 820 }];
export type Cell = { id: string; scenario: string; locale: string; theme: string; width: number; height: number };
export function matrix(): Cell[] {
  return scenarios.flatMap(s => locales.flatMap(locale => themes.flatMap(theme => viewports.map(v => ({
    id: `${s.id}/${locale}/${theme}/${v.width}x${v.height}`, scenario: s.id, locale, theme, ...v,
  })))));
}
export function previewUrl(cell: Cell): string {
  const scenario = scenarios.find(s => s.id === cell.scenario);
  if (!scenario || !locales.includes(cell.locale as 'vi') || !themes.includes(cell.theme as 'light')) throw new Error('Unknown preview cell');
  const query = new URLSearchParams({ pilot: scenario.id, locale: cell.locale, theme: cell.theme, viewport: `${cell.width}x${cell.height}` });
  for (const [key, value] of Object.entries(scenario.query)) if (value) query.set(key, value);
  return '/?' + query;
}
export function fixtureCopy(locale: string) {
  return locale === 'en' ? {
    title: 'A quiet morning — synthetic sample', second: 'Notes for tomorrow — synthetic sample',
    chapters: ['A quiet morning', 'A small plan'],
    paragraphs: ['The window opens onto a small garden. This paragraph was written for the preview.', 'We leave enough space between ideas to read at a comfortable pace.', 'A short note helps us return to the same thought tomorrow.', 'This is synthetic content. No personal books or audio services are involved.'],
  } : {
    title: 'Một buổi sáng yên — tài liệu mô phỏng', second: 'Ghi chú ngày mai — tài liệu mô phỏng',
    chapters: ['Buổi sáng yên', 'Một kế hoạch nhỏ'],
    paragraphs: ['Cửa sổ mở ra một khu vườn nhỏ. Đoạn văn này được viết riêng cho bản xem thử.', 'Chúng ta để khoảng trống giữa các ý để đọc với nhịp độ dễ chịu.', 'Một ghi chú ngắn giúp ta trở lại đúng ý nghĩ vào ngày mai.', 'Đây là nội dung tổng hợp. Không dùng sách cá nhân hay dịch vụ tạo giọng.'],
  };
}
