# Hướng đi để ReadEase thành app thương mại — nhỏ nhất có thể, lên App Store / Setapp / mobile

Chủ đặt bài (07/09/2026): app chuyên nghiệp, dung lượng thấp nhất, phát hành App Store + Setapp + mobile +
desktop. Bản GitHub vẫn mở cho người có API riêng; bản phát hành dùng API của chủ và thu phí.

Mọi con số đo trên bản đang cài `0.1.0+72f213e` hoặc lấy từ web ngày 07/09 (`[fetched]`); kiến thức nền chưa
kiểm lại ghi `[from training — may be stale]`.

## 0. Ba sự thật quyết định mọi thứ

**1. App "thật" chỉ nặng 10 MB.** Bundle 396 MB = vỏ Tauri (Rust + giao diện) **10 MB** + sidecar Python
**384 MB**. Model giọng còn tải riêng thêm 330/625 MB. Trong 384 MB sidecar, phần lớn **không phải thứ app
dùng**:

| Gói | MB | Vì sao có mặt | App cần? |
|---|---|---|---|
| `llvmlite` | 123 | `librosa` → `numba` → JIT compiler | Không — ta không JIT gì |
| `sea_g2p` | 65 | phonemizer của VieNeu | Có (khi chạy giọng local) |
| `onnxruntime` | 43 | chạy model | Có (giọng local) |
| `scipy` | 32 | `librosa`, `scikit-learn` | Không |
| `pandas` | 17 | `gradio` (SDK VieNeu kéo vào) | Không |
| `PIL` | 11 | `gradio` | Không |
| `pypdfium2` | 7 | đọc PDF | Có |

⇒ Ngay cả bản GitHub cũng cắt được **~180 MB** (một nửa sidecar) mà không đụng tính năng: gỡ `gradio`,
`librosa`/`numba`, `pandas`, `PIL`. Đó là việc rẻ nhất, làm được tuần này.

**2. Sidecar Python không lên iOS được, và không nên lên store.** iOS không cho app chạy trình thông dịch/binary
ngoài (App Store Review 2.5.2 `[from training]`); Tauri v2 chỉ hỗ trợ sidecar trên desktop `[fetched]`. Mà
Python hiện **sở hữu cả cuốn sách**, không chỉ giọng đọc:

| Khu vực Python | Dòng | Là gì |
|---|---|---|
| `importers` + `domain` + `storage` | ~4.500 | Nhập EPUB/PDF, tách câu, hình/chú thích, SQLite, tiến độ, ghi chú — **lõi app** |
| `headless` | 2.100 | Máy chủ RPC nói chuyện với Rust |
| `speech` + `playback` | 3.400 | Engine giọng + lịch phát |
| `integrations` | 1.600 | Apple Books |
| `ui` | 5.000 | **Vỏ Qt cũ — đã chết**, chỉ còn ăn dung lượng và thời gian test |

Rust hiện chỉ 1.300 dòng (bơm audio + lệnh). Nghĩa là: muốn mobile và muốn nhỏ, **lõi sách phải dời sang
Rust**. Đây là hạng mục lớn nhất, và cũng là hạng mục có sẵn lưới an toàn: 937 test Python là **bản đặc tả**
của lõi, và `tests/headless/test_shell_contract.py` đã ghim hợp đồng RPC giữa hai bên.

**3. "API của tôi" chỉ có một cách rẻ.** Giá đã ghi trong repo (`speech/external/pricing.py`, fetched 04/09):
OpenAI tts-1 **$0,015**/1k ký tự · ElevenLabs Flash **$0,05** · v3 **$0,10**. Một cuốn 300 trang ≈ 600k ký tự
⇒ **$9 / $30 / $60 mỗi cuốn** nếu proxy giọng trả phí. Không có gói thuê bao nào chịu nổi. Còn VieNeu v3 Turbo
ONNX int8 chạy **RTF 0,37 trên một nhân CPU** `[fetched]` ⇒ ~2,7× thời gian thực mỗi nhân, tức vài **xu** mỗi
cuốn trên VPS thường. VieNeu chưa có server v3 (server v2 đã bỏ) `[fetched]` — nhưng ta không cần: chính engine
ONNX ta đang chạy trong sidecar, đem chạy trên server là xong. **Giọng của ta = VieNeu trên CPU server của ta;
giọng trả phí vẫn là BYOK.**

