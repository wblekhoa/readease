# Kế hoạch chuyển ReadEase sang Tauri — và khai tử vỏ Qt

> Trạng thái: **đã duyệt hướng đi** (2026-08-31, chủ chọn Tauri sau khi cân với SwiftUI).
> Doc này là nguồn sự thật của chiến dịch. Mỗi phase kết thúc bằng cổng kiểm chứng
> chạy được bằng lệnh; app cũ chỉ bị xoá khi cổng nghỉ hưu (P6) xanh toàn bộ.

## 0. Vì sao Tauri (đã chốt — không mở lại trừ khi ràng buộc đổi)

Hai ràng buộc quyết định, không phải xu hướng:

1. **Động cơ là Python và không port được** — `sea-g2p` (luật ngữ âm tiếng Việt),
   `vieneu`/onnxruntime, WSOLA. Mọi con đường đều phải giữ nó làm tiến trình riêng.
2. **Design system của chủ là web** — DOL DS-Token (Tailwind, biến CSS, ui-registry TSX).
   Trong Tauri nó chạy **nguyên xi**; trong Qt/SwiftUI phải dịch tay và trôi dần.

Hệ quả kiến trúc: *cái vỏ càng mỏng càng tốt; mọi trí tuệ dồn vào động cơ.*

## 1. Kiến trúc đích

