# Kế hoạch nâng cấp ReadEase — quý 4/2026

> [!NOTE]
> **Kế hoạch, chưa phải hiện trạng.** Lập ngày 15/10/2026 sau khi chủ duyệt "lên kế hoạch nâng cấp tất cả" bảy hướng
> A–G. Mỗi bước có cổng kiểm (lệnh/đo được). Khi một bước xong, ghi vào `docs/product/` (ux · logic · decisions ·
> releases) — file này chỉ giữ thứ tự và trạng thái.

## 0. Nền tảng của kế hoạch

**Lõi hiện có** (đọc từ `docs/product/`, 15/10): đọc theo cấu trúc (ngắt nghỉ, tiêu đề, chuông chương, Markdown, chú
thích, hình EPUB) · từ điển phát âm riêng · ba nguồn giọng (VieNeu Việt và Kokoro Anh trên máy; OpenAI/ElevenLabs
bằng khoá riêng, có báo giá và trần ngân sách) · đầu vào EPUB/PDF, Apple Books, dán, quét chọn ở mọi app · đầu ra
nghe trực tiếp có nhớ chỗ, **xuất WAV + SRT cho Dán nội dung** (−14 LUFS, ghi chú giọng AI), nghe lại/đọc lại từng câu.

**Điều đã kiểm trên máy này (macOS 27.0, 15/10):**
- Apple Vision OCR có `vi-VT` (`VNRecognizeTextRequest.supportedRecognitionLanguages`, mức accurate) → hướng G khả thi
  không cần thư viện ngoài.
- Apple Translation `en → vi`: `LanguageAvailability().status` = `installed` → hướng D khả thi trên máy.
- SDK `vieneu` 3.6.3 có `add_voice(name, ref_audio)` / `encode_reference` (nhân bản giọng ONNX, trên CPU) và app đã
  ship sẵn codec encode (`CODEC_FILES`) → hướng E không cần model mới.
- Câu ngắn (≤3 từ) đọc đúng chữ 61 % ở temperature 0,8 → 74 % ở 0,1 (Whisper large-v3-turbo chấm, 180 bản/mức) —
  `docs/local-voice-model-survey-2026-10.md` §6.

**Luật chạy kế hoạch**
- Mỗi giai đoạn **phát hành được riêng**; không giữ nhánh dài.
- Giữ nguyên các bất biến: không telemetry, không tài khoản, văn bản dán không vào cache, khoá API không bao giờ đi ra,
  giọng trả phí luôn báo giá trước.
- Một phiên khác đang làm phần xuất âm thanh (commit 14/10). **Giai đoạn B nối tiếp đường xuất đó — đọc
  `logic/reading.md` RE-PLAY-010…016 và `git log` trước khi sửa**, không viết đường xuất thứ hai.

**Chờ chủ quyết (không tự làm):** thêm phụ thuộc mới · gỡ non-goal (xuất sách, OCR) · chính sách nhân bản giọng ·
đổi giọng mặc định · mọi lần "phát hành".

## 1. Thứ tự và kích cỡ

| Giai đoạn | Hướng | Kích cỡ | Phụ thuộc | Cổng chủ |
|---|---|---|---|---|
| **P0** | Kênh góp ý (không telemetry) | S | — | duyệt chữ và nơi nhận |
| **P1** | A · Giọng nghe đúng hơn | S–M | — | nghe mù; giọng mặc định |
| **P2** | B · Xuất chương / cả sách thành M4B | M | đường xuất 14/10 | gỡ non-goal "xuất sách"; phụ thuộc mới nếu có |
| **P3** | C · Đọc bài báo + hàng đợi + menu Dịch vụ | M | — | phụ thuộc trích bài (nếu dùng thư viện) |
| **P4** | D · Đọc bản dịch / song ngữ | L | Swift helper (dùng chung với G) | — |
| **P5** | G · OCR PDF scan | M | Swift helper | gỡ non-goal OCR |
| **P6** | E · Giọng của riêng mình | M | quyền micro | **chính sách đồng ý** trước khi code |
| **P7** | F · Tô sáng từng chữ | M | mốc thời gian theo câu (đã có) | — |

