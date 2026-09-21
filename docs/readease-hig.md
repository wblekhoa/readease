# ReadEase HIG v2 — guideline SINH ra UI

> **v2 (2026-09-01)**: nâng cấp sau khi mổ cấu trúc các design system hàng đầu. Mỗi thứ vay
> đều ghi nguồn ở §9. Hướng đã chốt: **xương Apple, hồn DOL** — pattern/nhịp HIG, màu/chữ/
> nhận diện DOL DS-Token. Luật nghiệm thu: *màn không chỉ ra được pattern gốc ⇒ thiếu pattern
> (bổ sung vào đây trước) hoặc màn sai.*
> Cấu trúc tài liệu này đã được promote thành chuẩn canon DOL: `DOL-DS-token/design-guideline/ds-guideline/generative-guideline.md` (01/09) — tài liệu này là bản thực thi sống đầu tiên của chuẩn đó.

## 0. Cách đọc — mô hình 4 mặt (vay Carbon)

Mỗi pattern được tả trên 4 mặt: **Usage** (khi nào/không) · **Anatomy** (bộ phận có tên —
diệt mơ hồ "token này áp vào đâu") · **Behavior** (trạng thái + bàn phím) · **Content**
(chữ viết gì). Code là mặt thứ 5, sống ở `app/src/ui/` — doc này KHÔNG lặp code.

## 1. Chọn pattern theo ý định (vay HIG: tổ chức theo việc-người-dùng-làm)

| Người dùng cần… | Pattern | Ở đâu trong app |
|---|---|---|
| Duyệt danh sách mục, mỗi mục có hành động | `ListRow` | Lịch sử Quét đọc, mục lục sách |
| Điều hướng cấp app + danh sách nơi chốn trong sách (mục lục · ghi chú · tìm) | `SideColumn` (§3.16) — cột trái 240 thật trong layout, thu/mở, nội dung theo ngữ cảnh | Mọi màn: Thư viện · Dán · Quét · Chuyển ghi chú · Đang đọc; trong sách: Mục lục / Ghi chú / Tìm |
| Chọn một CUỐN SÁCH trong nhiều cuốn | `BookGrid` + `BookCard` + `BookCover` | Thư viện (kệ bìa) |
| Xem/chọn trong một nhóm thiết lập | `GroupedSection`+`GroupedRow` | Panel Chất lượng, danh sách xem-trước ghi chú |
| Bắt đầu khi chưa có gì | `EmptyState` | Thư viện rỗng |
| Định hướng vùng làm việc | `RailItem` trong `SideColumn` (§3.16; trước 16/09: `AppTabs` trong `Toolbar`) | Cột bên |
| Điều khiển việc đang chạy | PlayerBar | Footer đọc |
| Xác nhận huỷ tại chỗ | ConfirmInline | Xoá sách (trailing của ListRow) |
| Kéo dữ liệu từ app khác, một chiều | Sheet `Surface radius="sheet"` + `BookTile` (§3.12) | Từ Apple Books |
| Tuỳ chọn phụ sau một hành động | `MenuButton` (icon → danh sách ngắn, mục đầu = mặc định) | Nhập/đồng bộ trong sheet Apple Books |
| Bật/tắt một mục vào danh sách | `Switch` (role=switch, ô gạt) | Chọn giọng cho danh sách đổi nhanh |
| Nút nhỏ nằm giữa dòng chữ | `InlineIconButton` (co theo cỡ chữ, tự chặn click của đoạn) | Icon ghi chú trong đoạn |
| Danh sách bất kỳ | `GroupedSection` + `GroupedRow` (kẻ chấm, không thẻ) | Cài đặt · Chất lượng · Transfer · danh sách giọng |
| Xin quyền hệ thống | PermissionCard | Quét đọc |
| Mời chọn cách đọc khi máy chưa đọc được gì (KHÔNG chặn — "Vào thư viện" luôn bấm được, chủ 15/09) | First-run = thân sheet Giọng đọc & mô hình trong một cột giữa màn | Màn đầu tiên |
| Thống kê máy đọc được gì, bằng gì, và thêm bớt (mô hình / khoá API) | Sheet `Surface radius="sheet"` giữa màn, mỗi ngôn ngữ một `GroupedSection`: hàng đầu = trạng thái (chấm + "Đọc được/Chưa đọc được · bằng gì"), rồi hàng mô hình, rồi nhóm khoá API | Nút bánh răng trang chủ · nút "Quản lý…" trong bảng giọng đọc |
| Chọn ngôn ngữ đọc trước rồi mới tới giọng; gợi ý khi nội dung là tiếng khác | `SegmentedControl` Tiếng Việt/Tiếng Anh + `SuggestionDot` trên tuỳ chọn của ngôn ngữ nội dung + `Notice tone="info" action=` một nút (gợi ý, không tự đổi) | Bảng Cài đặt giọng đọc |

## 2. Bảng trạng thái chuẩn (vay M3: state layer — một lớp phủ, không đổi bản thể)

Mọi bề mặt tương tác có ĐỦ 7 trạng thái, cùng một công thức phủ:

| Trạng thái | Công thức (token) |
|---|---|
| default | như khai báo |
| hover | phủ `wash` = neutral-alpha **na10** (chủ 06/09: na05 "hơi nhạt"; **đảo lại** quyết định 01/09 — xem ghi chú dưới) |
| focus-visible | **một chỗ duy nhất**: outline 2px `--color-focus` (info b60) trong `index.css` — KHÔNG bao giờ brand |
| pressed | control trung tính: phủ `press` = neutral-alpha **na20** (cùng thang hover, **luôn** nặng hơn một bậc — hover đổi thì press đổi theo) · nút primary đã có nền brand thì đậm xuống `brand-700` — phủ xám lên nền đỏ chỉ làm bẩn màu |
| disabled | chữ luôn `ink-faint`, **không bao giờ opacity**; control có viền giữ nguyên viền `edge-strong`, control không viền vẫn không viền. Ngược lại: **chữ có nghĩa thì không bao giờ `ink-faint`** — gợi ý trong menu ("Đang mở", "⌃⌘S"), "Đang dùng" cạnh giọng, dòng dữ kiện của hàng, nhắc "bấm để tới" đều `ink-mute` (17/09, chủ: "status mờ quá"; faint đo 1,76:1 trên nền tối). Faint chỉ còn cho glyph trang trí, dấu "+" giữa phím, lựa chọn chưa chọn |
| loading | chữ đổi sang trạng thái ("Đang nhập sách…", "Đang chuẩn bị giọng đọc…") — không spinner mồ côi |
| error | `Notice tone=error` màu **danger**, nói-gì-sai + làm-gì-tiếp |

**Do/Don't sống của bảng này** (vòng audit 01/09, đo bằng số ở cả hai theme):
- ✗ **hai công thức focus.** Control từng `outline-none` rồi tự đổi màu viền khi focus; ở control
  không viền, việc thêm viền lúc focus **đẩy nhãn lệch 1px** mỗi lần tab tới. Nay chỉ còn vòng
  outline dùng chung — đo lại: outline `2px solid rgb(111,138,226)`, viền đứng yên.
- ✗ **disabled bằng opacity.** Làm mờ control có viền thì mờ luôn viền của nó. Đổi sang ink-faint.
- ✗ **viền disabled dùng `edge`.** Đo được `edge` **1.00:1** so với nền desk sáng — đúng bằng màu
  nền, tức vô hình; `edge-strong` cho 1.24 (sáng) / 1.76 (tối): vẫn im, nhưng còn thấy dáng nút.
- ✗ **danger dùng bậc `primary`.** Đo 3.12:1 (sáng) và 3.72:1 (tối) — dưới AA cho chữ 14px. Đổi
  sang `--text-color-danger-bold`. **Đo lại 01/09 sau khi desk chuyển sang trắng: 5.14:1 ở CẢ hai
  theme** khi chữ danger nằm thẳng trên desk. Ghi chú cũ nói 4.06 (dưới AA) — con số đó đo trên
  desk **xám n20** đã bị thay; nền trắng tự nâng tương phản, và ca dưới-AA đó không còn tồn tại.
  *Bài học: số đo tương phản gắn với MỘT nền cụ thể — đổi nền là phải đo lại, đừng chép số cũ.*
- **Hover đã đi na10 → na05 → na10** (01/09 rồi 06/09, cùng một người). Ghi lại vì đây là **đảo chiều**,
  không phải trôi: na05 đọc như tiếng thì thầm trên mặt bàn trắng, nơi hover phải tự nói "đây là nút" mà
  không có gì đỡ ngoài giấy. Thang alpha **không có bậc nào giữa hai cái đó**, nên "đậm một xíu" chỉ có
  thể là na10. *Bài học: đừng chép lại một con số cũ như thể nó là chân lý — chép cả lý do, rồi đo lại
  trên nền hiện tại.*
- **Trên vật liệu (cột bên, 20/09) "đang chọn" = phủ `tint` na20, một bậc trên hover** — không phải `band` đục:
  fill đục trên kính là tấm che, và chọn = hover cùng na10 thì mục đang chọn và mục bên cạnh đang rê chuột trùng màu (§3.16).
- **Press luôn là một bậc TRÊN hover, dù hover là bao nhiêu**: ngón tay đang nhấn phải nặng hơn con trỏ
  lướt qua, và chỉ nặng trong lúc giữ. Nâng hover mà quên nâng press là lặng lẽ xoá mất trạng thái nhấn.
- **Ô nhập chữ và select đeo vòng focus cả khi bấm chuột** (nút thì không) — đó là hành vi của
  `:focus-visible` với trường nhập liệu, không phải lỗi. Giữ vòng đó, nhưng ô nhập nhiều dòng
  vẽ vòng **đè lên viền của chính nó** (`outline-offset: -1px`): một đường xanh gọn như ô văn
  bản macOS, thay vì viền xám + khe + vòng xanh đọc ra kiểu form web (nhìn tận mắt 01/09).

## 3. Pattern catalog

### 3.1 `ListRow`
- **Usage**: mục trong danh sách có thể mở + có hành động phụ. KHÔNG dùng cho cặp nhãn-control (đó là `GroupedRow`). KHÔNG dùng cho sách trong thư viện nữa — sách là VẬT có bìa, đi kệ (§3.11).
- **Anatomy**: `leading` (glyph 16, ink-mute) · `body` (title 14 semibold + chip 12 · subtitle 12 mute một dòng truncate) · `trailing` (accessory **nằm trong** mặt hover).
- **Behavior**: cả hàng = một mặt hover 2xl; click body = hành động chính; accessory lộ khi hover/focus; focus ring quanh body.
- **Content**: subtitle = dữ kiện phân biệt thật, nối bằng " · " (vd "108 chương · 9,1 MB · Nhập 31/08/2026 · Đang đọc dở"); trường thiếu thì BỎ, không bao giờ chữ "undefined".
- **Do/Don't sống**: ✗ accessory thò ngoài hàng (chủ bắt 01/09) · ✗ hàng một tầng khi có metadata · ✗ block bao ngoài danh sách (hàng tự mang cấu trúc rồi thì hộp là vỏ thừa — vòng đời chrome, 01/09).

### 3.2 `GroupedSection` + `GroupedRow`
- **Usage**: nhóm thiết lập/lựa chọn liên quan — hình thái System Settings. KHÔNG dùng card riêng từng hàng (slop-03).
- **`roomy`** (02/09): sheet liệt kê mục có hành động (Apple Books) thở hơn nhóm thiết lập — hàng
  `px-5 py-3.5`, gap 16/12, tiêu đề nhóm cách 10 px; mặc định không đổi cho panel cài đặt.
- **Anatomy**: header 12 uppercase mute (tuỳ chọn) · một mặt giấy 2xl · hairline `edge` giữa các hàng · mỗi hàng: title 14 medium + subtitle 12 mute | trailing controls.
- **Header là NHÃN hay là TÊN** (`heading="label" | "name"`, 17/09): nhãn nhóm ("Giọng", "Mô hình & API", "Đang đọc")
  = IN HOA tracking-wide; **tên** — tên chương trong danh sách ghi chú — là nội dung, viết như tác giả viết: 13 px
  semibold `ink-mute`, xuống dòng được (chủ 17/09 trước "CÁC NGUYÊN TẮC PHỔ QUÁT CỦA TRẢI NGHIỆM NGƯỜI DÙNG" hai dòng
  in hoa: "Uppercase không đẹp"). Chữ in hoa chỉ chịu được vài từ; một tên chương tiếng Việt thì không.
- **Behavior**: hàng không hover trừ khi bấm được cả hàng; control bên trong tự mang trạng thái.
- **Content**: subtitle chỉ khi mang tin ("Đang dùng", "Chưa tải") — không lặp lại title.

### 3.3 `EmptyState`
- **Usage**: vùng nội dung trống lần đầu.
- **Anatomy**: cụm lối-vào đứng GIỮA chỗ nội dung sẽ nằm · ràng buộc (nếu có) đứng DƯỚI lựa chọn nó ràng buộc.
- **Don't sống**: ✗ hộp trống + nút parked dưới đáy (bản Qt cũ) · ✗ câu cảnh báo trước khi người dùng làm gì.

### 3.4 `Toolbar` (+ `AppTabs`, đã rời sang cột bên 16/09)
- **Usage**: hàng đầu cửa sổ, một hàng duy nhất cao h-9. Điều hướng dẫn trái, hành động/ngôn ngữ theo phải.
- **Vỏ (shell) = DOL `premium-blur`, chủ opt-in 02/09** (guideline Apps `plugin-shell.md` §2/§6 +
  `plugin-footer-shell.md` §1; trước đó là `utility-flat`). Header và footer là LỚP PHỦ, trang cuộn
  BÊN DƯỚI — cách duy nhất để blur có thứ để mờ (Rule 1 của lesson `frosted-glass-progressive-blur`:
  bar là flex-sibling của vùng cuộn thì blur vô hình). Engine = recipe canonical `gradient-blur-shell`
  (đã ship Flowsmith): **8 lớp thật** (`GradientBlur` trong patterns.tsx), bán kính nhân đôi 128→0,
  dải mask 12,5% chồng nhau → ramp liền, không "cắt ngang"; tint token (`--app-ground` 78%) đặt
  SAU stack; các lớp `pointer-events: none` (đo: điểm trong vùng ramp trả về đoạn văn/ảnh, không
  phải bar). **Inset đặt tên** (`--shell-top-h` 72 · `--shell-bottom-h` 56/0): vùng cuộn chạy dưới
  bar tự đệm nội dung bằng `shell-inset-content`; màn không cuộn bắt đầu dưới bar bằng `shell-inset`.
  **Ramp nằm TRONG bar** (`--shell-ramp` 0 — chủ chỉnh 02/09: bản 40px tràn xuống che tiêu đề
  thư viện và mép bìa); bar chừa padding mép trong (header pb-6, footer pt-4) cho dải tan hết trước mép.
  Inset không khai hai lần: ResizeObserver đo chiều cao thật của bar rồi ghi `--shell-*-h`. Bán kính/dải là hình học nên được literal
  (guideline §3.1); màu chỉ token.
- **Anatomy (AppTabs = ToggleButtonGroup *style 2*, chủ chốt 01/09 — lịch sử: component gỡ 16/09 khi điều
  hướng dọn sang `RailItem` của cột bên, §3.16)**: rãnh `rail` có viền,
  **không đệm trong** → mục đang chọn **tràn sát viền** rãnh, góc do chính rãnh cắt
  (`overflow-hidden`). Rãnh 34 nằm trong toolbar 36; mục 32 = đúng chiều cao select ngôn ngữ
  bên phải. Style 1 (viên pill nhỏ trôi trong rãnh có đệm) là bản cũ, đã thay.
- **Behavior**: mục đang chọn = nền `paper` + **shadow phân lớp của DS**
  (`--shadow-neutral-to-bot-2`: một lớp toả rộng + một lớp tiếp xúc sát) — `shadow-sm` của
  Tailwind là một nét cứng, cạnh shadow DS đọc ra như đường kẻ in dưới nút.
- **Don't**: tiêu đề app trong toolbar (macOS đã vẽ trên titlebar) · nút trùng chức năng với tab đứng cạnh (đều đã gỡ, 08/31).
- **Mở app là vào Thư viện** (chủ, 16/09: "trang mặc định của app là trang Thư Viện"): màn đầu = tab đầu
  của rãnh, đúng thứ tự CHÍNH đã xếp — sách trước, dán sau. Kệ trống tự dẫn sang Dán nội dung bằng nút của
  nó (`EmptyState` → `onPaste`), nên người chưa có sách không mất gì. Trước 16/09 app mở vào Dán nội dung.
- **Hai bậc tính năng** (chủ, 02/09: "phân chia rõ tính năng phụ và tính năng chính"): **CHÍNH** = cách
  đưa chữ tới giọng — Thư viện (sách) · Dán nội dung — nằm trong rãnh `AppTabs`, mỗi tab một glyph
  (`AppTab.icon`). **PHỤ** = công cụ quanh việc đọc — Quét đọc (đọc phần bôi đen ở app khác) · Chuyển
  ghi chú — cụm ghost có icon ở cụm phải, tách bằng vạch `bg-edge`, `aria-pressed` + `bg-wash` khi
  đang mở. Cùng ngôn ngữ glyph 16px/1.5 stroke của `ui/icons`. Rãnh vẫn nhận phím ←/→ khi giá trị đang
  ở một màn phụ (vào rãnh từ mục đầu).
- **Footer = lưới 3 cột** (trái: hint · giữa: CTA+chip hoặc transport · phải: trạng thái/lỗi), cao
  76 px như header; KHÔNG dùng absolute cho cụm giữa — nó không tạo chiều cao, footer từng bị ép còn
  40 px (chủ bắt 02/09).
- **Nút sáng/tối** (chủ, 02/09): IconButton mặt trời/mặt trăng; bấm = sang phía ngược lại của cái đang hiện,
  nhớ trong localStorage (`ui/theme.ts`); chưa chọn thì theo macOS live. Đây là nơi DUY NHẤT ghi `[data-theme]`.
  Từ 16/09 nút sống ở **chân cột bên** (§3.16) cùng bánh răng và ngôn ngữ; toolbar chỉ mang chúng khi cột thu.
- **Chọn ngôn ngữ UI** (chủ, 02/09: chỉ ở trang chủ; 16/09: ở chân cột bên, mọi màn): toolbar của một cuốn
  sách chỉ mang thứ phục vụ cuốn sách (quay lại · mục lục · ⓘ · cỡ chữ · chế độ).
- **Tiêu đề màn tính năng đứng ở toolbar, nút đổi chế độ đứng trước nó (chủ, 16/09: "title của trang tính năng… bên
  trái sẽ là nút sidebar" → rồi "trên title thì nút ở đây là nút đổi chế độ. icon sẽ ở dạng arrow swap. tuỳ vào tính
  năng và sẽ có nút khác nhau")**: ở trang chủ, cụm dẫn = [chỗ đèn 52 px khi cột thu — chỉ trong cửa sổ Tauri, trình
  duyệt không có đèn nên không chừa (`ui/host.ts`)] + **nút đổi chế độ** (`MenuButton`, icon `ArrowSwapIcon` = mũi
  tên swap dựng đứng, khác glyph ngang của Chuyển ghi chú; menu = bốn màn, màn đang mở ghi "Đang mở"; khi cột thu có
  thêm hàng "Cột bên ⌥⌘S" để mở cột — không còn nút mở cột riêng) + `h2` tên màn (đúng nhãn mục trong cột: "Thư viện",
  "Dán nội dung", "Quét đọc", "Chuyển ghi chú") — cùng chỗ và cùng cỡ với tên sách khi đang đọc. **Mỗi tính năng mang
  nút riêng ở chỗ này**: sách mang ← ▤ ghi chú ⓘ; trang chủ mang nút đổi chế độ. **Một tiêu đề cho một
  màn**: trang không lặp lại tên dưới toolbar (Thư viện bỏ "Thư viện sách", Dán bỏ "Dán nội dung để đọc", Quét bỏ
  "Quét đọc"; sheet Chuyển ghi chú giữ câu tiêu đề riêng của nó vì đó là một câu khác). Hành động của trang (Từ Apple
  Books · Mở PDF hoặc EPUB) đứng ở cụm phải của toolbar qua một slot/portal — như AA · tìm của sách — trang giữ state
  của nút, toolbar giữ chỗ.
- **Chrome ở chân cột / toolbar là ghost** (chủ 16/09: nút ngôn ngữ "theo style transparent"): `Select ghost` — không
  viền, không nền cho tới khi hover (`wash`), chữ `ink-mute` → `ink`, đứng cùng hàng với `IconButton` nên cùng độ nhẹ;
  select trong bảng cài đặt vẫn có viền + nền giấy (ở đó nó là một ô của form, không phải chrome).
- **Tab và công cụ rời toolbar (16/09)**: bốn mục (Thư viện · Dán · Quét · Chuyển ghi chú) là `RailItem` trong cột bên (§3.16), `AppTabs.tsx` gỡ; dải
  trên của cột nội dung còn lại là vùng kéo cửa sổ 52 px, mang nút mở cột + (khi cột thu) bánh răng/theme/ngôn
  ngữ, và chrome của sách khi đang đọc.
- **ⓘ cạnh tên sách (02/09, chủ)**: thông tin vị trí ("Trang 3/12" · tên chương · "Đã đọc 11%") là
  thông tin PHỤ → tooltip `Surface edge="strong"` MỘT DÒNG ("Trang 1/3 · 04 · Đã đọc 29%", không xuống
  dòng — chủ chỉnh 02/09) hiện khi hover/focus icon, KHÔNG là dòng chữ dưới trang. Lớp nổi trên nội dung
  dùng viền `strong` để đọc thành vật ở cả hai nền (`edge-field` tan trong nền tối). Chế độ
  cuộn chỉ có chương + %. Nguồn: `Reader.onPageInfo` → App. Trang chỉ còn sách.

### 3.5 PlayerBar
- **Cài đặt = một chip ở GIỮA, chi tiết trong panel (02/09, chủ: "tối giản, tinh tế, đưa vào giữa")**:
  chip ghost `⚙ Thu Hà · 1,25×` nằm giữa footer khi rảnh; bấm → `SettingsPanel` (Surface nổi trên
  footer, giữa): Giọng · Tốc độ (GroupedRow + Select) · Chất lượng (`ModelChoices`, ruột của ModelPanel
  cũ). Đang đọc: select bị vô hiệu (giọng/tốc độ chỉ đọc lúc bắt đầu). Esc đóng, trừ khi đang tải
  model. Hàng "Giọng": select chỉ mang TÊN giọng (≤ 11rem), mô tả "Nữ · Bắc · Kể chuyện"
  là dòng phụ của hàng — nhãn đầy đủ trong select từng tràn hàng, cắt mất chữ "Giọng" (chủ, 02/09). **Tên dài hơn
  ô thì ô tự cắt và đánh dấu ba chấm** (16/09): WKWebView vẽ nhãn đang chọn của `<select>` hết bề rộng của nó rồi
  mới che, và phần thừa ấy vẫn đếm vào chiều rộng cuộn của panel — đo trên panel 26rem với một giọng ElevenLabs tên
  56 ký tự: 651 px trong khung 414 ⇒ thanh cuộn ngang lòi ra, ăn 13 px chiều cao, đẩy nội dung vừa khít thành tràn
  dọc ⇒ thêm thanh cuộn dọc; rê chuột vào là cả hai hiện (chủ, 16/09: "đúng ra sẽ không có scroll ở popover này").
  Chromium che ngay trong ô nên audit render không thấy. Luật: `select` mang `overflow: hidden` + `text-overflow:
  ellipsis` (một chỗ, `index.css`, cho mọi select), và thân panel cài đặt `overflow-x-hidden` — panel nổi không bao
  giờ cuộn ngang, chỉ cuộn dọc khi cửa sổ thấp hơn nó. Khi đang đọc, TRANSPORT cũng đứng giữa (như mọi trình phát),
  trạng thái/lỗi lùi sang phải.
  **CTA và chip cùng loại nên đi chung** (chủ, 02/09): khi rảnh cả hai đứng GIỮA cạnh nhau; CTA nói rõ
  điểm bắt đầu — "Đọc tiếp · Chương 3" (có vị trí đã lưu/đã dừng, chương lấy từ `PageInfo.resumeChapterTitle`)
  hoặc "Đọc từ đầu"; màn dán giữ "Đọc nội dung". Bên trái footer một hint nhỏ "Nhấn vào đoạn văn để đọc từ
  đó" (chỉ màn đọc). **Đường về chỗ đang đọc** (chủ, 02/09): đang phát mà người đọc rời khỏi nguồn (sang thư viện, tab
  khác) → ô trái footer nói đang đọc gì ("Đang đọc: «sách»" / "…nội dung đã dán" / "…phần đã quét") +
  nút ghost "Quay lại" mở đúng màn/sách. Nguồn ghi lúc BẮT ĐẦU đọc (`origin`: book · paste · external);
  đứng đúng nguồn thì không hiện — trong sách, viên "Về chỗ đang đọc" lo phần "mắt đi lạc".
  Footer là lớp phủ, CAO BẰNG HEADER (76 px: pt-6 · hàng 36 · pb-4, padding lớn ở mép trong như
  header — chủ chỉnh 02/09); inset đo thật (`--shell-bottom-h`).

