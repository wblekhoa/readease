// RE-PG-001: the preview and its audit consume this one registry.
export const scenarios = [
  { id: 'library/empty', label: { vi: 'Thư viện trống', en: 'Empty library' }, query: { empty: 'library' }, steps: ['library'], checkpoint: 'empty' },
  { id: 'library/ready', label: { vi: 'Thư viện có sách', en: 'Library with books' }, query: {}, steps: ['library'], checkpoint: 'shelf' },
  { id: 'library/error', label: { vi: 'Lỗi tải thư viện', en: 'Library error' }, query: { fail: 'library.list' }, steps: ['library'], checkpoint: 'library-error' },
  { id: 'reader/ready', label: { vi: 'Sẵn sàng đọc', en: 'Reader ready' }, query: {}, steps: ['library', 'open'], checkpoint: 'reader' },
  { id: 'reader/preparing', label: { vi: 'Chuẩn bị giọng', en: 'Preparing voice' }, query: { warm: 'hold' }, steps: ['library', 'open', 'read'], checkpoint: 'preparing' },
  { id: 'reader/playing', label: { vi: 'Đang đọc', en: 'Playing' }, query: {}, steps: ['library', 'open', 'read'], checkpoint: 'playing' },
  { id: 'reader/paused', label: { vi: 'Tạm dừng', en: 'Paused' }, query: {}, steps: ['library', 'open', 'read', 'pause'], checkpoint: 'paused' },
  { id: 'reader/error', label: { vi: 'Lỗi đọc có thể thử lại', en: 'Recoverable reading error' }, query: {}, steps: ['library', 'open', 'read'], checkpoint: 'reading-error' },
];
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