S ≈ 1–2 ngày, M ≈ 3–6 ngày, L ≈ 1–2 tuần làm việc của một phiên, gồm cả kiểm thử. G đứng trước E vì dùng lại Swift
helper vừa dựng cho D.

## P0 · Kênh góp ý

1. Mục menu **ReadEase › Gửi góp ý…** mở một form trong app: loại (lỗi đọc / tính năng / khác), nội dung, tuỳ chọn
   đính kèm phiên bản app + giọng đang dùng (không đính kèm văn bản đang đọc). Gửi = mở trang GitHub Issues mới đã điền
   sẵn (người dùng tự bấm gửi) — không có máy chủ ReadEase.
   → verify: test UI tạo đúng URL issue đã mã hoá; không chuỗi nào của tài liệu/văn bản dán đi vào URL
   (test đọc URL); `PRIVACY.md` thêm một đoạn.
2. Câu hỏi khảo sát ngắn gửi nhóm bạn dùng thử: chọn giữa B, C, D cái nào cần nhất.
   → verify: kết quả ghi vào `docs/product/decisions.md`, dùng để xếp lại P2–P4 nếu khác thứ tự trên.

## P1 · A — Giọng nghe đúng hơn

1. **Bài nghe mù câu ngắn 0,8 vs 0,3** (trang nghe như bài A/B 13/10, 10 câu × 2 giọng × 2 mức, xáo nhãn).
   → verify: chủ chấm xong; 0,3 không bị chê "đều giọng" (điểm trung bình 0,3 ≥ 0,8).
2. **Temperature riêng cho câu ≤3 từ**: hằng `SHORT_UTTERANCE_TEMPERATURE` cạnh `SHORT_UTTERANCE_WORDS` trong
   `src/vieneu_reader/speech/vieneu.py`, chỉ áp vào nhánh `sdk.infer`.
   → verify: test đơn vị (nhánh ngắn gọi `infer` với temperature mới, nhánh dài giữ cài đặt người dùng); khoá cache
   audio đổi (thêm temperature vào khoá) để không phát lại bản cũ; `./scripts/verify.sh` xanh.
3. **Chọn bản tốt nhất cho câu ngắn**: sau `infer`, nếu bản chạm trần khung hoặc số cụm âm > số tiếng
   (`babble_suspect` của SDK) thì sinh thêm tối đa 1 bản và giữ bản không nghi ngờ.
   → verify: đo lại bằng bộ đo 10 câu × 10 lần × 2 giọng (Whisper) — mục tiêu **≥ 80 % đúng chữ**, Adam **≥ 75 %**,
   "Whisper bịa câu" = 0; độ trễ âm đầu câu ngắn tăng ≤ 0,3 s (đo `gen_s`).
   **15/10: đã có sẵn trong SDK** (`babble_retries` = 2 trong `infer`, giữ bản không nghi) — số đo §6/§7 đã gồm nó.
   Lỗi còn lại chủ yếu là sai thanh, bộ dò cụm âm không thấy được. Giọng mặc định mới (Đức Trí) đạt 96 %.
4. **Bộ đo câu ngắn thành công cụ của repo**: `scripts/measure-short-utterances.py` (render) — phần chấm Whisper chạy
   trong môi trường riêng ngoài repo, không vào bundle. **Phụ thuộc dev mới (mlx-whisper) → hỏi chủ trước.**
   → verify: một lệnh in bảng như §6 tài liệu khảo sát; ghi hướng dẫn chạy trong `docs/`.
5. **Giọng mặc định**: chạy bộ đo trên cả 23 giọng; đề xuất 2–3 giọng tốt nhất (đúng chữ câu ngắn + nghe thử đoạn dài).
   → verify: bảng xếp hạng; **chủ chọn**; tiến độ cũ vẫn giữ giọng đã lưu (`DEFAULT_VOICE_ID` chỉ áp người mới).