- **Usage — thanh dưới chỉ mang đúng NĂNG LỰC của màn đang mở** (mở rộng luật "ẩn-khi-chết",
  01/09). Footer hiện khi: màn có thể bắt đầu đọc **HOẶC** đang đọc **HOẶC** đang có lỗi đọc.
  Vế cuối là bắt buộc: phím tắt toàn cục đọc được ở MỌI màn, nên một lần đọc hỏng lúc đang ở
  màn Chuyển ghi chú vẫn phải báo được — ẩn footer đúng lúc đó là nuốt mất lỗi.

  | Màn | Nút bắt đầu | Giọng/Tốc độ | Vì sao |
  |---|---|---|---|
  | Đang đọc sách (Reader) | có | có | sách đang mở là thứ để đọc |
  | Thư viện (danh sách) | **không** | **không** | năng lực của màn này là MỞ SÁCH, không phải phát; giọng/tốc độ chọn ở màn đọc. (Bản nháp luật này ghi "có" — dựng ra rồi mới thấy sai: thanh chỉ còn hai ô cài đặt không hành động nào.) |
  | Dán nội dung | **có, kể cả khi rỗng** (disabled) | có | đó là hành động chính của màn |
  | Quét đọc | **không** | có | bắt đầu bằng phím tắt, không bằng nút; nhưng giọng/tốc độ áp cho phím tắt |
  | Chuyển ghi chú | không | không | không dính gì tới phát tiếng |

- **Đang phát thì thanh dưới CHỈ là transport** (tối giản 01/09): 4 nút icon `⏮ ⏸/▶ ⏹ ⏭`, không
  nhãn chữ — đây là ngôn ngữ ai cũng đọc được, và 4 nút chữ ăn ~300px trong khi 4 icon ăn ~128px.
  Nút phát/tạm dừng sáng hơn (`text-ink`) vì nó là việc chính; ba nút kia `ink-mute`.
- **Giọng/Tốc độ/Chất lượng BIẾN MẤT khi đang đọc** — không phải để cho gọn, mà vì chúng **không
  ăn vào lượt đọc đang chạy**: `rate` và `voiceId` chỉ được truyền lúc gọi `read_text`/`read_book`,
  đổi giữa chừng không đổi được thứ đang phát. Để chúng ở đó là hứa một điều app không làm.
  Chúng trở lại ngay khi dừng, tức đúng lúc chúng có tác dụng cho lượt sau.
- **Nút Dừng là ngoại lệ có nhãn + tone danger** (chủ chốt 01/09): ba nút kia là icon trần, riêng
  Dừng mang cả icon lẫn chữ và màu `danger`, vì nó là hành động duy nhất KẾT THÚC lượt đọc — cái
  không quay lại được bằng một cú bấm như tạm dừng. Đo: 5.14:1 trên desk ở cả hai theme.
  Không đụng brand: brand là CTA "Đọc", mà CTA không hiện lúc đang đọc nên hai màu không bao giờ đứng
  cạnh nhau (và từ 21/09 brand là xanh — §7 — nên chúng khác hẳn nhau ngay cả khi đứng cạnh).
- **Dòng trạng thái không được xuống dòng**: "Đang chuẩn bị giọng đọc…" từng vỡ thành 5 dòng dựng
  đứng giữa thanh (chủ bắt 01/09) → `whitespace-nowrap` + truncate.
- **Thanh transport trả lời NGÓN TAY, không trả lời engine** (02/09): bấm Dừng/Tạm dừng thì
  trạng thái đổi NGAY rồi mới báo cho engine — engine trả lời stop giữa hai câu nên có độ trễ
  thật, và một nút đứng đợi nó thì đọc ra là nút hỏng. Đo: engine cố tình trả lời sau 3000ms,
  giao diện về idle sau **26ms**. Mọi chuyển trạng thái đi qua MỘT máy trạng thái thuần tuý
  (`ui/playback.ts`, có test riêng) — trước đó là 5 chỗ tự tay `setReading`, hai chỗ trong số
  đó quên tắt dòng "đang chuẩn bị giọng đọc".
- **Ẩn ≠ vô hiệu hoá**: ẩn khi màn **không bao giờ** cấp được hành động đó (Quét đọc, Chuyển ghi
  chú, thư viện chưa mở sách); **hiện-nhưng-mờ** khi đó là hành động chính của màn và chỉ đang
  chờ dữ liệu (ô dán còn trống) — ẩn kiểu này sẽ làm nút nhảy ra khi vừa gõ ký tự đầu.
- **Anatomy**: trái = transport (**ẩn-khi-chết**: Dừng/Lịch sử chỉ hiện khi có việc) · phải = chuỗi `Field` nhãn+control (Chất lượng · Giọng · Tốc độ), khoảng trong-cặp 8 < giữa-cặp 16.
- **Behavior**: Space = tạm dừng/tiếp tục khi không gõ chữ; "Đang chuẩn bị giọng đọc…" hiện từ lúc bấm tới chunk PCM đầu.
- **Don't sống**: ✗ divider trên footer (chủ bỏ 01/09) · ✗ control mồ côi không nhãn (chip "Cao
  nhất" từng thế) · ✗ nhãn đứng cạnh control của cặp khác (bug Tốc-độ-chỉ-nhầm-ô, goal đầu tiên)
  · ✗ **nút chính ăn state của màn KHÁC** — trên Quét đọc/Chuyển ghi chú, nút "Đọc nội dung"
  từng bật/tắt theo ô dán ở tab khác và bấm vào là đọc đúng nội dung vô hình đó (01/09).

### 3.6 ConfirmInline · 3.7 PermissionCard · 3.8 Màn đầu tiên (từng là Setup gate)
ConfirmInline: thay chỗ trailing, hành động huỷ = **danger** + "Giữ lại" trung tính; không modal
cho việc một hàng. PermissionCard: Surface + note + hành động chính brand + đường "Cài đặt hệ
thống". **Quyền được dò SỐNG, thẻ biến ngay khi có quyền** (19/09, chủ: "user đã cấp quyền rồi thì ẩn khung
đó đi nhanh chóng chứ đừng giữ lại"): trước đó chỉ hỏi `AXIsProcessTrusted` một lần lúc mount, nên người
bật quyền trong Cài đặt hệ thống quay lại vẫn thấy thẻ cho tới khi rời màn. Nay hỏi lại khi cửa sổ focus /
hiện lại, và cứ 1,5 s một lần trong lúc thẻ đang hiện; có quyền → thẻ và ba bước hướng dẫn biến ngay, một
dòng "Đã có quyền Trợ năng." hiện 3 s rồi tắt. Câu "thoát rồi mở lại" chỉ còn là lối thoát *nếu phím tắt
vẫn không đọc* (AX trust được macOS đánh giá lại mỗi lần gọi; phím tắt toàn cục qua Carbon không cần AX),
không phải bước bắt buộc.

**Trạng thái "Đang đọc phần bạn vừa chọn…" trên màn Quét đọc** (19/09): là callout `info` **kèm nút "Tới đoạn
đang đọc"** (mở đoạn đang đọc nếu đang gập, cuộn phần giọng đang ở vào giữa) — không còn là dòng `error`; và
nó **tắt khi đọc xong**: hiển thị suy ra từ máy trạng thái phát (`reading ≠ idle` và nguồn là quét đọc), không
từ sự kiện `external:status` "reading" của host — sự kiện ấy không bao giờ được xoá nên dòng "Đang đọc…"
từng đứng lại mãi sau khi giọng đã im (chủ: "đọc hết thì tự động stop").

Màn đầu tiên (đổi 15/09): hiện khi máy **chưa đọc được gì** (không mô hình nào, không khoá API) —
và chỉ khi đó. Trước 15/09 đây là gate: chặn toàn app cho tới khi tải xong VieNeu. Chủ bỏ gate
("không được bắt buộc user phải tải một model duy nhất nào đó"): thân màn = đúng thân sheet Giọng
đọc & mô hình (§3.13) trong một cột giữa màn, cuộn trong cột khi cửa sổ thấp; một hành động brand
"Vào thư viện" **luôn bấm được** (chỉ khoá trong lúc đang tải). Không có cờ "đã qua màn này": đọc
được rồi thì tự hết hiện.

### 3.13 Giọng đọc & mô hình · bảng giọng đọc theo ngôn ngữ (15/09)
- **Usage**: chủ muốn "một nơi thống kê để user quản lý và tải model hoặc nhập API", và bảng giọng đọc
  "cho user chọn trước là họ muốn đọc ở ngôn ngữ nào rồi mới hiển thị các nội dung liên quan".