```
┌────────────────────────── ReadEase.app (Tauri v2) ──────────────────────────┐
│  WebView (React + Tailwind + DOL DS-Token, ui-registry components)          │
│      │  invoke/events                                                       │
│  Rust core:                                                                 │
│    • spawn + own sidecar (kill-on-drop, process group)                      │
│    • audio out qua rodio (pause/resume/stop tức thời, không lệ thuộc        │
│      autoplay-policy của WKWebView)                                         │
│    • global shortcut (tauri-plugin-global-shortcut)                         │
│    • tray "đang đọc - bấm để dừng" (tray-icon)                              │
│    • selection capture: FFI thẳng vào libReadEaseSelectionNative.dylib      │
│      (giữ nguyên file ObjC hiện có - C ABI sẵn rồi)                         │
│    • quyền: tauri-plugin-macos-permissions (Accessibility)                  │
│      │ JSONL trên stdin/stdout                                              │
│  Sidecar `readease-engine` (PyInstaller, arm64):                            │
│    toàn bộ src/vieneu_reader trừ ui/ - synthesis, prosody, cache,           │
│    time-stretch, importers, storage, apple-books                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

Quyết định kèm theo:

- **Rust phát tiếng, không phải WebView.** Web Audio vướng autoplay-policy khi
  đọc được kích hoạt bằng phím tắt toàn cục (chưa hề click vào cửa sổ), và webview
  bị throttle khi ẩn. `rodio` nhận thẳng frame PCM từ stdout sidecar mà Rust vốn
  đang cầm. JS chỉ vẽ UI.
- **Giữ nguyên bundle id `vn.dolenglish.vieneureader` và data root "VieNeu Reader"**
  → sách, model 626MB, cache, vị trí đọc, settings **không cần migrate byte nào**.
  (Accessibility sẽ hỏi lại một lần vì binary mới - hành vi TCC bình thường.)
- **Sửa luôn bug ngữ nghĩa cũ**: chỉ báo tray phải hiện cả khi PAUSED
  (bản Qt: `is_reading` loại PAUSED nên tray biến mất lúc tạm dừng).

## 2. Hiện trạng đã được chứng minh (P0 — XONG 2026-08-31)

`src/vieneu_reader/headless/server.py` + `tests/headless/test_server.py`:

- Giao thức JSONL v1: `ping` · `voices` · `read {text, voice_id, rate}` · `stop`.
- Ngắt nghỉ câu là frame im lặng thật (vỏ không cần biết prosody); rate đi qua
  đúng WSOLA của app; nghỉ scale số học chính xác.
- EOF ≠ stop (chế độ batch: gửi một lệnh, đóng stdin, thu trọn audio).
- 6/6 test giao thức xanh với engine giả · `verify.sh` **685 test OK**.
- **Bằng chứng sống với model thật**: ping 0.1s · 20 giọng · "Xin chào. Đây là
  bằng chứng sống." → 2.42s audio, RMS 0.101, đúng 1 quãng nghỉ, exit 0.

## 3. Kiểm kê: từng module đi đâu

| Module hiện tại | Đích | Ghi chú |
|---|---|---|
| `domain/` (models, prosody, segmenter, presentation) | **Engine, giữ nguyên** | |
| `speech/` (vieneu, cache, contracts, preferences, self_check) | **Engine, giữ nguyên** | |
| `playback/time_stretch.py` | **Engine, giữ nguyên** | đã chạy qua pipe |
| `playback/coordinator.py` | Logic thuần đã tái hiện ở headless; phần Qt nghỉ hưu | |
| `playback/qt_audio.py` | **Nghỉ hưu** → rodio (Rust) | |
| `importers/epub*.py` | **Engine, giữ nguyên** (thuần Python) | |
| `importers/pdf.py` | **Engine, PHẢI thay QtPdf → pypdfium2** | chốt chặn duy nhất giữa engine và PySide6 |
| `storage/` (SQLite) | **Engine, giữ nguyên** | |
| `integrations/apple_books*.py` | **Engine** | thuần Python/filesystem |
| `integrations/macos_selection.py` (ctypes) | **Nghỉ hưu** → Rust FFI cùng dylib | |
| `native/macos/*.m` | **Giữ nguyên, tái sử dụng** | C ABI sẵn |
| `integrations/selection_shortcut.py` (CGEvent tap) | **Nghỉ hưu** → tauri-plugin-global-shortcut | |
| `integrations/macos_settings.py` | Shell (mở URL `x-apple.systempreferences:`) | |
| `ui/` toàn bộ (13 file, ~5.000 dòng) + `theme.py` | **Nghỉ hưu** → React + DS thật | theme.py là bản dịch tay của DS - hết cần dịch |
| `ui/i18n.py` (chuỗi VI/EN) | **Port sang JSON i18n web** | giữ nguyên nội dung đã được rà |
| `app_main.py`, `__main__.py` | Nghỉ hưu → Tauri main + entry sidecar | |

## 4. Giao thức v2 (mở rộng trong P1)

Đã có: `ping` · `voices` · `read` · `stop`.

Thêm: `library.list` · `library.import {path}` · `library.remove {id}` ·
`book.render {id}` (chương + đoạn + hình cho web vẽ) · `progress.get/save` ·
`read.book {book_id, from_segment}` phát kèm event `position` (để highlight theo
câu + engine tự lưu vị trí) · `model.status` · `model.prepare` (event `progress`)
· `model.remove_build` · nhóm `notes.*` cho Chuyển ghi chú.

**Pause/resume KHÔNG nằm trong giao thức** — rodio Sink lo, stop mới là lệnh engine.

## 5. Các phase và cổng kiểm chứng

| Phase | Nội dung | Cổng (phải xanh mới sang phase sau) | Ước lượng |
|---|---|---|---|
| **P0 ✓** | Headless server v1 | 685 test + live smoke PASS | xong |
| **P1** | Giao thức v2 + thay QtPdf → pypdfium2 | unittest mới; **diff text-layer trên 2 sách thật** trong thư viện của chủ = không lệch nội dung | 2–3 phiên |
| **P2** | Scaffold `app/` Tauri v2 (React+TS+Tailwind) nối DS-Token thật; copy `Button`/`ToggleButtonGroup`… từ ui-registry (kèm provenance header theo guideline component-reuse) | `pnpm tauri dev` mở cửa sổ vẽ đúng token; screenshot đối chiếu | 1–2 phiên |
| **P3** | Rust spawn sidecar (dev: venv python) + rodio + 4 màn (Thư viện · Đọc sách · Dán · Quét đọc) chạy end-to-end | flow đọc sách thật từ thư viện hiện có; **độ trễ stop < 150ms đo được**; kill app → sidecar chết theo (kiểm bằng pgrep, bài học process-group) | 3–5 phiên |
| **P4** | Parity macOS: phím tắt ⌥⌘R, tray đang-đọc (hiện cả khi paused), FFI selection dylib, luồng xin quyền + khởi động lại, i18n VI/EN, màn chuẩn bị model có tiến trình | checklist parity từng-tính-năng so với app Qt (danh sách ở §7) | 2–4 phiên |
| **P5** | Đóng gói: `build-sidecar.sh` (PyInstaller onedir arm64, `--collect-all onnxruntime` + hooks cho sea_g2p/librosa/kaldi) · `externalBin` · ad-hoc sign · installer script mới | app bundle chạy live-smoke **từ bản đóng gói**; trỏ vào bản sao data root thật → thấy đúng thư viện cũ | 2–4 phiên |
| **P6** | **Nghỉ hưu app cũ**: 7 ngày dùng thật bản mới → tag `qt-final` → xoá `ui/`, `qt_audio`, selection_shortcut/macos_selection cũ, PySide6 khỏi dependencies; viết lại README/INSTALL | verify.sh (mới) xanh; `uv.lock` không còn PySide6; cài từ nguồn cho bạn bè chạy được theo INSTALL mới | 1 phiên |

Tổng thực tế: **~11–19 phiên làm việc tập trung**. Không phải một tuần; cũng không phải một quý.

## 6. Rủi ro và đối sách

| Rủi ro | Đối sách |
|---|---|
| PyInstaller thiếu hidden-import (onnxruntime/sea_g2p/librosa lazy-load) | `--collect-all` + hook riêng; cổng P5 là live-smoke chạy **từ bundle**, không tin build xanh |
| Sidecar mồ côi khi app chết | Rust kill-on-drop + engine tự thoát khi stdin EOF (đã có); kiểm pgrep trong cổng P3 — đúng bài học verify-app.sh giết theo nhóm |
| Phím tắt lúc paused (bug cũ) | Định nghĩa lại trong shell mới: tray hiện khi LOADING/PLAYING/**PAUSED**; phím tắt lúc đang đọc = dừng (giữ hành vi đã ship) |
| pypdfium2 trích text khác QtPdf | Cổng P1 diff trên sách thật của chủ, không phải sách mẫu |
| WKWebView autoplay/throttle | Né hẳn: audio thuộc Rust (rodio) |
| TCC hỏi lại quyền Accessibility (binary mới) | Có sẵn màn hướng dẫn + `tauri-plugin-macos-permissions`; luật "cấp xong phải khởi động lại" đã biết từ bản Qt |
| Gatekeeper cho bạn bè | Không đổi lập trường: cài từ nguồn qua script, chưa ký/notarize (đúng scope đã ghi nhớ) |
| RAM 2 runtime | Không tệ hơn hôm nay: webview ~50MB thay chỗ Qt; engine 1.3GB giữ nguyên |

## 7. Checklist parity (cổng P4 — trích để không ai quên tính năng nhỏ)

Thư viện (import PDF/EPUB, xoá, mở lại đúng vị trí) · đọc theo chương/đoạn,
Trước/Sau · chọn đoạn rồi "Đọc phần đã chọn" · Dán nội dung (giới hạn 100k ký tự,
không lưu thư viện) · Quét đọc mọi app + đổi phím tắt + hai đường dừng
(tray, phím tắt) · pause/resume · tốc độ 0.5–2.0 (8 nấc) · 2 bản dựng model
(Tiêu chuẩn/Cao nhất) + tải + xoá bản + đổi có xác nhận · 20 giọng · lịch sử phiên
· Chuyển ghi chú Apple Books (kèm backup + PRIVACY đúng lời hứa) · VI/EN ·
prosody (nghỉ câu/đoạn/chương, unshout) · cache audio theo revision.

## 8. Điều KHÔNG đổi (để đọc nhanh khi nghi ngờ scope)

Động cơ giọng, prosody, cache key, SQLite schema, data root, model files,
dylib ObjC, nội dung chuỗi VI/EN, lập trường không-ký-app.

## 9. Nhật ký quyết định

- 2026-08-31 · Chốt Tauri thay vì SwiftUI (một câu hỏi quyết định: có người dùng
  ngoài Mac trong tương lai + DS là web). SwiftUI bị loại vì khoá DS ngoài cửa.
- 2026-08-31 · Chốt audio thuộc Rust/rodio, không WebView.
- 2026-08-31 · Chốt giữ bundle id + data root → zero migration.

---

# Kế hoạch chi tiết thi công (bổ sung 2026-08-31, sau khi chủ duyệt "tập trung làm app")

Sắp xếp lại theo **mốc nhìn thấy được**, không theo tầng kỹ thuật. P1 giao thức v2
không chặn scaffold — v1 (`ping/voices/read/stop`) đã đủ cho luồng đầu tiên.

## Mốc A — "App nói được" (P2 + nửa P3)

| # | Việc | Chi tiết |
|---|---|---|
| A1 | Scaffold `app/` | Tauri v2 + React + TS + Vite, pnpm. Cửa sổ min 960×600 |
| A2 | Nối DS thật | Tailwind v4 + snapshot `tokens.css` từ DOL-DS-token (provenance header, ghi ngày + nguồn); font @fontsource Plus Jakarta Sans + Be Vietnam Pro (offline, không CDN) |
| A3 | Khung màn | Nav 4 tab kiểu ToggleButtonGroup (copy từ ui-registry) · i18n VI/EN port từ `ui/i18n.py` (JSON) |
| A4 | Rust ↔ sidecar | Dev-mode spawn `.venv/bin/python -m vieneu_reader.headless.server`; JSONL client (thread đọc stdout, map id→pending); app thoát ⇒ đóng stdin ⇒ engine tự thoát (đã chứng minh EOF-exit) |
| A5 | Rust phát tiếng | Thread audio riêng sở hữu rodio OutputStream+Sink (không Send); nhận f32 48k mono từ frames; pause/resume = Sink, stop = lệnh engine + xả Sink |
| A6 | Màn Dán nội dung | Luồng end-to-end đầu tiên: textarea → Đọc → nghe; Dừng/Tạm dừng; chọn giọng + tốc độ (từ `voices`) |

**Cổng A**: dev-app đọc được tiếng Việt thật từ ô dán · Dừng < 150ms đo bằng log ·
thoát app ⇒ `pgrep` không còn python mồ côi · tab nav vẽ đúng token DS (đối chiếu ảnh).

## Mốc B — "Thư viện + Đọc sách" (P1 + nửa P3)

| # | Việc |
|---|---|
| B1 | Engine: `library.list/import/remove` · `book.render` (chương/đoạn/hình) · `progress.get/save` · `read.book {from_segment}` phát event `position` |
| B2 | Thay QtPdf → pypdfium2; cổng: diff text-layer 2 sách thật |
| B3 | UI: Thư viện (import + kéo-thả + empty state DS) · Trình đọc (cột 65ch, highlight câu theo `position`, click-đoạn-để-đọc, Trước/Sau, Đọc phần đã chọn) |

**Cổng B**: trỏ bản sao data root thật → thấy đúng 2 sách cũ, đọc tiếp đúng vị trí đã lưu.

## Mốc C — "Quét đọc + parity" (P4)

⌥⌘R (plugin global-shortcut) · FFI `libReadEaseSelectionNative.dylib` · tray đang-đọc
(hiện cả khi PAUSED — sửa bug cũ) · luồng xin quyền + khởi động lại · màn chuẩn bị model
(prepare/progress/đổi bản có xác nhận/xoá bản) · lịch sử phiên · Chuyển ghi chú · VI/EN đủ.

**Cổng C**: checklist parity §7 xanh từng dòng.

## Mốc D — Đóng gói + nghỉ hưu (P5 + P6, giữ nguyên như trên)

## Nguyên tắc thi công

- Mỗi mốc kết thúc bằng chạy thật + ảnh/số đo, không tin build xanh.
- Engine test bằng unittest sẵn có; UI web test sau khi khung ổn định (vitest), không viết test cho markup đang đổi từng ngày.
- Không commit khi chưa được duyệt (giữ kỷ luật hiện tại).

- 2026-08-31 · **Audit màu light/dark (sau ảnh chụp của chủ)**: app nửa sáng nửa tối vì
  (a) component registry `ToggleButtonGroup` mang 17 màu slate/white cứng — nó được viết cho
  web DOL light-first, không tiêu thụ được trong app hai chế độ → đúng guideline component-reuse:
  **ghi nhận gap, thay bằng `src/ui/AppTabs.tsx`** (giữ nguyên hình học style-1, màu 100% qua
  token) — ứng viên đóng góp ngược: biến thể dark-capable cho registry; (b) 8 chỗ `bg-white`
  của chính shell. Giải pháp gốc: **cầu token `@theme inline`** (paper/ground/ink/edge/band/
  wash/rail) — mọi className đi qua biến DS đã tự flip theo `[data-theme]`; cấm màu literal
  ngoài brand. Đo số cả hai chế độ (giải chuỗi var từ snapshot): phát hiện `--fill-neutral-tint`
  đè thành dải gần-trắng dưới chữ trắng ở dark (bug trắng-trên-trắng của vòng Qt quay lại qua
  ngả token) → vai trò app khai tường minh 2 chế độ như theme.py: ground n20/n00 · band n10/n20 ·
  rail n10. Viền ~1.6:1 GIỮ có chủ đích (DS tự dùng hairline lớp slate-200; control nổi bằng fill)
  — cùng quyết định đã ghi ở vòng Qt. Scrollbar WKWebView + ::selection cũng theo token.

- 2026-08-31 (đêm) · **Goal "đọc-trọn-vẹn" READY** (AQC `a25e538a…` 0.881/0.85, 0 hard-fail):
  P1 pypdfium2 thay QtPdf (9 assertion parity giữ nguyên, xanh; sort rect theo vị trí thị giác
  vì pdfium trả theo content-stream; pin dep cập nhật có lý do; test `_utf16_length` nghỉ hưu
  cùng chủ thể QtPdf) + `library.import/remove` đi qua LibraryService thật (khoá, dedupe,
  managed copy; xoá = rows luôn luôn, file chỉ khi nằm trong paths.books — không bao giờ đụng
  file nguồn của người dùng) · P2 import UI (nút → file panel WKWebView → bytes → temp →
  service; webview không thấy path thật nên đi đường bytes — id sách theo hash nội dung nên
  giống hệt import theo path; kéo-thả DEFER) + xoá-có-confirm inline + empty-state theo mẫu Qt ·
  P3 Quét đọc: **ObjC bridge nhúng tĩnh qua build.rs** (cải tiến so với dylib: không còn bài
  toán install-name khi đóng gói), ⌥⌘R qua plugin global-shortcut (đang-đọc = dừng), tray
  chỉ-hiện-khi-đọc **kể cả PAUSED** (sửa bug Qt), màn Quét đọc + 7 thông điệp lỗi verbatim +
  lịch sử phiên + nghe lại; giọng/tốc độ sống ở webview nên hotkey đi vòng event → invoke
  (giới hạn đã ghi: đóng cửa sổ là hotkey mất — mốc D xử) · P4 model.status (duck-type
  method/property) + chip bản dựng + nổi lỗi đọc + Space tạm dừng + focus-visible.
  **Bug kiến trúc bắt được nhờ smoke root-trống**: một handler nổ từng GIẾT CẢ SERVER
  (model.status trên root trống) → lưới dispatch: mọi exception thành một reply lỗi, có test
  giữ. Smoke 2 chốt: import/list/status thật + voices/read trả lỗi tử tế trên root trống +
  EOF exit sạch. **Chờ tay chủ**: bấm ⌥⌘R lần đầu (TCC prompt) — UNKNOWN có khai cho tới khi
  chủ xác nhận.

- 2026-09-01 · **Goal "parity + bundle" READY** (AQC risk=high `14eb8f6e…` 0.900/0.88, review độc
  lập bởi advisor): phím tắt tuỳ chỉnh (recorder + persist settings.json + re-register, đăng-ký-
  trước-lưu-sau) · quản lý model (status/prepare-qua-event/switch-kèm-restart-engine/xoá bản dự
  phòng; EngineSlot swappable, tray slot sống qua restart) · VI/EN (module language + config,
  re-render key) · **Chuyển ghi chú qua pipe**: tái dùng nguyên reader/planner/writer/backup,
  4 test outcome-matrix khoá bất biến backup-trước-ghi + từ-chối-khi-Books-mở · **Mốc D**:
  PyInstaller onedir 393M (loại PySide6/librosa/soxr/kaldi như Nuitka), `playback/__init__`
  lazy-Qt (PEP 562, test poison sys.modules — venv che lớp gãy này), `pnpm tauri build` →
  **ReadEase.app 403M + dmg**, engine BÊN TRONG .app ping được + fp32 ready + 20 giọng,
  bundle id đúng `vn.dolenglish.vieneureader`, resources-first fallback venv.
  **Advisor bắt 3 bug thật trước receipt, đã sửa + re-verify**: tabs cache ngôn ngữ (useMemo
  deps) · model.prepare chết ở timeout 30s (→ notify() + event `engine:orphan_reply`) ·
  MutexGuard giữ khoá suốt call chặn làm nút Dừng đứng hình (→ `client_of()` bind-then-drop).
  Ghi chú không chặn đã nhận: restart-đang-đọc = stop trước + khoá nút switch khi đọc ✓ ·
  unregister-trước-register có thể mất phím cũ nếu phím mới bị từ chối (minor, ghi nhận) ·
  bookmark kind hiển thị như highlight (cosmetic) · đừng chạy song song app release + dev
  (2 sidecar cùng 1 sqlite) · notes lần đầu có thể cần Full Disk Access (đường xử lý có sẵn).
  **User-verified-later**: recorder thật, tải model thật, transfer thật vào Apple Books.

- 2026-09-01 · **Lát "first-run + polish" READY** (AQC `055405b2…` 0.899/0.85): màn **Chuẩn bị
  giọng đọc** gate toàn app khi model chưa sẵn (máy bạn bè cài mới không còn gặp nút đọc chết;
  fallback engine-chết → vẫn hiện app thay vì cửa sổ trắng) · **hình minh hoạ EPUB** qua pipe
  (`book.open` thêm refs additive + `book.figure` lazy từng hình, IntersectionObserver, test
  kèm đường từ chối) · **Đọc phần đã chọn trong sách** (nút nổi chỉ hiện khi có vùng chọn) ·
  **reading:started** từ chunk PCM đầu → "Đang chuẩn bị giọng đọc…" thay khoảng lặng ·
  refetch voices sau đổi model · **icon thật** từ readease-icon-master.png (hash khớp trong
  .app) · title "ReadEase - Thư Âm". `verify.sh` 701 · sidecar + .app rebuild, engine trong
  .app fp32 ready. Bằng chứng render: EN-switch lật trọn tabs/labels (chốt fix advisor #1).
  User-verified-later: màn Setup trên máy trắng model, hình trong sách thật, warming bằng tai.

- 2026-09-01 · **Audit UI theo phản hồi chủ (dark screenshots)**: (1) phân cấp — Library từng là
  chữ-trôi-trên-bàn, nay danh sách nằm trên **paper rounded-2xl** như Reader (một ngôn ngữ mặt
  phẳng toàn app), tiêu đề màn nâng text-lg → **text-xl**; (2) bo góc tròn hơn theo bậc DS:
  **tabs thành pill trọn** (shape=pill của ToggleButtonGroup), control 30px đồng bậc rounded-xl,
  mặt phẳng rounded-2xl — sed quét lố từng làm nút phụ nhảy 2xl cạnh nút chính xl (vi phạm
  sibling-radius harmony, tự bắt bằng grep bậc và chuẩn hoá lại); (3) **bỏ divider trên footer**
  (tách bằng khoảng trống); kèm: chip model có nhãn "Chất lượng" đồng dạng control (hết chip
  mồ côi khó hiểu), nút primary disabled đổi brand-mờ → neutral outline (hết "đỏ bẩn" trong
  dark). Engine không đổi — cổng = pnpm build + render đối chứng.

- 2026-09-01 · **Hàng sách theo phản hồi chủ**: icon sách + hàng 2 dòng, dòng phụ = "{n} chương ·
  {size} MB · Nhập {date} (· Đang đọc dở)" — engine mở rộng `library.list` (chapters/size_bytes/
  imported_at qua `repository.imported_at`; test hợp đồng đỏ-trước) để **phân biệt 2 bản trùng
  tên bằng dữ kiện thật**, kèm marker Đang-đọc-dở là dấu phân biệt hữu ích nhất. Nút xoá →
  icon thùng rác, màu qua bridge `--color-danger` (token `--text-color-danger-primary` của DS)
  — sửa luôn lỗi ngữ nghĩa cũ: confirm Xoá từng mượn brand-600, phạm luật cứng **brand ≠ danger**.
  Icons: DsIcon không tiêu thụ được ngoài repo DOL (gap đã ghi) → 2 glyph vẽ theo hình học của
  nó (grid 16, stroke 1.5, currentColor). Bài học sed lần 2: `h-7 shrink-0 rounded-md` thoát
  lưới "h-7 rounded-md" — anchor class Tailwind phải lỏng hoặc grep-hậu-kiểm theo bậc.

## Cơ chế đọc - audit và sửa (2026-09-02)

Chủ báo: highlight nhảy loạn không khớp nội dung đang đọc; bấm nhanh thì đọc không ngừng dù đã
bấm dừng. Đọc cả ba tầng, tìm ra **sáu lỗi chồng lên nhau**, tất cả đều xác nhận bằng mã nguồn:

1. **Bắt đầu một lượt đọc KHÔNG huỷ lượt đang chạy.** `fire()` chỉ ghi đè `current_read`. Engine
   Python **hoãn** (`_deferred`) mọi request không phải `stop` khi đang stream, nên click thứ hai
   mua thêm MỘT lượt đọc đầy đủ nữa chứ không thay thế. → `fire()` nay huỷ trước khi gửi.
2. **Sự kiện `position` không lọc theo id** — vị trí của lượt đã bị bỏ vẫn lái highlight.
3. **Chunk đóng dấu epoch lúc Rust ĐỌC được**, không phải epoch của lượt sinh ra nó.
4. **Luồng âm thanh gọi `player.play()` sau MỖI lần append** ⇒ tạm dừng bị phá: chunk kế tiếp tự
   bật lại tiếng. Pause nay là TRẠNG THÁI (`AtomicBool`), append không được phép bật lại.
5. **`Player::clear()` của rodio kết thúc bằng `pause()`** (đọc mã crate) — sau mỗi lần dừng,
   player nằm im; lượt sau chỉ kêu nhờ đúng cái `play()` sai ở lỗi 4 che đi.
6. **Không có backpressure thật**: hàng đợi của rodio vô hạn nên `sync_channel(48)` không bao giờ
   đầy; engine dựng chạy trước tai rất xa, và vì `position` phát lúc dựng nên highlight chạy
   trước giọng. → giới hạn `PLAYER_LOOKAHEAD = 2` + mốc vị trí đi chung hàng đợi âm thanh.

**Thứ tự trong `fire()` là bắt buộc** (sai một nhịp là hở race): đặt `current_read` mới TRƯỚC để
bộ lọc id bắt đầu chặn lượt cũ → rồi mới tăng epoch để giết chunk đã lọt qua bộ lọc → clear →
`play()` (gỡ pause mà `clear` để lại) → gửi `stop` nếu đang đọc → gửi lượt mới. Toàn bộ trong một
mutex `start` để hai click nhanh xếp hàng thay vì đan vào nhau.

**Kèm theo**: `engine:orphan_reply` chỉ còn phát cho request gửi qua `notify()` (sổ `notified`) —
trước đây reply muộn của một lượt đọc bị bỏ cũng phát ra, và ModelPanel/Setup nghe nhầm thành
"tải model xong".

**Đã kiểm**: probe trên engine THẬT (cắt giữa dòng: lượt cũ 0 chunk sau khi cắt, lượt mới chạy
14 chunk rồi kết thúc) · test hồi quy mới trong `tests/headless` · toàn bộ 702 test engine OK ·
`cargo build --release` sạch cảnh báo · cổng frontend xanh.
**CHƯA kiểm được bằng máy**: tai người - hết tiếng ngay khi bấm dừng, không còn tồn đọng, và
highlight bám đúng câu đang nghe. Đó là 3 mục cần chủ nghe thử.

### Nửa sau: máy trạng thái ở vỏ (2026-09-02, chạy dưới /goal)

Sáu lỗi trên nằm ở Rust/engine. Nửa còn lại của cùng triệu chứng nằm ở React và chưa từng được
audit: `stopReading` **await** engine rồi mới đổi trạng thái, mà `stop()` bên Rust chặn ở
`player.clear()` → `sleep_until_end()` cộng một `request("stop")` đồng bộ. Người bấm Dừng thấy
giao diện y nguyên nên bấm tiếp — đúng lời chủ mô tả. Cộng thêm **5 chỗ** tự tay `setReading`,
trong đó 2 chỗ quên `setWarming`.

Sửa: tách máy trạng thái ra `app/src/ui/playback.ts` — hàm thuần tuý `playback(state, event)`
với 6 sự kiện (start · stop · toggle · failed · voice · done), không phụ thuộc React nên test
được bằng runner zero-dep sẵn có (8 test mới, tổng frontend 10 → 18). App tiêu thụ qua
`useReducer`; **stop/pause đổi trạng thái TRƯỚC rồi mới gọi engine**.

Bằng chứng: engine giả trả lời `stop_reading` sau 3000ms → giao diện về idle sau **26ms** (trước
đây phải chờ đủ 3000ms) · `grep` còn **0** chỗ tự đổi trạng thái ngoài reducer · Space vẫn đổi
Tạm dừng/Tiếp tục · bảng hiện-footer-theo-màn (HIG §3.5) không đổi · tsc·UI_AUDIT·18 test xanh.

**Sửa đổi ranh giới sau review độc lập (02/09)**: `stop()` bên Rust không lấy khoá `start` mà
`fire()` dùng, dù cả hai cùng viết `current_read`, `epoch` và player. Cử chỉ rất thường —
"dừng cái này, đọc từ đây" — là hai lệnh Tauri chạy trên hai luồng, và có một thứ tự hợp lệ
khiến `stop()` xoá mất id của lượt vừa bắt đầu: lượt mới bị giết, reply của nó không khớp ai,
không có `reading:done` nào được phát, và vỏ kẹt ở "đang đọc" trong im lặng. Đây đúng là đường
mà tiêu chí H2 cấm, và KHÔNG sửa được ở tầng UI. Đã cho `stop()` lấy cùng khoá; phép gán lại
`current_read` trong `fire()` nhờ đó thành thừa và đã bỏ.

**Rủi ro còn lại, cố ý KHÔNG gộp vào vòng này**: lượt cũ kết thúc TỰ NHIÊN đúng trong khe vài
ms giữa lúc UI phát `start` và lúc `fire()` nhận `current_read`. Rust phát một `reading:done`
hợp lệ, reducer về idle, trong khi lượt mới đang chạy → hiện nút "Đọc" dù đang phát. Khe hẹp,
tự phục hồi ở tương tác kế tiếp. Cách sửa sạch: `fire()` trả id, `reading:done` mang id, UI bỏ
qua done của thế hệ đã bị thay — việc đó mở rộng hợp đồng sự kiện nên thuộc vòng khác.

## Đối chiếu parity với vỏ Qt (2026-09-02)

Cách soi: liệt kê bề mặt app cũ (13 module UI, 5026 dòng + `ui/controller.py` 847 dòng +
`playback/preferences.py`), lấy **155 khoá i18n cũ** làm proxy cho bề mặt tính năng rồi diff
với 117 khoá mới, và kiểm từng khoá chênh xem là **đổi tên** hay **mất thật**.

**Đã đưa qua trong vòng này**

| Thiếu | Vì sao quan trọng | Đã làm |
|---|---|---|
| Không nhớ giọng + tốc độ | App cũ lưu `voice`/`rate` vào settings.json; bản mới mặc định lại mỗi lần mở | Cho phép đúng HAI khoá cũ qua `_CONFIG_KEYS`, đọc lúc khởi động, ghi khi đổi — người dùng bản Qt giữ nguyên lựa chọn |
| Không huỷ được lượt tải model | fp32 = 453MB, bấm nhầm là kẹt tới hết | `report()` thăm dò stop và ném `_PreparationCancelled` (đúng chỗ app cũ dùng), reply `cancelled: true`; nút Huỷ ở cả Setup lẫn ModelPanel |
| Ảnh trong sách hỏng thì im lặng | Người đọc chỉ thấy khoảng trắng, không biết là lỗi hay sách vốn thế | `reader.figure_unavailable` + bắt cả lỗi tải lẫn lỗi giải mã (`onError`) |
| Vượt giới hạn ký tự không nói gì | Nút mờ đi mà không giải thích | `paste.over_limit` |
| Không xoá được lịch sử quét đọc | App cũ có trong menu lịch sử | Nút "Xoá lịch sử" ở màn Quét đọc |

**Cố ý KHÔNG đưa qua** (nêu để chủ quyết, không phải bỏ sót):
- `player.source.*` — nhãn "đang đọc từ Apple Books / từ sách / từ nội dung dán". Thanh dưới bản
  mới đã mang đúng năng lực của từng màn nên bản thân màn đã nói nguồn; thêm nhãn là lặp.
- Lịch sử đọc nằm trong **menu của thanh phát** (bản cũ). Bản mới đặt lịch sử ở màn Quét đọc —
  đúng chỗ hơn theo luật "thanh dưới chỉ mang năng lực của màn".
- Biểu tượng menu bar: bản cũ vẽ hình loa dạng template cho macOS tô màu; bản mới dùng icon app.
  Thuần thẩm mỹ, một click dừng đọc thì cả hai như nhau.

**Không hở**: 6 lý do trạng thái của cầu chọn văn bản (`selection_status_name`) khớp đủ 6 chuỗi
`status.*`; các khoá `transfer.*`/`model.*` chênh chỉ là đổi tên (`outcome.*`, `noteserr.*`,
`model.build_*`).

## Hình trong sách chưa từng hiện được (sửa 2026-09-02)

Chủ báo "Không mở được hình này" trên sách thật. Không phải lỗi giao diện: gọi thẳng engine cũng
trả `figure unavailable`.

**Gốc rễ - sai khoá tra cứu.** `load_epub_assets` trả `{asset_path: bytes}` (khoá là tên member
trong file EPUB), nhưng `_book_figure` tra bằng `figure_id` (một chuỗi băm). Không bao giờ khớp
⇒ **chưa một hình nào từng hiện trong vỏ Tauri**. Controller của vỏ Qt vốn làm đúng:
`assets.get(figure.asset_path)`.

**Gốc rễ thứ hai - con giả trong test mô phỏng CÁI SAI của người gọi.** Test `book.figure` đã tồn
tại và luôn xanh, vì fake `assets_for` trả `{"fig-1": bytes}` tức khoá theo figure id, và fixture
đặt `id` trùng vai trò với đường dẫn. Một fixture mà hai khoá là một chuỗi thì không thể phân
biệt tra đúng với tra sai. Đã cho fixture `asset_path="OEBPS/images/one.png"` khác hẳn `id`, và
fake trả về đúng hợp đồng thật.

**Verify**: test mới ĐỎ với mã cũ / XANH với mã mới (thử cả hai chiều) · engine chạy từ nguồn lấy
được **5/5 hình** của một sách thật 195 hình (image/jpeg, bytes thật) · 703 test engine + 18 test
frontend xanh.

**Bài học chung**: fake trong test phải mô phỏng HỢP ĐỒNG của thứ nó thay thế, không phải mô
phỏng cách người gọi đang dùng - nếu không, test chỉ đóng dấu cho lỗi.

## Báo hình khi đọc (2026-09-02, chủ duyệt 4 quyết định)

Người nghe không thấy trang, nên tới hình thì giọng nói **"Xem hình N."** + nghỉ 600ms. Quyết
định đã chốt: câu "Xem hình N." · số theo **chương** · báo **mọi** hình · ẩn alt rác.

Cách làm: `_figure_cues()` gom hình theo segment neo; `read.book` dệt một utterance cue vào
TRƯỚC hoặc SAU segment đúng theo `placement`; utterance mang `figure_id`, và sự kiện `position`
của nó mang `figure_id` ⇒ đi chung hàng đợi âm thanh bên Rust (không sửa Rust) ⇒ vỏ nhận đúng
lúc tai nghe, cuộn tới + nháy hình. `book.open` nay gửi thêm `number` (theo chương) và
`alt_is_generic` — hai trường domain đã tính sẵn nhưng bản viết lại bỏ rơi.

Test: `test_reading_a_book_announces_each_picture_where_it_sits` (thứ tự nói: "Đoạn đầu." →
"Xem hình 1." → "Xem hình 2." → "Đoạn hai."; position mang figure_id đúng chỗ; số 41/42 của
domain thành 1/2 theo chương). Câu cue đăng ký vào `ui/i18n.py` vì test phủ-dịch coi lời nói
cũng là chữ đặt trước mặt người. Bẫy đã gặp: đặt tên biến `position` cho dict sự kiện đè lên
biến đếm `position` của vòng lặp ⇒ `is_last` cộng dict với int.

## App bị đứng khi đang chạy (sửa 2026-09-02) - hai tầng

Chủ báo app thỉnh thoảng non-responsive khi đang chạy. Hai nguyên nhân xếp chồng, đều xác minh
bằng mã nguồn crate + đo trên engine thật; nghi vấn thứ ba (rodio `clear()` treo khi pause) bị
loại sau khi đọc `Pausable` ("returns zero value samples" - mẫu vẫn chảy).

**Tầng 1 - lệnh Tauri chạy trên LUỒNG CHÍNH.** `tauri-macros/src/command/wrapper.rs`: lệnh `fn`
thường → ngữ cảnh `"sync"` (chạy ngay trong IPC handler, trên main thread); chỉ `async fn` hoặc
`#[tauri::command(async)]` → `"sync_threadpool"`. Cả 12 lệnh của app đều là `fn` thường, và
nhiều lệnh CHỜ engine (`request()` có timeout 30s). Mỗi lần chờ = cửa sổ đứng. → Tất cả 12 lệnh
chuyển sang `#[tauri::command(async)]`; biên dịch sạch (mọi State đều Send+Sync).

**Tầng 2 - engine HOÃN mọi request khác trong lúc đọc.** `_stop_requested()` chỉ bắt `stop`,
còn lại đẩy vào `_deferred` tới khi lượt đọc xong. Đo trên engine đã cài: `library.list` và
`config.get` gửi lúc đang đọc chỉ được trả lời sau **6.56s** (đúng lúc 6 câu đọc xong); một
chương dài = hàng phút = quá timeout 30s. Với người dùng: đang nghe mà bấm sang Thư viện thì
danh sách không bao giờ về; đổi tốc độ thì không lưu; cuộn tới hình thì hình không tải — trên
main thread thì cả cửa sổ đứng. → `_INLINE_WHILE_STREAMING`: 9 method nhanh, vô hại
(ping · voices · library.list · book.open · book.figure · config.get/set · model.status ·
notes.books) được `_dispatch` ngay giữa hai chunk, cùng lưới try/except như `run()`; thứ nặng
hoặc ghi (import/remove/prepare/set_precision/transfer/read*) vẫn hoãn. Đo lại: trả lời trong
vài ms.

Test: `test_quick_requests_are_answered_while_a_reading_streams` (ping về TRƯỚC reply của
lượt đọc). Rust không có test tự động cho tầng 1 - bằng chứng là mã macro + biên dịch.

## "#N" đọc thành số thứ tự (2026-09-02)

Chủ: "#1 đọc thành 'thứ nhất', #2 → 'thứ hai' thì hay hơn". Sách đang đọc có 9 chỗ. Sửa ở
`speakable_text` (chỉ lời nói, không đổi chữ hiển thị): `spell_ordinal_marks` + `ordinal_words`
với luật bất quy tắc tiếng Việt (nhất/tư; mốt/tư/lăm trong số ghép). 3 test mới trong
`tests/domain/test_prosody.py`. Cache khoá theo chữ đưa model ⇒ tự vô hiệu.

## Gạch ngang trước số không được nghỉ (sửa 2026-09-02)

Chủ: "kể—99 xu" đọc liền không nghỉ. Gốc: `_CLAUSE_BOUNDARY` có guard khoảng số viết là
`(?<!\d)…(?!\d)` = né gạch chạm chữ số ở bất kỳ phía nào, trong khi khoảng số cần chữ số ở CẢ
hai phía. Sửa: bắt khoảng số làm nhóm riêng `(?P<range>\d\s*[—–-]\s*\d)` và bỏ qua nó; mọi
gạch ngang khác là ranh giới; thêm gạch nối có khoảng trắng hai bên. Tổng quát hoá guard
mở-lời-thoại (đầu văn bản HOẶC ngay sau câu đã kết) — test cũ "Cô ấy gật đầu. - Vâng" bắt được
khi tôi thêm gạch nối. 3 test mới, 41 prosody test OK.

## Chú thích siêu chỉ số bị đọc thành tiếng (sửa 2026-09-02)

Quét toàn thư viện qua chính giao thức engine (3 sách, 6.722 đoạn) tìm "rác" mà giọng sẽ đọc:
noteref `[N]` 0 · siêu chỉ số `¹²³` **6** (tất cả là chú thích: sau dấu chấm hoặc dính vào từ, không
có luỹ thừa) · URL/email 10 (tiền văn) · ISBN/© 19 (tiền văn) · tiêu đề "01…100" 203 (cấu trúc
sách 100 nguyên tắc, chưa rõ model đọc "01" ra sao - chờ tai) · `[ghi chú]` 12 (lời dẫn trong
transcript, là nội dung). Sửa cái duy nhất rõ ràng và an toàn: `drop_note_marks` trong
`speakable_text` bỏ siêu chỉ số KHÔNG đứng sau chữ số (giữ "10³"). Trang giữ ký hiệu. 4 test
(đỏ trước/xanh sau: "Tang.³ Developer" đọc là "Tang. Developer"); 715 test OK.
Không làm: URL/ISBN (tiền văn, người đọc bỏ qua bằng cách bấm vào chương), `[N]` (0 ca).
Cùng lượt: tiêu đề "01…100" - đo thời lượng "01." 0,64s · "1." 0,48s · "không một." 0,72s (bước
lượng tử 0,08s) → số 0 gần như chắc được đọc. `_LEADING_ZERO` chỉ áp cho heading, chỉ số 0 dẫn đầu
ngay trước chữ số; nước đi không thể thua (model vốn nói "một" thì không đổi gì). 3 test, 718 OK.
Chứng minh trên binary (sandbox HOME, bản sao DB, sách thật, 9 tiêu đề 0N): engine cũ 17:56 →
mới 18:25: "01" 0,72s → 0,48s · "02" 0,88s → 0,56s. Số 0 đúng là được đọc; giờ chỉ nói số.

## Bản app rác trong thư mục ẩn (2026-09-02)

`open -a ReadEase` mở nhầm bản Qt cũ trong `~/.config/superpowers/worktrees/…/dist/` - `mdfind`
đợt dọn trước không thấy vì Spotlight không index thư mục ẩn. Nguồn sự thật cho "open -a chọn
bản nào" là **LaunchServices**: `lsregister -dump | grep ReadEase.app`. Dọn: bản worktree → Trash;
`lsregister -u` bản build trong `target/` (file giữ, chỉ gỡ đăng ký - `tauri build` nào cũng tạo
lại bản này nên gỡ đăng ký sau MỖI lần cài); `-gc` dọn 13 mount `.dmg` đã biến mất. Còn đúng 1.

## Ký hiệu liệt kê "(a)(b)(c)" (2026-09-02, chủ chọn bằng tai)

Đề xuất đầu "xoá" bị tự phản biện lật (xem reading-intelligence-audit §7). Render 4 wav từ chính câu
trong ảnh của chủ; chủ chọn **"3-chu-cai-nghi"**: giữ chữ cái, thêm nghỉ - "a, nhiệm vụ hiện tại, hoặc
b, sở thích cá nhân". `speak_enumerators` trong `speakable_text`: `(x)` chữ thường đơn, có khoảng trắng
trước → "x,"; nếu có liên từ dẫn vào (hoặc/hay/và/rồi/cũng như) thì nghỉ chuyển lên TRƯỚC liên từ
(đúng bản đã nghe; lỗi đầu tiên để sót khoảng trắng " , hoặc" - bắt bằng test so khớp từng ký tự);
tham chiếu "mục (b)" → "mục b" không nghỉ (guard giữ dù thư viện 0 ca). Không mở rộng sang "(1)",
"(A)": 0 ca trong thư viện. 4 test; 722 OK. Trang giữ nguyên "(a)".

## Sự cố: probe làm hỏng tiến độ thư viện thật (2026-09-02) - sửa engine + luật probe

Probe đo "01" gọi `read.book` KHÔNG kèm `voice_id` → engine ghi progress (segment, rate, voice="")
ở position đầu tiên RỒI mới hỏi giọng → giọng từ chối ("Voice '' not found") nhưng dòng đã nằm
trong `reader.sqlite3`; `load_progress` đòi voice không rỗng → `RepositoryCorruptionError` → cả
`library.list` sập (3 sách đều không liệt kê được). WAL cho thấy phiên bản trước của dòng đó cũng
là probe (giọng "Minh Đức", probe báo hình lúc chiều) ⇒ vị trí thật của chủ trong cuốn Universal
Principles (nếu từng có) đã mất từ trước, không khôi phục được. Đã xoá dòng voice rỗng; thư viện
liệt kê lại (3 sách). Cuốn "Đừng bắt tôi phải suy nghĩ!" (giọng Adam) không bị đụng.
Sửa gốc: `_read_book` từ chối `voice_id` rỗng TRƯỚC `_speak` (điểm ghi progress). Test:
read.book không voice → lỗi, engine không được gọi, `load_progress` None, `library.list` sau đó OK.
Không nới `load_progress` (giữ nguyên tắc "hỏng thì kêu to"). Advisor chỉ thêm nửa kia của hợp đồng loader: `rate` ngoài 0,5–2,0 cũng bị từ chối khi nạp → guard + test tương tự (724 OK). **Source đi trước binary 18:35 đúng một guard `rate`** (UI không gửi được giá trị đó nên chưa dựng lại; gói ở lần cài kế). Luật probe (memory + brief):
`read` chữ thường không ghi gì; `read.book` LUÔN là ghi → chạy trên app-root tạm / bản sao DB.

## Nút nổi trong suốt khi hover (sửa 2026-09-02, chủ bắt)

"Về chỗ đang đọc" bị chữ đè lên khi rê chuột. Đo trong preview đúng trạng thái lỗi (đang đọc +
cuộn xa): nền hover = `rgba(243,243,243,0.05)` — `hover:bg-wash` THAY nền giấy đục bằng alpha 5%.
Sửa ở bộ control: utility `hover-wash` (index.css) vẽ wash/press bằng `background-image` gradient
PHỦ LÊN `background-color`; áp cho Button secondary/ghost/danger + IconButton (nút đóng lightbox trên
nền đen cùng lỗi). `Select` giữ nguyên (chevron nằm trong background-image). Sau sửa: tối
`rgb(38,39,39)` + gradient, sáng `rgb(255,255,255)` + gradient. HIG §3.9b. Kèm: mock thiếu
`__TAURI_EVENT_PLUGIN_INTERNALS__.unregisterListener` (mọi cleanup effect ném lỗi trong preview) — vá.

## Thư viện thành kệ bìa (2026-09-02, chủ yêu cầu "layout có cover")

Nghiên cứu (miền ổn định, không tra web): Apple Books, Kindle, Google Play Books, Libby, Calibre đều
hội tụ về lưới bìa 2:3 + tiêu đề dưới + thanh tiến độ cho sách đang đọc; "continue reading" tách riêng
chỉ đáng khi thư viện hàng trăm cuốn. Quyết định: MỘT lưới, đang-đọc xếp trước (`orderShelf`, test
node), thanh tiến độ brand dưới bìa, placeholder chữ trên `panel` khi không bìa, accessory xoá nổi
góc bìa + ConfirmInline thay khối chữ. Khoảng cách 32/40px giữa sách, 12px trong thẻ (chủ chỉnh).
Engine: `load_epub_cover` (3 quy ước: `cover-image` → `<meta name=cover>` id/href → tên chứa
"cover"; chỉ png/gif/jpeg/svg, xác minh byte thật, cap 8MB, qua `_verified_archive` + hash),
`load_pdf_cover` (trang 1 → JPEG 600px, 21 ms), `shrink_cover` (bìa >300KB/900px → JPEG 600px; bìa
in 2MB của chủ → 48KB), `service.cover_for` cache theo hash, `book.cover` (null = bình thường, trả
lời ngay khi đang đọc — đo lạnh trên sách thật sau shrink: 67 / 22 / 13 ms, nóng 0 ms, dưới ngưỡng
100 ms giữa hai chunk audio), `library.list` thêm `progress_ratio`/`progress_chapter`. `_package_contract`
tách `_package_document` (giữ nguyên tuple trả về). Gate sách thật (đọc-chỉ, bản sao DB): **3/3 có
bìa**. Frontend cache bìa theo book id qua các lần vào/ra kệ. `progress_chapter` = tooltip "Đang ở: …" trên dòng dữ kiện (advisor: không ship
trường không ai đọc). Test: 7 importer + 2 server + 3 node.
Pillow (đã có trong venv) giờ được import tường minh trong `importers/covers.py` để PyInstaller gói.
**Suýt hỏng**: `build-sidecar.sh` còn `--exclude-module PIL` (chép từ danh sách Nuitka cũ) → engine
đóng băng chết ngay lúc import `covers.py` (`ModuleNotFoundError: PIL`) trong khi 733 test venv xanh
và `tauri build` EXIT=0. Bắt được nhờ chạy thử binary vừa dựng trước khi cài. Sửa: bỏ loại trừ PIL +
**cổng khói** trong script (binary phải trả lời `ping`, không thì build fail) — lớp lỗi "đóng băng
thiếu module" chỉ lộ ở đây, không ở suite.

## Vỏ premium-blur + bốn chỉnh sửa của chủ (2026-09-02)

1. Bỏ nhấc 2px khi hover bìa (giữ bóng đậm hơn). 2. Cột đọc 36em → 40em (~80 ký tự). 3. Cột đọc
bật `select-text`; guard click-khi-đang-chọn để kéo-chọn không nhảy giọng. 4. Header/footer thành
lớp phủ gradient-blur theo guideline DOL (`plugin-shell.md` §6 tier 3 · recipe
`gradient-blur-shell.md` verbatim: 8 div, 128→0, dải 12,5%; tint token sau stack). Bố cục App đổi:
root `relative h-screen`, `main` phủ toàn bộ, bar `absolute` z-20; inset đặt tên `--shell-top-h` 72 /
`--shell-bottom-h` 56 hoặc 0 (footer ẩn) — Reader/Library cuộn dưới bar và đệm nội dung, các màn
khác `shell-inset`. Đo trong preview 1060×720: scroller 0→720, 2 stack × 8 lớp (128/64/32…), điểm
trong vùng ramp trả về `<p>`/`<img>` (click xuyên), cột 600px, userSelect text. Reader scroll-spy +
viên nổi tính theo inset. HIG §3.4/§3.9/§3.11/§6.
Chủ chỉnh ngay trên preview: (a) viên "Về chỗ đang đọc" căn tâm CỘT chứ không phải cột+mục lục →
bọc vùng cuộn cột trong hộp `relative`, viên neo vào đó (đo: tâm viên 644 = tâm cột, tâm cả vùng
530); (b) blur đừng tràn — ramp 40px che tiêu đề thư viện và mép bìa → `--shell-ramp: 0`, dải nằm
trong bar, header pb-6 / footer pt-4 cho dải tan; inset đo bằng ResizeObserver (advisor: footer có
thể cao lên khi dòng lỗi dài). Advisor bắt lỗi thật: double-click chọn từ làm giọng nhảy (click đầu
tới khi caret còn gập) → click đơn hoãn 220 ms, `onDoubleClick` huỷ; ảnh `draggable={false}` để kéo
qua hình không thành kéo ảnh.

## Lật trang kiểu Apple Books (2026-09-02, chủ chọn hướng + gật 4 đề xuất)

Meta-trigger UI/Code → REFINE+EXECUTE (Continue — General). Quyết định: giữ cuộn làm lựa chọn ·
ranh giới chương = ranh giới trang · 2 trang khi vùng đọc ≥ 1040 px & chữ ≤ 19 · số trang theo
chương + % sách. Kỹ thuật = CSS multi-column (như Apple Books/WebKit): `PageFlow` đo hộp trang
(ResizeObserver), `layoutPages` (thuần, test) chọn 1/2 cột + bề rộng, flow cao cố định
`column-fill:auto` tràn cột sang phải, lật = `translateX`; vị trí đoạn = `getBoundingClientRect`
so với flow → cột → view. Địa chỉ luôn là segment id → engine/giọng/mục lục/tiến độ không đổi.
Reflow giữ `anchor` (đoạn đầu trang). `reason` của mỗi lần hiện trang ("turn" vs app-driven) quyết
định `following`. Mục lục = popover, mặc định đóng. Lỗi gặp khi soát: số trang đổi sau khi ảnh tải
muộn → đếm lại khi `load` + ảnh chương tải ngay ở chế độ trang; popover mở sẵn che trang → đóng
mặc định. UI audit bắt popover viết tay → `Surface`. Test node 25 (4 mới).

## ⓘ vị trí + footer tối giản (2026-09-02, chủ chỉnh trên preview)

Dòng "Trang 3/3 · Chương 3 · 11%" dưới trang → tooltip ⓘ cạnh tên sách (`PageFlow` báo page/pages
qua `onPageShown`, `Reader.onPageInfo` → App; cuộn chỉ có chương + %). Footer: cụm Chất lượng/Giọng/
Tốc độ bên phải → một chip ghost ở giữa "Thu Hà · 1,25×" mở `SettingsPanel` (Giọng · Tốc độ ·
Chất lượng = `ModelChoices`, tách từ ModelPanel; Esc đóng trừ khi đang tải); transport đứng giữa khi
đọc, trạng thái/lỗi bên phải. Advisor (vòng trước): phím trên nút đang focus không lật thêm; `reason`
báo qua ref + reset "idle" để giọng sang trang không bật nhầm viên "Về chỗ đang đọc".
Chủ chốt thêm: mục lục dạng panel nổi "quá tối ưu" → chế độ cuộn cũng dùng panel (dưới header, đóng
mặc định, bấm chương → nhảy + đóng); bỏ cột mục lục cố định. Soát preview: cuộn + trang đều đạt.
Mũi tên lật → `EdgeZone`: dải rộng bằng lề trống trừ 8 px lề âm của đoạn (≥ 32 px), không lấn chữ (chủ:
"cẩn thận quá lố width"; đo: mép dải = mép hộp chữ). Chủ chỉnh thêm: chọn ngôn ngữ chỉ ở trang chủ;
`::selection` = brand 24% tint thay vì đỏ đặc chữ trắng.
Nút sáng/tối trên toolbar (`useAppearance` = lựa chọn đè lên OS, `resolveTheme`/`nextTheme` thuần + 3 test).
Footer rảnh: CTA + chip cùng nhóm ở giữa ("cùng loại đi chung"); CTA = "Đọc tiếp · <chương>" / "Đọc
từ đầu" (Reader báo `resumeChapterTitle` từ đoạn đánh dấu); hint trái "Nhấn vào đoạn văn để đọc từ đó".
Tooltip ⓘ một dòng + `Surface edge="strong"` (prop mới của kit; viền đậm hơn theo chủ). Footer cao bằng
header: 24 + 36 + 16 = 76 px (padding lớn ở mép trong, như header).
Phân cấp tính năng (chủ 02/09): rãnh AppTabs = 2 tab chính có icon (Thư viện · Dán nội dung); Quét đọc ·
Chuyển ghi chú = cụm ghost phụ bên phải (icon + nhãn, aria-pressed), vạch tách; 3 icon mới. Footer:
lưới 3 cột `min-h-[76px]` thay cho cụm absolute (footer bị ép 40 px, thành phần sát mép dưới — chủ bắt).

## Đồng bộ từ Apple Books (2026-09-02, chủ: tính năng phụ, "tinh gọn, nhẹ", + "sync tất cả nhanh")

Tận dụng `integrations/apple_books.py` sẵn có (đọc BKLibrary/AEAnnotation qua bản sao). Mới:
`apple_books_sync.py` (nén thư mục tất định · DRM theo CipherReference không-font · `same_title` ·
`match_annotations` theo chữ + CFI phân xử), bảng `annotations` + `apple_books_links` (thêm, không bump
schema), `applebooks.shelf/import/sync_notes` (KHÔNG trong nhóm trả lời giữa chunk), `book.open`
kèm `annotations`; frontend `AppleBooksPanel` (lặp từng cuốn, tiến độ, tóm tắt), `ui/highlight.ts`
(+4 test), `<mark>` token. Advisor định hình: nén tất định + bảng link (nhập lại không trùng), sandbox
`Books` phải là thư mục thật (symlink từng trỏ vào thư mục thật của chủ), từng cuốn một request (timeout
30 s). Cổng dữ liệu thật trong sandbox: 7 cuốn đúng trạng thái, nhập 0,2–0,3 s, nhập lần hai
`was_existing`, highlight thật 1/1. Lỗi gặp: `ZANNOTATIONSTYLE` làm 50 test fixture cũ vỡ (INSERT theo
vị trí) → KHÔNG đọc cột màu nữa (ba test cũ canh `_rows` = một truy vấn/một bản sao DB, đúng lời hứa
PRIVACY), khôi phục fixture, `style` = 0; `useMemo` đặt sau `return null` → màn
trắng → chuyển lên trước.

## Đường về chỗ đang đọc + đệm khung trang (2026-09-02, chủ)

`origin` (book/paste/external) ghi lúc bắt đầu đọc ở 5 điểm (sách, dán, chọn-trong-sách, phím tắt,
phát lại lịch sử); `atOrigin` so với tab/sách đang mở; ô trái footer hiện "Đang đọc: …" + "Quay lại"
khi đang phát mà không ở nguồn. Khung trang `px-2`, rộng view+16 để lề âm hover không bị cắt (dải lật
vẫn dừng đúng mép khung).
Sheet Apple Books làm lại theo hình thái sheet macOS (chủ: "phân cấp và layout"): header gọn, nhóm
Nhập được/Đã có/Không nhập được (`GroupedSection`+`GroupedRow`, glyph trạng thái, chip số ghi chú),
hành động chính "Đồng bộ N cuốn" + tóm tắt/tiến độ ở footer sheet. Icon mới: Check, Lock.
Chủ chỉnh tiếp: modal tròn hơn → `Surface radius="sheet"` 24 px (bậc mới, card giữ 16); bỏ chia vùng →
một danh sách phẳng tự xếp ưu tiên (`ui/shelfFilter.ts`, 3 test) + ô tìm không dấu hiểu từ trạng thái,
hiện khi > 6 cuốn; kit thêm `Input` một dòng.
Chủ: "thử layout listing khác" → hàng kiểu thư viện: `ListRow` + `MiniCover` 32×48 (bìa thật cho cuốn đã
có qua `ui/useCover.ts` dùng chung với kệ; ô xám + glyph khi chưa nhập; khoá + mờ khi chặn), hairline
thay khối xám, dữ kiện gộp một dòng.
Chủ: lớp nổi phải viền đậm → SettingsPanel + mục lục nổi `edge="strong"` (luật chung HIG); select giọng
chỉ tên, mô tả xuống dòng phụ hàng "Giọng".
Chủ: ô 2 cột như Apple Books (không màu) → `BookTile` + `MiniCover size="md"`; "Đọc phần đã chọn" xuống
footer (Reader `onSelection` → App; primary khi rảnh, nhỏ cạnh transport khi đọc; viên trong trang bỏ).
Chủ: ô = card trắng viền xám, hover viền đậm + bóng 3; hành động thành icon phải; "Nhập" có tuỳ chọn
phụ (mặc định chỉ nhập sách) → kit `MenuButton` (Esc/click ngoài đóng), engine `sync_notes {mode:
both|highlights|notes}` + test; footer primary mặc định chỉ nhập + chevron tuỳ chọn. Sidecar dựng lại.
Chủ: item dropdown bo tròn hơn → 12 (đồng tâm với khung 16 + đệm 4), đệm dọc 6→8, cao 36.
Chủ (03/09): cần nơi quản lý giọng (nghe thử + switch vào danh sách) và đổi giọng khi đang đọc mà vẫn
đọc tiếp. Đảo lại quyết định "giọng đọc-một-lần" cũ: `switchVoice` phát lại chính lượt đang đọc từ đoạn
hiện tại bằng giọng mới. Engine: `read` đánh địa chỉ `part-N` + nhận `segment_id` (3 test) để văn bản
dán/quét cũng nối tiếp được, không phải đọc lại từ đầu. Kit thêm `Switch`; `voiceShortlist.ts` (6 test)
giữ luật danh sách; `VoicesPanel` là nơi chọn, `MenuButton` ở transport là nơi đổi. Tốc độ VẪN đọc-một-lần.
Chủ: danh sách giọng bỏ nền xám + hộp, chuyển sang danh sách phẳng trên giấy, phân tầng bằng dot divider
(chấm 2px/nhịp 8px theo DS, không phải border-dotted) + đệm trên dưới, không đệm trái phải. Kit: DotDivider,
DottedList. Ba test engine đỏ vì `read` nay phát `position` trước `chunk` - sửa kỳ vọng (helper _first_audio),
không sửa hành vi; suite 747 OK.
Chủ (03/09, một loạt chỉnh khi nhìn màn hình): chấm nhạt hơn -> token --color-dot theo nền (sáng edge, tối
edge-strong, vì edge ở nền tối biến mất); gộp kiểu danh sách chấm vào chính GroupedSection nên cả product
đi theo (bỏ DottedList, kit còn MỘT kiểu list); hàng thoáng hơn py-3.5/py-4; bỏ px-3 của tiêu đề mục;
select giọng chỉ hiện giọng đã bật; đệm lớp nổi hai tầng 24 (panel) / 8 (menu hàng); nút quản lý có icon
loa; chip cài đặt đóng sheet giọng.
Chủ (03/09): xem được ghi chú + có nơi quản lý danh sách highlight/note. Dựng NotesPanel (lề phải, đối
xứng mục lục) + annotationsList.ts gom theo chương (5 test) + InlineIconButton cho icon ghi chú trong
đoạn; PageInfo mang thêm số annotation để header ẩn nút khi sách không có gì. Dữ liệu đã có sẵn ở
book.open.annotations nên KHÔNG cần đụng engine. CHƯA làm: xoá/sửa (giao thức chỉ có replace_annotations
ghi đè cả cụm, và sync_notes gọi chính nó -> cái đã xoá quay lại sau lần đồng bộ sau; cần chốt sản phẩm).
Chủ: thanh cuộn NotesPanel lòi ra ngoài panel va cuon ca header -> panel thanh cot flex overflow-hidden
(header shrink-0 dung yen, chi body cuon); scrollbar doi sang cong thuc DS scrollbar-width thin +
scrollbar-color hover-reveal, GIU khoi ::-webkit-scrollbar lam duong lui vi day la WKWebView (DS bo khoi
do sau khi do tren Chromium). Panel cung doi sang le TRAI cho khop nut mo no.
Chu chot (03/09): "xoa han luon" -> bang bia mo annotations_forgotten + loc trong replace_annotations
(mot cho, moi duong ghi deu tuan) + giao thuc annotations.delete; 2 test moi canh dung cai da xoa KHONG
quay ve sau sync. UI: nut thung rac hien khi hover, xac nhan trong hang. Kem 2 sua nho: tooltip position
fixed theo le cua so (icon troi theo ten sach nen neo ben nao cung co luc tran), va dot divider nhan
--dot-inset de ke thang hang voi noi dung o list co outdent.
Chu: xem nhanh note ngay tren UI -> bong bong hover tren icon ghi chu, toa do tinh tu getBoundingClientRect
roi ve bang position:fixed o lop ngoai (neo trong doan van se bi cot CSS + translateX + overflow-hidden cua
mode lat trang cat mat), kep ngang va lat len tren khi icon nam thap. Bam van mo bang nhu cu.
Chu: bong bong note doi sang w-max + tran tinh tu cho trong that ben phai icon (chan tren 28rem); duoi
260px cho trong thi thoi bam icon, canh theo le phai cua so. Do: 129/206/293 o 1060, 448 o 1400.
Chu (03/09): BO co che tu dong build/cai sau moi sua - chi dong goi khi co update lon hoac khi duoc yeu
cau; van chay typecheck + unit test + UI_AUDIT + preview moi lan. Kem: bo px-5 ep them o 2 nut CTA (ve
px-4 cua kit); IconButton tu ve tooltip co kieu tu title (portal + do roi kep), 4 nhan duoc rut gon ve
dang hanh dong.
Chu: mac dinh bat san 5 giong (Adam, Truc Ly, Pham Tuyen, Ngoc Linh, Thai Son - mot dai, khong phai xep
hang) thay vi tat het. initialShortlist phan biet "chua tung chon" (mo) voi "da chon la rong" (ton trong),
loc theo catalogue cua ban dung. 3 test moi.
Chu: dong bo khoang cach nut->popover (--layer-gap = 8, LAYER_GAP=8 cho lop dinh vi bang do) va chan chieu
cao (utility layer-capped). Bay: --layer-max-h khai o :root bi thay var() ngay tai :root nen nuong cung
inset khoi tao 72/0, khong thay 76 do duoc -> phai viet thanh utility de calc giai o phan tu dung.
SettingsPanel tach header dung yen / than cuon.
Chu: lop noi co tieu de len bac sheet 24 (SettingsPanel + NotesPanel, khop voi 2 sheet san co); menu gom
cac hang giu 16 de hang 12 con dong tam voi khung 16 + dem 4.

