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
| Duyệt danh sách mục, mỗi mục có hành động | `ListRow` | Thư viện, lịch sử Quét đọc |
| Xem/chọn trong một nhóm thiết lập | `GroupedSection`+`GroupedRow` | Panel Chất lượng, danh sách xem-trước ghi chú |
| Bắt đầu khi chưa có gì | `EmptyState` | Thư viện rỗng |
| Định hướng vùng làm việc | `AppTabs` trong `Toolbar` | Header |
| Điều khiển việc đang chạy | PlayerBar | Footer đọc |
| Xác nhận huỷ tại chỗ | ConfirmInline | Xoá sách (trailing của ListRow) |
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
  sang `--text-color-danger-bold`: 4.06/5.14 (sáng: desk/giấy) · 5.14/4.56 (tối). Chỗ duy nhất
  còn dưới 4.5 là dòng danger nằm thẳng trên desk sáng (4.06) — mọi bề mặt danger quan trọng
  (xác nhận xoá, phán quyết chuyển ghi chú) đều nằm trên giấy.
- Pressed **na10 không phải là re-litigate**: na10 bị bác với tư cách trọng lượng HOVER; ngón tay
  đang nhấn thì nặng hơn con trỏ lướt qua, và chỉ nặng trong lúc giữ.
- **Ô nhập chữ và select đeo vòng focus cả khi bấm chuột** (nút thì không) — đó là hành vi của
  `:focus-visible` với trường nhập liệu, không phải lỗi. Giữ vòng đó, nhưng ô nhập nhiều dòng
  vẽ vòng **đè lên viền của chính nó** (`outline-offset: -1px`): một đường xanh gọn như ô văn
  bản macOS, thay vì viền xám + khe + vòng xanh đọc ra kiểu form web (nhìn tận mắt 01/09).

## 3. Pattern catalog

### 3.1 `ListRow`
- **Usage**: mục trong danh sách có thể mở + có hành động phụ. KHÔNG dùng cho cặp nhãn-control (đó là `GroupedRow`).
- **Anatomy**: `leading` (glyph 16, ink-mute) · `body` (title 14 semibold + chip 12 · subtitle 12 mute một dòng truncate) · `trailing` (accessory **nằm trong** mặt hover).
- **Behavior**: cả hàng = một mặt hover 2xl; click body = hành động chính; accessory lộ khi hover/focus; focus ring quanh body.
- **Content**: subtitle = dữ kiện phân biệt thật, nối bằng " · " (vd "108 chương · 9,1 MB · Nhập 31/08/2026 · Đang đọc dở"); trường thiếu thì BỎ, không bao giờ chữ "undefined".
- **Do/Don't sống**: ✗ accessory thò ngoài hàng (chủ bắt 01/09) · ✗ hàng một tầng khi có metadata · ✗ block bao ngoài danh sách (hàng tự mang cấu trúc rồi thì hộp là vỏ thừa — vòng đời chrome, 01/09).

### 3.2 `GroupedSection` + `GroupedRow`
- **Usage**: nhóm thiết lập/lựa chọn liên quan — hình thái System Settings. KHÔNG dùng card riêng từng hàng (slop-03).
- **Anatomy**: header 12 uppercase mute (tuỳ chọn) · một mặt giấy 2xl · hairline `edge` giữa các hàng · mỗi hàng: title 14 medium + subtitle 12 mute | trailing controls.
- **Behavior**: hàng không hover trừ khi bấm được cả hàng; control bên trong tự mang trạng thái.
- **Content**: subtitle chỉ khi mang tin ("Đang dùng", "Chưa tải") — không lặp lại title.

### 3.3 `EmptyState`
- **Usage**: vùng nội dung trống lần đầu.
- **Anatomy**: cụm lối-vào đứng GIỮA chỗ nội dung sẽ nằm · ràng buộc (nếu có) đứng DƯỚI lựa chọn nó ràng buộc.
- **Don't sống**: ✗ hộp trống + nút parked dưới đáy (bản Qt cũ) · ✗ câu cảnh báo trước khi người dùng làm gì.

