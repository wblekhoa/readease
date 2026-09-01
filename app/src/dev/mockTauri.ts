/** A fake Tauri host, so the UI can be looked at in a plain browser.
 *
 * Every screen but this one could already be checked in the preview; the
 * reader could not, because it needs a book, and a book needs the engine.
 * That made the one screen with the most layout in it the only screen nobody
 * could see. This installs the same seam Tauri uses - the invoke bridge on
 * `window` - and answers with fixtures.
 *
 * Dev only, and only when no real Tauri host is present. `pnpm build` must
 * not carry a byte of it: the import that pulls it in is behind
 * `import.meta.env.DEV`, and the build check greps the bundle to prove it.
 */

type Handler = (event: { event: string; id: number; payload: unknown }) => void;

const handlers = new Map<string, Handler[]>();
const callbacks = new Map<number, Handler>();
let nextCallbackId = 1;

/** Drive events from the console: __mockEmit("reading:position", {...}) */
function emit(event: string, payload: unknown) {
  for (const handler of handlers.get(event) ?? []) {
    handler({ event, id: 0, payload });
  }
  return (handlers.get(event) ?? []).length;
}

// A 2x2 PNG, enough for the figure path to fetch, decode and open.
const TINY_PNG =
  "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAHElEQVQI12P4z8Dwn4GBgYGJgYGB4T8DAwMDAwANHQEDrDoJ0gAAAABJRU5ErkJggg==";

const PARAGRAPHS = [
  "Năm nào họ cũng chú ý rất tốt đến tính dễ sử dụng (usability), nội dung và chức năng, nhưng lại bỏ qua phần giá trị cộng thêm có thể khiến một tương tác trở nên riêng biệt và đáng nhớ.",
  "Vì thế, những phương án đầu tiên của họ đều nhanh chóng chìm vào quên lãng. Chỉ khi học cách nhìn vấn đề từ một góc khác, họ mới tạo ra được điều đặc biệt.",
  "Đừng hiểu lầm ý tôi. Trước hết, sản phẩm phải hoạt động. Nếu không, bạn chỉ đang tô điểm bề ngoài cho một thứ vốn dĩ tệ hại. Nhưng hoạt động được mới chỉ là điều kiện tối thiểu để cạnh tranh.",
  "Yêu cầu ấy có thể từng là đủ vào cuối thập niên 1990 và đầu những năm 2000, khi người dùng chỉ có vài lựa chọn. Còn ngày nay, số ứng dụng di động đã lên đến gần mười triệu.",
  "Một sản phẩm dùng được nhưng chẳng để lại ấn tượng sẽ khó có chỗ đứng.",
  "Vậy một trải nghiệm tích cực và đáng nhớ được tạo nên từ đâu? Có hai yếu tố.",
  "Thứ nhất, ta cần tạo ra những tính năng mà người dùng không ngờ tới, như khi Steve Jobs giới thiệu thao tác chụm hai ngón tay để thu phóng tại một sự kiện Apple năm 2007. Cả khán phòng khi ấy đã ồ lên.",
  "Thứ hai, ta cần giúp người dùng bước vào trạng thái dòng chảy (flow), khái niệm được nhà tâm lý học Mihály Csíkszentmihályi mô tả là sự đắm mình hoàn toàn.",
];

const CHAPTER_NAMES = [
  "Bìa sách",
  "Các nguyên tắc phổ quát của trải nghiệm người dùng",
  "Chương 3",
  "Chương 4",
  ...Array.from({ length: 22 }, (_, index) => String(index + 1).padStart(2, "0")),
];

const BOOK = {
  id: "book-ux",
  title: "Universal Principles of UX",
  chapters: CHAPTER_NAMES.map((title, chapterIndex) => ({
    id: `ch-${chapterIndex}`,
    title,
    figures:
      chapterIndex === 1
        ? [
            {
              id: "fig-1",
              anchor_segment_id: "ch-1-seg-3",
              placement: "after",
              alt: "Sơ đồ ba khối nội dung",
            },
          ]
        : [],
    segments: [
      {
        id: `ch-${chapterIndex}-seg-h`,
        text: title,
        kind: "heading",
      },
      ...PARAGRAPHS.slice(0, chapterIndex === 1 ? 8 : 4).map((text, index) => ({
        id: `ch-${chapterIndex}-seg-${index}`,
        text,
        kind: "paragraph",
      })),
    ],
  })),
};

const LIBRARY = [
  {
    id: "book-ux",
    title: "Universal Principles of UX",
    source_format: "epub",
    segment_id: "ch-1-seg-2",
    chapters: BOOK.chapters.length,
    size_bytes: 9_512_000,
    imported_at: "2026-08-28T09:12:00Z",
  },
  {
    id: "book-two",
    title: "Thiết kế cho người đọc vội",
    source_format: "pdf",
    segment_id: null,
    chapters: 12,
    size_bytes: 2_310_000,
    imported_at: "2026-08-30T15:40:00Z",
  },
];

const VOICES = [
  { id: "Minh Đức", label: "Minh Đức - Nam · Bắc · Phong cách tin tức" },
  { id: "Thu Hà", label: "Thu Hà - Nữ · Bắc · Kể chuyện" },
];

function engineRequest(method: string, params: Record<string, unknown> = {}): unknown {
  switch (method) {
    case "library.list":
      return { books: LIBRARY };
    case "book.open":
      return { book: BOOK, progress: { segment_id: "ch-1-seg-2" } };
    case "book.figure":
      return { media_type: "image/png", data: TINY_PNG };
    case "model.status":
      return { ready: true, precision: "fp32", installed: { fp32: 1 } };
    case "config.get":
      // Per KEY, not one answer for everything: answering "vi" to the
      // shortcut key made the keycaps render "VI" and looked like an app bug.
      return {
        value:
          params.key === "tauri_selection_shortcut"
            ? "shift+super+t"
            : params.key === "ui_language"
              ? "vi"
              : null,
      };
    case "notes.books":
      return { books: [] };
    default:
      return {};
  }
}

function invoke(command: string, args: Record<string, unknown> = {}): Promise<unknown> {
  if (command === "plugin:event|listen") {
    const handler = callbacks.get(args.handler as number);
    const event = args.event as string;
    if (handler) handlers.set(event, [...(handlers.get(event) ?? []), handler]);
    return Promise.resolve(nextCallbackId++);
  }
  if (command === "plugin:event|unlisten") return Promise.resolve();
  if (command === "engine_voices") return Promise.resolve(VOICES);
  if (command === "engine_request") {
    return Promise.resolve({
      result: engineRequest(
        args.method as string,
        (args.params as Record<string, unknown>) ?? {},
      ),
    });
  }
  return Promise.resolve({ result: {} });
}

window.__TAURI_INTERNALS__ = {
  invoke,
  transformCallback(callback: Handler, _once = false) {
    const id = nextCallbackId++;
    callbacks.set(id, callback);
    return id;
  },
  unregisterCallback(id: number) {
    callbacks.delete(id);
  },
};
window.__mockEmit = emit;

declare global {
  interface Window {
    __TAURI_INTERNALS__: Record<string, unknown>;
    __mockEmit: (event: string, payload: unknown) => number;
  }
}

export {};