6. **Chuẩn hoá văn bản**: bộ test số (12,5 · 3,2 tỷ · 2025 · số La Mã chương), ngày tháng, đơn vị, viết tắt hay gặp
   (TP.HCM, v.v., GS., ThS.); sửa ở tầng chuẩn hoá trước SDK.
   → verify: test mới trong `tests/domain/`; Whisper đọc lại đúng ≥ 90 % mẫu.
   **15/10:** dò 34 dạng qua bộ chuẩn hoá SDK — số, ngày, giờ, đơn vị, %, La Mã, TP.HCM, GS./PGS.TS., UBND… đã đúng.
   Đã thêm ThS./TP./tr./Q1/2025 (RE-PLAY-018), OK (RE-PLAY-019), Nxb./Sđd/Tlđd/"H.:" (RE-PLAY-018). Chưa nghe lại
   bằng Whisper các dạng mới (chúng thành chữ thường mà SDK đọc như mọi câu).
7. **Gói phát âm dựng sẵn** (tuỳ chọn nhập): thuật ngữ công nghệ, tên riêng phổ biến — nhập vào từ điển phát âm hiện có,
   người dùng xoá được từng dòng.
   → verify: nhập không vượt trần 300 dòng; trùng từ thì hỏi giữ bản nào.
   **Kết quả 15/10: bỏ.** Đo 20 từ: nguyên văn 54/60, viết kiểu Việt 49/60 — gói làm tệ hơn. Chỉ sửa "OK" →
   "ô kê" (RE-PLAY-019). Khảo sát §8, `decisions.md` 15/10.
8. Phát hành 0.1.22 (chờ "phát hành").

## P2 · B — Xuất chương / cả sách thành sách nói M4B

1. **Spike định dạng (0,5 ngày)**: ghi M4B có mốc chương + ảnh bìa **không thêm phụ thuộc** — thử AVFoundation
   (`AVAssetWriter` + nhóm metadata chương) qua Swift helper, so với `afconvert` + ghi atom chương bằng tay.
   → verify: file mở trong Apple Books và QuickTime trên Mac, danh sách chương đúng tên/mốc; nếu cả hai hỏng → đề xuất
   phụ thuộc (ví dụ ffmpeg) và **hỏi chủ**.
   **15/10: đạt (trừ mở tay trong Books).** `afconvert` + track chương QuickTime tự ghi bằng Python
   (`src/vieneu_reader/headless/m4b.py`), AVFoundation đọc lại đủ chương/tiêu đề tiếng Việt; không thêm phụ thuộc.
   `decisions.md` 15/10.
2. **Engine `export.book`** (nối đường xuất 14/10): phạm vi = một chương / từ chương X đến Y / cả sách; mỗi chương là
   một mốc; dùng chung ngắt nghỉ, chuông, phát âm, −14 LUFS, metadata giọng AI; ghi dần ra đĩa (không giữ cả sách trong
   RAM); huỷ được; xuất xong không để lại gì ngoài file.
   → verify: test engine (mốc chương khớp ranh giới chương, tổng thời lượng = tổng câu + nghỉ, huỷ giữa chừng không để
   file dở); bộ nhớ đỉnh khi xuất sách 300 trang < +300 MB so với lúc đọc.
   **15/10: engine xong** (`export.book`: `from_chapter` + `chapters`, mốc tính theo câu như phụ đề, AAC chép dần 1 MB
   một lần). Chỉ giọng trên máy; giọng trả phí bị từ chối có tên (`paid_voice_export`) tới bước 3. Chưa đo bộ nhớ đỉnh
   trên sách 300 trang thật. Đợt tiếp nối: đã nối ảnh bìa JPEG/PNG nếu có; có phép đo fixture dài trong
   `scripts/measure-audiobook-export.py`, chưa đo với model thật trên Mac 8 GB.
3. **Ước lượng trước khi bấm**: thời lượng nghe dự kiến, dung lượng file, thời gian xuất trên máy này; **giọng trả phí
   hiện giá cả cuốn** và chịu trần ngân sách như lúc đọc.
   → verify: test cost guard với cả sách (vượt ngân sách → dừng trước khi gửi ký tự); sai số ước lượng thời lượng ≤ 10 %.