### 3.4 `Toolbar` + `AppTabs`
- **Usage**: hàng đầu cửa sổ, một hàng duy nhất cao h-9. Điều hướng dẫn trái, hành động/ngôn ngữ theo phải.
- **Anatomy (AppTabs = ToggleButtonGroup *style 2*, chủ chốt 01/09)**: rãnh `rail` có viền,
  **không đệm trong** → mục đang chọn **tràn sát viền** rãnh, góc do chính rãnh cắt
  (`overflow-hidden`). Rãnh 34 nằm trong toolbar 36; mục 32 = đúng chiều cao select ngôn ngữ
  bên phải. Style 1 (viên pill nhỏ trôi trong rãnh có đệm) là bản cũ, đã thay.
- **Behavior**: mục đang chọn = nền `paper` + **shadow phân lớp của DS**
  (`--shadow-neutral-to-bot-2`: một lớp toả rộng + một lớp tiếp xúc sát) — `shadow-sm` của
  Tailwind là một nét cứng, cạnh shadow DS đọc ra như đường kẻ in dưới nút.
- **Don't**: tiêu đề app trong toolbar (macOS đã vẽ trên titlebar) · nút trùng chức năng với tab đứng cạnh (đều đã gỡ, 08/31).

### 3.5 PlayerBar
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

- **Ẩn ≠ vô hiệu hoá**: ẩn khi màn **không bao giờ** cấp được hành động đó (Quét đọc, Chuyển ghi
  chú, thư viện chưa mở sách); **hiện-nhưng-mờ** khi đó là hành động chính của màn và chỉ đang
  chờ dữ liệu (ô dán còn trống) — ẩn kiểu này sẽ làm nút nhảy ra khi vừa gõ ký tự đầu.
- **Anatomy**: trái = transport (**ẩn-khi-chết**: Dừng/Lịch sử chỉ hiện khi có việc) · phải = chuỗi `Field` nhãn+control (Chất lượng · Giọng · Tốc độ), khoảng trong-cặp 8 < giữa-cặp 16.
- **Behavior**: Space = tạm dừng/tiếp tục khi không gõ chữ; "Đang chuẩn bị giọng đọc…" hiện từ lúc bấm tới chunk PCM đầu.
- **Don't sống**: ✗ divider trên footer (chủ bỏ 01/09) · ✗ control mồ côi không nhãn (chip "Cao
  nhất" từng thế) · ✗ nhãn đứng cạnh control của cặp khác (bug Tốc-độ-chỉ-nhầm-ô, goal đầu tiên)
  · ✗ **nút chính ăn state của màn KHÁC** — trên Quét đọc/Chuyển ghi chú, nút "Đọc nội dung"
  từng bật/tắt theo ô dán ở tab khác và bấm vào là đọc đúng nội dung vô hình đó (01/09).

### 3.9 Reader — sidebar chương
- **Usage**: điều hướng trong sách đang mở; mỗi hàng nhảy tới đầu chương.
- **Anatomy**: `ListRow` một dòng; **hàng của chương đang đọc mang nền `band`** — cùng token với
  dòng đang đọc trong cột chữ, nên "chỗ tôi đang ở" chỉ có một ngôn ngữ màu duy nhất.
- **Behavior**: chương đang đọc suy từ segment hiện tại (hoặc tiến độ đã lưu), không giữ state
  riêng — nếu không, nhảy đoạn bằng cách bấm giữa cột chữ sẽ làm sidebar nói sai.
- **Don't sống**: ✗ sidebar không dấu vị trí — đọc audio hàng giờ mà nhìn vào không biết đang ở
  đâu (bắt trong vòng audit theo tính năng, 01/09) · ✗ đếm "Chương X/Y" cho PDF không có mục lục:
  ở đó mỗi TRANG là một "chương" tên "Trang 37", header nói "Chương 37/300" là tự mâu thuẫn.

### 3.6 ConfirmInline · 3.7 PermissionCard · 3.8 Setup gate
ConfirmInline: thay chỗ trailing, hành động huỷ = **danger** + "Giữ lại" trung tính; không modal
cho việc một hàng. PermissionCard: Surface + note + hành động chính brand + đường "Cài đặt hệ
thống"; nói rõ phải thoát-mở-lại (luật TCC). Setup gate: một cột giữa màn, field chung trục,
một hành động brand; chặn TOÀN app cho tới khi model sẵn sàng.

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
| rail (rãnh tab) | n20 | n05 | `AppTabs` |
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
- **Rãnh phải lùi dưới cái nổi trên nó.** Rãnh tab n10 trên nền trắng gần như tàng hình → n20;
  ở tối rãnh từng là n10 **đúng bằng màu viên pill** (chỉ viền cứu) → n05.

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
