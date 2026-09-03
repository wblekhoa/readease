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
/* Which handler a listen() id stands for, so unlisten can take it back out.
 * The real API tears listeners down through
 * `__TAURI_EVENT_PLUGIN_INTERNALS__.unregisterListener`, not through
 * invoke - without it every effect cleanup in App threw (seen 2026-09-02). */
const listeners = new Map<number, { event: string; handler: Handler }>();
let nextCallbackId = 1;

/** Drive events from the console: __mockEmit("reading:position", {...}) */
function emit(event: string, payload: unknown) {
  for (const handler of handlers.get(event) ?? []) {
    handler({ event, id: 0, payload });
  }
  return (handlers.get(event) ?? []).length;
}

/* Real pictures, so the figure path can actually be LOOKED at: the fixture
 * used to serve a 2x2 pixel PNG, which proved the plumbing and showed the
 * owner nothing. SVG keeps the file small and stays sharp when the lightbox
 * blows it up. One landscape, one portrait - the two shapes the reader has
 * to lay out differently. */
const FIGURE_WIDE =
  "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMjAwIiBoZWlnaHQ9IjYyMCIgdmlld0JveD0iMCAwIDEyMDAgNjIwIj4KPHJlY3Qgd2lkdGg9IjEyMDAiIGhlaWdodD0iNjIwIiBmaWxsPSIjRjZGN0Y5Ii8+Cjx0ZXh0IHg9IjYwMCIgeT0iOTIiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJIZWx2ZXRpY2EsQXJpYWwiIGZvbnQtc2l6ZT0iNDQiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMyMTI2MkQiPkvhur90IG7hu5FpIHbDoCBwaMOhdCB0cmnhu4NuIG5ow6JuIHTDoGkgdHLDqm4gdG/DoG4gdGjhur8gZ2nhu5tpPC90ZXh0Pgo8dGV4dCB4PSI2MDAiIHk9IjE0MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9IkhlbHZldGljYSxBcmlhbCIgZm9udC1zaXplPSIyNCIgZmlsbD0iIzZCNzI4MCI+QmEgbeG6o25nIHPhuqNuIHBo4bqpbSBi4buVIHRy4bujIGNobyBuaGF1PC90ZXh0Pgo8ZyBmb250LWZhbWlseT0iSGVsdmV0aWNhLEFyaWFsIj4KPHJlY3QgeD0iODAiIHk9IjIxMCIgd2lkdGg9IjMyMCIgaGVpZ2h0PSIzMDAiIHJ4PSIyNCIgZmlsbD0iI0ZGRkZGRiIgc3Ryb2tlPSIjQzhDRkQ2IiBzdHJva2Utd2lkdGg9IjIiLz4KPGNpcmNsZSBjeD0iMTQwIiBjeT0iMjcwIiByPSIyMiIgZmlsbD0iI0Q0MjUyNSIvPgo8dGV4dCB4PSIxMTIiIHk9IjM0MCIgZm9udC1zaXplPSIzMCIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzIxMjYyRCI+VHJ1ZSBTZWFyY2g8L3RleHQ+Cjx0ZXh0IHg9IjExMiIgeT0iMzg0IiBmb250LXNpemU9IjIxIiBmaWxsPSIjNkI3MjgwIj5Uw6xtIMSRw7puZyBuZ8aw4budaSw8L3RleHQ+Cjx0ZXh0IHg9IjExMiIgeT0iNDE0IiBmb250LXNpemU9IjIxIiBmaWxsPSIjNkI3MjgwIj5raMO0bmcgY2jhu4kgxJHDum5nIGjhu5Mgc8ahLjwvdGV4dD4KPHJlY3QgeD0iNDQwIiB5PSIyMTAiIHdpZHRoPSIzMjAiIGhlaWdodD0iMzAwIiByeD0iMjQiIGZpbGw9IiNGRkZGRkYiIHN0cm9rZT0iI0M4Q0ZENiIgc3Ryb2tlLXdpZHRoPSIyIi8+CjxjaXJjbGUgY3g9IjUwMCIgY3k9IjI3MCIgcj0iMjIiIGZpbGw9IiMxMTlBRDUiLz4KPHRleHQgeD0iNDcyIiB5PSIzNDAiIGZvbnQtc2l6ZT0iMzAiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMyMTI2MkQiPlRocml2ZTwvdGV4dD4KPHRleHQgeD0iNDcyIiB5PSIzODQiIGZvbnQtc2l6ZT0iMjEiIGZpbGw9IiM2QjcyODAiPkdp4buvIGNow6JuIGLhurFuZyBs4buZIHRyw6xuaDwvdGV4dD4KPHRleHQgeD0iNDcyIiB5PSI0MTQiIGZvbnQtc2l6ZT0iMjEiIGZpbGw9IiM2QjcyODAiPnBow6F0IHRyaeG7g24gcsO1IHLDoG5nLjwvdGV4dD4KPHJlY3QgeD0iODAwIiB5PSIyMTAiIHdpZHRoPSIzMjAiIGhlaWdodD0iMzAwIiByeD0iMjQiIGZpbGw9IiNGRkZGRkYiIHN0cm9rZT0iI0M4Q0ZENiIgc3Ryb2tlLXdpZHRoPSIyIi8+CjxjaXJjbGUgY3g9Ijg2MCIgY3k9IjI3MCIgcj0iMjIiIGZpbGw9IiMyRTlFNkIiLz4KPHRleHQgeD0iODMyIiB5PSIzNDAiIGZvbnQtc2l6ZT0iMzAiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMyMTI2MkQiPlN5bnRoZXNpczwvdGV4dD4KPHRleHQgeD0iODMyIiB5PSIzODQiIGZvbnQtc2l6ZT0iMjEiIGZpbGw9IiM2QjcyODAiPlThu5VuZyBo4bujcCBk4buvIGxp4buHdSB0aMOgbmg8L3RleHQ+Cjx0ZXh0IHg9IjgzMiIgeT0iNDE0IiBmb250LXNpemU9IjIxIiBmaWxsPSIjNkI3MjgwIj5xdXnhur90IMSR4buLbmggdHV54buDbiBk4bulbmcuPC90ZXh0Pgo8L2c+CjxwYXRoIGQ9Ik00MDAgMzYwIEg0NDAgTTc2MCAzNjAgSDgwMCIgc3Ryb2tlPSIjQzhDRkQ2IiBzdHJva2Utd2lkdGg9IjMiLz4KPC9zdmc+";