4. **UI**: trong Trình đọc, menu sách "Xuất sách nói…" (chọn phạm vi, giọng, định dạng M4B/WAV), thanh tiến độ, Huỷ,
   "Mở trong Finder". Xuất chạy nền, đọc sách khác vẫn được hay phải chờ — theo luật hiện tại "mọi nút đọc chờ khi đang
   xuất" (giữ nguyên trừ khi chủ đổi).
   → verify: kiểm thử UI (pnpm build), render audit trạng thái xuất; ảnh chụp sáng/tối.
   **15/10, tiếp nối:** UI M4B có khoảng chương, chọn nơi lưu và trạng thái toàn app (tạo giọng / chuẩn hoá / mã hoá,
   thời gian đã chạy, Huỷ, Finder). Điều hướng tiếp tục, phát âm thanh chờ; đóng cửa sổ thu nhỏ, Thoát hỏi huỷ trước.
   Chưa có lựa chọn WAV cho sách, báo giá giọng trả phí hay ước lượng trước khi xuất; chưa smoke native cửa sổ/Dock.
5. **Xuất phần quét chọn** (dùng chung engine với Dán nội dung).
   → verify: test; non-goal trong `goal.md` cập nhật theo quyết định của chủ.
6. Cập nhật `README`, `PRIVACY.md` (mục Exported audio), landing page (một khối "Mang sách đi nghe"). Phát hành.

## P3 · C — Đọc mọi thứ đang xem

1. **Đọc bài báo từ link**: ô dán nhận cả URL → app tải trang trên chính máy người dùng, trích nội dung chính, đưa vào
   luồng Dán nội dung (không lưu, không cache — như văn bản dán). Ưu tiên tự viết bộ trích đơn giản (thẻ `article`/mật
   độ chữ); nếu không đủ tốt → đề xuất thư viện (ví dụ trafilatura) và **hỏi chủ**.
   → verify: bộ 20 trang tin tiếng Việt và Anh lưu sẵn làm test (không gọi mạng trong CI): trích đúng tiêu đề + thân bài
   ≥ 18/20; trang lỗi/paywall báo lý do.
2. **Menu Dịch vụ macOS "Đọc bằng ReadEase"** (chuột phải vào chữ ở mọi app): khai báo `NSServices`, chuyển chữ vào
   luồng Quét đọc hiện có.
   → verify: thử trong Safari, Notes, Preview trên màn phụ (luật thử nghiệm hiển thị); không cần quyền Trợ năng cho
   đường này.
3. **Hàng đợi nghe**: thêm nhiều bài/đoạn dán vào hàng, đọc nối tiếp, kéo đổi thứ tự, bỏ qua. Hàng đợi chỉ trong bộ
   nhớ phiên (giữ bất biến "văn bản dán không được lưu"); tuỳ chọn lưu hàng đợi là quyết định riêng của chủ.
   → verify: test coordinator (hết bài này sang bài kia, Stop dừng cả hàng, tiến độ sách không đổi).
4. Phát hành.

## P4 · D — Nghe sách ngoại văn bằng tiếng Việt

1. **Swift helper dùng chung** (cho D và G): một tiến trình nhỏ đi kèm app, nói JSON qua stdin/stdout như engine Python;
   ký và notarize cùng bundle.
   → verify: helper chạy được từ bản đã notarize trên máy "người lạ" (giữ quarantine, như quy trình sidecar hiện tại).
2. **Spike Translation**: dịch theo lô từng đoạn bằng `TranslationSession` từ helper không có cửa sổ — kiểm API có
   chạy ngoài SwiftUI trên macOS 15 không; nếu chỉ chạy trong view thì gọi qua cửa sổ ẩn của app.
   → verify: 1 chương sách tiếng Anh dịch xong, đo thời gian/đoạn, chất lượng nghe thử; báo lỗi rõ khi gói ngôn ngữ chưa
   tải (`LanguageAvailability` ≠ installed → mời tải).
3. **"Đọc bản dịch"** cho sách tiếng Anh: dịch trước vài đoạn chạy trước tai, đọc bằng VieNeu; trang hiện bản gốc, đoạn
   đang đọc hiện bản dịch bên cạnh. Bản dịch lưu theo sách (để đọc lại không phải dịch lại), xoá được.
   → verify: tiến độ theo đoạn gốc (resume đúng chỗ); chuyển qua lại gốc/dịch không mất chỗ; test lưu/xoá bản dịch.
