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
| Chọn một CUỐN SÁCH trong nhiều cuốn | `BookGrid` + `BookCard` + `BookCover` | Thư viện (kệ bìa) |
| Xem/chọn trong một nhóm thiết lập | `GroupedSection`+`GroupedRow` | Panel Chất lượng, danh sách xem-trước ghi chú |
| Bắt đầu khi chưa có gì | `EmptyState` | Thư viện rỗng |
| Định hướng vùng làm việc | `AppTabs` trong `Toolbar` | Header |
| Điều khiển việc đang chạy | PlayerBar | Footer đọc |
| Xác nhận huỷ tại chỗ | ConfirmInline | Xoá sách (trailing của ListRow) |
| Kéo dữ liệu từ app khác, một chiều | Sheet `Surface radius="sheet"` + `BookTile` (§3.12) | Từ Apple Books |
| Tuỳ chọn phụ sau một hành động | `MenuButton` (icon → danh sách ngắn, mục đầu = mặc định) | Nhập/đồng bộ trong sheet Apple Books |
| Xin quyền hệ thống | PermissionCard | Quét đọc |
| Chặn cho tới khi sẵn sàng | Setup gate | First-run model |

## 2. Bảng trạng thái chuẩn (vay M3: state layer — một lớp phủ, không đổi bản thể)

Mọi bề mặt tương tác có ĐỦ 7 trạng thái, cùng một công thức phủ:

| Trạng thái | Công thức (token) |
|---|---|
| default | như khai báo |
| hover | phủ `wash` = neutral-alpha **na05** (na10 đã thử — đậm, chủ bác 01/09) |
| focus-visible | **một chỗ duy nhất**: outline 2px `--color-focus` (info b60) trong `index.css` — KHÔNG bao giờ brand |
| pressed | control trung tính: phủ `press` = neutral-alpha **na10** (cùng thang hover, nặng hơn một bậc) · nút primary đã có nền brand thì đậm xuống `brand-700` — phủ xám lên nền đỏ chỉ làm bẩn màu |
| disabled | chữ luôn `ink-faint`, **không bao giờ opacity**; control có viền giữ nguyên viền `edge-strong`, control không viền vẫn không viền |
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
- Pressed **na10 không phải là re-litigate**: na10 bị bác với tư cách trọng lượng HOVER; ngón tay
  đang nhấn thì nặng hơn con trỏ lướt qua, và chỉ nặng trong lúc giữ.
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
- **Behavior**: hàng không hover trừ khi bấm được cả hàng; control bên trong tự mang trạng thái.
- **Content**: subtitle chỉ khi mang tin ("Đang dùng", "Chưa tải") — không lặp lại title.

### 3.3 `EmptyState`
- **Usage**: vùng nội dung trống lần đầu.
- **Anatomy**: cụm lối-vào đứng GIỮA chỗ nội dung sẽ nằm · ràng buộc (nếu có) đứng DƯỚI lựa chọn nó ràng buộc.
- **Don't sống**: ✗ hộp trống + nút parked dưới đáy (bản Qt cũ) · ✗ câu cảnh báo trước khi người dùng làm gì.

### 3.4 `Toolbar` + `AppTabs`
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
- **Anatomy (AppTabs = ToggleButtonGroup *style 2*, chủ chốt 01/09)**: rãnh `rail` có viền,
  **không đệm trong** → mục đang chọn **tràn sát viền** rãnh, góc do chính rãnh cắt
  (`overflow-hidden`). Rãnh 34 nằm trong toolbar 36; mục 32 = đúng chiều cao select ngôn ngữ
  bên phải. Style 1 (viên pill nhỏ trôi trong rãnh có đệm) là bản cũ, đã thay.
- **Behavior**: mục đang chọn = nền `paper` + **shadow phân lớp của DS**
  (`--shadow-neutral-to-bot-2`: một lớp toả rộng + một lớp tiếp xúc sát) — `shadow-sm` của
  Tailwind là một nét cứng, cạnh shadow DS đọc ra như đường kẻ in dưới nút.