- **Sheet ở giữa CỬA SỔ, không phải giữa cột nội dung** (17/09, chủ: "cho setting nằm giữa, tương đồng với việc
  setting không có sidebar của nó"): hai sheet giữa màn (hub này, Tài liệu trong Apple Books) dùng `fixed left-1/2
  top-1/2` thay `absolute` trong cột nội dung — khi cột bên mở, sheet vẫn đứng đúng tâm cửa sổ, cùng khung với scrim
  phủ cả cửa sổ; sheet là của app, không của một cột. Danh sách giọng KHÔNG phải sheet giữa màn: nó neo trên nút của
  nó ở góc footer (05/09) → không scrim, không dời.
- **Scrim mờ dưới sheet** (17/09, chủ: "khi mở modal thì có một lớp blur overlay để focus vào phần modal"): mọi sheet
  giữa màn (hub này, Tài liệu trong Apple Books) đặt trên `Scrim` (`patterns.tsx`): `fixed inset-0`, đen 25 % + `backdrop-filter:
  blur(40px)` (`blur-2xl`; 6 px lúc đầu còn đọc được chữ phía sau — chủ 17/09 "blur mạnh hơn, như một nền background"),
  phủ cả cột bên; bấm vào scrim = bấm ra ngoài (đóng, trừ lúc đang tải — `useDismiss` giữ luật cũ). Popover
  neo nút (§3.9d) KHÔNG có scrim: chúng là lớp tra cứu nhanh, trang vẫn phải bấm được.
- **Anatomy (sheet)**: `Surface edge="strong" radius="sheet"` giữa màn (khung của sheet Apple Books,
  rộng 36rem, cao tối đa 84%, thân cuộn); header = tiêu đề 16 bold + caption 12 mute + đóng; mỗi ngôn
  ngữ một `GroupedSection` — hàng đầu là **trạng thái** (chấm `ok`/`edge-strong` + "Đọc được / Chưa đọc
  được" · subtitle "Mô hình X trên máy · N giọng · API · M giọng" hoặc "Tải mô hình về máy, hoặc nhập
  khoá API bên dưới"), rồi hàng mô hình (`ModelRows`: tiếng Việt hai bản Tải về / Dùng bản này / Tải và
  dùng / Xoá; tiếng Anh một hàng Tải về / Tải tiếp / Xoá), rồi nhóm **Giọng API** (`ProviderKeys`, subtitle
  "Đã có khoá · N giọng"); tiến độ + Huỷ tải ở cuối (`ModelProgress`). Nguồn sự thật duy nhất: hook
  `useModels` (trạng thái + lượt tải + hành động), để màn đầu, sheet và bảng giọng đọc không cãi nhau.
  **Huỷ tải là lời riêng của lượt tải** (`model.cancel`, 16/09), không phải Dừng của giọng đọc: trước đó
  cả hai là một lệnh `stop`, nên bấm Đọc trong lúc đang tải rồi Dừng (hoặc bấm Đọc lần nữa) là huỷ luôn
  lượt tải mà không ai định huỷ — và bài đọc đã xếp hàng sau lượt tải vẫn chạy cho một vỏ đã bỏ nó, không
  ai cấp credit, engine đứng chờ chỗ mãi, mọi bài sau xếp sau nó: "giọng không generate được, phải mở lại
  app" (chủ, 16/09). Luật engine: một `stop` phủ MỌI bài đọc đã xin trước nó, đang phát hay còn xếp hàng.
- **Anatomy (bảng giọng đọc)**: `SegmentedControl` "Ngôn ngữ đọc" Tiếng Việt / Tiếng Anh ở đầu;
  `SuggestionDot` trên tuỳ chọn của ngôn ngữ **nội dung** khi khác tab; `Notice tone="info" action=` một câu
  + một nút ("Đọc bằng tiếng Anh" / "Thêm giọng tiếng Việt"); nhóm Giọng (select gộp `optgroup` Trên máy /
  API · Quản lý giọng · Tốc độ · **Âm hiệu chương** (Tắt / Marimba / Harp / Piano) · **Chú thích** (Rút gọn /
  Đầy đủ / Bỏ qua) — hai `GroupedRow` + `Select` như Tốc độ, subtitle một dòng nói luật (§5.1), ghi thẳng
  vào engine qua `config.set` và nhớ qua khởi động · giới hạn chi khi giọng trả phí); nhóm Mô hình & API = một hàng tóm tắt +
  "Quản lý…" mở sheet. Tab không có giọng nào: hàng "Chưa có giọng … trên máy này" + hàng mô hình của
  tiếng đó (tải ngay tại chỗ) + nút mở sheet.
- **Behavior**: đổi tab = đổi sang giọng đã dùng cho tiếng đó (`voice_vi`/`voice_en`), không có thì giọng
  cục bộ đầu tiên hợp tiếng, không có nữa thì tab đổi một mình. Chọn một giọng làm-cho-một-tiếng ở bất kỳ
  đâu (kể cả menu đổi nhanh khi đang đọc) kéo tab về tiếng đó. **Gợi ý không bao giờ tự làm**: giọng chỉ
  tự đổi đúng một ca — mô hình vừa tải xong cho chính tab đang mở mà giọng đang dùng không hợp — và không
  bao giờ tự nhảy sang giọng trả phí. Esc/click-ngoài đóng, trừ lúc đang tải. Chip footer mang
  `SuggestionDot` + câu gợi ý trong `title` khi có gợi ý.
- **Content**: câu gợi ý nói NỘI DUNG là tiếng gì và giọng được làm cho tiếng kia — không nói "sai",
  không nói "không đọc được" (từ 15/09 giọng nào cũng đọc được).

### 3.9 Reader - màn đọc sách
Màn duy nhất mà NỘI DUNG là sản phẩm, chrome là chi phí. Luật gốc: mọi pixel chrome phải trả
được câu hỏi "nó giúp đọc hay xem hình chỗ nào".

- **Hai cách đi qua sách (chủ chốt 02/09): LẬT TRANG mặc định, CUỘN là lựa chọn** — nút chuyển
  trong cụm cỡ chữ, nhớ trong localStorage (`ui/readingMode.ts`). Đây là hình thái mọi app đọc sách
  hội tụ (Apple Books, Kindle, Play Books): trang, không phải cuộn; hai trang khi rộng.
- **Phân trang (`screens/PageFlow.tsx`)**: mỗi CHƯƠNG đổ vào cột CSS rộng bằng một trang, cao bằng
  vùng nhìn giữa hai inset; trang = một "view" gồm 1 hoặc 2 cột; lật = dịch flow sang view kế.
  Ranh giới chương = ranh giới trang (Apple Books cũng vậy; sách 6.700 đoạn chỉ layout một chương).
  Luật thuần trong `ui/pageLayout.ts` (test node): 2 trang khi vùng đọc ≥ 1040 px (≈ cửa sổ 1100)
  VÀ chữ ≤ 19 px; mỗi trang ≤ 40em; khe 48 px. Số trang là dẫn xuất của cỡ chữ + cửa sổ nên chỉ
  tính theo chương ("Trang 3/12") kèm % toàn sách theo chỉ số đoạn — và chỉ hiện trong tooltip ⓘ
  trên toolbar (§3.4), không có dòng đếm dưới trang (chủ bỏ 02/09).
- **Đoạn giọng đang đọc = gạch chấm dưới chữ, màu brand** (`.voice-here`, `index.css`): chấm 2 px, offset
  0,22em, không né nét chữ — một vạch dưới đoạn, không phải link; mực chữ giữ nguyên. Độ đậm: đặc 60 % (đầu) → chấm
  40 % (chủ 15/09: "nhẹ hơn") → chấm **55 %** (chủ 17/09: "đậm hơn xíu" — 40 % trên nền sáng còn lẫn với giấy khi
  nhìn xa). Con trỏ rê qua đoạn khác: cùng gạch chấm nhưng mực trung tính 30 %; đoạn đang đọc thắng khi hai cái gặp
  nhau.
- **Địa chỉ = đoạn, không phải số trang**: giọng, mục lục, vị trí đã lưu, engine đều theo
  `segment_id` (không đổi). Mở sách → mở đúng trang có vị trí đã lưu. Đổi cỡ chữ / cửa sổ → phân
  trang lại, giữ đoạn đầu trang đang xem (`anchor`). Ảnh của chương tải NGAY (ảnh ở cột tràn không
  bao giờ "giao" viewport; ảnh tới muộn làm số trang đổi giữa chừng — đã gặp: "1/2" → "2/3").
  `break-inside: avoid` cho hình, ảnh cao co theo `--page-h`.
- **Khung trang có đệm 8 px hai bên trong vùng cắt** để nền hover/active của đoạn (lề âm `-mx-2`)
  không bị cắt ở mép trang (chủ, 02/09); dải lật dừng ở mép khung.
- **Điều hướng**: ←/→, ↑/↓, PageUp/Down, Space, vuốt trackpad (ngang hoặc dọc, ngưỡng 40, khoá
  500 ms), và **hai dải mép** (`EdgeZone`, chủ chốt 02/09): dải = lề trống từ mép hộp tới mép trang
  (tối thiểu 40 px, rộng ra khi trang hẹp hơn hộp), KHÔNG BAO GIỜ phủ lên cột chữ — click và kéo-chọn
  trên chữ vẫn là của việc đọc; mũi tên mờ, đậm khi rê, ẩn khi không còn chỗ đi. Click đoạn = đọc từ đây.
- **Giọng theo trang**: giọng sang đoạn ngoài trang → tự lật (nếu đang theo). Chỉ TAY người đọc
  (lật/phím) mới tính là "đi chỗ khác" → `following=false` + viên "Về chỗ đang đọc"; app tự đưa đi
  (mở, mục lục, giọng, báo hình, phân trang lại) không bao giờ tính. Báo hình "Xem hình N" → lật tới
  trang có hình.
- **Mục lục = bảng nổi ở CẢ HAI chế độ** (`Surface` bên trái; chủ chốt 02/09 sau khi thấy overlay
  "quá tối ưu"): mặc định ĐÓNG (mở sẵn thì che sách); bấm chương → nhảy và đóng. Trong chế độ cuộn
  panel bắt đầu dưới header (`top = --shell-top-h + 0.5rem`); cột mục lục cố định đã bỏ.
- **Đo được**: 1060×720 → 1 trang 640 px; 1300 → 2 trang 602 px; phím → lật, qua mép chương đúng
  cả hai chiều; A+ hai bậc giữ đúng đoạn đầu trang.

- **Vị trí hiển thị bám theo TAI, không theo lúc tổng hợp** (02/09): engine phát sự kiện
  `position` lúc nó DỰNG xong đoạn, mà nó dựng nhanh hơn phát rất nhiều — nên nếu bắn thẳng lên
  UI thì highlight chạy trước giọng cả phút. Mốc vị trí nay đi CHUNG hàng đợi với âm thanh và chỉ
  được phát khi tới lượt nghe.
- **Hai vị trí, không phải một** (luật xương sống của màn này): **mắt** đang ở đâu (cuộn tới đâu)
  và **giọng** đang ở đâu (segment đang phát) là HAI thứ khác nhau. Sidebar đánh dấu theo MẮT
  (scroll-spy); nền `band` trong cột chữ đánh dấu theo GIỌNG.
- **Tự cuộn theo giọng chỉ khi mắt còn ở đó**: đang phát mà người ta cuộn đi chỗ khác thì PHẢI
  ngừng giật họ về, và hiện viên "Về chỗ đang đọc" để tự quay lại khi muốn. Không có luật này,
  scroll-spy và auto-scroll đánh nhau: cứ mỗi đoạn là màn hình nhảy.
- **Bấm chương = ĐI TỚI, không phải phát** (đổi ngữ nghĩa 01/09): cuộn tới chương đó; nếu đang
  phát thì giọng đi theo, nếu đang dừng thì chỉ cuộn. Bấm vào một ĐOẠN mới là lệnh đọc từ đó.
  Trước đây bấm chương là phát ngay - người chỉ muốn xem mục lục bị đọc vào mặt.
- **Cỡ chữ nội dung KHÔNG thuộc thang 14px của chrome**: đó là thang cho UI, còn đây là bề mặt
  nội dung - mặc định 16px, người đọc tự chỉnh được. Chỉnh bằng biến CSS trên gốc cột, không
  bằng class (class-mỗi-cỡ là drift, và `text-[1?px]` bị cổng chặn).
- **Anatomy**: **cửa sổ chỉ có MỘT hàng chrome, và trong sách hàng đó thuộc về sách** (01/09) —
  toolbar đổi nội dung: tabs lùi đi, thay bằng `‹ quay lại · ▤ mục lục · tên sách`, bên phải là
  `A− A+ · ngôn ngữ`. Đây là mô hình đẩy-màn-chi-tiết của macOS/iOS: màn con chiếm luôn thanh
  điều hướng, nút quay lại đưa tabs trở lại. Trước đó hai hàng chrome chồng nhau ăn ~76px trên
  đầu trang chữ; nay 36px. → mục lục hàng dày đặc (`ListRow dense`) → cột chữ KHÔNG bọc thẻ:
  nội dung nằm thẳng trên trang, vì viền + đệm của thẻ ăn mất bề ngang mà không nói thêm gì.
- **Đánh đổi đã biết**: trong sách không bấm thẳng sang tab khác được, phải quay lại một nhịp.
  Đổi lại là toàn bộ chiều cao của một hàng chrome. Nếu cần tabs ngay trong sách thì đó là quyết
  định ngược lại, không phải bổ sung — hai hệ điều hướng trên cùng một hàng sẽ chật ở 960px.
- **Hình được BÁO cho tai, không chỉ hiện cho mắt** (chủ chốt 02/09): tới hình thì giọng đọc
  "Xem hình N." rồi nghỉ 600ms; N đánh **theo chương** ("Xem hình 187" không ai nhớ nổi khi chỉ
  nghe); báo **mọi** hình ở bản đầu (sách đang đọc toàn ảnh nội dung mà chữ nhắc tới). Cue đi
  CHUNG hàng đợi vị trí nên hình được cuộn tới + nháy `band` đúng lúc tai nghe, không phải lúc
  model dựng. Dưới hình hiện "Hình N · chú thích"; alt rác kiểu "Image" (`alt_is_generic`) bị
  ẩn, không hiện không đọc.
- **Don't sống**: ✗ sidebar không dấu vị trí (audit 01/09) · ✗ đếm "Chương X/Y" cho PDF không có
  mục lục (mỗi TRANG là một "chương") · ✗ hai hàng chrome chồng nhau trên đầu màn đọc.

**Sidebar mục lục**
- **Usage**: điều hướng trong sách đang mở; mỗi hàng nhảy tới đầu chương.
- **Anatomy**: `ListRow` một dòng; **hàng của chương đang đọc mang nền `band`** — cùng token với
  dòng đang đọc trong cột chữ, nên "chỗ tôi đang ở" chỉ có một ngôn ngữ màu duy nhất.
- **Behavior**: chương đang đọc suy từ segment hiện tại (hoặc tiến độ đã lưu), không giữ state
  riêng — nếu không, nhảy đoạn bằng cách bấm giữa cột chữ sẽ làm sidebar nói sai.
- **Don't sống**: ✗ sidebar không dấu vị trí — đọc audio hàng giờ mà nhìn vào không biết đang ở
  đâu (bắt trong vòng audit theo tính năng, 01/09) · ✗ đếm "Chương X/Y" cho PDF không có mục lục:
  ở đó mỗi TRANG là một "chương" tên "Trang 37", header nói "Chương 37/300" là tự mâu thuẫn.

- **Màu bôi chọn = tint brand 24%** (`::selection`, `color-mix`), chữ giữ nguyên màu — nền đỏ đặc chữ
  trắng quá nặng (chủ, 02/09); alpha nên đúng trên cả hai nền.
- **Bôi đen để copy (02/09, chủ)**: vỏ tắt `user-select` toàn cục, riêng cột đọc bật `select-text` +
  con trỏ text. Kéo chọn rồi thả = một click trên cùng đoạn → **guard**: selection chưa gập thì click
  KHÔNG chuyển giọng (đó là "tôi đang copy"), click thường mới chuyển. Có selection thì viên
  "Đọc đoạn đã chọn" hiện như cũ; Cmd+C copy. Đo: userSelect=text, click-khi-đang-chọn 0 lệnh đọc,
  click thường 1 lệnh.
  **Nút "Đọc phần đã chọn" nằm ở FOOTER** (chủ chuyển 02/09, viên nổi trong trang bỏ): Reader báo
  `onSelection`, App vẽ ở cụm giữa — rảnh: primary đứng trước "Đọc tiếp" (lùi thành secondary khi đang có
  chọn); đang đọc: cỡ nhỏ cạnh transport. Bấm = đọc + bỏ chọn.
- **Viên nổi** ("Về chỗ đang đọc", "Đọc đoạn đã chọn") đứng trên footer: `bottom = --shell-bottom-h + 1rem`.
- **Scroll-spy** tính "đầu trang" từ inset: dòng mắt = top + `--shell-top-h` + 40; dòng đang đọc
  "còn nhìn thấy" khi nằm giữa hai inset, không phải giữa hai mép cửa sổ.

### 3.9g Dấu trên một dòng danh sách: emoji, và chỉ cho ca KHÁC thường (07/09)

- **Nhãn chữ trong một hàng danh sách thành emoji khi nó chỉ nói một sự thật đơn lẻ.** "Trả phí" → 💵,
  "Tiếng Việt" → 🇻🇳, "Tiếng Anh" → 🇬🇧. Hàng ngắn lại, và cái tên giọng — thứ người ta thực sự quét — không
  còn phải chia chỗ với hai viên nang chữ.
- **Không đeo nhãn cho ca thường.** Giọng miễn phí không mang dấu nào: một nhãn cho ca thường là hai mươi
  dòng cùng nói một điều chẳng ai cần đọc, và nó làm ca KHÁC thường (trả phí) khó thấy hơn.
- **Bỏ viên nang bọc ngoài khi nội dung là emoji.** Viên nang tồn tại để CHỮ đọc ra như một nhãn; emoji vốn
  đã là một vật thể riêng, và một bao xám quanh lá cờ chỉ đánh nhau với chính màu làm nó dễ nhận.
- **Dấu không tự mang nghĩa thì phải nói lời hai lượt**: `title` cho con trỏ, `role="img"` + `aria-label`
  cho cây trợ năng. Hàng phải đọc được với người không bao giờ nhìn thấy emoji.
- **Cụm dấu có khoảng cách riêng, hẹp hơn khoảng cách của hàng.** Xếp theo `gap` của hàng, ba dấu đọc ra như
  ba thứ rời nhau trôi khỏi cái tên; gom lại thì chúng là một cụm sự thật về giọng đó.
- **Nhãn nói cái ĐÃ BIẾT, bộ lọc không hành động trên cái CHƯA BIẾT.** Cờ chỉ hiện khi nhà cung cấp đã xác
  nhận (`vouchedFor`); còn bộ lọc theo ngôn ngữ chỉ loại giọng nào TỰ khai ngôn ngữ khác (`canSpeak`). Cùng
  một trường dữ liệu, hai mặc định ngược nhau, cố ý.

### 3.9f Cửa sổ thấp: chữ giải thích nhường chỗ, nút bấm thì không (07/09)

Đo trên bảng Giọng đọc ở cửa sổ cao 423px: trần của bảng là 239px, nhưng các hàng cố định phía trên danh
sách cộng lại 348px. Hậu quả **không phải** là chật — mà là **110px vẽ ra NGOÀI mặt bo góc**, chân bảng
trôi xuống dưới mép cửa sổ, và danh sách giọng — thứ duy nhất bảng này tồn tại vì nó — được **0px**. Ở
560px nó được 26px.

- **Mọi lớp nổi có trần chiều cao phải `overflow-hidden`.** Có trần mà không cắt thì con vượt trần cứ thế
  vẽ ra ngoài; cắt rồi thì tệ nhất cũng chỉ là bảng bị hụt ở đáy, đúng hình dạng của một bảng có trần.
- **Thứ tự nhường chỗ: câu giải thích trước, nội dung sau cùng.** Dưới ngưỡng (`short-hidden`, 640px) thì
  phụ đề dưới tiêu đề, câu giải thích dưới ô điều khiển, và dòng đếm ở chân bảng đứng xuống. Cảnh báo thì
  **không**: "không lấy được danh sách" và "đang đọc nên không nghe thử được" là lý do, không phải trang trí.
- **Nút bấm không bao giờ bị giấu — nó được GẤP LẠI sau một nút khác.** Hàng chip lọc chiếm 80px cố định;
  ở cửa sổ thấp nó lui về sau một nút trong hàng tiêu đề, đúng khuôn ô tìm kiếm đã làm (§3.9d). Giấu hẳn
  một bộ lọc là để lại một danh sách thiếu dòng mà trên màn hình không có gì nói vì sao.
- **Đừng đánh nhau với cascade.** `short-only` (một utility `display:none`) không thắng nổi lớp `flex` mà
  `IconButton` tự đặt — nút vẫn hiện ở cửa sổ cao. Thứ gì component đã tự đặt `display` thì phải quyết bằng
  **render hay không render**, không phải bằng CSS. Đã bỏ `short-only`, dùng hook `useShortWindow`.
- **Một ngưỡng, khai hai nơi, phải bằng nhau.** CSS không đọc được state của React và ngược lại, nên 640px
  nằm cả trong `index.css` lẫn `ui/useShortWindow.ts` — và có test đọc cả hai file so số. Lệch nhau là một
  bảng gấp chữ ở một chiều cao còn mời nút ở chiều cao khác.
- **Hook nghe cả `change` lẫn `resize`.** Máy chủ xem trước đổi khung nhìn mà **không** phát sự kiện nào
  của `matchMedia` (đo 07/09) — nghe một tín hiệu thì trạng thái đứng im sau lần đổi cỡ đầu tiên.

**Sàn của cửa sổ, và vì sao ngưỡng gấp phải nằm trên nó.** `tauri.conf.json` khai `minHeight: 600`, và nó
có hiệu lực thật — ép cửa sổ xuống 380px qua System Events thì macOS kẹp lại đúng 600 (đo 07/09). Trừ thanh
tiêu đề còn **khung nhìn ≈ 572px**, tức cửa sổ NHỎ NHẤT hợp lệ vẫn nằm dưới ngưỡng gấp 640 — nên đường gấp
là đường mà app thật sự chạy vào, không phải mã chết. Có test đọc cả `tauri.conf.json` lẫn `SHORT_WINDOW`
để giữ quan hệ đó; nâng sàn lên 700 làm test đỏ.

Đừng lấy bản xem trước trong trình duyệt làm chuẩn: một thẻ trình duyệt không có sàn nào, nên nó dựng được
những chiều cao mà app không bao giờ đạt tới (423px trong ảnh chủ gửi là một trong số đó).

Kết quả đo lại (cùng bảng, cùng thư viện giả có 3 nhà cung cấp):

| Khung nhìn | Danh sách trước | Danh sách sau |
|---|---:|---:|
| 423px (chỉ có trong bản xem trước) | 0 | 85px · 1,3 giọng |
| **572px — sàn thật của app** | 96px · 1,5 giọng | **234px · 3,7 giọng** |
| 900px | 366px | 366px · không đổi |

Không còn gì vẽ ra ngoài mặt bảng ở bất kỳ chiều cao nào.

### 3.9e Khối nội dung sách: góc theo FILL, và nhãn không mặc màu vô hiệu (06/09)

- **Bo góc thuộc về lớp nền, không thuộc về khối.** Khối chữ để trần thì `rounded-none`; có nền thì `rounded-2xl` —
  đang đọc (`bg-band`) hoặc đang rê chuột (`bg-wash`). Trước đó khối luôn mang `rounded-lg`, và ở trạng thái trần
  chẳng có gì để bo ngoài **vạch trái của khối trích dẫn**, nên vạch bị cong hai đầu (chủ 06/09). Dùng `2xl` chứ
  không phải `xl`: thang bán kính chỉ có hai nấc — surface `2xl`, content `lg` — `xl` nằm ngoài thang và
  `npm run audit:ui` chặn nó.
- **Tiêu đề giữa trang cách thân trên nó 24 px** (`mt-6`, 17/09, chủ: "space top của heading xa thêm xíu nữa với text
  body bên trên"): ở chế độ trang, tiêu đề từng mang `mt-2` (8 px) cho MỌI tiêu đề vì tiêu đề mở chương đứng đầu trang
  không cần khoảng trống — nhưng tiêu đề mục giữa trang thì dính vào đoạn trên. Nay: khối ĐẦU TIÊN của chương giữ
  `mt-2`, tiêu đề còn lại `mt-6`; chế độ cuộn vẫn `mt-10`. Tiêu đề rơi đúng đầu cột trang thì margin bị cắt tại
  điểm ngắt (css-break: margin trước một điểm ngắt không ép bị bỏ), nên không sinh khoảng trống ở đầu trang.
- **Dấu đầu dòng là chữ của tài liệu, không phải chrome** (17/09, chủ: "style của các bullet point đẹp hơn"). Trước:
  chấm 6 px và số "1." ở 0,9em đều `ink-mute` — số đọc như dấu chú thích chứ không phải thứ tự, và rãnh 20 px làm "10."
  tràn đè lên chữ. Nay hai bậc (chủ chốt sau khi xem bản "cùng mực với chữ": "bullet có màu riêng, số màu nhẹ hơn để phân cấp"):
  **chấm 5 px màu `brand-600`** (≈ dấu • của font; điểm nhấn duy nhất của app trên trang chữ), giữa x-height dòng đầu
  (`top-1` = `py-1` của khối, line-height thừa kế); **số đúng cỡ chữ, `tabular-nums`, màu `ink-mute`** — nhẹ hơn lời để
  đứng dưới lời. Cả hai canh phải trong **cùng một rãnh 32 px** (`pl-8`, `w-8`, chứa tới "99.") để mép chữ của mọi
  danh sách trong chương thẳng nhau; số cách chữ 8 px (`pr-2`), chấm cách chữ 14 px (`pr-3.5`) để **chấm nằm dưới CHỮ
  SỐ chứ không dưới dấu chấm của số** (tâm chữ số ≈ 15 px kể từ chữ; chủ 17/09: "bullet xa ra bên trái một xíu để
  align với number") (chủ 17/09: "padding left của bullet bằng với number"; bản 24/32 tách rãnh chỉ
  sống vài phút).
- **`ink-faint` là màu VÔ HIỆU, đừng dùng cho chữ của sách.** Nhánh "trích dẫn ngắn = nhãn" (`quoteRole`, ≤3 từ và
  không có dấu kết câu) từng tô chữ thật của sách bằng `ink-faint`, tương phản ~2:1 trên giấy trắng — chủ đọc không
  ra và hỏi "nội dung gì mà mờ quá vậy". **Nhãn là NHỎ và khẽ, không phải không dùng được**: cỡ chữ và độ đậm nói
  rằng đây là nhãn, còn màu phải giữ ở mức đọc được (`ink-mute`). Luật rộng hơn: token trạng thái (`faint` = vô
  hiệu) không được mượn sang làm sắc độ cho nội dung.

### 3.9b Hover/press của control = lớp wash PHỦ LÊN fill, không thay fill (02/09)

- Bộ control vẽ hover bằng `hover-wash` (index.css): `background-image` gradient của `wash`/`press`
  đè lên `background-color` sẵn có. Trước đó `hover:bg-wash` **thay** nền giấy đục bằng alpha 5% nên
  nút nổi trên nội dung ("Về chỗ đang đọc") hoá trong suốt khi rê chuột — chữ bên dưới xuyên qua
  (chủ bắt 02/09; đo: nền hover `rgba(243,243,243,0.05)` → sau sửa `rgb(38,39,39)` + gradient).
  Cùng lỗi ở nút đóng lightbox trên nền đen. **Ngoại lệ**: `Select` giữ `hover:bg-wash` vì chevron
  của nó đã sống trong `background-image`.

### 3.9d Panel nổi trên trang (popover) — lót 24, bo cỡ sheet (03/09, nhắc lại 06/09)
- **Mọi panel nổi trên nội dung** (`SettingsPanel` dưới footer, `ReadingSettingsPanel` dưới header, panel chi phí…)
  dùng `Surface radius="sheet"` (`rounded-3xl`) và **lót nội dung 24 px** (`px-6`, `pt-5`/`pb-6`) — cùng một inset với
  sheet, không phải 16 của card. Lý do: panel là một LỚP đứng trên trang, cần đọc như lớp; 16/2xl làm nó lẫn với thẻ
  trong trang (chủ, 06/09: "tăng padding và tăng radius của popover").
- **Menu (`MenuButton`) bo 20 px** (17/09, chủ: "radius của dropdown tròn hơn để tương đồng với item bên trong"): hàng
  menu bo 12 px (`rounded-xl`) đặt trong lót 8 px → góc ngoài đồng tâm = 12 + 8 = 20 (`Surface radius="menu"`); 16 của
  card làm menu vuông hơn chính hàng của nó. Luật chung cho mọi vỏ có hàng bo bên trong: **góc ngoài = góc trong + lót**.
- **Vật liệu = kính của Books** (17/09, chủ đưa hai popover của Apple Books: "tận dụng các thiết kế từ Apple để có
  style glass"): panel nổi và menu dùng `Surface material="glass"` — nền `paper` **74 %** + `backdrop-filter: blur(28px)
  saturate(1.5)`, viền `edge-strong`, bóng `lifted`; trang mờ đi phía sau như popover "Contents"/"Themes & Settings" của
  Books. Chỉ LỚP NỔI TRÊN TRANG mới là kính (popover cài đặt giọng, cài đặt chữ, chi phí, menu đổi chế độ, tooltip
  chương); sheet giữa màn (Giọng đọc & mô hình, Danh sách giọng) và cột bên vẫn đặc — Books cũng thế, và chủ 16/09 đã
  chọn cột trắng. Kính thật của hệ (NSVisualEffectView qua `windows[].effects` của Tauri) cần cửa sổ trong suốt +
  `macOSPrivateApi` — để dành, chưa cần. Đo chữ trên kính: 74 % paper trên trang chữ mờ vẫn ≥ 4,5:1 cho `ink`.
- **Trong cột bên cũng thế, với inset 16** (17/09, chủ: "align với các thành phần khác"): ô tìm, dòng đếm, pill tab
  đều `px-4`; track của Mục lục và Tìm (`ListRow dense`, inset 10) là `px-1.5`, hàng ghi chú (inset 8) outdent `-mx-2`
  — đo: ô tìm 16 · dòng đếm 16 · chữ hàng đầu 16 · pill 16. Trước đó hai danh sách để track `px-4` nên chữ đứng ở 26.
- **Panel là DANH SÁCH DÒNG** (mục lục, tìm trong sách, ghi chú) theo cùng luật, chỉ khác cách đạt tới 24: header và ô
  nhập `px-6`, còn track của danh sách hẹp hơn đúng phần inset của hàng (`ListRow dense` = 10 px ⇒ `px-3.5`; hàng ghi chú
  = 8 px ⇒ `px-5`), để CHỮ của hàng thẳng hàng với tiêu đề. Cùng `radius="sheet"` (chủ, 06/09: "đồng bộ").
- **Góc của nhóm = NỬA CHIỀU CAO MẶC ĐỊNH, cố định** (17–18/09, chủ: "radius tổng thể của các group vừa đủ với item
  bên trong, để khi tăng height nó không còn là pill" rồi "vừa đủ để pill"): nhóm cao 44 → bo **22** (`rounded-[22px]`)
  — đúng pill ở 44, và VẪN 22 khi cụm cỡ chữ mở hàng chấm lên 60 (không thành stadium 30 như `rounded-full`); ô bên
  trong cao 36 → bo **18** (22 − lót 4, cũng đúng pill). Cụm cỡ chữ và nút "Tuỳ chỉnh" cùng 22/18. Bản 16/12 (rounded
  rect) chỉ sống một giờ: chủ muốn giữ dáng pill ở trạng thái thường. Áp cho MỌI `SegmentedControl` (bảng giọng, tab
  cột bên — cao 36 thì 22 tự kẹp về pill) để một control chỉ có một hình. Luật chung §3.9d: góc ngoài = góc trong + lót.
- Hàng điều khiển bên trong panel nổi theo Books: hàng toàn bề rộng cao 44, ô chia đều (`SegmentedControl size="lg"`),
  có icon + chữ `text-sm` không xuống dòng; phần mở rộng đặt trong khối `bg-band rounded-2xl px-5 py-4`.
- Nút mở panel trên toolbar mang `data-popover-trigger` và **blur sau click**: tooltip theo focus sẽ không treo trên
  panel vừa mở.
- **Divider = `controls.tsx::Divider`**, dựng theo DS `Divider`: kiểu `dotted` là radial-gradient chấm 2px trên nhịp 8px
  (viền `border-dotted` của trình duyệt mỗi nơi một nhịp), `solid`/`dashed` là hairline. Không ghép tên lớp Tailwind từ
  biến — lớp không xuất hiện nguyên vẹn trong nguồn thì không được sinh ra.
- **Control bị khoá phải NÓI vì sao**: ô đang chọn **GIỮ NGUYÊN** viên trắng nổi (`bg-paper` + `shadow-raised`) — nó vẫn
  là lựa chọn của người đọc, làm phẳng đi thành ra "chưa chọn gì". Cái nói lên trạng thái khoá là **icon ổ khoá nằm trong
  chính ô đang chọn**, cùng chữ nhạt đi (`disabled:text-ink-faint` cho cả ô lẫn icon), cộng một dòng nhỏ nói điều kiện
  ("Số cột · Chỉ dùng được khi đọc theo trang", chủ 06/09). `SegmentedControl` tự vẽ ổ khoá khi một ô vừa `on` vừa
  `disabled`, nên luật nằm một chỗ; **đừng** gắn ổ khoá lên nhãn — trạng thái thuộc về control, không thuộc về cái tên
  của nó. Một hàng chữ xám không giải thích gì.
- **Mũi tên để QUAY LẠI, chevron để LẬT TRANG** (chủ 06/09): nút quay lại đeo `ArrowLeftIcon` — đầu mũi tên
  **có thân**; `ChevronLeftIcon` là dấu trần, giữ nguyên chỗ của nó ở hai mép trang, nơi cặp trái/phải chỉ dọc
  theo dòng chữ. Mũi tên là *rời đi*, chevron là *bước một nhịp*. Mũi tên lấy bản outline vì bản bulk của bộ nguồn
  không phải mũi tên trần — nó là một huy hiệu bo góc khoét hình mũi tên, một vật khác hẳn.
- **Tooltip cách DẤU 12, không cách vùng bấm** (`IconButton`, chủ 06/09): nút tròn 32 để bấm cho dễ, nhưng glyph chỉ
  20 — đo `LAYER_GAP` từ mép nút thì bong bóng nằm cách thứ nó đặt tên **18**, trong khi mọi lớp nổi khác cách vật
  của nó 12, nên riêng nó trông rời ra. Đo từ `svg` bên trong; **căn giữa thì vẫn theo nút**, vì nút mới là chỗ con
  trỏ đang ở.
- **Slider ba tầng** (`Slider`, chủ 06/09): **glyph + TÊN cùng một hàng trên** · thanh trượt **suốt bề ngang**, không
  có gì đứng cạnh làm nó ngắn đi · dưới thanh là bản đọc: **một chữ bên trái, con số bên phải**. Hai đầu bản đọc tả
  **cùng một trạng thái** ("Thoáng · 1,70") nên đọc như một cặp; một mốc chết (giá trị nhỏ nhất của thang) đặt bên
  trái thì không — nó không bao giờ nhúc nhích, và núm chạm đầu thanh đã nói điều đó rồi. Chữ là thứ người đọc hành
  động được ("1,70" là một tỉ số, không ai chỉnh giãn dòng bằng cách biết 1,70 là đẹp); con số là cách quay lại đúng
  chỗ đã thích. Ranh giới các chữ **đặt tay, không chia ba đều**: mặc định phải nằm GIỮA một khoảng, mặc định rơi
  trúng ranh thì chữ lật qua lật lại chỉ với một nấc núm (`lineHeightBand`/`marginBand`, có test ghim).
  Cả cụm là **một** `<label>` — đừng bọc thêm `<label>` bên ngoài (lồng label thì click không tới input).
  Thanh: `appearance: none` rồi tự vẽ `::-webkit-slider-runnable-track` (cao 4, bo tròn) + `::-webkit-slider-thumb`
  (20 tròn, `bg-paper`, `shadow-raised`); **tắt appearance là mất luôn phần đã tô**, nên phần tô là một gradient mà
  component dời điểm dừng qua biến `--fill`. Chuỗi hiển thị do **caller** truyền: dấu thập phân là chuyện ngôn ngữ
  (tiếng Việt viết `1,75` — `decimal()` trong `i18n.ts`), không phải chuyện của control.
- **Chỉ báo bậc thì im khi đang ở mặc định** (hàng chấm dưới cụm cỡ chữ, chủ 06/09): người chưa đụng tới cỡ chữ không
  cần được chỉ chỗ trên một thang họ chưa dùng. Mức vẫn nằm trong `aria-label` của cả cụm. **17/09 (chủ: "ở size mặc
  định không cần space bên dưới")**: hàng chấm không còn chỉ mờ đi mà **xếp lại** — viên thuốc cao **44** ở mặc định
  (bằng hai pill hàng dưới), mở ra 60 khi rời mặc định; xếp/mở bằng `grid-template-rows 0fr → 1fr` chuyển `--dur-move` (240 ms, §3.17; trước 200) +
  opacity, nên chữ A không nhảy như khi tháo hàng khỏi DOM (lý do của bản 06/09 giữ hàng cố định), `motion-reduce`
  tắt chuyển động.

### 3.9c `Kbd` - hiển thị phím tắt
- **Usage**: cho THẤY tổ hợp phím hiện hành. Đây là THÔNG TIN, không phải hành động.
- **Anatomy**: mỗi phím một keycap rời (`Shift` `Command` `T`), nối bằng dấu `+` mờ. Nền `panel`
  (lõm) chứ không phải `paper`, bo **8px** chứ không phải 12px của control, chữ **12px**, và
  **viền dưới dày 2px** — thứ để bấm trên bàn phím, không phải trên màn hình.
- **Don't sống**: ✗ một hộp bo tròn có viền trên nền `paper` ở đúng radius control — trong app này
  đó CHÍNH LÀ hình dạng cái nút, và chủ đã nhầm nó với nút "Đổi phím tắt" đứng ngay cạnh (01/09).
  Phải khác NHIỀU chiều cùng lúc (nền + bo + cỡ + số hộp) thì mắt mới phân loại lại được.
- **Content**: lời nhắc lúc đang ghi phím ("Nhấn tổ hợp phím mới…") là CÂU, không nhét vào keycap.

### 3.10 Lightbox ảnh
- **Usage**: hình trong sách hiển thị vừa phải trong dòng chảy đọc; muốn xem kỹ thì mở lớn.
- **Behavior**: bấm ảnh để mở · **Esc** hoặc bấm nền để đóng (listener gắn khi mở, gỡ khi đóng)
  · nút đóng là `IconButton`, không phải chữ "✕" tự vẽ.
- **Don't**: ✗ ảnh to hết cỡ ngay trong dòng đọc (đẩy chữ đi, mà vẫn không đủ to để xem chi tiết).

### 3.11 `BookGrid` + `BookCard` + `BookCover` - kệ sách (02/09)

- **Usage**: chọn một cuốn trong thư viện. Sách là VẬT có mặt bìa; kệ bìa là hình thái mọi app đọc
  sách lớn hội tụ về (Apple Books "Library", Kindle, Google Play Books, Libby, Calibre) — vì bìa là
  thứ người đọc nhớ, chữ tiêu đề là thứ phải đọc. Danh sách `ListRow` chỉ còn cho mục lục và lịch sử.
- **Anatomy**: `BookCover` tỉ lệ in 2:3, góc `rounded-lg` (bìa là ảnh của một vật, không phải control),
  `shadow-raised`; hover: nhấc lên 2px + `shadow-lifted` (`--shadow-neutral-to-bot-3`, bậc kế tiếp
  của chính DS — cùng chất liệu tiến lại gần, không phải bóng mới); **không nhấc/translate** (chủ bỏ 02/09: kệ không cựa quậy). Thứ tự dọc (chủ đổi 03/09): bìa → tiêu đề
  14 semibold tối đa 2 dòng → một dòng dữ kiện 12 mute → **thanh tiến độ ở DƯỚI CÙNG**, `mt-auto` nên nó
  bám đáy thẻ kể cả khi thẻ bên cạnh cao hơn (xảy ra ngay khi một tiêu đề xuống hai dòng). Cả hàng vì thế
  cho **một đường tiến độ thẳng**, thay vì mỗi bìa bị một vạch chen giữa nó và tiêu đề của chính nó.
  Màu: **`--color-progress` = `--fill-progress-primary`** (ramp xanh) — DS có hẳn vai `progress` cho đúng
  việc này; brand (đỏ lúc đó) là *bản sắc* của app, không phải *trạng thái*, và nó làm mọi cuốn đang đọc gào
  lên. Từ 21/09 brand là xanh b100 — cùng ramp với `progress` — nên dải tiến độ và brand cùng họ; vẫn giữ token
  `progress` riêng vì hai vai khác nhau có thể tách lại bất cứ lúc nào.
- **Hai dấu ở góc bìa, và cả hai neo theo BÌA chứ không theo thẻ**: accessory (thùng rác) góc trên-phải,
  lộ khi hover/focus; **tag nguồn** (`tag`) góc dưới-trái, **hiện thường trực** — nó là một *dữ kiện* về
  cuốn sách, mà dữ kiện chỉ xuất hiện dưới con trỏ thì không ai tìm ra. Tag hiện tại: **icon app Apple Books** 20px
  (`AppleBooksIcon`) cho sách **còn cặp nối** (`from_apple_books` mới trong `library.list`, lấy từ
  `apple_book_links`, có test cả ca âm — đã chứng minh test đỏ khi hardcode `True`).
  **Icon APP, không phải logo Apple** (chủ đưa asset 03/09): nó gọi tên *sản phẩm* chứ không phải *công
  ty*, và vì có màu nên đọc được ở 20px — bản logo quả táo đơn sắc thử trước đó ở 12px chỉ còn là một
  vết mờ. Đây là icon DUY NHẤT trong `icons.tsx` không theo lưới 16px/`currentColor`: một nhãn sản phẩm
  là *ảnh của một vật*, nên giữ nguyên hình học và màu của nó, y như bìa sách.
  **Không có chip giấy phía sau**: bản thân nhãn đã là một khối màu đặc có cạnh, thêm đĩa trắng là badge
  bọc badge; `shadow-raised` của chính nó lo việc tách khỏi bìa tối.
  Id gradient lấy từ `useId()` — hai cuốn trên một kệ là hai bản svg trong cùng một tài liệu, id viết
  cứng sẽ trùng và cả hai cùng trỏ về cái xuất hiện trước (đo: `_r_0_-books` / `_r_1_-books`).
  Tag mang `pointer-events-none` để không bao giờ ăn cắp cú bấm mở sách — nên nó **không thể** mang
  tooltip; nghĩa của nó đi vào cây trợ năng bằng một nhãn `sr-only`, chứ không dùng `title` của hệ điều
  hành (thứ đã bị bỏ ở §3.4).
  Tag KHÔNG đi kiểm phía Apple mỗi lần mở kệ — việc đó phải sao chép DB của Books, quá đắt cho một nhãn;
  nó báo **cặp nối còn sống**, và việc đối chiếu thật vẫn thuộc sheet Apple Books (§3.12).
  `BookGrid`: `auto-fill` cột tối thiểu 8.5rem, khoảng cách rộng (32/40px) vì bìa là khối đặc, đứng
  xa nhau mới thở (chủ yêu cầu 02/09).
- **Behavior**: cả bìa là một nút (aria-label "Mở {tiêu đề}"); xác nhận xoá thay chỗ khối chữ
  (ConfirmInline), không mở hộp thoại. Bìa tải theo từng cuốn ngay khi kệ hiện (`book.cover`, một yêu cầu mỗi cuốn — thư viện 3–30
  cuốn không cần tải lười), cache ở tầng màn hình vì kệ bị rời/quay lại mỗi lần mở sách. Chương đang
  đọc (`progress_chapter`) là tooltip trên dòng dữ kiện — không có chỗ trên một dòng dưới bìa.
- **Content**: dòng dữ kiện ~24 ký tự dưới bìa 150px → thứ tự = **điều đổi hành vi trước**: "Đã đọc
  42%" (đang đọc) · "26 chương" · "9,5 MB" · định dạng cuối (chỉ để phân biệt hai bản, bị cắt trước).
  Không bìa → placeholder chữ: tiêu đề trên `panel` với dải `band` bên trái (cách Apple Books/Kindle
  làm) — luôn đọc được, không bao giờ là icon vỡ. Thứ tự kệ: đang đọc trước, rồi mới nhập gần nhất
  (`orderShelf`, test node). **Một lưới, không "kệ đọc tiếp" riêng** phía trên: thư viện 3–30 cuốn
  mà liệt kê cùng cuốn hai lần chỉ để có tiêu đề là nhiễu; sắp trước + thanh tiến độ cho cùng tín hiệu.
- **Do/Don't sống**: ✗ bìa co giãn theo tiêu đề (mọi bìa cùng cột, cùng tỉ lệ) · ✗ lớp wash phủ lên
  ảnh khi hover (làm bẩn bìa; bìa nhấc lên, không đổi màu) · ✗ chữ "undefined"/icon vỡ khi thiếu bìa
  · ✗ meta dài hơn một dòng.
- **Nguồn engine**: EPUB — `properties="cover-image"` (EPUB 3) → `<meta name="cover">` (EPUB 2) →
  ảnh có id/tên chứa "cover"; PDF — trang 1 render 600px. Bìa lớn hơn 300KB/900px được thu về JPEG
  600px trước khi đi qua ống JSONL (bìa in 2MB của chủ → ~60KB). `<guide type="cover">` trỏ trang
  XHTML là lỗ đã biết; cũng vậy: PNG có kênh trong suốt sẽ nền đen sau `convert("RGB")`, SVG có
  prolog dài quá 512 byte bị từ chối — 0 ca trong thư viện chủ, ghi nhận, không mở rộng trước.
  Thư viện chủ: 3/3 có bìa (02/09).

### 3.12 Đồng bộ từ Apple Books - công cụ phụ, một chiều (02/09)

- **Usage**: kéo sách và highlight/ghi chú từ Apple Books sang, trên yêu cầu. PHỤ: một nút ghost "Từ
  Apple Books" cạnh "Mở PDF hoặc EPUB" (và trong `EmptyState` — đường nhanh nhất tới một kệ đầy),
  mở panel `Surface edge="strong"` giữa màn. **Một chiều**: chỉ đọc hai DB của Apple (bản sao tạm,
  như "Chuyển ghi chú"), không bao giờ ghi ngược — panel nói rõ.
- **Anatomy (sheet macOS; chủ chỉnh ba lần 02/09: "phân cấp và layout" → "tối giản, một danh sách" →
  "thử layout listing khác")**: `Surface radius="sheet"` (24 px — bậc bán kính cho lớp đứng riêng giữa cửa
  sổ; card vẫn 16) viền `strong`; header = tiêu đề 16 bold + caption 12 mute một câu + đóng; **ô tìm
  thông minh** khi > 6 cuốn (`SEARCH_ABOVE`, không dấu, hiểu từ trạng thái — `matchesQuery`, test node);
  **lưới ô 2 cột** (`BookTile`, chủ chỉnh hai lần 02/09): ô = card `paper` viền `edge`, hover → viền
  `edge-strong` + `shadow-lifted` (bậc 3); bìa `MiniCover size="md"` 44×66 bên trái (bìa THẬT khi đã
  có qua `useCover` dùng chung, ô `band` + glyph khi chưa nhập, khoá + mờ khi chặn), tên tối đa 2 dòng,
  một dòng dữ kiện "N ghi chú · Đã có / Ghép với «…» / lý do chặn"; hành động = **icon bên phải**
  (`MenuButton`): nhập (mũi tên vào khay) mở tuỳ chọn *Chỉ nhập sách (mặc định) · kèm highlight · kèm
  ghi chú · kèm cả hai*; đồng bộ (hai mũi tên) mở *Highlight và ghi chú (mặc định) · chỉ highlight ·
  chỉ ghi chú*. Engine: `applebooks.sync_notes {mode}` — highlights = bỏ ghi chú, notes = chỉ đoạn có ghi
  chú, both = tất cả (test server). Footer sheet = tóm tắt/tiến độ/kết quả + primary "Đồng bộ N cuốn"
  (mặc định CHỈ nhập sách) + chevron cùng 4 tuỳ chọn. Rộng 38rem, lề 24.
- **Behavior**: "Đồng bộ tất cả" = nhập mọi cuốn nhập được rồi đồng bộ ghi chú mọi cuốn đã ghép có
  highlight. Ghi chú đồng bộ là GƯƠNG: thay toàn bộ hàng `source=applebooks` của cuốn đó — xoá bên
  Apple thì mất bên này. Esc đóng, trừ khi đang chạy.
  **Hệ quả của "gương" mà menu chưa nói ra (đo 04/09, CHỜ CHỦ QUYẾT)**: `mode` không chỉ lọc thứ mang
  sang, nó lọc luôn thứ đang giữ. Chọn *chỉ ghi chú* trên cuốn đã đồng bộ *cả hai* thì highlight không
  kèm ghi chú **bị xoá khỏi ReadEase** — reply đếm nó là `skipped` (đường vào), không hề nói có thứ đang
  giữ vừa bị bỏ đi, nên vỏ cũng không nói được cho người dùng. **Không mất dữ liệu**: Apple Books là
  nguồn thật, đồng bộ lại *cả hai* là nó về đủ (đo: 2 → 1 → 2). Câu hỏi cho chủ: *chỉ ghi chú* nên đọc
  là "chỉ MANG ghi chú sang" (lọc lần chuyển) hay "chỉ GIỮ ghi chú" (lọc tấm gương)? Hành vi hôm nay là
  vế sau, và nay có test ghim (`test_a_narrower_sync_mode_also_drops_what_it_no_longer_covers`) để đổi
  là một quyết định chứ không phải một tai nạn.
- **Engine**: Apple giữ sách tự thêm dưới dạng THƯ MỤC `.epub` → nén tất định (mimetype trước, STORED,
  mốc thời gian cố định, bỏ `iTunesMetadata.plist`/`.DS_Store`/`__MACOSX`) để hash không đổi → importer
  sẵn có nhận ra cùng sách khi nhập lại. Bảng `apple_books_links(asset_id→book_id)` nhớ cuốn nào đã
  thành cuốn nào; chưa có link thì ghép theo tiêu đề chuẩn hoá (khớp toàn bộ hoặc 24 ký tự đầu) và
  HIỆN cặp ghép để sai thì thấy. DRM = `encryption.xml` có CipherReference trỏ vào thứ không phải
  font (font obfuscation không phải DRM). Highlight về đoạn bằng CHỮ đã bôi (40 ký tự đầu, chuẩn hoá
  ngoặc kép/khoảng trắng), CFI chỉ dùng phân xử khi trùng; bookmark bỏ qua, không tính là thất bại.
- **Màn đọc**: highlight = `<mark>` tô `--fill-warning-haze` (vàng alpha 30%, đúng cả hai nền), chữ giữ
  màu; ghi chú = icon nhỏ sau đoạn bôi, hover thấy nội dung. Highlight tràn sang đoạn sau chỉ tô hết
  đoạn nó bắt đầu. Tách trong `ui/highlight.ts` (test node: ngoặc cong, NBSP, khoảng trắng đôi, tràn đoạn, nhiều highlight một đoạn — §3.14 cuối).
- **Thư viện chủ (02/09, đếm, không đọc chữ)**: 7 cuốn Apple Books, tất cả là thư mục; 2 ghép theo tiêu
  đề với bản đã có; 1 quá lớn (230 MB, 3 highlight — không đồng bộ được); 4 nhập được; highlight thật
  khớp 1/1 trên «101 Essays». Nhập cuốn 1,4 MB mất 0,2 s.
- **Parking lot**: màu highlight theo Apple (cột `ZANNOTATIONSTYLE` CHƯA đọc — ba test cũ canh "một truy vấn,
  một bản sao" của `_rows`; đọc thêm cột = cập nhật fixture có chủ đích; `style` lưu 0) · nâng cap 200 MB · sách tệp `.epub`
  đơn (đã hỗ trợ đường đi, chưa gặp ca thật).

## 4. Hợp đồng bàn phím (vay Radix: bảng phím tường minh)

| Phím | Ở đâu | Làm gì |
|---|---|---|
| ⌥⌘R (đổi được) | toàn hệ thống | đọc vùng chọn; đang đọc → dừng |
| Space | trong app, ngoài ô nhập | tạm dừng/tiếp tục |
| ⌥⌘S | mọi màn (trừ Setup) | thu/mở cột bên — là lựa chọn tay, được nhớ. Là chord "Hide/Show Sidebar" của Finder · Notes · Photos · Reminders; đổi từ ⌃⌘S 17/09 (chủ: "thông minh hơn và tránh các phím tắt thông dụng khác" — ⌃⌘ là tầng chord hệ thống: ⌃⌘Space emoji, ⌃⌘F toàn màn hình, ⌃⌘Q khoá máy, ⌃⌘D tra từ). Bắt bằng `event.code` (KeyS), vì với ⌥ macOS đổi `event.key` thành "ß" |
| ⌘1 · ⌘2 · ⌘3 · ⌘4 | ngoài tài liệu | về màn Thư viện · Dán nội dung · Quét đọc · Chuyển ghi chú (thứ tự menu Đổi chế độ) — khuôn ⌘1–4 của Finder/Mail |
| ⌘1 · ⌘2 · ⌘3 | trong tài liệu | Mục lục · Ghi chú · Tìm của cột bên, qua `show(tab)`: cột gập thì mở đúng tab, bấm đúng tab đang hiện thì gập (công tắc) |
| ⇧⌘O | mọi màn | Thêm vào thư viện… — về kệ rồi mở hộp chọn tệp (Books cũng ⇧⌘O cho "Add to Library"; ⌘O để dành cho "mở một tài liệu" mà app chưa có) — **menu Tệp** (20/09) |
| ⌘W | trong tài liệu | đóng tài liệu, về kệ — app một cửa sổ, "Close Window" của hệ sẽ để lại một app không cửa sổ — **menu Tệp** |
| ⌘= · ⌘− · ⌘0 | trong tài liệu | cỡ chữ lớn hơn · nhỏ hơn · về mặc định (5 nấc của Cài đặt đọc) — **menu Xem** |
| ⌘. | đang đọc | dừng đọc (⌘. là "huỷ" của macOS) — **menu Đọc** |
| ⌘, | mọi màn | Giọng đọc & mô hình — chỗ gần nhất với "Settings…" của app — **menu Đọc** |
| ⌃⌘F · ⌘M · ⌘H · ⌥⌘H · ⌘Q | hệ | toàn màn hình · thu nhỏ · ẩn · ẩn app khác · thoát — mục có sẵn của hệ trong menu |
| ⌘F | trong tài liệu | mở cột bên ở tab Tìm và focus ô nhập; tab Tìm ĐANG hiện thì chỉ focus + chọn sẵn chữ để gõ đè (không gập — ⌘F là "tìm", không phải công tắc; trước 17/09 bấm ⌘F lần hai là gập cột) |
| ↑/↓ · Tab | cột bên | đi qua các mục (nút thường, thứ tự DOM; roving focus của AppTabs cũ không còn) |
| Esc | recorder phím tắt | giữ phím cũ |
| Esc | panel Chất lượng | đóng panel — trừ khi đang tải bản giọng (đóng lúc đó = giấu việc đang chạy) |
| Tab | mọi nơi | focus ring **info blue**, không bao giờ brand |

### 4.1 Thanh menu — mọi lệnh có chỗ đứng (20/09)

Chủ 20/09: "tiếp tục mục tiêu tạo một app chuyên nghiệp riêng". Kiểm kê: app chỉ có menu MẶC ĐỊNH của Tauri (App · Edit
· Window · View của hệ), không có lệnh nào của app, và các phím tắt ⌥⌘S · ⌘1–4 · ⌘F chỉ sống trong `App.tsx` — không nơi
nào để người dùng *tìm thấy* chúng. HIG Apple: **menu bar là bề mặt khám phá** — mọi lệnh của app có một chỗ trong menu,
phím tắt hiện ngay cạnh lệnh; nút trong cửa sổ là lối tắt, menu là bản đồ.

**Cấu trúc** (`ui/appMenu.ts`, dựng bằng API menu của Tauri từ phía trang — nhãn đi cùng `i18n.ts`, hành động đi cùng
state của `App.tsx`; mục có sẵn của hệ dùng `PredefinedMenuItem` với nhãn tiếng Việt khi app ở VI):

| Menu | Mục | Ghi chú |
|---|---|---|
| **ReadEase** | Giới thiệu ReadEase · Dịch vụ · Ẩn ⌘H · Ẩn ứng dụng khác ⌥⌘H · Hiện tất cả · Thoát ⌘Q | có sẵn của hệ; About mang phiên bản, bản quyền, giấy phép |
| **Tệp** | Thêm vào thư viện… ⇧⌘O · Từ Apple Books… · — · Đóng tài liệu ⌘W | hai mục đầu về kệ rồi làm; ⌘W chỉ bật trong tài liệu |
| **Chỉnh sửa** | Hoàn tác ⌘Z · Làm lại ⇧⌘Z · — · Cắt ⌘X · Chép ⌘C · Dán ⌘V · Chọn tất cả ⌘A · — · Tìm trong tài liệu ⌘F | 7 mục đầu có sẵn — bỏ chúng là ⌘C/⌘V chết trong mọi ô nhập; Tìm bật trong tài liệu |
| **Xem** | Thu/Mở cột bên ⌥⌘S · — · Thư viện ⌘1 · Dán nội dung ⌘2 · Quét đọc ⌘3 · Chuyển ghi chú ⌘4 · — · Cỡ chữ lớn hơn ⌘= · nhỏ hơn ⌘− · mặc định ⌘0 · — · Giao diện: Sáng · Tối · Theo hệ thống · — · Toàn màn hình ⌃⌘F | trong tài liệu bốn mục ⌘1–4 ĐỔI CHỮ thành Mục lục · Ghi chú · Tìm (mục 4 tắt) — cùng bốn mục, không hai nhóm trùng phím; giao diện là mục có dấu ✓ |
| **Đọc** | Đọc tiếp / Tạm dừng · Dừng đọc ⌘. · — · Đọc phần đã chọn · — · Cài đặt giọng đọc… · Giọng đọc & mô hình… ⌘, | Đọc tiếp/Tạm dừng đổi chữ theo trạng thái, tắt khi rảnh; KHÔNG gán Space cho nó (mục menu có phím Space sẽ cướp Space của mọi ô nhập); Đọc phần đã chọn KHÔNG ghi ⌥⌘R (⌥⌘R là hotkey toàn hệ qua plugin, gán trùng vào menu = bắn hai lần khi app đang ở trước) |
| **Cửa sổ** | Thu nhỏ ⌘M · Phóng to · — · Đưa tất cả ra trước | có sẵn của hệ; đăng ký làm Windows menu của NSApp |
| **Trợ giúp** | Hướng dẫn sử dụng · Báo lỗi hoặc góp ý · — · Phiên bản mới nhất | mở GitHub bằng opener; đăng ký làm Help menu của NSApp |

**Luật**:
- **Một bộ điều phối**: `App.tsx::perform(command)` — menu gọi nó, và bộ xử lý phím của trang cũng gọi nó. Trong CỬA SỔ,
  menu là chủ các chord nó ghi (⌥⌘S · ⌘1–4 · ⌘F · ⌘= ⌘− ⌘0 · ⌘. · ⌘, · ⇧⌘O · ⌘W): bộ xử lý phím của trang **nhường**
  (`IN_WINDOW`), vì WebKit trao keydown cho trang TRƯỚC rồi mới tới menu — trang `preventDefault` là menu không bao giờ
  thấy, trang không chặn thì cả hai cùng bắn. Trong trình duyệt (mock, audit) không có menu → bộ xử lý phím của trang làm.
- **Nhãn theo ngôn ngữ của app**, không theo locale hệ: đổi VI/EN là dựng lại menu (`Menu.new` + `setAsAppMenu`); mục
  đổi trạng thái thì `setText`/`setEnabled`/`setChecked` — TẮT chứ không giấu (Apple: mục biến mất là người dùng tưởng
  lệnh không tồn tại).
- **Không có menu riêng cho Giới thiệu**: dùng About có sẵn (phiên bản từ `getVersion()`, bản quyền và giấy phép trong
  metadata) — một cửa sổ About tự vẽ là việc sau, khi có credits đáng kể.
- Chưa vào menu: "Về chỗ đang đọc" (là hành vi theo màn — Quét đọc có, Reader có tip riêng — chưa có một lệnh toàn app).
- Mock không có menu bar: điều chứng minh được ở mock là bộ điều phối (gọi `perform` bằng tay) và không lỗi console;
  menu thật chỉ có ở bản build.

## 5. Content guidelines (vay Polaris: luật chữ theo component)

- Chuỗi VI/EN port **nguyên văn** từ nguồn đã audit (`ui/i18n.py` gốc) — đổi hộp, không đổi chữ.
- Gạch ngang `-`; **cấm em/en dash** (test tự động canh).
- Nhãn nút = hành động cụ thể ("Đọc nội dung", "Chép sang") — không "OK/Có".
- Thông điệp lỗi = chuyện gì + làm gì tiếp ("…Hãy thoát Apple Books rồi thử lại.").
- Placeholder {x} phải khớp giữa hai ngôn ngữ (test canh).
- Metadata thiếu → ẩn mục đó, không bao giờ render "undefined"/"null".

### 5.1 Luật CHỮ cho TAI (giọng đọc), khác luật chữ cho mắt
Chữ trên trang giữ nguyên; chỉ lời NÓI được chỉnh trong `speakable_text`. Đã có: hạ chữ hét, bỏ
ký tự đầu dòng, tiêu đề thêm dấu chấm, "Xem hình N." tại chỗ hình. Thêm 02/09 (chủ nêu):
- **"#N" đọc thành số thứ tự tiếng Việt** — "#1" → *thứ nhất*, "#2" → *thứ hai*, "#4" → *thứ
  tư*, "#21" → *thứ hai mươi mốt*, "#24" → *thứ hai mươi tư*, "#25" → *thứ hai mươi lăm*; quá 99
  thì "thứ 120" để model tự đọc số. Chỉ bắt "#" đứng một mình trước 1-3 chữ số; `#hashtag`,
  `C#`, `##12` giữ nguyên. Bằng chứng trong sách của chủ: 9 chỗ, hai dạng ("#1. Nói thẳng nhé"
  và "SỰ THẬT #1:").
- Cache âm thanh khoá theo chính đoạn chữ đưa cho model, nên đổi lời nói không phát lại bản cũ.
- **Gạch ngang là chỗ nghỉ, kể cả khi đứng trước SỐ** (chủ nêu 02/09: "kể—99 xu" bị đọc
  liền). Khoảng số "1975—1980" (chữ số ở CẢ hai phía, có hay không có khoảng trắng) mới là một
  khối; luật cũ né mọi gạch chạm chữ số ở *bất kỳ* phía nên nuốt luôn ca chữ-trước-số-sau. Gạch
  nối chỉ tính là gạch ngang khi có khoảng trắng hai bên ("Anh - em"); "tháng 1-2", "Anh-Mỹ" giữ
  nguyên. Gạch MỞ lời thoại (đầu văn bản hoặc ngay sau câu đã kết) không cắt lần nữa.
- **Số chú thích siêu chỉ số không đọc** — "Tang.³", "người³" là số chú thích cho MẮT; giọng đọc thành "ba" dính vào từ trước là rác. Quét thư viện 02/09: 6/6 siêu chỉ số đều là chú thích, 0 phép toán. Trang giữ nguyên ký hiệu; chỉ lời nói bỏ. Siêu chỉ số đứng ngay sau CHỮ SỐ là luỹ thừa ("10³") nên giữ (`drop_note_marks`, chỉ trong `speakable_text`). **Lỗ đã biết**: đơn vị đo sau chữ cái ("m²", "km²") sẽ bị coi là chú thích — thư viện hiện 0 ca (quét 02/09), gặp thì mới quyết bằng tai, không mở rộng trước.
- **Tiêu đề đánh số có số 0 đệm nói số, không nói số 0** — "01"…"09" (9 tiêu đề trong 203 tiêu đề số của sách 100 nguyên tắc của chủ). Chứng minh 02/09 trên sách thật, engine cũ → mới: "01" 0,72s → 0,48s, "02" 0,88s → 0,56s — số 0 đúng là được đọc ("không"), bản mới chỉ nói số. Chỉ TIÊU ĐỀ, chỉ số 0 dẫn đầu ngay trước chữ số ("0", "0.5 giây" giữ; đoạn văn "01/09" giữ). Trang giữ "01".
- **Tiêu đề nghe khác đoạn văn** (chủ, 16/09: "đổi giọng điệu hoặc đọc to hơn một xíu các tiêu đề, thêm
  ngắt nghỉ phù hợp trước và sau"). Hai giọng trên máy không đổi được cao độ, nên tiêu đề đọc **chậm hơn 8 %**
  (`HEADING_RATE` 0,92 nhân với tốc độ đang chọn) và **to hơn 2 dB** (`HEADING_GAIN` 1,26, kẹp ±1), nghỉ
  **1 000 ms trước / 850 ms sau** (đoạn văn 800/700). Áp cho MỌI heading vì `Segment` chưa có cấp; áp SAU
  cache câu (cache lưu PCM gốc của giọng), nên đổi số không phát lại bản cũ và không bump `READING_REVISION`.
  Không có tick âm cho tiêu đề: chủ nghe bốn mẫu 16/09 và không chọn.
- **Chuyển chương có nhạc chờ** (chủ, 16/09: "sound effect dạng nhạc chờ ngắn giữa các chương"). Ba âm sinh
  bằng ElevenLabs rồi hạ mono 48 kHz, −14 dBFS, đóng vào gói `speech/chimes/` (marimba 0,9 s · harp 2 s ·
  piano 2 s; nguồn ghi ở `THIRD_PARTY_NOTICES.md`, audit công khai ghim hash). Thay chỗ 1 200 ms im lặng
  bằng **300 ms → âm → 500 ms**; chỉ khi ĐỔI chương giữa bài, không ở câu đầu; phát như khung im lặng
  (`from_voice=False`: không stretch theo tốc độ, không vào cache, không tính tiền giọng API). Setting
  `chapter_chime` ∈ {off, marimba, harp, piano}, mặc định **marimba** (ngắn nhất); setting chưa từng ghi =
  mặc định, không phải tắt.
- **Chú thích không lê thê** (chủ, 16/09: "tối ưu nội dung khi đọc các ref để tránh dài dòng"). Setting
  `note_reading` ∈ {full, short, off}, mặc định **short**: thân chú thích là *thư mục* (Sđd/Ibid/op. cit.,
  "tr."/"p."/"pp.", năm bốn số + NXB/Press, URL/DOI/ISBN, số tạp chí) → **không đọc**; thân là *bình luận* →
  đọc **2 câu đầu hoặc 40 chữ** rồi "…"; `full` đọc nguyên văn; `off` bỏ mọi chú thích. Trích dẫn trong
  ngoặc "(Trần, 2019)", "(Nguyễn & Trần, 2019, tr. 12)", "[12]", "[3–5]" **không đọc** ở mọi chế độ trừ
  `full`; ngoặc là chữ ("(một người bạn cũ)") và năm trong câu giữ nguyên. Chữ trên trang không đổi; ước
  tính chi phí giọng API đi qua cùng hàm nên tính đúng chữ được đọc.
- **Ký hiệu liệt kê "(a) … (b) …" nói thành chữ cái kèm nghỉ** — chủ chọn bằng tai 02/09 giữa 4 bản render cùng một câu (giữ nguyên · xoá · "một là/hai là" · chữ cái + nghỉ): "khớp với a, nhiệm vụ hiện tại, hoặc b, sở thích cá nhân". Nghỉ đặt TRƯỚC liên từ dẫn vào ký hiệu (hoặc/hay/và/rồi/cũng như). Tham chiếu "mục (b)" → "mục b", không nghỉ. Chỉ chữ thường đơn có khoảng trắng phía trước; "book(s)", "(ii)", "(1)" không đụng (thư viện: 31 ký hiệu, 0 chữ số/hoa/tham chiếu). Test chốt = chính câu chủ duyệt, so khớp từng ký tự với bản render đã nghe.


## 6. Số đo đã chốt (vay M3: measurements tường minh)

Control 30px `rounded-xl` · nhỏ 28px `rounded-lg` (phím tắt `Kbd` cùng bậc) · icon-button 32
tròn · pill cho nav/ngôn ngữ · surface + ô nhập nhiều dòng `rounded-2xl` · chữ 16 bold (tiêu đề)
/ **14 base** / 12 micro (+18 màn chào) · trong-cặp 8 / giữa-cặp 16 / khối 24 · cột đọc 65ch ·
hover na10 · pressed na20 · hairline `edge` · cột bên **240** (kéo được 200–400; đầu 52 = vùng kéo, đèn {20,20}; thu = 0;
dải trên chừa 76 khi thu; **lót trong 16**, hàng rail 36, khối cách 24 — chủ 16/09 "tăng spacing tổng thể… thoáng") ·
ngưỡng tự thu **1100** px · chuyển động: quick **120** / vào **200** / ra **150** / dời chỗ **240** ms (§3.17).

**Ngoài thang là lỗi**: `rounded-md` (6px) không thuộc thang nào — cổng `audit:ui` chặn. Bốn
biến thể nút: `primary` (CTA brand) · `secondary` (viền) · `ghost` (không viền, việc phụ như
"Giữ lại") · `danger` (huỷ bỏ). Muốn một biến thể mới thì thêm vào kit, KHÔNG đè bằng
`className` — nút "Giữ lại" từng là secondary bị đè ba class để giả ghost.

**Góc KHÔNG phải quyết định của từng control** (DS radius §3.1 · chủ bắt 01/09): mắt đọc một
hàng control như MỘT khối, nên cả cụm dùng chung một tier — không phải tier suy ra từ chiều cao
riêng của từng cái. Trước đó nút 28px `rounded-lg` đứng cạnh select 30px `rounded-xl`, và `Kbd`
lệch 4px góc so với nút ngay bên nó. Nay mọi control đọc `--ctl-radius`; đổi tier bằng
`<Cluster radius="control | pill | sharp">`, mặc định 12px, cụm điều hướng (tab + ngôn ngữ) =
`pill`. Cổng `audit:ui` chặn `rounded-xl` viết tay trong màn để radius cứng không quay lại.

**Số đo màn đọc (đo thật 01/09, sân giả lập engine)**
- Cỡ chữ nội dung: 5 nấc **15 · 16 · 17 · 19 · 21** (mặc định 16), nhớ trong `localStorage`.
- **Lớp nổi (popover · tooltip · panel · sheet) LUÔN `Surface edge="strong"`** (chủ chốt 02/09): viền `field` tan
  trong nền tối, lớp nổi phải đọc thành vật ở cả hai nền. Card nằm trong dòng chảy giữ `field`.
- **Lớp nổi có TIÊU ĐỀ thì thuộc bậc sheet 24**, không phải bậc card (chủ, 03/09: "đúng guideline là sẽ
  cần tròn hơn"): panel cài đặt, bảng ghi chú, sheet Apple Books, sheet giọng — đo được 24 cả bốn. Còn
  **menu gồm các hàng** (mục lục, menu đổi giọng, menu tuỳ chọn nhập) giữ **16**, vì ở đó hàng 12px mới
  đồng tâm với khung 16 + đệm 4; kéo khung lên 24 thì hàng phải lên 20, quá tròn cho một hàng cao 36.
- Bán kính: control 12 · surface/card 16 (`rounded-2xl`) · **sheet/modal 24 (`Surface radius="sheet"`, chủ 02/09:
  "modal tròn trịa hơn")** · bìa sách 8 (`rounded-lg`, vật in) · viên nổi pill.
- Bề rộng cột: **40em** (chủ nới từ 36em, 02/09) → ~80 ký tự/dòng ở cỡ 16px; 36em đo bằng `Range` được 72 ký tự, dải dễ đọc cổ điển 45–75 — nới một bậc theo mắt chủ, không nới thêm.
  65-75. **Đừng dùng `ch`**: `70ch` của font này ra 804px ≈ 95 ký tự/dòng - đơn vị `ch` đo bề
  rộng chữ "0", không phải chữ trung bình. `em` giữ số ký tự/dòng ổn định khi đổi cỡ chữ.
- Nhịp: line-height **1.75** · đoạn cách 0.75rem · tiêu đề chương **1.35em** bold, cách trên 2.5rem.
- Hàng mục lục `dense`: px 10 / py 4 - 26 chương lọt trong 820px so với 15 hàng thường.
- Tương phản (đo cả hai theme): dải đang đọc/nền **1.12** (sáng) · **1.24** (tối); chữ trên dải
  **11.71** (sáng) · **12.82** (tối) - dải đủ thấy mà không cướp mất chữ.
### 3.14 Highlight và ghi chú: đọc được, và có một danh sách (03/09)

Ghi chú trước đây chỉ nằm trong `title` của thẻ `<mark>` — tooltip hệ điều hành: chậm hiện, cắt cụt, và
trên màn cảm ứng thì không đọc được. Nay:

- **Icon ghi chú trong dòng chữ là NÚT** (`InlineIconButton`, control mới trong kit — `IconButton` tròn
  32px đẩy giãn dòng khi nhét giữa đoạn). Bấm vào mở bảng và **ghim đúng ghi chú đó** (`bg-wash` +
  `scrollIntoView`). Nút tự `stopPropagation`: bấm vào đoạn văn nghĩa là "đọc từ đây", bấm icon ghi chú
  nghĩa là ngược lại — đã kiểm là không phát sinh lệnh đọc nào.
- **Xem nhanh ngay tại chỗ** (chủ, 03/09): rê chuột (hoặc tab tới) icon ghi chú thì hiện **bong bóng** đọc
  luôn nội dung — không phải mở gì cả; bấm mới mở bảng. Bong bóng được **tính toạ độ từ icon rồi vẽ bằng
  `fixed` ở lớp ngoài**, KHÔNG neo trong đoạn văn: ở mode lật trang, chữ nằm trong cột CSS bị trượt bằng
  `translateX` trong một khung `overflow-hidden`, nên một popover con của đoạn văn sẽ bị cắt hoặc rơi sai
  chỗ. **Lật lên trên** khi icon ở nửa dưới màn hình. Đã bỏ `title` gốc của trình duyệt để hai tooltip
  không chồng nhau.
- **Bề rộng co theo ghi chú, trần tính theo chỗ trống thật** (chủ, 03/09): một ghi chú năm chữ trong hộp
  20rem phần lớn là hộp rỗng. Bong bóng `w-max`, còn thứ tính bằng JS là **trần**: khoảng trống THẬT bên
  phải icon (icon có thể nằm bất kỳ đâu trên dòng), chặn trên bởi **28rem** — quá ngưỡng đó thì ghi chú
  không còn là liếc nhanh nữa mà nên mở bảng. Khi chỗ trống bên phải hẹp hơn **260px** (bong bóng sẽ thành
  một cột hai chữ mỗi dòng), nó **thôi bám icon** và canh theo lề phải cửa sổ. Đo được: 129 / 206 / 293px
  cho ba ghi chú ở cửa sổ 1060, và đúng 448px (4 dòng) cho ghi chú dài ở cửa sổ 1400.
- **`NotesPanel`** nổi ở lề TRÁI, **ngay dưới nút mở nó** — cùng chỗ với mục lục (chủ bắt 03/09: nút bên
  trái thì bảng phải bên trái). Hai bảng dùng chung góc được vì không bao giờ mở cùng lúc. Gom
  theo chương, đúng thứ tự đọc (`annotationsList.ts`, 5 test); mỗi hàng = đoạn được tô (`<mark>`) + ghi
  chú **đầy đủ** bên dưới. Bấm hàng **nhảy tới chỗ đó và KHÔNG đọc** — cùng luật với mục lục ("browsing
  should not read at you").
- **Mỗi hàng nói nó là loại gì, ở bên trái** (chủ, 03/09): `HighlightIcon` (hai dòng chữ + một vệt bút)
  cho đoạn tô trơn, `NoteIcon` cho đoạn có ghi chú — một cặp đọc được khi lướt dọc danh sách. Icon canh
  theo **dòng đầu**, không canh giữa hàng: một ghi chú ba dòng sẽ kéo icon canh-giữa rời khỏi đoạn nó
  thuộc về. Màu `ink-faint` để không tranh với chữ; kèm nhãn `sr-only` cho trình đọc màn hình.
- **Nút trên header chỉ hiện khi sách có highlight** (`PageInfo.annotations`), tooltip đếm số lượng. Nút
  mở một bảng rỗng là nút nói dối về cuốn sách.
- Một lớp nổi tại một thời điểm: mở ghi chú thì đóng mục lục và ngược lại.
- Annotation trỏ vào đoạn **không thuộc sách này** bị bỏ khỏi danh sách, không đoán chương — hàng nhảy
  đi đâu không biết còn tệ hơn là không có hàng.

**Thanh cuộn** (chủ, 03/09: "đừng để nó lòi ra khỏi panel… phạm vi nên chỉ thuộc phần body"): panel là
cột flex `overflow-hidden` — tiêu đề `shrink-0` đứng yên, **chỉ body cuộn**, nên thanh cuộn thuộc về danh
sách chứ không phải cả bảng, và `overflow-hidden` giữ nó trong góc bo thay vì chạy tràn ra.
Kiểu dáng theo **công thức Scroller của DS**: `scrollbar-width: thin` + `scrollbar-color` trong suốt lúc
nghỉ, hiện khi hover. DS đã **bỏ hẳn khối `::-webkit-scrollbar`** ngày 19/08 (đo được: Chromium bỏ qua mọi
luật webkit ngay khi có một trong hai thuộc tính chuẩn). App này **giữ lại** khối webkit — lệch DS có chủ
đích — vì chạy trên **WKWebView chứ không phải Chromium**: chỗ nào thuộc tính chuẩn thắng thì nó là thừa,
chỗ nào không hỗ trợ thì nó là thứ duy nhất chặn một thanh cuộn trắng nằm giữa trang nền tối. Hai đường
được chỉnh về cùng một kết quả (8px, trong suốt lúc nghỉ).

**Highlight giữ MÀU của nó** (04/09). Trước đó mọi highlight bị vẽ lại thành một sắc vàng, nên năm màu
người đọc đã chọn ở Apple Books biến thành một. Nay `ZANNOTATIONSTYLE` được đọc và `mark[data-style]` đổ
màu: **1 lục · 2 lam · 3 vàng · 4 hồng · 5 tím**; 0 hoặc không có thì rơi về vàng cũ.

- **Bản đồ số→màu không phải tôi chế**: hai cài đặt độc lập đọc cùng DB này khớp nhau chính xác
  (`py-apple-books` enum `AnnotationColor`, và plugin `apple-books-annotation-import`). Web không có tài
  liệu chính thức, nên hai nguồn độc lập là mức chắc chắn cao nhất lấy được.
- **Đều dùng bậc `haze`** (~30% alpha): highlight là mực phủ LÊN chữ, phải để chữ đọc được. Đo tương phản
  chữ trên nền tô: **6,5–8,6 ở nền sáng · 7,7–7,8 ở nền tối** — đều trên AA. (Lần đo đầu ra 1,4–8,6 lệch
  nhau vô lý vì ghép nền của các mark nằm sau lớp mờ của panel; đo lại theo đúng nền của từng mark.)
- **Mẫu highlight trong danh sách ghi chú = đúng độ của trang, riêng nền tối tô hai lớp** (04/09 chủ: trên giấy tối
  mẫu "hơi nhạt, khó nhìn" → `.mark-sample` tô alpha hai lần; 16/09, danh sách đứng trên cột trắng, chủ: "đậm quá so
  với highlight trong nội dung" → lớp thứ hai chỉ còn ở `[data-theme="dark"]`, nền sáng một lớp như trang).
- **Cột màu là TUỲ CHỌN, không bắt buộc**: schema của Books đi theo phiên bản đã ghi nó, nên reader hỏi
  `PRAGMA table_info` rồi mới thêm cột vào `SELECT`. Thiếu cột thì mất *màu*, không mất *ghi chú* — một
  `SELECT` cột không tồn tại làm hỏng cả lượt đọc. Có test cho cả hai hình dạng schema.

**Xoá là xoá HẲN** (chủ chốt 03/09: "xoá hẳn luôn"). Đồng bộ Apple Books là một tấm gương — `sync_notes`
gọi `replace_annotations` ghi đè cả cụm — nên nếu chỉ xoá dòng thì lần đồng bộ kế tiếp sẽ **đặt nó về chỗ
cũ**. Vì vậy engine giữ **bia mộ**: bảng `annotations_forgotten` (thêm mới, không bump SCHEMA_VERSION, cùng
lối với `annotations`), và bộ lọc nằm **trong `replace_annotations`** chứ không ở nơi gọi — để mọi đường
ghi annotation về sau đều phải tuân. Giao thức `annotations.delete {book_id, annotation_id}` trả `removed`
để phân biệt "vừa xoá" với "vốn không có"; nằm trong nhóm trả lời ngay giữa lúc đang đọc, vì người ta dọn
ghi chú trong khi nghe. Nút thùng rác **im lặng cho tới khi rê chuột vào hàng** (vẫn tới được bằng bàn
phím) và **hỏi lại ngay trong hàng** — cùng mẫu với xoá sách khỏi thư viện, câu hỏi nói thẳng hậu quả:
"Xoá hẳn, đồng bộ lại cũng không quay về?". Từ 16/09 nút **không giữ chỗ trong hàng** nữa (chủ: "bỏ đi
phần space chứa nút xoá… khi hover thì cho nút xoá overlay kèm background gradient-blur"): chữ chạy hết
bề rộng, nút nằm `absolute` ở góc trên-phải của hàng trên một **chip kính cỡ nút** `tail-reveal` (`index.css`,
17/09 — trước đó là một dải cao suốt hàng có gradient + mask, chủ: "action overlay này chỉ nằm trong vùng của button
thôi, chứ không full height"): 32×32, bo `ctl-radius`, nền màu cột 85 % + `backdrop-filter: blur(6px)`, viền `edge` 1 px
để chip nổi trên chữ dưới nó — một lớp blur, không phải ramp 8 lớp của thanh chrome. `focus-visible` vẫn hiện.

**Và nếu engine từ chối thì ghi chú QUAY LẠI trang, kèm lý do** (04/09). Trước đó hàng biến mất khỏi màn
hình ngay rồi lời gọi engine đi kèm `.catch(console.error)`: engine hỏng là ghi chú **trông như đã xoá mà
vẫn nằm nguyên trên đĩa** — người ta đóng sách, mở lại, nó ở đó. Với một thứ riêng tư thì đó là kiểu nói
dối tệ nhất. Nay: bỏ khỏi trang ngay (ngón tay xứng đáng có câu trả lời tức thì) nhưng lời gọi hỏng thì
**đặt lại đúng chỗ cũ** (`groupAnnotations` xếp theo vị trí trong sách nên thêm vào cuối là về đúng chỗ)
và bảng ghi chú hiện `notes.remove_failed` kèm nguyên văn lời engine. Đo bằng `?fail=annotations.delete`:
hàng 6→5 rồi **về lại 6**, vệt trên trang giữ nguyên 2; bỏ cờ thì xoá thật, 6→5 và vệt 2→1.

**Sách không mở được thì NÓI, đừng để trắng** (04/09). `if (!opened) return null` biến mọi lỗi `book.open`
thành một màn đọc trống trơn — không phân biệt được với sách đang tải, cũng không phân biệt được với sách
không có chữ, và thứ duy nhất nó không bao giờ hiện là **lý do**. Nay đang tải vẫn trống (nó qua trong
chớp mắt), còn hỏng thì hiện `reader.open_failed` giữa màn kèm lời engine. Đo bằng `?fail=book.open`:
TRƯỚC = 0 đoạn văn + không một chữ nào; SAU = 0 đoạn + "Không mở được sách này…".
**Còn treo (quyết định sản phẩm)**: footer trong trạng thái đó vẫn mời "Nhấn vào đoạn văn để đọc từ đó"
trong khi không có đoạn nào để nhấn. Nút "Đọc" thì KHÔNG hẳn là nói dối — engine đọc sách không cần
`book.open` của vỏ, nên nghe vẫn có thể chạy. Bỏ hay giữ là câu hỏi cho chủ.

**Danh sách giọng rỗng cũng là một LỜI KHẲNG ĐỊNH** (04/09). `engine_voices` hỏng thì `.catch` cũ để
danh sách rỗng nói thay — màn hình đọc thành *"máy này không có giọng nào"*, select 0 lựa chọn, và chip
footer thành **"· 1.25×"**: một dấu phân cách không có gì bên trái. Nay `voicesError` tách khỏi `voices`;
cả `SettingsPanel` lẫn `VoicesPanel` nói `voices.unavailable` kèm nguyên văn lời engine, và chip bỏ dấu
chấm khi chưa có tên giọng. Đo bằng `?fail=engine_voices`: chip "· 1.25×" → **"1.25×"**, hai bảng đều
hiện câu thật; bỏ cờ thì "Minh Đức · 1.25×", 6 giọng, không notice. Cùng luật §3.11/§3.14 — đây là chỗ
thứ **năm**.

**Nút "Đọc tiếp" chỉ nói nó LÀM gì; thứ nó sẽ đọc nằm ở tooltip** (chủ, 04/09). Trước đó tên chương bị
nhét vào nhãn nút rồi cắt cụt thành vô nghĩa. Nay hover (hoặc tab tới) hiện một tooltip: tên chương, **ba
dòng đầu của chính đoạn sẽ được đọc** (`PageInfo.resumeExcerpt`), và **bấm vào đoạn đó là nhảy tới chỗ
ấy — không đọc**. Cùng luật với mục lục và bảng ghi chú: duyệt thì không được đọc vào mặt người ta.

- **Mở bằng state, không phải `group-hover`**: tooltip này **với tới được** (chữ trong nó là một liên
  kết), nên nó phải sống sót khi con trỏ đi từ nút vào trong nó — và phải **kiểm được**. `pb-2` ở lớp bọc
  là cây cầu giữ cho cây con liền mạch, nếu không `onMouseLeave` sẽ bắn ngay lúc con trỏ rời khỏi nút.
  (`group-hover` của CSS không kiểm được bằng sự kiện tổng hợp, mà một nút bấm không kiểm được thì không
  được ship.)
- **Đường "đưa tôi tới đó" đi qua prop `reveal={{segmentId, at}}`** của Reader. Dấu `at` là thứ khiến hỏi
  **cùng một chỗ hai lần** vẫn chạy — chỉ mỗi id thì effect thấy không đổi và im lặng bỏ qua.
  `useEffect` đặt **sau** `showSegment`: mảng phụ thuộc được đánh giá lúc render, viết ở trên thì đọc vào
  vùng chết tạm thời và ném lỗi trước khi vẽ.
- Kiểm: nhảy sang chương khác → bấm nội dung trong tooltip → **về đúng đoạn nghỉ, không lệnh đọc nào**.

**Chip cài đặt nằm ở ô PHẢI của footer** (chủ, 04/09): ô giữa là *một cú bấm thì làm gì*, còn chip là một
**dữ kiện thường trực** về lượt đọc kèm lối vào — nó thuộc về bên cạnh trạng thái, không thuộc nhóm hành
động. Panel của nó vẫn mở ở giữa trên thanh.

**Tooltip ⓘ ghim theo LỀ CỬA SỔ, không theo icon** (chủ, 03/09: nó tràn mép). Icon ⓘ trôi theo độ dài tên
sách, nên neo trái thì cửa sổ hẹp tràn phải, neo phải thì cửa sổ rộng tràn trái — không lựa chọn tĩnh nào
đúng cho cả hai. `fixed left-6` dưới header + chặn `max-w` là bản duy nhất không thể ra khỏi màn hình; đổi
lại nó không còn chỉ vào icon mà đọc như một dòng trạng thái dưới thanh — vốn đúng là thứ nó đang là.

**Kẻ chấm canh theo nội dung**: `dot-divided` nhận `--dot-inset` (mặc định 0). Danh sách nào có hàng
**thụt ra ngoài** để vệt hover tràn quá chữ thì đẩy kẻ vào đúng bằng ngần ấy, nếu không kẻ rộng hơn nội
dung nó ngăn (chủ, 03/09).

**Một đoạn tô ĐỦ mọi highlight nó mang** (04/09). Trước đó `marked()` dừng ở highlight khớp ĐẦU TIÊN, nên
đoạn có hai highlight hiện đủ hai ở bảng ghi chú nhưng chỉ tô một trên trang — và ghi chú gắn vào cái thứ
hai không có icon nào để mở. `markParagraph` **cắt đoạn thành từng khúc** thay vì tách một lần; mỗi khúc
biết highlight nào sinh ra nó, nên mang đúng màu và đúng ghi chú của cái đó.

- **Không ký tự nào bị hai vệt cùng nhận.** Highlight rơi trúng chỗ một cái trước đã lấy thì dời sang lần
  xuất hiện còn trống kế tiếp, hết chỗ thì thôi: câu lặp hai lần trong đoạn ⇒ hai vệt; đánh dấu trùng một
  câu chỉ nói một lần ⇒ một vệt; cụm nằm TRONG một câu đã tô cả ⇒ không tô lại lần nữa.
- **Chồng lấn một phần thì cắt**, và vệt bị cắt đầu bỏ khoảng trắng dẫn — nếu không nó hiện ra như một ô
  màu rỗng trước chữ.
- **Bất biến**: ghép mọi khúc lại phải ra đúng đoạn văn cũ. Test node giữ tính chất này, không chỉ giữ ví dụ.

Đo trên harness (04/09): đoạn `ch-1-seg-1` trước **1** vệt → sau **2** vệt, `data-style` 3 và 1 (vàng ·
xanh lá), `p.textContent` không đổi một ký tự.

**Giới hạn còn lại (chưa sửa, cố ý)**: sửa nội dung ghi chú chưa có — ghi chú vẫn là dữ liệu một chiều từ
Apple Books.

### 3.15 Sidebar — danh sách đứng cạnh trang, trên nền kính mờ (15/09) — **ĐÃ THAY bằng §3.16 (16/09)**

> Ship trong 0.1.5 sáng 16/09; cùng ngày chủ xem và nói rõ ý là **một cột thật trong layout** ("giống như
> cách codex làm"), không phải lớp nổi. Mục này giữ lại làm hồ sơ của một lần hiểu sai: lớp nổi kính đã gỡ,
> `glass` utility gỡ theo. Luật hiện hành ở §3.16.

Chủ 15/09: "một sidebar trái được mở ra cho một vài tính năng, style có background blur, ví dụ khi bấm nút mở
chương". Thay cho ba thẻ đục rời (mục lục 288, ghi chú 368, tìm 352) — mỗi thẻ một vỏ, cao tối đa
`100vh − chrome − 2rem`, ở cửa sổ 600 px chỉ còn ~14 dòng chương — là **một** lớp cho cả ba.

- **Usage**: một DANH SÁCH nơi chốn trong sách mà người đọc mở, nhìn, chọn rồi quay về chữ: mục lục, ghi chú,
  kết quả tìm. KHÔNG dùng cho bảng thiết lập (chúng là popover neo vào nút của mình, §3.9d), không dùng ở màn
  ngoài Reader, không phải sidebar điều hướng cấp app (đó là `AppTabs`). Vẫn là **lớp NỔI** trên trang, không
  phải cột cố định — chủ 02/09: một cột cố định ăn mất bề rộng trang; và trang không được biến mất dưới nó,
  nên nền là kính chứ không phải giấy đục.
- **Anatomy** (`patterns.tsx::Sidebar`, `side="left" | "right"`): *frame* — hộp `absolute z-10`, bo `sheet`
  (24), viền `edge-strong` ở CẢ hai theme (kính cần một mép; ở tối lớp n10 76% trên n00 mờ đi không tự đứng),
  `shadow-lifted`, `overflow-hidden` để danh sách cuộn trong góc bo; *kính* — một lớp con `absolute inset-0`
  mang tint **giấy theo theme** (`--fill-neutral-base`, 76 %) + `backdrop-filter: blur(24px) saturate(140%)`;
  đặt trên lớp con chứ không trên frame để filter không thành containing block của thứ gì `fixed` bên trong;
  *header* — tiêu đề `text-sm font-bold` + `IconButton` đóng, lót 24/20 như mọi panel nổi (§3.9d); *thân* — do
  nơi dùng cung cấp, `min-h-0 flex-1 overflow-y-auto`, track hẹp theo inset hàng (mục lục `px-3.5`, ghi chú
  `px-5`) để chữ hàng thẳng với tiêu đề; *chiều cao* — suốt khoảng giữa hai thanh: cuộn → `top = --shell-top-inner
  + --layer-gap`, `bottom = --shell-bottom-inner + --layer-gap` (thanh player hiện khi đọc thì mép dưới lùi theo,
  live, nhờ observer của App); lật trang → cột đã lùi đúng `--shell-top-h`/`--shell-bottom-h`, nên trừ lại hai
  số đó để vẫn cách CONTROL 12 px ở cả hai chế độ (đo 15/09: neo theo cột thì lật trang cách 36, cuộn cách 12 —
  hai lớp khác nhau cho cùng một thứ). Bề rộng theo nội dung (mục lục `w-72`, ghi chú `w-[23rem]`, tìm `w-[22rem]`).
  Material giới hạn trong vùng sidebar là điều §7 cho phép; toàn cửa sổ vẫn nghỉ hưu.
- **Behavior**: mở bằng nút toolbar (▤ · ghi chú · tìm) — nút mang `data-popover-trigger` và `blur()` sau click
  để là CÔNG TẮC thật (bấm lần nữa đóng, không đóng-rồi-mở); trượt vào 12 px + hiện dần 180 ms bằng
  `@starting-style` (`starting:` của Tailwind), `motion-reduce:` tắt; đóng bằng Escape, bấm ra ngoài, nút ✕ —
  cùng một `useDismiss` cho cả ba (mục lục từng không có Escape, ghi chú từng không đóng khi bấm ngoài); mục lục
  ↔ ghi chú ↔ tìm loại trừ nhau (luật ở App); chọn chương / ghi chú → nhảy và ĐÓNG; chọn kết quả tìm → nhảy,
  GIỮ MỞ (lần tìm tiếp một click); mục lục không cướp focus (phím đọc vẫn chạy), tìm autofocus ô nhập; note
  editor (z-40), peek và lightbox (z-30) vẫn ở trên. Không có hoạt cảnh đóng: unmount tức thì như mọi lớp.
- **Content**: tiêu đề là tên danh sách ("Mục lục", "Highlight và ghi chú", "Tìm trong sách"); không dòng mô
  tả; hàng hai dòng cho tiêu đề chương (`line-clamp-2`); rỗng thì `EmptyState` của nơi dùng.

### 3.16 `SideColumn` — cột trái thật trong layout, thu/mở như Codex (16/09)

Chủ 16/09, sau khi xem 0.1.5: "tôi muốn nó là một sidebar riêng nằm một bên của layout luôn chứ không phải là
popover như hiện tại. giống như cách codex làm" + "cột trái sẽ có thể ẩn hiện thông minh tuỳ vào nhu cầu. User
có thể tắt/mở giống codex. màu đèn giao thông là các nút của app macOS có sẵn". Điều này **đảo** lựa chọn 02/09
(lớp nổi vì "cột cố định ăn mất bề rộng trang"): cột thu được, và tự thu khi cửa sổ hẹp, là câu trả lời cho lo
ngại đó.

- **Usage**: nơi ở của ĐIỀU HƯỚNG cấp app (Thư viện · Dán nội dung · Quét đọc · Chuyển ghi chú) và của mọi
  DANH SÁCH NƠI CHỐN trong sách (mục lục · ghi chú · tìm). Cột là một phần của layout: nội dung đứng bên phải và
  bị ĐẨY, không có gì đè lên gì. Không dùng cho bảng thiết lập (vẫn popover neo nút, §3.9d); màn đầu tiên
  (Setup) không có cột.
- **Anatomy** (`patterns.tsx::SideColumn`): gốc app = `flex` hàng `[aside][content]`; *aside* rộng **240**, nền = **vật liệu sidebar của macOS**
  (17/09, chủ: "sidebar sẽ có background blur" — `NSVisualEffectView` material `sidebar` qua `windows[].windowEffects`
  của Tauri, cửa sổ `transparent: true` + `app.macOSPrivateApi: true`; cột trong suốt để vật liệu lộ ra, phần còn lại
  của trang tự sơn `ground` — vật liệu chỉ sống trong VÙNG cột, không dưới cả trang: đó là lý do bản material toàn cửa
  sổ bị bỏ 01/09 "làm loãng tông của desk"); cửa sổ đổi appearance theo theme của app (`setTheme`) để vật liệu sáng/tối
  đúng theme kể cả khi khác hệ. Trong trình duyệt (mock, audit) không có vật liệu → cột lại là `--app-column`
  (= `--app-ground`: trắng ở sáng — chủ 16/09 — n00 ở tối). Viền phải hairline `edge` là thứ duy nhất ngăn cột với
  trang; hàng đang chọn đọc được trên nền đó (đo 16/09 trên cột đục: `band`/`wash` đọc, còn cột màu `band` thì hàng chương
  đang đọc biến mất — từ 20/09 cột trên vật liệu dùng thang alpha `veil`/`wash`/`tint`, xem mục bên dưới); ba tầng — *đầu* **60 px** là vùng kéo cửa sổ (`data-tauri-drag-region`) chứa
  đèn giao thông của macOS (cửa sổ `titleBarStyle: Overlay`, `hiddenTitle`, `trafficLightPosition` **{20, 29}** → tâm
  đèn y ≈ 30 = tâm hàng toolbar của cột nội dung (pt-3 + 36/2; hàng từng ở 34 với pt-4 — chủ 17/09 "đưa navbar lên
  trên một xíu", đầu cột theo đó **60 px**). **`y` của tao ≈ TÂM đèn, không phải mép trên**: tao
  đặt chiều cao khung title bar = cao nút + y và giữ nguyên origin của nút trong khung, nên tâm ≈ y + 1 (đo trên bản
  cài 17/09: y 28 → tâm 28,5, vẫn cao hơn hàng 6 px). Trước là {20, 20} và đầu cột 52 px: khi cột thu, đèn cao hơn
  hàng "⇅ Thư viện" ~13 px và nút đầu tiên đứng sát đèn 4 px — chủ 17/09 "vị trí các nút window… chưa đẹp") và
  nút thu/mở ở mép phải; **một đường ngang duy nhất** cho đèn · nút thu/mở · toolbar; *thân* cuộn — ở home: mục điều hướng (`RailItem`: icon + nhãn, đang chọn = `tint` +
  `ink` — 20/09, trước là `wash`; luật state layer §2) rồi nhóm **Đang đọc** (nhãn nhóm = kiểu nhãn của `GroupedSection`: xs semibold IN HOA
  `tracking-wide` `ink-mute` — chủ 17/09 "thử style khác" cho nhãn thường; tối đa 5 tài liệu có tiến độ, thứ tự `orderShelf`; engine
  chưa có mốc thời gian đọc nên "gần đây" = thứ tự kệ). Mục đích của nhóm là **cầm lại đúng chỗ**, nên mỗi hàng
  là `RailDocument` (17/09; trước đó chỉ là tên bị cắt một dòng): *bìa nhỏ* 24×36 (2:3, bo 3 px, `MiniCover`-lite:
  ảnh thật hoặc panel `tint` có gáy — 20/09, trước là `band`) mang **dải tiến độ 2 px** ở mép dưới (`brand` trên `wash`) — cùng ngôn ngữ với
  vạch dưới bìa ở kệ; *tên* tối đa **hai dòng** (`line-clamp-2`, tên tài liệu tiếng Việt dài, một dòng cắt mất phần
  phân biệt "— bản nháp thứ ba"), `title=` tên đầy đủ; *dòng dữ kiện* xs `ink-mute`: "42% · Chương 3" (phần trăm
  rồi chương, chương cắt một dòng; thiếu cả hai thì bỏ dòng; `ink-faint` đo 1,76:1 trên nền tối — không đọc được — nên dòng này cũng `ink-mute`, phân cấp bằng cỡ chữ). Hai bậc rõ (chủ 17/09: "title đậm màu hơn và spacing của
  phần description sẽ cần nhiều hơn"): tên `ink` + `font-medium`, dòng dữ kiện cách tên **6 px** (`mt-1.5`), hàng
  cách hàng 4 px như nhóm điều hướng; hover chỉ thêm nền `wash`; không có trạng thái "đang chọn" vì mở tài liệu là
  cột đổi sang danh sách của nó; trong sách: `SegmentedControl compact`
  — mỗi tab mang glyph của nút toolbar tương ứng (▤ · ghi chú · kính lúp), **tab đang mở mới có nhãn** ("Ghi chú · 6"),
  hai tab kia chỉ còn icon (chủ 16/09: "khi active thì mới có label, còn bình thường sẽ là dạng icon only" — rãnh 216
  px không đủ cho ba nhãn, "Tìm" từng bị cắt) rồi danh sách của tab đó — Reader vẫn là CHỦ ba danh sách và render chúng
  vào slot của cột bằng portal (state chương, scroll-spy, xoá ghi chú không rời Reader); *chân* — bánh răng
  Giọng đọc & mô hình · sáng/tối · ngôn ngữ, cùng một hàng. *content* = cột nội dung `relative flex-1 min-w-0`,
  header/main/footer vẫn là overlay bên trong nó, inset đo như cũ; dải trên 52 px cũng là vùng kéo. Cột thu
  = `width: 0` (transition width `--dur-move` 240 ms `--ease-standard` — 20/09, §3.17; trước là 200 ms `ease-out`; `motion-reduce` tắt; KHÔNG dùng `@starting-style` — trong
  một WKWebView bị ẩn, timeline đứng và phần tử kẹt ở trạng thái đầu, đo 16/09), thân giữ bề rộng 240 để chữ
  không gãy trong lúc thu; khi thu, đèn nằm trên góc trái của cột nội dung → dải trên chừa **88 px** (đèn
  chiếm x 20–72, rồi 16 px thở), nút mở đứng ngay cạnh đèn (Codex làm đúng thế).
  **Kéo mép phải để đổi bề rộng** (chủ 16/09: "sidebar có thể nắm kéo để resize"): tay nắm là dải 6 px đè lên hairline
  (`role=separator`, con trỏ `col-resize`, pointer capture nên kéo ra ngoài dải vẫn ăn; rê vào hoặc đang kéo thì
  hairline đậm lên — mực 35 % thay `edge`, qua `aside:has(.rail-grip:hover)`, chủ 17/09), bề rộng **200–400**, mặc định
  240, nhớ trong `localStorage["readease.sidebar-width"]` lúc thả tay (không ghi từng pixel); bấm đúp về 240; trong lúc
  kéo tắt transition (cột chạy đuổi theo con trỏ thì lag). Thu/mở vẫn là 0 ↔ bề rộng đã chọn.
- **Cửa sổ nhớ khung** (20/09, `tauri-plugin-window-state` 2.4.1): kích thước + vị trí được lưu khi thoát và trả lại
  khi mở (chỉ khi màn hình đã lưu còn đó — plugin tự kiểm; không lưu fullscreen/visible: trả cờ fullscreen lên cửa sổ
  trong suốt có title bar overlay là lỗi vibrancy kinh điển). Cửa sổ mới lần đầu vẫn 1060×720 của `tauri.conf.json`.
  Cột bên tự thu/mở theo bề rộng đã trả lại, đúng luật (2) dưới đây.
- **Behavior** (luật kiểm được, reducer thuần `ui/sidebarState.ts`): (1) **tay thắng tự động** — bấm nút hoặc
  ⌥⌘S là lựa chọn, nhớ trong `localStorage["readease.sidebar"]`; (2) chưa từng chọn → **tự động theo bề rộng**:
  cửa sổ < 1100 px thu, ≥ 1100 mở, đổi live khi kéo cửa sổ (kể cả cửa sổ mặc định 1060 → thu, để trang được
  rộng; chủ 02/09); (3) **ngữ cảnh đổi nội dung, không đổi hiển thị**: mở sách → tab Mục lục (chương đang đọc
  đánh dấu và cuộn tới), quay lại thư viện → điều hướng; (4) `show(tab)` — ▤ · nút ghi chú · nút tìm · ⌘F · icon
  ghi chú trong đoạn — MỞ cột và chọn tab; bấm lại đúng tab đang hiện = thu (công tắc thật, không cần
  `data-popover-trigger` nữa); (5) chọn chương / ghi chú / kết quả tìm → nhảy, cột GIỮ NGUYÊN (một cột không
  biến mất khi được dùng); (6) không Escape, không bấm-ngoài; (7) toolbar mang bánh răng / theme / ngôn ngữ
  CHỈ khi cột thu — cột mang gì thì toolbar bỏ nấy; tab và công cụ rời hẳn toolbar; Reader giữ back · ▤ ·
  ghi chú · tên · ⓘ · AA · tìm; (8) **tối ưu theo layout** (chủ 16/09: "UI đọc sách thì sẽ không cần icon
  sidebar"): nút mở cột chỉ có ở toolbar TRANG CHỦ khi cột thu — trong sách, ▤ / ghi chú / tìm đã là ba nút
  mở cột đúng danh sách, thêm một nút mở chung là thừa; và toolbar sách khi cột thu chỉ nhận lại nút
  sáng/tối (luật 06/09: cạnh AA), không nhận bánh răng lẫn ngôn ngữ — chúng cách một lần mở cột.
- **Tìm tô lên trang** (17/09, chủ: "thêm highlight nội dung trong bài với các keyword khớp"): trong lúc tab Tìm
  có từ khoá (≥ 2 chữ), MỌI chỗ khớp trong chương đang mở được tô `mark[data-search]` (**vàng** `--yellow-alpha-ya50` — "tìm" là màu vàng
  trên mọi máy Mac, Safari lẫn Books; đậm hơn highlight vàng ya30 của người đọc để phân biệt; chủ 17/09 đổi từ brand đỏ) — cùng
  cách khớp không dấu với danh sách (`textSearch.ts::matchRanges`, trên chữ NHƯ TRANG IN, không phải chữ gốc của đoạn,
  nên đoạn danh sách bị cắt dấu đầu dòng vẫn đúng chỗ); kết quả vừa bấm trong danh sách = `data-search="current"`
  (vàng đặc `--yellow-y100`, chữ `ink`), xác định bằng (đoạn, thứ tự khớp trong đoạn). Tô CHỒNG lên highlight của người đọc (mark lồng mark),
  không thay màu của họ; xoá từ khoá hay rời tab Tìm là trang sạch lại. Safari/Books làm đúng thế: thấy chỗ khớp
  ngay trên trang, chỗ đang đứng đậm hơn.
- **Mục lục trong cột** (18/09, chủ: "thêm một xíu gap cho các item mục lục, audit và tối ưu design"): audit — các hàng
  dính nhau (không gap) nên `band` của chương đang đọc chạm hàng trên/dưới, hàng `py-1.5` chật với tên chương hai dòng,
  và tên chương hai dòng dùng leading mặc định. Sửa: danh sách `flex-col gap-1` (4 px, cùng nhịp với nhóm điều hướng ở
  trang chủ), hàng `ListRow dense` cao hơn một nấc (`py-2`; 36 px với tên một dòng), tên chương `leading-snug`. Không
  thêm số trang/phần trăm cạnh chương (EPUB không có trang; Books cũng chỉ tô hàng đang đọc), không đổi màu chữ theo
  chương — hàng đang đọc nói bằng fill "đang chọn" của cột (`tint` từ 20/09, `band` trước đó) là đủ.
- **Hàng kết quả tìm** (17/09, chủ: "phân tích và tối ưu design của item"): mục đích của hàng là *nhận ra đúng chỗ
  khớp trong một giây* — nên (1) chỗ khớp mang **đúng màu vàng của trang** (`mark[data-search]`, không phải chip `band`
  xám semibold như trước: cùng một thứ thì cùng một màu ở danh sách và trên trang); (2) lời quanh chỗ khớp là phụ →
  `ink-mute`, chỗ khớp `ink` đậm — chip nổi khỏi câu như Spotlight; (3) kết quả **gom theo chương** (`GroupedSection
  heading="name"`), tên chương đứng một lần trên nhóm thay vì lặp "Chương 3 · Bộ mẫu trình bày" dưới từng hàng — Books
  cũng gom thế, và một màn chứa nhiều kết quả hơn; (4) dấu đầu dòng của đoạn danh sách ("• ", "1. ") bị cắt khỏi trích
  đoạn khi trích bắt đầu từ đầu đoạn — nó là dấu cho mắt trên trang, trong hàng kết quả chỉ là rác; (5) hàng `py-2`
  thay `py-1.5` cho hai dòng trích thở. Hàng đang chọn vẫn là fill "đang chọn" của cột (`tint` từ 20/09).
- **Cột trên vật liệu: mọi fill là alpha của mực** (20/09, chủ: "update UI của sidebar theo hướng dùng các màu
  alpha neutral sáng, để phù hợp với background blur"): trên `NSVisualEffectView` vật liệu CHÍNH LÀ nền, nên một fill
  đục là một tấm che — nhìn bản 0.1.8: rãnh tab và hàng chương đang đọc là hai khối n20 đục nằm trên cột mờ, ô tìm là
  một hộp n10 đặc. macOS sơn trạng thái của sidebar bằng alpha của màu chữ (`unemphasizedSelectedContentBackgroundColor`
  ≈ trắng 10–15 % ở tối, đen ~8 % ở sáng; `separatorColor` cũng alpha) để vật liệu lộ qua và tự đổi theo thứ đứng sau
  cửa sổ. Thang `neutral-alpha` của DS đúng là thứ đó — alpha phía mực, **sáng khi theme tối, tối khi theme sáng** —
  nên cột dùng nó thay cho thang đục:

  | Bậc | Token | Ở đâu trong cột |
  |---|---|---|
  | nghỉ | vật liệu (không sơn) | hàng, nhãn nhóm, chân cột |
  | lõm `veil` | na05 | rãnh của segmented control, ô tìm |
  | hover `wash` | na10 (không đổi) | mọi hàng, nút ở chân cột |
  | chọn `tint` | na20 | chương đang đọc · kết quả đang xem · mục điều hướng đang mở · tab đang mở · bìa thay thế |
  | hairline `edge-alpha` | sáng na20 · tối na10 | mép phải cột, đường trên chân cột, viền ô tìm |

  Hover và chọn cách nhau đúng một nấc (na10 → na20), cùng luật press-trên-hover của §2; `tint` trùng giá trị `press`
  nhưng là vai trò khác. Segmented trên vật liệu **không lót** (`p-0`; chủ 20/09: "không có padding, các item sẽ tràn
  viền"): tab đang mở chạy sát mép rãnh và lấy đúng góc 22 của rãnh — kiểu segmented trên toolbar của Apple; segmented
  trên giấy giữ lót 4 px (góc 18 = 22 − 4, §3.9d) vì pill giấy nổi cần rãnh quanh nó mới đọc ra là đang cưỡi trên rãnh.
  Tab đang mở **không còn shadow**: bóng dưới một fill trong suốt là vết bẩn trên kính; pill
  trắng + bóng là kiểu control trong THÂN cửa sổ (System Settings), còn control trên chrome mờ của Apple là tint phẳng
  (segmented của Finder). Hairline lệch bậc theo theme vì cùng lý do với `--app-dot`: na10 ở tối ≈ trắng 12 % (đúng
  `separatorColor`), nhưng na10 ở sáng chỉ ≈ đen 6 % — na20 mới ngang đường n20 đang có. Trong trình duyệt (mock/audit)
  cột không có vật liệu → cùng token nằm trên nền phẳng trắng/n00: vẫn đọc được (na20 trên trắng ≈ n20), và đó là SÀN
  của thiết kế, không phải bản thật — chỉ bản build mới cho thấy nó trên kính, nên thay đổi kiểu này phải nhìn bản
  cài trước khi duyệt. Hệ quả cho "một màu cho vị trí hiện tại": trên GIẤY vẫn là `band` đục (dòng đang đọc ở Reader);
  trên VẬT LIỆU là `tint` — cùng một nấc của thang, khác chất liệu; hai thứ không bao giờ đứng cạnh nhau trên cùng
  một nền. Mục điều hướng đang mở ở trang chủ đi từ `wash` lên `tint` cho cùng luật với chương đang đọc (trước đây
  mục đang mở và mục bên cạnh đang được rê chuột cùng một màu na10; nay cách nhau một bậc). Cơ chế: ba token vai trò `veil` · `tint` ·
  `edge-alpha` trong `index.css`, dùng TƯỜNG MINH ở từng chỗ — KHÔNG override token theo scope `aside`: tooltip của
  các nút trong cột là con DOM của `aside`, một override `paper` trong scope làm tooltip trong suốt (index.css ~205
  từng dính đúng lớp lỗi này); `SegmentedControl material` và `SearchField material` là biến thể có tên, ba chỗ dùng
  `SearchField` khác (Giọng đọc, Apple Books, khoá API) giữ giấy.
- **Content**: nhãn điều hướng = nhãn tab cũ (`nav.*`); nhóm "Đang đọc" (`sidebar.reading`); tab sách "Mục lục"
  · "Ghi chú" · "Tìm"; nút thu/mở `aria-label` "Thu cột bên" / "Mở cột bên", tooltip kèm ⌥⌘S.
- **Don't**: cột trên màn Setup · cột che thanh player (player nằm trong cột nội dung) · hai nơi cùng mang
  theme/ngôn ngữ khi cột đang mở · kính/blur TỰ VẼ trong cột (`backdrop-filter`) — vật liệu là của macOS (`windowEffects`), cột chỉ
  để trong suốt cho nó lộ ra · fill ĐỤC (`band`, `paper`) hay shadow trên vật liệu — xem thang alpha ở trên.

### 3.17 Chuyển động — luật motion theo Apple (20/09)

Chủ 20/09: "xây dựng animation mượt mà cho app theo tiêu chuẩn của Apple design". Trước đó app có bốn chuyển động rời
nhau — cột bên (width 200 ms `ease-out`), xếp/mở hàng dấu cỡ chữ (200 ms), lật trang (220 ms `ease-out`), màu chữ
hover (150 ms mặc định Tailwind) — còn MỌI lớp nổi (popover · menu · sheet · tooltip) hiện và biến tức thì (quyết định
15/09 ở §3.15: "không có hoạt cảnh đóng: unmount tức thì như mọi lớp" — **đảo** hôm nay: một lớp biến mất trong một
frame đọc như lỗi render, và Apple không có lớp nào rời màn kiểu đó).

**Ba nguyên tắc** (vay HIG › Motion của Apple):
1. Chuyển động để *nói* — thứ này từ đâu ra, đi về đâu, còn hay mất — không để trang trí. Mỗi lớp nổi mọc từ nút mở nó
   (`transform-origin` ở cạnh neo) và rút về đó; sheet giữa cửa sổ lớn dần tại chỗ.
2. Ngắn và chính xác: không lớp nào bắt người dùng chờ. Vào **200 ms**, ra **150 ms** — thứ đang rời đi không đáng
   nhìn bằng thứ đang tới; ra chậm ngang vào là app "dính tay".
3. Tuỳ chọn: **Reduce Motion** của hệ (`prefers-reduced-motion`) thay mọi *di chuyển* (scale, trượt, cuộn mượt) bằng
   mờ dần ngắn — giữ phản hồi, bỏ chuyển động (đúng cách Apple làm với chính họ).

**Token** (`index.css` `@theme`; ngoài thang là lỗi, như radius §6):

| Token | Giá trị | Dùng cho |
|---|---|---|
| `--dur-quick` | 120 ms | màu chữ/viền khi hover, tooltip, chip xoá, dấu chấm |
| `--dur-enter` | 200 ms | một lớp nổi hiện |
| `--dur-exit` | 150 ms | một lớp nổi biến |
| `--dur-move` | 240 ms | thứ *dời chỗ*: cột bên, hàng dấu cỡ chữ, lật trang, sheet |
| `--ease-out` | `cubic-bezier(0.2, 0, 0, 1)` | vào — giảm tốc về chỗ nghỉ |
| `--ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | ra — tăng tốc rời đi |
| `--ease-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | dời chỗ có hai đầu (cột thu/mở) |

**Bản đồ lớp** (cái gì động thế nào — và cái gì ĐỨNG YÊN có chủ ý):

| Lớp | Vào | Ra |
|---|---|---|
| popover neo nút (Cài đặt giọng · Cài đặt đọc · Chi phí · Giọng đọc & mô hình · tip "về chỗ đang đọc") | `opacity 0→1` + `scale .96→1`, `--dur-enter` `--ease-out`, gốc ở cạnh neo (`origin-top-right`, `origin-bottom-right`, `origin-bottom`) | `opacity→0` + `scale→.98`, `--dur-exit` `--ease-in` |
| sheet giữa cửa sổ (Nguồn giọng · Apple Books) + `Scrim` | sheet `scale .96→1` + mờ vào `--dur-move` `--ease-out`; scrim mờ vào `--dur-enter` | cả hai mờ ra `--dur-exit` |
| menu (`MenuButton`) | **hiện ngay** — NSMenu không có hoạt cảnh mở | mờ ra `--dur-exit` |
| tooltip (`IconButton`), peek chương / ghi chú, callout `Notice` | mờ vào `--dur-quick` (peek/Notice: `--dur-enter`, Notice trồi 4 px) | tức thì (lớp không nhận chuột, không có gì để "rút") |
| cột bên | width `--dur-move` `--ease-standard` (từ 200 `ease-out`: thu/mở có hai đầu như nhau, ease-out là cho thứ *xuất hiện*) | như vào |
| hàng dấu cỡ chữ (§3.9d) | `grid-template-rows` + opacity `--dur-move` `--ease-standard` | như vào |
| lật trang (`PageFlow`) | `transform` `--dur-move` `--ease-out` (giảm tốc về trang mới; 220 → 240 cho cùng một thang) | — |
| cuộn tới chỗ NGƯỜI DÙNG chọn (chương, kết quả tìm, ghi chú, "Về chỗ đang đọc") | `scrollIntoView({behavior: "smooth"})` — Books cũng cuộn tới, không nhảy | — |
| màu chữ/viền hover | `--dur-quick` `--ease-out` (`--default-transition-duration` của Tailwind = 120) | như vào |

Đứng yên có chủ ý: **nền hover/press của `hover-wash`** (macOS tô hover tức thì; nền là `background-image` nên cũng
không mờ dần được — đúng ý) · **theo giọng** ở Quét đọc và Reader (`block: "nearest"` tức thì: trang nhích theo từng
câu, cuộn mượt liên tục thành trang trôi) · đổi theme · hàng danh sách xuất hiện (kết quả tìm khi gõ) · mark tìm trên
trang · đổi tab cột · pill của segmented KHÔNG trượt (bản `compact` đổi bề rộng khi đổi tab, trượt sẽ méo; đổi màu
`--dur-quick` là đủ, macOS cũng không trượt).

**Cơ chế** (`ui/motion.tsx` + `index.css`):
- `Presence open={…}`: giữ con đã render thêm `--dur-exit` sau khi `open` tắt (con cuối cùng được nhớ, vì props của nó
  có thể đã mất — `speechSettings` null), đóng dấu `data-state="open|closed"` lên một wrapper `display: contents`,
  `pointer-events: none` cho MỌI thứ bên trong trong lúc ra (kể cả lớp bắt click sau editor ghi chú, nếu không nó nuốt cú
  bấm kế tiếp suốt 150 ms). Con mount ở trạng thái `closed` rồi lật sang `open` ở frame kế — KHÔNG
  `@starting-style` (WKWebView ẩn làm timeline đứng, phần tử kẹt ở trạng thái đầu, đo 16/09 §3.16).
- `Surface layer="popover | sheet | menu"`: class `.layer-*` mang transition trên **`opacity` + `scale`** (thuộc tính
  riêng, không đụng `translate` đang định vị `-translate-x-1/2` của Chi phí và Apple Books); gốc scale qua class
  `origin-*` của Tailwind do chỗ gọi đưa vào.
- Guard cửa sổ khuất: `visibilitychange` → `html[data-hidden]` → mọi transition 0 ms, để một lớp mở lúc cửa sổ khuất
  không kẹt ở opacity 0.
- Reduce Motion: `@media (prefers-reduced-motion: reduce)` đặt `--dur-move: 0ms`, scale = 1 và trồi = 0 ngay từ đầu,
  giữ mờ dần ≤ 100 ms; JS hỏi `matchMedia` (`ui/motion.ts::scrollBehavior()`) cho `scrollIntoView`.
- Chỉ animate `opacity` · `scale` · `translate` (compositor, 60 fps trên `glass-panel` có blur 28 px). Ngoại lệ có chủ
  ý và đã có: width cột bên, `grid-template-rows` hàng dấu (layout, ngắn, một phần tử).
- Đo (mock, Chromium — WebKit thật chỉ trên bản cài): sau khi mở, `opacity` tại 0 / 100 / 250 ms tăng dần tới 1; sau
  khi đóng, phần tử còn đó với `pointer-events: none` ở 50 ms, biến khỏi DOM trước 300 ms.

**Don't**: `transition: all` · animate `width/height/top/left` cho lớp nổi · hoạt cảnh ra dài bằng hoạt cảnh vào · một
số ms viết tay trong màn (mọi thời lượng đi qua token) · hoạt cảnh cho thứ người dùng không nhìn (đổi theme, danh
sách đang gõ) · trượt-vào cho popover (Apple: popover *lớn ra* từ neo, sheet *lớn ra* tại chỗ; trượt là của banner).

### 3.18 Mở tài liệu từ Finder, Dock và "Open With" (20/09)

Kiểm kê 20/09: app không khai loại tệp nào (`bundle.fileAssociations` trống) — bấm đúp một EPUB trong Finder mở Books,
kéo tệp lên icon Dock của ReadEase bị từ chối, menu "Open With" không có ReadEase. Một app tài liệu chuyên nghiệp phải
là một *người mở* của loại tệp nó đọc.

- **Khai báo** (`tauri.conf.json` › `bundle.fileAssociations`): EPUB (`org.idpf.epub-container`, `application/epub+zip`)
  và PDF (`com.adobe.pdf`) với vai **Viewer**, hạng **Alternate** — app đọc được, có mặt trong "Open With" và nhận drop
  trên Dock, nhưng KHÔNG tự chiếm chỗ mặc định của Books/Preview (đó là lựa chọn của người dùng, không phải của bản cài).
- **Đường đi**: macOS gọi `RunEvent::Opened { urls }` (bấm đúp · Dock · Open With · `open -a`). Host xếp đường dẫn vào
  hàng `OpenedFiles` rồi nhắc trang bằng `files:opened` (không mang payload); trang **rút hàng** (`take_opened_files`)
  khi vừa dựng xong VÀ mỗi lần được nhắc — vì tệp mở app thì đến TRƯỚC khi webview tồn tại, còn tệp mở khi app đang chạy
  thì đến sau; rút hàng là idempotent nên không tệp nào mở hai lần hay rơi mất.
- **Trang làm gì**: lọc đúng đuôi (`bookPaths`), nhập từng tệp qua `library.import` (idempotent — engine băm nội dung,
  tệp đã có thì trả về đúng bản đã có, không nhân đôi kệ), nạp lại kệ, rồi **mở tệp cuối** trong danh sách — đúng như
  Preview mở tệp vừa bấm; các tệp còn lại nằm trên kệ. Đang đọc dở một tài liệu khác thì cũng chuyển sang tài liệu vừa
  mở (cùng hành vi với bấm một bìa trên kệ). Tệp hỏng → ghi `stderr`, không cửa sổ lỗi: người dùng đã ở trên kệ và thấy
  tệp không xuất hiện; báo lỗi có tên tệp là việc sau, chung với thông báo của kệ.
- **Don't**: khai `Owner`/`Default` (cướp mặc định của hệ) · nhận tệp bằng `argv` (macOS không đưa tệp qua argv, chỉ qua
  Apple Event `odoc`) · mở bằng event mang payload rồi bỏ hàng (mất tệp mở-lúc-khởi-động).

### 3.19 Now Playing và phím media — app đọc là một app âm thanh của hệ (20/09)

Kiểm kê 20/09: giọng đang đọc mà bấm F8 (⏯) trên bàn phím, bóp cuống AirPods, hay mở Control Center › Now Playing —
không có gì. Với macOS, ReadEase không phải một thứ đang phát; Music, Podcasts, Books (đọc to) đều là. Một app đọc
thành tiếng phải đứng vào chỗ đó.

- **Hợp đồng**: khi một bài đọc bắt đầu, app trở thành *now-playing app* của hệ — Control Center và thanh menu Now
  Playing hiện tên tài liệu (chương ở dòng dưới), nút ⏯ / ⏹ điều khiển ĐÚNG bài đọc đó; **F7/F8/F9 và tai nghe** (bóp
  cuống AirPods = toggle) đi tới app kể cả khi cửa sổ không ở trước hay đang ẩn. Tạm dừng thì hệ hiện "paused"; đọc xong
  hay dừng thì **rút khỏi** Now Playing (không để một ReadEase "đã dừng" đứng mãi trong Control Center).
- **Tên hiện**: tài liệu → tên tài liệu / chương đang đọc; Dán nội dung → "Dán nội dung" / "ReadEase"; Quét đọc → "Quét
  đọc" / "Phần đã chọn".
- **Ảnh bìa** (21/09): tài liệu có bìa thì Control Center / thanh menu Now Playing hiện bìa (như Music hiện album).
  Trang đã có bìa dưới dạng data-URL (`useCover`, cache theo id) nên trang gửi; host nhận `artwork { key,
  data? }` — `key` là id tài liệu, `data` (base64) chỉ đi kèm **lần đầu** cho key ấy (trang nhớ key đã gửi), các lần
  sau (tạm dừng/tiếp tục, đổi chương) chỉ gửi key: `now_playing` bắn ở mọi đổi trạng thái, không gửi 100–200 KB mỗi
  lần. Host giữ bytes theo key (`ArtworkCache`, một ảnh), dựng `NSImage` từ `NSData` rồi `MPMediaItemArtwork`
  (`initWithBoundsSize:requestHandler:` — block giữ `Retained<NSImage>` và trả `NonNull` vào nó, MediaPlayer giữ
  block) trên main thread cùng `apply`. Không bìa hay ảnh hỏng → dict không có `MPMediaItemPropertyArtwork`, hệ hiện
  icon app như trước. Dán nội dung / Quét đọc: không ảnh.
- **Cơ chế** (`src-tauri/src/media.rs`, `objc2-media-player` 0.3.2 — API đọc từ mã nguồn crate, không từ trí nhớ): host
  đăng ký ở `setup` (main thread) bốn lệnh của `MPRemoteCommandCenter` — togglePlayPause · play · pause · stop — mỗi lệnh
  bắn `media:command` về trang, giữ target trả về để handler sống suốt đời app; **tắt** nextTrack/previousTrack để Control
  Center không vẽ nút vô dụng. Trang gọi lệnh `now_playing { title, subtitle, state }` mỗi khi trạng thái đọc hay nguồn
  đọc đổi; host đặt `MPNowPlayingInfoCenter.nowPlayingInfo` (title · artist · mediaType audio · playbackRate 1/0) và
  `playbackState` **trên main thread** (`run_on_main_thread`); `stopped` = xoá info + `Stopped`.
- **Trang trả lời** `media:command` qua CÙNG bộ điều phối của menu (§4.1): toggle → `play-pause`; play chỉ khi đang tạm
  dừng, pause chỉ khi đang đọc (lệnh trái trạng thái bị bỏ qua, không bật/tắt ngược); stop → `stop`. Vì thế mục này xếp
  trên menu bar: một chỗ cho mọi lệnh, dù đến từ menu, phím hay tai nghe.
- **Mock**: `now_playing` trả `null`; không có gì để chứng minh ngoài cửa sổ — phím media chỉ tới app khi app đã là
  now-playing app, nên bằng chứng duy nhất là F8/AirPods trên bản cài.
- **Don't**: giữ Now Playing sau khi đọc xong · đăng ký handler nhiều lần (mỗi lần dựng lại = một handler nữa) · gọi
  MediaPlayer ngoài main thread · bật lệnh mà app không làm được.

### 3.20 Cập nhật trong app — "Kiểm tra bản mới…" (20/09)

Kiểm kê 20/09: bản mới chỉ đến với người dùng nếu họ tự quay lại GitHub. Một app Mac tự nói khi có bản mới và tự thay
mình (Sparkle là chuẩn; Tauri có `tauri-plugin-updater` 2.12.0 + `tauri-plugin-process` 2.3.1 để khởi động lại).

- **Chỗ đứng**: mục **Kiểm tra bản mới…** ngay dưới *Giới thiệu* trong menu ReadEase — đúng ô Apple dành cho nó. Khi mở
  app, **5 s sau** app hỏi lặng lẽ một lần; CÓ bản mới thì một viên nhỏ nổi giữa mép trên trang ("Có ReadEase 0.1.10 ·
  Xem"), KHÔNG có thì im, hỏi không được (mất mạng, GitHub lỗi) cũng im — lỗi chỉ hiện khi chính người dùng bấm kiểm tra.
- **Sheet "Bản mới"** (`ui/UpdatePanel.tsx`, `Surface layer="sheet"` + `Scrim`, §3.17): các trạng thái *đang kiểm tra* →
  *đang dùng bản mới nhất (x.y.z)* / *có bản x.y.z* (ngày, ghi chú phát hành rút gọn, **Tải và cài** · Để sau) → *đang
  tải… n %* → *đã cài, khởi động lại để dùng* (**Khởi động lại**) / *không kiểm tra được* (câu lỗi + **Mở trang phát
  hành** làm lối thoát thủ công). Đang tải thì Escape/bấm ngoài không đóng (giấu việc đang chạy = luật panel Chất lượng).
- **Cơ chế**: `useUpdater()` gói `check()` / `downloadAndInstall(onEvent)` / `relaunch()`; endpoint cố định
  `https://github.com/wblekhoa/readease/releases/latest/download/latest.json`; chữ ký minisign kiểm bằng khoá công khai
  nhúng trong `tauri.conf.json › plugins.updater.pubkey`. Không cấu hình `requireSignedVersion` (CLI 2.11 chưa chắc ghi
  version vào trusted comment) và không `allowDowngrades`.
- **Phía phát hành** (`scripts/build-release-app.sh`, SAU khi staple — thứ tự là cái bẫy: bundler tạo artifact cập nhật
  lúc `tauri build`, TRƯỚC khi ta ký lại/notarize, nên KHÔNG bật `createUpdaterArtifacts`): `tar -czf ReadEase.app.tar.gz`
  từ app đã staple → `tauri signer sign` bằng khoá riêng ở `~/.tauri/readease.key` (mật khẩu trong `Apps/.env`
  `TAURI_SIGNING_PRIVATE_KEY_PASSWORD_READEASE`, không bao giờ in) → `.sig` → `latest.json` { version, notes, pub_date
  RFC 3339, platforms."darwin-aarch64".{signature, url} } với url = asset của release. Release phải upload **zip + dmg +
  tar.gz + latest.json**. Thiếu khoá thì script bỏ qua bước này và nói rõ.
- **Cửa sổ `.dmg` có nền** (22/09, Phase 3): app bên trái, Applications bên phải, mũi tên xanh brand ở giữa và một dòng
  "Kéo ReadEase vào Applications để cài" (VI + EN) — `assets/branding/dmg-background.png` + `@2x` (vẽ bằng
  `scripts/build-dmg-background.py`, chữ SF của hệ vì cửa sổ Finder là của Mac, không phải của app), bố cục
  `scripts/dmg-settings.py` cho `dmgbuild` (qua `uvx`, ghim 1.6.7): nó tự viết `.DS_Store`, gộp TIFF HiDPI bằng
  `tiffutil`, gắn icon volume, mount `-nobrowse` — không mở cửa sổ Finder nào lúc build. Không có `uvx` thì về ảnh
  trơn như trước. Vị trí icon (165,175)/(495,175) trong khung 660×400 là hợp đồng giữa ảnh và settings.
- **Hành vi kiểu Sparkle** (22/09, chủ hỏi khi thấy LidRun; chốt "theo đề xuất tối ưu nhất"): bộ cập nhật giữ nguyên
  (plugin đã chứng minh 0.1.10 → 0.1.11), thêm đúng những hành vi người dùng Mac chờ ở Sparkle — và bỏ viên nổi:
  - **Bỏ qua phiên bản này**: nhớ `readease.update.skipped`; kiểm tra lặng bỏ qua đúng phiên bản đó, kiểm tra bằng tay
    vẫn hiện. **Để sau** = im tới lần mở app sau (không viên nổi, không nhắc lại).
  - **Mục menu đổi chữ** thay cho viên nổi: *Kiểm tra bản mới…* → *Đã có ReadEase 0.1.12 — Cập nhật…* khi biết có, →
    *ReadEase 0.1.12 đã sẵn sàng — Cài đặt…* khi đã tải. Đó là chỉ báo thường trực, không chen vào trang.
  - **Cài đặt khi thoát**: tải ngay, cài lúc thoát app, KHÔNG khởi động lại — app đọc không bao giờ cắt ngang một bài
    đang nghe. Host chặn `CloseRequested`/`ExitRequested` khi có bản đã tải chờ cài, bảo trang cài (`update:install-now`),
    trang cài xong gọi `exit_now`; lưới an toàn: 60 s không thấy trang trả lời thì host tự thoát.
  - **Tự động tải và cài bản mới** (ô trong sheet, **mặc định tắt**, nhớ `readease.update.auto`): bật thì kiểm tra lặng
    tải luôn (115 MB — vì thế mặc định tắt, không âm thầm kéo qua 4G) và tự đặt cài-khi-thoát; sheet nói "đã sẵn sàng".
  - Sheet ghi **phiên bản · ngày phát hành** (`pub_date` của manifest); giữ sheet, không mở cửa sổ riêng (Apple không
    đòi; cửa sổ thứ hai trong Tauri là thêm webview + IPC mà không thêm gì cho người dùng).
  - Không hiện sheet giữa lúc đang đọc: sheet chỉ mở khi người dùng bấm; kiểm tra lặng chỉ đổi chữ menu.
- **Sự thật về bằng chứng**: 0.1.9 chưa có updater. Bản đầu tiên mang nó (0.1.10) chỉ chứng minh được *đường kiểm tra*
  (thấy "đang dùng bản mới nhất"); đường tải-cài-khởi động lại chỉ chạy thật khi **0.1.11 cập nhật 0.1.10**. Dry-run tại
  chỗ: tar + ký + dựng `latest.json` từ bản build ký, kiểm chữ ký bằng khoá công khai.
- **Mất khoá = hết cập nhật tại chỗ**: khoá công khai nằm trong mọi app đã phát; đổi khoá là người dùng cũ phải tải tay
  một lần. Chủ tự sao lưu `~/.tauri/readease.key` + mật khẩu.
- **Don't**: dialog khi kiểm tra lặng lẽ thất bại · tự tải khi chưa bấm (người dùng quyết) · ghi mật khẩu vào log/commit
  · bật `createUpdaterArtifacts`.

### 3.21 Loa nào đang phát — thiết bị ra âm nói tên (20/09)

Ghi chú của chủ 20/09: "app chưa nghe được Multi-Output device" + "tối ưu theo hệ thống". Đo (probe `audio-probe`, cùng
cpal 0.17.3 + rodio 0.22.2 với app): một Multi-Output (aggregate stacked) mở được và phát real-time — thiết bị không
phải chỗ hỏng. Chỗ hỏng thật là **không ai biết app đang phát ra đâu**: host mở sink một lần lúc khởi động bằng
`open_default_sink()` của rodio — thứ này khi mặc định không mở được sẽ *lặng lẽ* lấy thiết bị khác đầu tiên (trên máy
chủ: một màn hình), không log, không báo trang, không error-callback.

- **Host** (`engine.rs::open_output`): mở đúng **thiết bị mặc định của hệ theo tên**; chỉ khi nó không mở được mới
  thử thiết bị khác, và **nói to** ở cả hai phía — `stderr` `[audio] opened "…"` (kèm "NOT the system's default
  output" khi phải rơi) và sự kiện `audio:device {name, default}`; stream lỗi giữa chừng → `[audio] stream error`.
  Lệnh `audio_output` để trang hỏi sau khi đã dựng (sự kiện lúc khởi động bắn trước khi có trang).
- **Trang**: *Cài đặt giọng đọc* có hàng **Loa** ghi tên thiết bị đang phát; khi không phải mặc định, hàng nói thẳng
  "không phải thiết bị mặc định của hệ" — người dùng Multi-Output thấy ngay giọng đi đâu, và phép thử A/B (đổi output
  khi app đang chạy / chọn trước rồi mở app) trả lời bằng một dòng chữ thay vì bằng tai.
- **Chưa làm, có điều kiện**: đi theo thiết bị mặc định KHI NÓ ĐỔI lúc app đang chạy (listener
  `kAudioHardwarePropertyDefaultOutputDevice` → mở lại sink, bài đọc dở đọc lại từ vị trí vừa báo). cpal mở thiết bị
  mặc định bằng unit `DefaultOutput` nhưng ghim `CurrentDevice`; Apple không nói unit có còn theo mặc định không — chỉ
  phép thử A trên bản cài trả lời được (đổi output mặc định của máy là cài đặt hệ thống, AI không đụng). A hỏng → làm.

### 3.22 Nhật ký — "Báo lỗi" có gì để gửi (21/09)

Kiểm kê 21/09: host và sidecar viết chẩn đoán ra `stderr` (`[audio] opened …`, `[shortcut] …`, lỗi engine) — khi app
mở từ Finder, `stderr` không đi đâu cả. Trợ giúp › *Báo lỗi hoặc góp ý* mở một issue mà người dùng không có gì để đính
kèm ngoài lời kể.

- **Tệp**: `~/Library/Logs/ReadEase/readease.log` — đúng chỗ Console.app và mọi app Mac ghi. Host làm một việc ở đầu
  `run()`: nếu `stderr` KHÔNG phải terminal (tức mở từ Finder/Dock), mở tệp ở chế độ ghi thêm rồi `dup2` lên fd 2 —
  mọi `eprintln!` của host, `stderr` thừa kế của sidecar Python và của các dylib đều rơi vào tệp mà không phải sửa
  một dòng gọi nào. Chạy `tauri dev` (stderr là terminal) thì giữ nguyên ra terminal.
- **Xoay vòng**: lúc mở, tệp > 2 MB thì đổi tên thành `readease.log.1` (giữ một thế hệ) rồi bắt đầu tệp mới; mỗi lần
  mở ghi một dòng đầu `=== ReadEase <version>+<build> · <thời điểm> ===` để một tệp chứa nhiều phiên vẫn đọc được.
- **Vào tệp**: Trợ giúp › **Mở thư mục nhật ký** (`revealItemInDir` của opener — Finder hiện tệp được chọn). Lệnh
  `log_path` cho trang biết tệp ở đâu.
- **Riêng tư** (chủ chốt 21/09: chỉ dòng kỹ thuật): host không ghi tên tài liệu, nội dung, đường dẫn tệp của người
  dùng vào nhật ký (lỗi nhập tài liệu ghi ở console của trang, không ra stderr). Sidecar ghi gì thì sidecar chịu — cần
  rà một lượt riêng; tệp nằm ở máy người dùng, họ tự quyết định có đính kèm không.
- **Mẫu issue** (`.github/ISSUE_TEMPLATE/bug.yml`): phiên bản (từ Giới thiệu ReadEase), macOS, chuyện gì xảy ra, các
  bước, và ô dán vài dòng cuối nhật ký (tuỳ chọn) — để một báo cáo có đủ ba thứ người sửa cần.
- **Don't**: `dup2` khi stderr là terminal (mất log dev) · ghi nội dung tài liệu · giữ nhật ký không giới hạn.

### 3.23 Tiếp tục sau khi tạm dừng lâu — lùi về đầu câu (21/09)

Đề xuất 02/09 (`docs/reading-flow-proposal.md` §A), chủ nêu lại trong kế hoạch 21/09: tạm dừng rồi tiếp tục là nhảy
THẲNG vào giữa câu — tai mất mạch. Audible, Apple Books (đọc to), Voice Dream đều lùi một nhịp khi tiếp tục sau một quãng
nghỉ; ReadEase làm cùng một việc, theo CÂU thay vì theo giây, vì câu là đơn vị của giọng.

- **Hợp đồng**: bấm tiếp tục sau khi đã tạm dừng **từ 30 giây trở lên** (đo bằng đồng hồ tường, `SystemTime` — máy
  ngủ qua đêm vẫn tính; `Instant` trên macOS đứng yên khi máy ngủ nên không dùng) → giọng đọc lại **từ đầu câu đang
  dở**; nếu điểm dừng rơi vào khoảng lặng giữa hai câu (chỗ người ta hay bấm dừng — cuối một hơi), câu vừa xong được
  đọc lại. Tạm dừng ngắn hơn 30 s → tiếp tục đúng chỗ, không lùi. Highlight KHÔNG nhảy lùi (mốc vị trí đã báo thì đã
  báo), chỉ giọng lùi; tiến độ lưu không đổi.
- **Vì sao ở host, không ở engine**: engine đi trước tai tới ~47 khung (`ENGINE_WINDOW`) và không "gỡ tổng hợp" được;
  chỉ host giữ đúng phần âm thanh tai đã nghe. Vòng `drain` giữ **bóng** của các khung đã đưa vào thiết bị kể từ đầu
  câu trước đó (mỗi khung mang cờ `from_voice` của engine — khoảng lặng giữa câu, nghỉ đoạn, chuông chương, báo hình
  đều là `false`, nên "đầu câu" = khung có tiếng đứng sau một khung không tiếng — một luật cho mọi mối nối). Bóng được
  cắt bớt khi tai đi qua: chỉ giữ hai câu gần nhất đã bắt đầu phát + phần còn trong thiết bị; trần cứng **một phút**
  âm thanh (`SHADOW_MAX_SAMPLES`) phòng engine gửi một mạch không nghỉ — quá trần thì phần sau lưng tai đi trước.
- **Cơ chế**: `pause()` ghi thời điểm; `resume()` sau ≥ 30 s ghi **yêu cầu lùi** vào một ô chung (như cờ `paused`)
  rồi hạ `paused` — KHÔNG tự `play()`; luồng audio xử lý yêu cầu ở mọi chỗ nó chờ (vòng lookahead, vòng chờ `Done`,
  nhánh timeout, và trước khi phát khung mới): `clear()` thiết bị, đưa lại các khung từ đầu câu đích tới hết bóng,
  **không tăng `appended`** — nhờ vậy `appended − queued` vẫn là chỉ số khung đang ở tai và các mốc vị trí đang chờ
  (`due`) tự bắn đúng chỗ khi tai đi qua lần nữa (lỗi highlight-sớm 15/09 không quay lại); rồi `play()` nếu người
  dùng chưa bấm tạm dừng lại trong 20 ms đó. Bóng và thời điểm dừng bị bỏ khi epoch đổi (`stop`/`fire`).
- **Chỉnh được** (chưa làm): luật "nghe > 80 % câu thì lùi thêm câu trước" của đề xuất; ngưỡng 30 s.
- **Bằng chứng**: test trên harness `FakeSink` — dừng ngắn: không `clear`; dừng dài: một `clear` rồi đúng các khung
  của câu đích trở đi, số `reading:position` không đổi qua lần lùi; nghe thử trên bản cài.
- **Don't**: lùi khi dừng ngắn · gọi `play()` từ `resume()` khi có yêu cầu lùi (phát 20 ms chỗ cũ rồi mới lùi) · tăng
  `appended` khi đưa lại khung · lùi bằng một `read.book` mới từ đầu ĐOẠN (đoạn dài = lùi cả phút, và mất cả phần đã
  tổng hợp phía trước).

### 3.24 "Còn ~N phút" — biết còn nghe bao lâu (21/09)

Đề xuất 02/09 (`docs/reading-flow-proposal.md` §A): người nghe không biết mình đang ở đâu và còn bao lâu. Apple Books
(đọc to) và Audible đều ghi thời gian còn lại cạnh transport. ReadEase nói **còn bao lâu tới khi lượt đọc này dừng**
— tức tới hết phạm vi đã chọn (§3.5 "Đọc tới đâu": chương này / N chương / hết tài liệu). Một định nghĩa, đúng ở mọi
chỗ hiện.

- **Nguồn số** (engine, không phải trang): engine biết chính xác số ký tự sẽ NÓI (cùng chuỗi `speakable_text` mà
  `estimate` đếm tiền) và số giây âm thanh nó đã phát ra — kể cả khoảng lặng, sau bộ kéo giãn tốc độ. Mỗi sự kiện
  `position` mang `remaining_s` = ký tự còn lại của lượt đọc (từ đoạn này tới hết) × nhịp; trả lời `estimate` mang
  `remaining_s` tính từ **điểm sẽ tiếp tục** (không phải từ đầu phạm vi như tiền — tiền là trần, thời gian là dự báo).
- **Nhịp** (`playback/pace.py`): đo ngay trong lượt đang đọc — giây phát ra ÷ ký tự đã nói, quy về 1× — và nhớ theo
  giọng trong phiên; **10 giây đầu** chưa đủ tin thì dùng mặc định theo ngôn ngữ, đo 21/09 bằng probe hai đoạn văn
  bịa (~1 100 ký tự mỗi đoạn, rate 1,0, bản cài fp32): VieNeu (Minh Đức) **14,5 ký tự/s** (14,66 · 14,45; đoán đoạn
  B từ đoạn A sai −1,4 %), Kokoro (af_heart) **16,0 ký tự/s** (16,33 · 16,00; sai −2,0 %). Cổng kế hoạch < 15 % — đạt.
  Tốc độ đọc r: giây = ký tự ÷ (nhịp × r).
- **Hiện ở đâu** (luật "đừng hiện quá nhiều thông tin": KHÔNG thêm chrome): (1) đang đọc và đứng đúng nguồn → ô TRÁI
  footer, chữ xám nhỏ, chỗ đến nay bỏ trống khi đọc: "Chương này · còn ~52 phút" / "3 chương · còn ~1 giờ 5 phút" /
  "còn ~3 giờ 10 phút" (hết tài liệu — không cần nói phạm vi); (2) rảnh, trong tài liệu → dòng thứ ba của tooltip nút ⓘ
  (§3.9: "Trang 12/300 · Đã đọc 41 %" + tên chương + dòng này), từ `estimate`. Số tròn: dưới 30 s → "dưới 1 phút";
  tới 59 phút → phút; từ 60 → "N giờ M phút" ("N giờ" khi M = 0). Luôn có dấu "~": đây là dự báo.
- **Không hiện**: Dán nội dung / Quét đọc (lượt ngắn, không có phạm vi để nói) — `remaining_s` vẫn có trong sự kiện
  nhưng trang không vẽ; và khi đã rời nguồn (ô trái đang nói "Đang đọc: …" + Quay lại).
- **Don't**: hằng số nhịp viết tay không đo · tính ở trang từ chữ hiển thị (khác chuỗi engine nói: chú thích, "Xem
  hình", chữ hét đã hạ) · nói "còn" mà không nói phạm vi khi phạm vi là một chương · em dash trong chuỗi.

### 3.13 Giọng đọc: một nơi chọn, một nơi đổi (03/09)

Máy có **20 giọng**. Hai việc khác nhau, hai chỗ khác nhau:

- **Chọn** (`VoicesPanel`, sheet 32rem) — nghe thử + bật vào danh sách. Mỗi hàng `GroupedRow roomy`:
  tên (+ "đang dùng"), một dòng mô tả `Nữ · Bắc · Phong cách kể chuyện` tách từ nhãn engine, `IconButton`
  loa để nghe thử, `Switch` (control mới trong kit) để đưa vào danh sách. Chân sheet đếm "Đã chọn N giọng".
- **Đổi** (`MenuButton` loa ở thanh transport, chỉ hiện khi đang phát) — chỉ liệt kê **danh sách đã bật**
  + giọng đang dùng + "Quản lý giọng…". Đây đúng là định nghĩa của danh sách: giọng đáng với tay khi đang nghe.
- `SettingsPanel`: select giọng cũng **chỉ liệt kê danh sách đã bật** (chủ chốt lại 03/09 — một danh sách
  thì là một danh sách ở mọi nơi; hàng ngay dưới nó là lối thêm vào), và **không còn khoá khi đang đọc**.
- **Bật sẵn NĂM giọng khi chưa từng chọn** (chủ, 03/09: "đừng tắt hết"): không ai mở app lên là muốn nghe
  thử hai mươi giọng trước khi đọc được sách. Năm giọng đó là một **dải**, không phải bảng xếp hạng — không
  có dữ liệu dùng thật để xếp: giọng mặc định của engine, một giọng tự nhiên mỗi giới, và một giọng kể
  chuyện mỗi giới (thứ một cuốn sách hay cần). Giọng nào bản dựng này không có thì bỏ, không mời.
  **"Chưa từng chọn" khác "đã chọn là rỗng"**, và chỉ cái đầu được mồi — nếu không, người tự tay tắt hết
  sẽ thấy chúng bật lại nguyên si ở lần mở app sau (`initialShortlist`, 3 test).
- Một lớp nổi tại một thời điểm: bấm chip cài đặt ở footer **đóng** sheet giọng (nếu không, panel cài đặt
  mở NGAY DƯỚI sheet, nơi không ai với tới).

**Nghe thử không dùng được lúc đang đọc** — đó là sự thật của engine, không phải lựa chọn giao diện:
máy đọc mỗi lúc một thứ, nên một câu mẫu sẽ **huỷ chính chương** mà nó định giúp bạn chọn giọng cho.
Nút nghe thử bị khoá kèm câu giải thích ở tooltip và ở chân sheet. Nghe thử khi rảnh, đổi khi đang đọc.

**Đổi giọng giữa chừng = đọc lại từ ĐOẠN đang đọc, bằng giọng mới.** Engine không hoán giọng giữa câu
(giọng được chốt lúc bắt đầu), nên vết nối là **đầu đoạn hiện tại**, không phải đúng chữ đang đọc —
mịn hơn thì engine phải biết nó đang ở đâu trong đoạn âm thanh. Để việc này thật với **cả văn bản dán và
đoạn quét**, `read` nay đánh địa chỉ từng phần (`part-N`) và nhận `segment_id` y như `read.book`.
Tốc độ vẫn đọc-một-lần lúc bắt đầu nên vẫn khoá — thà khoá còn hơn hứa suông.

**MỘT kiểu danh sách cho cả product** (chủ, 03/09: "đồng bộ cho list tương đồng ở các nơi khác"):
`GroupedSection` **chính nó** nay là danh sách chấm - không còn thẻ xám kiểu iOS. Thẻ xám đúng cho hai ba
dòng cài đặt, nhưng đặt trong một sheet trắng là **hộp trong hộp**, đúng điều DS cấm ("no box-in-box:
card treatment max depth = 1"), và màu xám đánh nhau với mọi panel nó ngồi lên. Hàng **không tự đệm trái
phải** (panel đã lo lề) và thở bằng đệm dọc (`py-3.5`, roomy `py-4`). Đổi ở kit nên Cài đặt giọng đọc,
Chất lượng, Transfer và danh sách giọng đều đi theo cùng lúc - kit chỉ còn MỘT kiểu danh sách.

**Dot divider theo đúng DS**: chấm 2px trên nhịp 8px vẽ bằng `radial-gradient`, utility `dot-divided` đặt
cạnh `hover-wash` trong `index.css`. **Không dùng `border-style: dotted`** - DS bác bỏ vì nhịp chấm đổi
theo engine và theo độ dài đường kẻ (`DOL-DS-token/.../layout-structure-family.md`).

**Màu chấm là `--color-dot`, một ROLE riêng chứ không phải alias** (chủ xin nhạt hơn, 03/09): kẻ chấm vốn
đã nhẹ hơn kẻ liền - chỉ một phần tư được tô mực - nên bậc `edge-strong` quá đanh khi đổ xuống hai mươi
dòng. Nhưng hai nền cần HAI bậc DS khác nhau để ra cùng một độ nhạt: sáng dùng `edge`; tối mà cũng dùng
`edge` thì là n(45) trên nền n(38) - lệch bảy điểm, **biến mất** - nên tối giữ `edge-strong`, so với nền
của chính nó thì không nặng hơn `edge` trên nền sáng.

**Tooltip của nút icon nằm TRONG `IconButton`** (chủ, 03/09): truyền `title` là có tooltip có kiểu, và
`title` bị gỡ khỏi DOM để không chồng với tooltip của trình duyệt — thứ đợi cả giây, do hệ điều hành vẽ
theo một kiểu không giống gì trong app, và trên màn cảm ứng thì không hiện. Đặt ở kit nên **mọi nút icon
trong product** có cùng lúc, không màn nào phải nhớ tự thêm. Vẽ qua **portal** và định vị từ hình chữ nhật
đo được: nút icon có thể nằm trong cột đã `transform` của trang sách hoặc trong panel bị cắt, mà `fixed`
một mình KHÔNG sống sót qua một tổ tiên có transform. Đo trước rồi mới kẹp, nếu không nút ở sát mép sẽ
canh giữa tooltip ra nửa ngoài màn hình (đo: nút nền tối ở x=1004, tooltip 912-1048 trong cửa sổ 1060).
**Chữ tooltip là HÀNH ĐỘNG, ngắn**: "Chuyển sang lật trang", không phải "Đang cuộn · bấm để lật trang".
**Tooltip đợi một nhịp như help tag của macOS** (20/09, chủ duyệt sau khi được hỏi): rê vào **600 ms** mới hiện —
help tag của Apple cũng chờ, và tooltip hiện ngay từng làm cả toolbar nhấp nháy tên khi con trỏ lướt qua một hàng
nút. **Chuỗi nóng**: một tooltip vừa hiện thì nút kế bên hiện *ngay* nếu tới trong 400 ms (đúng cách macOS làm khi
đã "mở" help tag, người đang dò tên từng nút không phải chờ lại từng cái). Focus bàn phím hiện ngay (không ai gõ Tab
để rồi chờ). Rời nút trước hạn thì không hiện gì và không nợ gì (timer bị huỷ). Ghi chú 03/09 phía trên chê tooltip
trình duyệt "đợi cả giây" — cái bị chê là KIỂU VẼ của hệ và việc không hiện trên cảm ứng, không phải độ trễ; độ trễ
là đúng.
*Còn thiếu*: nút **đang bị vô hiệu** không hiện tooltip — trình duyệt không phát sự kiện chuột trên control
bị disable; muốn có phải bọc thêm một thẻ ngoài.

**Một khoảng cách, một trần cao cho mọi lớp nổi** (chủ, 03/09):

- **`--layer-gap` = 8** cho mọi lớp treo dưới thứ mở nó. Trước đó là 4 dưới menu, 6 dưới tooltip, 8 dưới
  panel — ba con số cho cùng một quan hệ. Lớp định vị bằng đo (tooltip icon, bong bóng ghi chú) dùng hằng
  `LAYER_GAP = 8` trong `controls.tsx`. Đo lại sau khi sửa: cả ba tooltip đều 8, menu 8.
  *Ngoại lệ có lý do*: panel cài đặt treo 8 trên **thanh footer**, không phải trên cái chip — chip thuộc
  về thanh, và một panel đè lên thanh sẽ đọc như lỗi.
- **`layer-capped`** (utility) chặn chiều cao bằng đúng khoảng trống giữa hai thanh: panel dài thì **tự
  cuộn bên trong** thay vì mọc lên dưới header. Panel cài đặt nay tách tiêu đề đứng yên / thân cuộn như
  bảng ghi chú; menu cũng bị chặn (danh sách 20 giọng không được dài quá màn).

  **Vì sao là utility chứ không phải một token** — và đây không phải chuyện thẩm mỹ: một custom property
  khai ở `:root` bị **thay `var()` ngay tại `:root`**, nên `--layer-max-h` đã nướng cứng cặp inset khởi tạo
  (72px/0px) và không bao giờ thấy 76px mà ResizeObserver đo lên shell. Viết thành utility thì phép `calc`
  giải ở chính phần tử dùng, nơi có số thật. Đo sai trước rồi mới ra (436px đúng, 516px sai).

**Đệm của lớp nổi, hai tầng** (chủ: "đồng bộ padding các popover"): **panel** (cài đặt · sheet Apple Books ·
sheet giọng) đặt nội dung vào **24**; **menu gồm các hàng** (popover mục lục · menu đổi giọng) chỉ có khung
**8**, vì ở đó chính HÀNG mang lề. Tooltip giữ thang chật riêng.

**Ba cái bẫy đã bịt** (kiểm trên harness): id giọng mới truyền thẳng vào lệnh chứ không đọc lại từ state
(`setVoiceId` chưa kịp về là gửi nhầm giọng cũ); nghe thử **xoá `origin`** nếu không chip "Đang đọc: …
/ Quay lại" sẽ trỏ về cuốn sách mà chính nghe-thử vừa cắt; `part-N` không phải segment của sách nên nút
⏮/⏭ và highlight của Reader đều bỏ qua nó (trước đó `indexOf` trả -1 rồi `-1 + 1` nhảy về đoạn đầu sách).

- **Bo đồng tâm cho lớp lồng**: một hàng nằm TRONG một lớp bo thì bán kính của nó = bán kính ngoài −
  đệm. Menu tuỳ chọn (`MenuButton`) khung 16 + đệm 4 ⇒ item **12** (`rounded-xl`), trùng luôn bậc
  control; ban đầu để 8 nên item trông vuông trong khung tròn (chủ bắt 02/09). Viết cứng chứ KHÔNG
  đọc `--ctl-radius`: lớp nổi có thể lơ lửng trên một `Cluster radius="pill"` và sẽ thừa hưởng nhầm.
- Radius nội dung KHÁC radius control: ảnh = bậc surface **2xl**, đoạn tô = **lg**. Cổng
  `audit:ui` bắt đúng chỗ này khi màn đọc lỡ viết `rounded-xl` (01/09).

## 7. Nền và thang bề mặt

Nền = neutral DS **nguyên bản, đục 100%**, bậc **n00 ở CẢ hai theme** — token tự lật nên sáng ra
trắng, tối ra gần-đen (chủ chốt 01/09: "background trắng, xám như vậy không đẹp"; nền xám n20
là di sản từ vỏ Qt). Material toàn-cửa-sổ đã thử và nghỉ hưu (01/09): mọi mức bleed đều pha
loãng tông ramp. Material nếu quay lại chỉ ở vùng giới hạn, không bao giờ dưới cả trang.

**Thang bề mặt** (nền trắng làm sập lớp lang cũ, nên có thêm bậc `panel`):

| Vai trò | Sáng | Tối | Dùng ở |
|---|---|---|---|
| desk (nền) | n00 trắng | n00 | `body` |
| panel (nhóm lõm) | n10 | n05 | `GroupedSection` |
| paper (mặt nổi) | n00 trắng | n10 | control, `Surface`, cột đọc |
| rail (rãnh tab) | n10 | n05 | (`AppTabs`, gỡ 16/09 — token giữ cho rãnh sau này) |
| band (dòng đang đọc) | n10 | n20 | highlight ở Reader |

**Màu brand = XANH DƯƠNG** (chủ, 21/09: "update màu brand của app thành màu xanh dương"): `--color-brand-600` =
`--blue-b100`, `--color-brand-700` = `--blue-b120` — ramp xanh của DS, lật theo theme (sáng #2B52D4 / #2446B4, tối
#486AF2 / #6988F0; ở tối bậc 120 sáng hơn bậc 100 nên hover *sáng lên*, đúng cách control tối phản hồi). Trước đó là đỏ
DOL `#D42525`/`#B31F1F` viết cứng, không lật theme. Đo: chữ trắng trên b100 6,6:1 (sáng) / 4,9:1 (tối); chấm đầu dòng
trên desk 6,6 / 4,4. Hệ quả: brand và `danger` là hai sắc khác hẳn (không còn phải giữ luật "hai sắc đỏ không đứng cạnh
nhau"); vòng focus (info b60) là họ hàng của brand — Apple cũng dùng một màu xanh cho cả accent lẫn focus ring, đó là
điều mong muốn. Icon app đổi theo: mark sóng âm trên nền xanh (xoay hue nguồn 1024 px sang 224°, `tauri icon` sinh lại
cả bộ). Ảnh chụp trong README còn màu đỏ — chụp lại ở Phase 3.

**Trên vật liệu** (cột bên trên `NSVisualEffectView`, 20/09) thang đục nhường cho thang alpha của DS — cùng một
token lật theo theme: `veil` na05 (lõm) · `wash` na10 (hover) · `tint` na20 (chọn) · `edge-alpha` (sáng na20 / tối
na10, hairline). Không `paper`, không shadow. Lý do và bảng "ở đâu" nằm ở §3.16.

**Viền là PHƯƠNG ÁN DỰ PHÒNG, không phải trang trí** (chủ chốt 01/09: "case đã phân cấp bằng bg
rồi thì không cần border nữa"). Bề mặt nào fill đã tự tách khỏi nền thì bỏ viền; viền chỉ còn ở
chỗ fill bất lực. Vì light/dark không cùng số bậc, đây phải là token theo theme —
`edge-field` = `edge-strong` ở sáng, **trong suốt** ở tối:

| Bề mặt | Sáng | Tối |
|---|---|---|
| ô nhập / `Surface` | có viền (giấy trắng = desk trắng, fill bất lực) | **không viền** (giấy n10 nổi trên desk n00) |
| rãnh tab | không viền (rail n20 vs trắng = 1,27) | không viền (rail n05 vs desk = 1,06) |
| nhóm `GroupedSection` | không viền ngoài, giữ hairline giữa các hàng | như sáng |
| tab đang chọn | **có viền `edge-strong`** — nó phải nổi hẳn khỏi rãnh | như sáng |

Mục tab KHÔNG được chọn vẫn mang `border-transparent` cùng độ dày: viền chỉ đổi MÀU khi active,
không sinh thêm 1px, nếu không chữ sẽ nhảy mỗi lần đổi tab.

Hai luật rút ra khi chuyển sang nền trắng:
- **Sáng và tối KHÔNG cùng số bậc, và thế là đúng.** Sáng: giấy trùng luôn màu desk → thẻ nổi
  phải nhờ **viền `edge-strong`** mới đọc ra là thẻ (viền `edge` mảnh biến mất trên trắng). Tối
  vẫn đủ ba bậc desk→panel→giấy nên viền chỉ là nét trang trí. Đây chính là cách macOS làm:
  sáng = tấm giấy trắng có nét, tối = nhiều lớp xám chồng.
- **Rãnh phải lùi dưới cái nổi trên nó** — nhưng "lùi bao nhiêu" phụ thuộc viên pill có tự đứng
  được không. Lúc pill CHƯA có viền, rãnh n10 trên nền trắng gần như tàng hình nên phải đẩy lên
  n20; sau khi pill có viền `edge-strong` + shadow phân lớp, rãnh trả về **n10** cho nhẹ mắt
  (chủ yêu cầu giảm một bậc 01/09) mà cụm vẫn đọc ra là segmented control: rãnh/nền 1.12,
  pill/rãnh 1.12. Ở tối rãnh từng là n10 **đúng bằng màu viên pill** (chỉ viền cứu) → n05, và
  giữ nguyên: thang tối không còn bậc nào để nhạt thêm mà không đụng desk.

## 8. Quy trình mở pattern mới

1. Chỉ ra màn cần dựng KHÔNG ghép được từ catalog → 2. viết mục pattern (4 mặt) vào doc này
TRƯỚC → 3. dựng component trong `src/ui/patterns.tsx` → 4. cổng `audit:ui` + `test:ui` xanh
→ 5. màn tiêu thụ. Không code-trước-doc-sau.

**Cổng `audit:ui` là phần cứng của luật này** — luật nào đo được thì thành regex, đừng để nó
nằm yên trong văn bản. Đang chặn: chiều cao/nền/viền control thô ngoài `src/ui` · `<select>` và
`<textarea>` thô · `rounded-md` · `text-brand-600` trong màn (brand ≠ danger) · cỡ chữ tuỳ tiện.
Thêm luật mới thì **chạy cổng trên cây CHƯA sửa trước** — luật chưa từng thấy đỏ là luật chưa
được kiểm; đợt 01/09 luật mới đỏ đúng 7 chỗ ở 4 file rồi mới xanh sau khi sửa.

## 9. Sổ vay — học từ đâu cái gì

| Nguồn | Cái đã vay |
|---|---|
| IBM Carbon | mô hình 4 mặt Usage/Anatomy/Behavior/Content |
| Material 3 (Expressive 2025) | anatomy có tên bộ phận · state-layer một công thức phủ · số đo tường minh |
| Shopify Polaris | content guidelines theo từng component · Do/Don't cặp cụ thể |
| Radix | bảng hợp đồng bàn phím |
| Apple HIG | tổ chức theo ý-định-người-dùng (§1) · nhịp toolbar/list |
| **Riêng của ta** | Do/Don't **sống** — mỗi luật gắn một vòng audit thật của chủ, không luật nào là lý thuyết |
