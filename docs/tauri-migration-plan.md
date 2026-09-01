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