- **Don't**: tiêu đề app trong toolbar (macOS đã vẽ trên titlebar) · nút trùng chức năng với tab đứng cạnh (đều đã gỡ, 08/31).
- **Hai bậc tính năng** (chủ, 02/09: "phân chia rõ tính năng phụ và tính năng chính"): **CHÍNH** = cách
  đưa chữ tới giọng — Thư viện (sách) · Dán nội dung — nằm trong rãnh `AppTabs`, mỗi tab một glyph
  (`AppTab.icon`). **PHỤ** = công cụ quanh việc đọc — Quét đọc (đọc phần bôi đen ở app khác) · Chuyển
  ghi chú — cụm ghost có icon ở cụm phải, tách bằng vạch `bg-edge`, `aria-pressed` + `bg-wash` khi
  đang mở. Cùng ngôn ngữ glyph 16px/1.5 stroke của `ui/icons`. Rãnh vẫn nhận phím ←/→ khi giá trị đang
  ở một màn phụ (vào rãnh từ mục đầu).
- **Footer = lưới 3 cột** (trái: hint · giữa: CTA+chip hoặc transport · phải: trạng thái/lỗi), cao
  76 px như header; KHÔNG dùng absolute cho cụm giữa — nó không tạo chiều cao, footer từng bị ép còn
  40 px (chủ bắt 02/09).
- **Nút sáng/tối** (chủ, 02/09): IconButton mặt trời/mặt trăng ở cụm phải trên MỌI màn; bấm = sang phía
  ngược lại của cái đang hiện, nhớ trong localStorage (`ui/theme.ts`); chưa chọn thì theo macOS live.
  Đây là nơi DUY NHẤT ghi `[data-theme]`.
- **Chọn ngôn ngữ UI chỉ ở trang chủ** (chủ, 02/09): toolbar của một cuốn sách chỉ mang thứ phục vụ cuốn
  sách (quay lại · mục lục · ⓘ · cỡ chữ · chế độ).
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
  là dòng phụ của hàng — nhãn đầy đủ trong select từng tràn hàng, cắt mất chữ "Giọng" (chủ, 02/09). Khi đang đọc, TRANSPORT cũng đứng giữa (như mọi trình phát), trạng thái/lỗi lùi sang phải.
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
  Không đụng brand: brand đỏ là CTA "Đọc", mà CTA không hiện lúc đang đọc nên hai sắc đỏ không
  bao giờ đứng cạnh nhau.
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

### 3.6 ConfirmInline · 3.7 PermissionCard · 3.8 Setup gate
ConfirmInline: thay chỗ trailing, hành động huỷ = **danger** + "Giữ lại" trung tính; không modal
cho việc một hàng. PermissionCard: Surface + note + hành động chính brand + đường "Cài đặt hệ
thống"; nói rõ phải thoát-mở-lại (luật TCC). Setup gate: một cột giữa màn, field chung trục,
một hành động brand; chặn TOÀN app cho tới khi model sẵn sàng.

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

### 3.9b Hover/press của control = lớp wash PHỦ LÊN fill, không thay fill (02/09)

- Bộ control vẽ hover bằng `hover-wash` (index.css): `background-image` gradient của `wash`/`press`
  đè lên `background-color` sẵn có. Trước đó `hover:bg-wash` **thay** nền giấy đục bằng alpha 5% nên
  nút nổi trên nội dung ("Về chỗ đang đọc") hoá trong suốt khi rê chuột — chữ bên dưới xuyên qua
  (chủ bắt 02/09; đo: nền hover `rgba(243,243,243,0.05)` → sau sửa `rgb(38,39,39)` + gradient).
  Cùng lỗi ở nút đóng lightbox trên nền đen. **Ngoại lệ**: `Select` giữ `hover:bg-wash` vì chevron
  của nó đã sống trong `background-image`.

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
  của chính DS — cùng chất liệu tiến lại gần, không phải bóng mới); **không nhấc/translate** (chủ bỏ 02/09: kệ không cựa quậy). Dưới bìa: **thanh tiến độ** brand
  (chỉ sách đang đọc) → tiêu đề 14 semibold tối đa 2 dòng → một dòng dữ kiện 12 mute. Accessory
  (thùng rác) nổi ở góc bìa, lộ khi hover/focus — đúng hợp đồng `ListRow` chuyển lên thẻ.
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
- **Engine**: Apple giữ sách tự thêm dưới dạng THƯ MỤC `.epub` → nén tất định (mimetype trước, STORED,
  mốc thời gian cố định, bỏ `iTunesMetadata.plist`/`.DS_Store`/`__MACOSX`) để hash không đổi → importer
  sẵn có nhận ra cùng sách khi nhập lại. Bảng `apple_books_links(asset_id→book_id)` nhớ cuốn nào đã
  thành cuốn nào; chưa có link thì ghép theo tiêu đề chuẩn hoá (khớp toàn bộ hoặc 24 ký tự đầu) và
  HIỆN cặp ghép để sai thì thấy. DRM = `encryption.xml` có CipherReference trỏ vào thứ không phải
  font (font obfuscation không phải DRM). Highlight về đoạn bằng CHỮ đã bôi (40 ký tự đầu, chuẩn hoá
  ngoặc kép/khoảng trắng), CFI chỉ dùng phân xử khi trùng; bookmark bỏ qua, không tính là thất bại.