> **Cập nhật 10/09/2026** — bảng giá trong repo không còn dòng `tts-1`/`tts-1-hd`: OpenAI đã đổi sang
> `gpt-4o-mini-tts`, ~**$0,02**/1k ký tự (ước lượng, model tính theo token). Con số trên giữ nguyên như bản ghi
> ngày 07/09; kết luận không đổi — 600k ký tự vẫn ra ~**$12** mỗi cuốn, cùng bậc với $9.

## 1. Kiến trúc đích: một mã nguồn, hai bản build

```
                ┌──────────────────────────────────────────┐
                │  Lõi Rust (Tauri v2, chung mọi nền tảng) │
                │  nhập EPUB/PDF · tách câu · SQLite ·     │
                │  tiến độ · ghi chú · bơm audio · UI web  │
                └───────────────┬──────────────────────────┘
                                │  trait SpeechSource (đã có mầm: Pump/AudioSink)
              ┌─────────────────┴──────────────────┐
   GitHub / BYOK                            Store / Setapp / iOS
   ┌──────────────────────┐                 ┌──────────────────────────┐
   │ sidecar ONNX (đã cắt │                 │ HTTP stream tới server   │
   │ mỡ, ~200 MB)         │                 │ của chủ · auth · đo ký tự│
   │ + BYOK OpenAI/Eleven │                 │ app ≈ 10–15 MB           │
   └──────────────────────┘                 └──────────────────────────┘
```

- **Bản GitHub** = lõi Rust + sidecar local (+ BYOK). Vẫn offline, vẫn riêng tư, đúng lời hứa PRIVACY.md.
- **Bản phát hành** = lõi Rust + engine từ xa. Không Python, không model, ~10–15 MB, chạy iOS/Android/macOS
  từ cùng một lõi. Server = VieNeu ONNX trên CPU + tài khoản + đếm ký tự.
- Đây là **open core**: giá trị bán được nằm ở server, giọng, đồng bộ, không nằm ở mã.

## 2. Ràng buộc phát hành đã kiểm `[fetched 07/09]`

| Kênh | Bắt buộc | Điều phải chấp nhận |
|---|---|---|
| **Setapp (macOS)** | Ký **Developer ID** + notarize · **Universal binary (arm64 + x86_64)** · Setapp Framework | **Cấm tính năng trả phí bên trong bản Setapp** ⇒ phí server phải nằm gọn trong khoản Setapp trả |
| **Mac App Store** | **App Sandbox** bắt buộc · chứng chỉ Mac Installer Distribution · provisioning profile | Sidecar 384 MB trong sandbox = đường không nên đi; bản thin client thì thẳng |
| **iOS App Store** | Tauri mobile · không sidecar · IAP | Thuê bao số: **ngoài Mỹ/EU phải qua IAP (15–30%)**; Mỹ được gắn link ngoài (Tối cao Pháp viện nhận vụ 06/2026, chưa ngã ngũ); EU chọn **một** trong hai mỗi storefront |
| **Setapp iOS** | Kích hoạt qua Setapp **hoặc** IAP; người không có Setapp vẫn phải mở khoá được toàn bộ app | Hai đường mở khoá song song |

Hai điều này **đảo lại quyết định cũ** của chủ: cần **Apple Developer Program** (ký + notarize) — từng từ chối
vì "bạn bè cài tay"; và cần build **x86_64** — hiện chỉ arm64.

## 3. Lộ trình — mỗi pha một cổng kiểm được