4. **Song ngữ cho người học**: từng câu đọc tiếng Anh (Kokoro) rồi tiếng Việt (VieNeu), tuỳ chọn tốc độ riêng.
   → verify: thứ tự câu đúng, nghỉ giữa hai thứ tiếng; tắt được.
5. Phát hành.

## P5 · G — OCR PDF scan

1. **Gỡ non-goal** — chủ duyệt; cập nhật `goal.md`, `RE-LIB-005/010`.
2. **OCR qua Swift helper** (Vision, `recognitionLanguages = ["vi-VT","en-US"]`, mức accurate), từng trang, có tiến độ
   và Huỷ; giữ bố cục đoạn thô (khối chữ → đoạn).
   → verify: bộ 5 PDF scan tiếng Việt mẫu: tỉ lệ ký tự đúng ≥ 95 % so với bản gõ tay; PDF 300 trang không làm treo
   giao diện; file gốc không đổi (RE-LIB-002).
3. Phát hành.

## P6 · E — Giọng của riêng mình

1. **Chính sách trước code (chủ quyết)**: chỉ nhân bản giọng của chính người dùng; câu cam kết đồng ý trước khi ghi;
   giọng nhân bản chỉ dùng trong app trên máy đó; mọi file xuất bằng giọng nhân bản ghi rõ trong metadata; xoá được
   hoàn toàn. Ghi vào `docs/product/decisions.md`.
   → verify: quyết định có ngày + lời chủ.
2. **Ghi mẫu giọng**: màn hình đọc một đoạn văn mẫu 10–20 s (quyền micro — xin khi bấm ghi, không lúc mở app), kiểm
   chất lượng (ồn, quá nhỏ, quá ngắn) trước khi nhận.
   → verify: test UI các trạng thái; từ chối mẫu kém có lý do.
3. **Đăng ký giọng** bằng `add_voice` của SDK; lưu embedding + mã tham chiếu trong thư mục app (không lưu file ghi âm
   gốc, trừ khi người dùng chọn giữ); giọng hiện trong danh sách với nhãn "Giọng của bạn".
   → verify: đọc thử bằng giọng mới; xoá giọng → file liên quan biến mất (test); dùng được khi offline.
4. Phát hành (sau khi chủ nghe thử chất lượng).

## P7 · F — Tô sáng từng chữ

1. **Mốc thời gian theo chữ**: chia mốc câu (đã có từ phụ đề) theo âm tiết; tinh chỉnh bằng năng lượng âm (ranh giới
   cụm âm).
   → verify: trên 50 câu, lệch trung bình giữa chữ tô sáng và chữ nghe ≤ 150 ms (đo bằng Whisper có mốc thời gian theo
   từ, chạy ngoài repo).
2. **UI**: chế độ "Tô sáng từng chữ" (tắt mặc định), chữ đang đọc nổi bật trong đoạn; tôn trọng Giảm chuyển động.
   → verify: render audit sáng/tối; không giật khi đọc nhanh 1,5×.
3. Phát hành.

## Rủi ro chung

| Rủi ro | Cách giữ |
|---|---|
| Đường xuất đang được phiên khác sửa | B bắt đầu bằng đọc `git log` + logic RE-PLAY-010…016; sửa nối tiếp, không nhân đôi |
| Swift helper làm phức tạp ký/notarize | dựng một lần ở P4 bước 1, kiểm bằng quy trình "máy người lạ" đã có |
| Đo bằng Whisper sai ở câu cực ngắn | luôn kèm bộ đối chứng (giọng macOS) và bài nghe mù cho quyết định cuối |
| Bộ nhớ trên máy 8 GB khi xuất sách / dịch | đo bộ nhớ đỉnh ở mỗi cổng; giữ cơ chế nhả model sau 5 phút |
| Nhân bản giọng bị lạm dụng | chính sách P6 bước 1 là điều kiện tiên quyết |