const FIGURE_TALL =
  "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2MjAiIGhlaWdodD0iOTAwIiB2aWV3Qm94PSIwIDAgNjIwIDkwMCI+CjxyZWN0IHdpZHRoPSI2MjAiIGhlaWdodD0iOTAwIiBmaWxsPSIjRkZGRkZGIi8+CjxyZWN0IHg9IjAiIHk9IjAiIHdpZHRoPSI2MjAiIGhlaWdodD0iMTIwIiBmaWxsPSIjMjEyNjJEIi8+Cjx0ZXh0IHg9IjQwIiB5PSI3NiIgZm9udC1mYW1pbHk9IkhlbHZldGljYSxBcmlhbCIgZm9udC1zaXplPSIzNCIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI0ZGRkZGRiI+SMOsbmggZOG7jWMgLSB0aOG7rSBraHVuZyBjYW88L3RleHQ+CjxnIGZvbnQtZmFtaWx5PSJIZWx2ZXRpY2EsQXJpYWwiPgo8dGV4dCB4PSI0MCIgeT0iMTkwIiBmb250LXNpemU9IjI0IiBmaWxsPSIjNkI3MjgwIj5N4bupYyDEkeG7mSBow6BpIGzDsm5nIHRoZW8gbsSDbTwvdGV4dD4KPGcgZmlsbD0iI0Q0MjUyNSI+CjxyZWN0IHg9IjYwIiB5PSIzMDAiIHdpZHRoPSI3MCIgaGVpZ2h0PSI0MjAiIHJ4PSI4Ii8+CjxyZWN0IHg9IjE2MCIgeT0iMjQwIiB3aWR0aD0iNzAiIGhlaWdodD0iNDgwIiByeD0iOCIvPgo8cmVjdCB4PSIyNjAiIHk9IjM4MCIgd2lkdGg9IjcwIiBoZWlnaHQ9IjM0MCIgcng9IjgiLz4KPHJlY3QgeD0iMzYwIiB5PSIyMDAiIHdpZHRoPSI3MCIgaGVpZ2h0PSI1MjAiIHJ4PSI4Ii8+CjxyZWN0IHg9IjQ2MCIgeT0iMTUwIiB3aWR0aD0iNzAiIGhlaWdodD0iNTcwIiByeD0iOCIvPgo8L2c+CjxwYXRoIGQ9Ik00MCA3MjAgSDU4MCIgc3Ryb2tlPSIjQzhDRkQ2IiBzdHJva2Utd2lkdGg9IjMiLz4KPGcgZm9udC1zaXplPSIyMCIgZmlsbD0iIzZCNzI4MCI+Cjx0ZXh0IHg9IjcyIiB5PSI3NTYiPjIwMjE8L3RleHQ+PHRleHQgeD0iMTcyIiB5PSI3NTYiPjIwMjI8L3RleHQ+PHRleHQgeD0iMjcyIiB5PSI3NTYiPjIwMjM8L3RleHQ+Cjx0ZXh0IHg9IjM3MiIgeT0iNzU2Ij4yMDI0PC90ZXh0Pjx0ZXh0IHg9IjQ3MiIgeT0iNzU2Ij4yMDI1PC90ZXh0Pgo8L2c+Cjx0ZXh0IHg9IjQwIiB5PSI4NDAiIGZvbnQtc2l6ZT0iMjAiIGZpbGw9IiM2QjcyODAiPuG6om5oIGNhbyBoxqFuIGtodW5nIHPhur0gYuG7iyBnaeG7m2kgaOG6oW4gNDZ2aCwgYuG6pW0gxJHhu4MgeGVtIMSR4bunLjwvdGV4dD4KPC9nPgo8L3N2Zz4=";

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