| Pha | Việc | Lợi ngay cho | Cổng |
|---|---|---|---|
| **0 — Cắt mỡ** (tuần này) | Gỡ `gradio`/`librosa`/`numba`/`pandas`/`PIL` khỏi sidecar (fork import của `vieneu` hoặc vendor phần dùng); xoá `ui/` Qt; nâng `vieneu` 3.6.3 (xem `local-voice-model-survey-2026-09.md`) | Bản GitHub | `du -sh Resources/engine` ≤ 200 MB; `verify.sh` xanh; bundle contract xanh |
| **1 — Lõi sách sang Rust** | Port `importers`/`domain`/`storage` (crate `epub`/`epub-parser`, `pdfium-render` `[fetched]`), giữ **cùng hợp đồng RPC** để 937 test Python chạy lên binary Rust như bộ oracle; Python chỉ còn `speech` | Cả hai | Test contract xanh trên Rust; 9 EPUB thật của chủ import ra **cùng** `segment_id`/hình/chú thích như Python (`stable_id` là hash — so được từng dòng) |
| **2 — Engine từ xa** | Rust `Pump` đọc frame từ HTTP stream thay vì stdin; server VieNeu ONNX CPU + auth + đếm ký tự; trần chi tiêu tái dùng `SpendMeter` | Bản phát hành | Bản build không Python ≤ 15 MB; Q1 stop < 150 ms và Q2 < 500 ms p95 giữ nguyên qua mạng |
| **3 — Phát hành** | Apple Developer · Developer ID + notarize · universal · sandbox cho MAS · Setapp Framework · IAP | Store | `spctl -a` chấp nhận; sandbox chạy được; Setapp review |
| **4 — Mobile** | Tauri iOS/Android từ cùng lõi Rust; UI web tái dùng; bỏ Quét đọc/phím tắt (desktop-only) | iOS/Android | TestFlight chạy một cuốn end-to-end |

**Tiến độ pha 0 (07/09):** sidecar 384 → **223 MB** (gỡ llvmlite/scipy/pandas/numba/sklearn/fastapi/starlette/
uvicorn khỏi bản đóng gói; PIL ở lại vì `covers.py` vẽ bìa bằng nó — loại thử thì engine chết lúc import, smoke
bắt được); `vieneu` 3.6.3 đã ghim (xem `local-voice-model-survey-2026-09.md` §3). Gate 200 MB chưa tới: phần còn
lại là onnxruntime 44 + sea_g2p 66 + libpython 17 + PIL 12 + tokenizers 9 — đều đang dùng. `ui/` Qt chưa xoá.

Pha 0 và 1 **không phụ thuộc** vào bất kỳ quyết định kinh doanh nào và làm bản GitHub tốt lên ngay — bắt đầu
từ đó dù pha 3–4 còn cân nhắc.

## 4. Những gì chủ phải quyết (không phải của AI)

1. **Mua Apple Developer Program** ($99/năm) — không có nó thì không có kênh nào ở trên.
2. **Mô hình thu phí**: thuê bao đọc không giới hạn (chỉ khả thi với VieNeu tự host) · hay gói ký tự · IAP hay
   link ngoài (theo storefront). Setapp thì miễn tính năng trả phí — phí server phải "chìm" trong payout.
3. **Giọng local có còn trong bản phát hành desktop không** (tuỳ chọn tải 330 MB cho ai muốn offline), hay
   bản phát hành thuần từ xa. Ảnh hưởng sandbox + kích thước + lời hứa riêng tư.
4. **Thứ tự nền tảng**: Setapp trước (không IAP, không sandbox, khách trả sẵn) hay App Store trước.

## 5. Chưa biết, phải kiểm khi tới pha

- Tỷ lệ chia của Setapp và cách đo "usage" (trang chi tiết chưa đọc được) — quyết định giá server chịu được.
- Chi phí thật của VieNeu trên CPU server dưới tải đồng thời (đo bằng probe, không ước).
- `pdfium-render` trên iOS: pdfium có build iOS, nhưng chưa thử với Tauri mobile.
- Setapp có nhận app Tauri (web-based UI) không — review guidelines nhắc "native", cần đọc bản Oct 2025.

## Nguồn `[fetched 2026-09-07]`
- Tauri App Store: https://v2.tauri.app/distribute/app-store/ · sidecar: https://v2.tauri.app/develop/sidecar/
- Setapp yêu cầu: https://docs.setapp.com/docs/preparing-your-application-for-setapp.md ·
  https://docs.setapp.com/docs/monetizing-on-setapp.md
- IAP/link ngoài 2026: https://stora.sh/blog/2026-05-16-apple-app-store-external-purchase-links-implementation-guide ·
  https://blog.funnelfox.com/subscription-app-compliance-2026/
- VieNeu RTF/server: https://github.com/pnnbao97/VieNeu-TTS
- Rust crates: https://crates.io/crates/epub-parser · https://docs.rs/pdfium-render