- **Màn đọc**: highlight = `<mark>` tô `--fill-warning-haze` (vàng alpha 30%, đúng cả hai nền), chữ giữ
  màu; ghi chú = icon nhỏ sau đoạn bôi, hover thấy nội dung. Highlight tràn sang đoạn sau chỉ tô hết
  đoạn nó bắt đầu. Tách trong `ui/highlight.ts` (test node: ngoặc cong, NBSP, khoảng trắng đôi, tràn đoạn).
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
| ←/→/Home/End | AppTabs | chuyển tab (roving focus) |
| Esc | recorder phím tắt | giữ phím cũ |
| Esc | panel Chất lượng | đóng panel — trừ khi đang tải bản giọng (đóng lúc đó = giấu việc đang chạy) |
| Tab | mọi nơi | focus ring **info blue**, không bao giờ brand |

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
- **Ký hiệu liệt kê "(a) … (b) …" nói thành chữ cái kèm nghỉ** — chủ chọn bằng tai 02/09 giữa 4 bản render cùng một câu (giữ nguyên · xoá · "một là/hai là" · chữ cái + nghỉ): "khớp với a, nhiệm vụ hiện tại, hoặc b, sở thích cá nhân". Nghỉ đặt TRƯỚC liên từ dẫn vào ký hiệu (hoặc/hay/và/rồi/cũng như). Tham chiếu "mục (b)" → "mục b", không nghỉ. Chỉ chữ thường đơn có khoảng trắng phía trước; "book(s)", "(ii)", "(1)" không đụng (thư viện: 31 ký hiệu, 0 chữ số/hoa/tham chiếu). Test chốt = chính câu chủ duyệt, so khớp từng ký tự với bản render đã nghe.


## 6. Số đo đã chốt (vay M3: measurements tường minh)

Control 30px `rounded-xl` · nhỏ 28px `rounded-lg` (phím tắt `Kbd` cùng bậc) · icon-button 32
tròn · pill cho nav/ngôn ngữ · surface + ô nhập nhiều dòng `rounded-2xl` · chữ 16 bold (tiêu đề)
/ **14 base** / 12 micro (+18 màn chào) · trong-cặp 8 / giữa-cặp 16 / khối 24 · cột đọc 65ch ·
hover na05 · pressed na10 · hairline `edge`.

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
- Bán kính: control 12 · surface/card 16 (`rounded-2xl`) · **sheet/modal 24 (`Surface radius="sheet"`, chủ 02/09:
  "modal tròn trịa hơn")** · bìa sách 8 (`rounded-lg`, vật in) · viên nổi pill.
- Bề rộng cột: **40em** (chủ nới từ 36em, 02/09) → ~80 ký tự/dòng ở cỡ 16px; 36em đo bằng `Range` được 72 ký tự, dải dễ đọc cổ điển 45–75 — nới một bậc theo mắt chủ, không nới thêm.
  65-75. **Đừng dùng `ch`**: `70ch` của font này ra 804px ≈ 95 ký tự/dòng - đơn vị `ch` đo bề
  rộng chữ "0", không phải chữ trung bình. `em` giữ số ký tự/dòng ổn định khi đổi cỡ chữ.
- Nhịp: line-height **1.75** · đoạn cách 0.75rem · tiêu đề chương **1.35em** bold, cách trên 2.5rem.
- Hàng mục lục `dense`: px 10 / py 4 - 26 chương lọt trong 820px so với 15 hàng thường.
- Tương phản (đo cả hai theme): dải đang đọc/nền **1.12** (sáng) · **1.24** (tối); chữ trên dải
  **11.71** (sáng) · **12.82** (tối) - dải đủ thấy mà không cướp mất chữ.
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
| rail (rãnh tab) | n10 | n05 | `AppTabs` |
| band (dòng đang đọc) | n10 | n20 | highlight ở Reader |

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