/** Where the pictures sit. Chapter 1 gets one after a paragraph, chapter 2 one
 * BEFORE its first - both placements the reader supports, so both get looked
 * at rather than only the one that happened to be wired. */
const FIGURES: Record<number, Array<Record<string, unknown>>> = {
  1: [
    {
      id: "fig-wide",
      anchor_segment_id: "ch-1-seg-3",
      placement: "after",
      alt: "Ba mảng sản phẩm: True Search, Thrive và Synthesis",
      number: 1,
      alt_is_generic: false,
    },
  ],
  2: [
    {
      id: "fig-tall",
      anchor_segment_id: "ch-2-seg-0",
      placement: "before",
      alt: "Image",
      number: 1,
      alt_is_generic: true,
    },
  ],
};

const FIGURE_DATA: Record<string, string> = {
  "fig-wide": FIGURE_WIDE,
  "fig-tall": FIGURE_TALL,
};

const BOOK = {
  id: "book-ux",
  title: "Universal Principles of UX",
  chapters: CHAPTER_NAMES.map((title, chapterIndex) => ({
    id: `ch-${chapterIndex}`,
    title,
    figures: FIGURES[chapterIndex] ?? [],
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
    progress_ratio: 0.42,
    progress_chapter: "Chương 2",
    chapters: BOOK.chapters.length,
    size_bytes: 9_512_000,
    imported_at: "2026-08-28T09:12:00Z",
  },
  {
    id: "book-two",
    title: "Thiết kế cho người đọc vội",
    source_format: "pdf",
    segment_id: null,
    progress_ratio: null,
    progress_chapter: null,
    chapters: 12,
    size_bytes: 2_310_000,
    imported_at: "2026-08-30T15:40:00Z",
  },
  {
    id: "book-three",
    title: "Đừng bắt tôi phải suy nghĩ! — Tái bản: Một cách tiếp cận bằng lẽ thường đối với usability trên Web",
    source_format: "epub",
    segment_id: "ch-0-seg-1",
    progress_ratio: 0.08,
    progress_chapter: "Chương 1",
    chapters: 26,
    size_bytes: 25_200_000,
    imported_at: "2026-08-26T08:00:00Z",
  },
  {
    id: "book-four",
    title: "The User Experience Team of One",
    source_format: "epub",
    segment_id: null,
    progress_ratio: null,
    progress_chapter: null,
    chapters: 23,
    size_bytes: 45_900_000,
    imported_at: "2026-09-02T10:20:00Z",
  },
];

/* Two drawn covers so the shelf can be LOOKED at with real proportions; the
 * other two books answer null and show the typographic placeholder. */
function coverSvg(top: string, bottom: string, fill: string, ink: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="900" viewBox="0 0 600 900">
<rect width="600" height="900" fill="${fill}"/>
<rect x="0" y="0" width="600" height="300" fill="${ink}" opacity="0.12"/>
<rect x="60" y="360" width="480" height="6" fill="${ink}"/>
<text x="60" y="440" font-family="Helvetica,Arial" font-size="56" font-weight="700" fill="${ink}">${top}</text>
<text x="60" y="510" font-family="Helvetica,Arial" font-size="56" font-weight="700" fill="${ink}">${bottom}</text>
<text x="60" y="820" font-family="Helvetica,Arial" font-size="26" fill="${ink}" opacity="0.7">READEASE · MOCK</text>
</svg>`;
  return btoa(unescape(encodeURIComponent(svg)));
}
const COVERS: Record<string, string> = {
  "book-ux": coverSvg("Universal", "Principles", "#E8DCC8", "#2B2118"),
  "book-four": coverSvg("Team", "of One", "#1F3A5F", "#F4F1EA"),
};

const VOICES = [
  { id: "Minh Đức", label: "Minh Đức - Nam · Bắc · Phong cách tin tức" },
  { id: "Thu Hà", label: "Thu Hà - Nữ · Bắc · Kể chuyện" },
];

/** Stands in for settings.json - including the two keys carried over from the
 * Qt shell, so "it remembers my voice" can be looked at, not just believed. */
const SETTINGS: Record<string, string | number | null> = {
  tauri_selection_shortcut: "shift+super+t",
  ui_language: "vi",
  voice: "Thu Hà",
  rate: 1.25,
};

/* Apple Books, as the panel sees it: one already in the library, one to
 * import, one purchased (encrypted), one without highlights. Import and
 * sync mutate the shelf so the flow can be watched end to end. */
const APPLE_SHELF: Array<{ asset_id: string; title: string; status: string; book_id: string | null; paired_title: string | null; highlights: number }> = [
  { asset_id: "ab-1", title: "Universal Principles of UX", status: "linked", book_id: "book-ux", paired_title: "Universal Principles of UX", highlights: 3 },
  { asset_id: "ab-2", title: "Thiên Nga Đen", status: "importable", book_id: null, paired_title: null, highlights: 5 },
  { asset_id: "ab-3", title: "The Daily Stoic", status: "encrypted", book_id: null, paired_title: null, highlights: 1 },
  { asset_id: "ab-4", title: "101 Essays That Will Change The Way You Think", status: "importable", book_id: null, paired_title: null, highlights: 0 },
  { asset_id: "ab-5", title: "Đừng bắt tôi phải suy nghĩ! Tái bản", status: "linked", book_id: "book-three", paired_title: "Đừng bắt tôi phải suy nghĩ! — Tái bản: Một cách tiếp cận bằng lẽ thường đối với usability trên Web", highlights: 0 },
  { asset_id: "ab-6", title: "The Ultimate Guide to iPhone Photography", status: "too_large", book_id: null, paired_title: null, highlights: 3 },
  { asset_id: "ab-7", title: "The Designer's Guide to Figma", status: "importable", book_id: null, paired_title: null, highlights: 0 },
];
const ANNOTATIONS = [
  { id: "applebooks:1", segment_id: "ch-1-seg-1", selected_text: "những phương án đầu tiên của họ đều nhanh chóng chìm vào quên lãng", note: "Đúng với dự án năm ngoái.", style: 3 },
  { id: "applebooks:2", segment_id: "ch-1-seg-3", selected_text: "số ứng dụng di động đã lên đến gần mười triệu", note: null, style: 1 },
];

function engineRequest(method: string, params: Record<string, unknown> = {}): unknown {
  switch (method) {
    case "applebooks.shelf":
      return { books: APPLE_SHELF };
    case "applebooks.import": {
      const row = APPLE_SHELF.find((b) => b.asset_id === params.asset_id);
      if (!row) throw new Error("applebooks.import failed: book_gone");
      if (row.status === "encrypted") throw new Error("applebooks.import failed: encrypted");
      const id = `imported-${row.asset_id}`;
      row.status = "linked"; row.book_id = id; row.paired_title = row.title;
      LIBRARY.push({ id, title: row.title, source_format: "epub", segment_id: null, progress_ratio: null, progress_chapter: null, chapters: 9, size_bytes: 1_400_000, imported_at: new Date().toISOString() });
      return { book_id: id, title: row.title, was_existing: false };
    }
    case "applebooks.sync_notes": {
      const row = APPLE_SHELF.find((b) => b.asset_id === params.asset_id);
      if (!row?.book_id) throw new Error("applebooks.sync_notes failed: not_in_library");
      return { book_id: row.book_id, matched: Math.max(0, row.highlights - 1), unmatched: row.highlights ? 1 : 0, skipped: 2 };
    }
    case "library.list":
      return { books: LIBRARY };
    case "book.open":
      return { book: BOOK, annotations: ANNOTATIONS, progress: { segment_id: "ch-1-seg-2" } };
    case "book.cover": {
      const data = COVERS[String(params.book_id)];
      return data ? { media_type: "image/svg+xml", data } : { media_type: null, data: null };
    }
    case "book.figure":
      return {
        media_type: "image/svg+xml",
        data: FIGURE_DATA[String(params.figure_id)] ?? FIGURE_WIDE,
      };
    case "model.status":
      return { ready: true, precision: "fp32", installed: { fp32: 1 } };
    case "config.get":
      // Per KEY, not one answer for everything: answering "vi" to the
      // shortcut key made the keycaps render "VI" and looked like an app bug.
      return { value: SETTINGS[String(params.key)] ?? null };
    case "config.set":
      SETTINGS[String(params.key)] = params.value as string | number;
      return { saved: true };
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
    const listenerId = nextCallbackId++;
    if (handler) {
      handlers.set(event, [...(handlers.get(event) ?? []), handler]);
      listeners.set(listenerId, { event, handler });
    }
    return Promise.resolve(listenerId);
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
window.__TAURI_EVENT_PLUGIN_INTERNALS__ = {
  unregisterListener(event: string, listenerId: number) {
    const entry = listeners.get(listenerId);
    if (!entry) return;
    listeners.delete(listenerId);
    handlers.set(event, (handlers.get(event) ?? []).filter((h) => h !== entry.handler));
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
