# Giọng tiếng Anh cục bộ cho ReadEase — khảo sát và đo thật (15/09/2026)

> [!NOTE]
> Nối tiếp `english-reading-2026-09.md` §3. Phần **đo** chạy trên máy chủ (Apple M4 Max, macOS 26,
> Python 3.13, không có espeak-ng), trong một venv riêng ngoài repo; số trên máy yếu hơn sẽ khác.
> Mọi sự thật lấy từ web đều gắn `[fetched 2026-09-15]`; số đo tự chạy gắn `[đo]`.

## 0. Kết luận ngắn

**Chọn Kokoro-82M (fp32 ONNX) làm engine tiếng Anh cục bộ**, với G2P là từ điển của `misaki` cộng
một mạng phụ nhỏ cho từ lạ. Không cần espeak-ng, không cần torch. Giấy phép sạch (Apache-2.0 + MIT),
chạy nhanh hơn thời gian thực gần 3 lần, giọng tự nhiên nhất trong nhóm chạy được trên CPU.
Supertonic 3 là phương án dự phòng nếu chủ nghe thấy Kokoro không hợp.

Bốn điều còn phải chốt nằm ở §5.

## 1. Ứng viên còn lại sau khi loại theo giấy phép và dung lượng

| Ứng viên | Model | Runtime / G2P | Cỡ tải | Kết luận |
|---|---|---|---|---|
| **Kokoro-82M v1.0** | Apache-2.0 `[fetched]` | ONNX có sẵn; G2P `misaki` Apache-2.0 + spaCy MIT; espeak chỉ là fallback **tuỳ chọn** `[fetched]` | fp32 326 MB · int8 92 MB · q8f16 86 MB `[fetched]` | **Chọn** |
| Supertonic 3 (99M) | OpenRAIL-M: dùng thương mại được, không copyleft, kèm danh sách hạn chế sử dụng `[fetched]` | ONNX; **không cần G2P**, đọc thẳng từ chữ; 31 ngôn ngữ kể cả tiếng Việt `[fetched]` | 404 MB `[đo]` | Dự phòng: nhanh hơn, giọng phẳng hơn |
| KittenTTS (15–80M) | Apache-2.0 `[fetched]` | requirements ghi `phonemizer` + `espeakng_loader` → espeak-ng **GPL** `[fetched]` | 25–80 MB | Loại (GPL) |
| Piper | piper1-gpl GPL-3.0, espeak-ng GPL (khảo sát 07/09) | | | Loại (GPL) |

Không có bản Kokoro mới hơn v1.0 (01/2025) tính tới hôm nay `[fetched]`.

## 2. Đo trên máy chủ `[đo]`

Cùng một đoạn tiếng Anh 112 từ, 7 câu, sinh offline, không espeak-ng, không torch.

| Cấu hình | Nạp | RTF (thời gian sinh / thời lượng) | Câu đầu (dài) |
|---|---|---|---|
| Kokoro fp32, 4 luồng | 0,4 s | **0,33** | 1,2 s |
| Kokoro fp32, 1 luồng | 0,4 s | 0,75 | 3,1 s |
| Kokoro int8 (`model_quantized`), 4 luồng | 0,4 s | 0,55 | 2,3 s |
| Kokoro q8f16, 1 luồng | 6,3 s | 1,19 | 4,2 s |
| Supertonic 3, 8 bước, 4 luồng | — | 0,26–0,33 | — |
| Supertonic 3, 5 bước, 4 luồng | — | 0,18–0,22 | — |

Đọc: fp32 Kokoro là cấu hình nên ship (nhanh nhất, chất lượng gốc); int8 tiết kiệm 234 MB tải về nhưng
chậm hơn; q8f16 không hợp CPU. VieNeu fp32 của app hiện ở RTF ~0,37 — Kokoro fp32 cùng bậc.

**Từ lạ (out-of-lexicon)** trên cuốn tiếng Anh thật trong thư viện (Atomic Design, 600 khối đầu,
13.235 từ): **1,2%** — chủ yếu tên riêng (Boulton), từ kỹ thuật (webpage, Node.js), ký tự lẻ. Đoạn
mẫu 112 từ: 0%. Vậy fallback là bắt buộc cho ~1 từ mỗi 100, và đó đúng là những từ không được phép
nuốt (tên người, thuật ngữ).

Bên thứ ba đo độc lập (4 nhân EPYC): Kokoro RTF 0,47–0,51, "prosody tự nhiên, không nghe như TTS";
Supertonic 3 5 bước RTF 0,31, "rõ, dùng được, nhưng phẳng hơn"; 2 bước "robotic" `[fetched]`.

Mẫu nghe: 6 file WAV đã gửi chủ (3 giọng Kokoro, 3 giọng Supertonic 8 bước), cùng đoạn văn.

## 3. Cái bẫy G2P, và lời giải

`misaki[en]` trên PyPI kéo theo `phonemizer-fork`, `espeakng-loader` (espeak-ng GPL), `torch`,
`transformers` `[fetched]`, và bản PyPI đòi Python < 3.13 (app chạy 3.13). Nhưng đó là **extras**,
không phải cách G2P hoạt động:

- Lõi G2P tiếng Anh là **từ điển** (`us_gold.json` + `us_silver.json`, ~15 MB) + spaCy `en_core_web_sm`
  (MIT, 15 MB) để gán từ loại cho từ đa âm. Đã chạy được ở Python 3.13 từ nhánh `main` (0.9.4),
  không có espeak, không có torch `[đo]`.
- Từ lạ: bản `main` của misaki đã đổi fallback mặc định từ espeak sang một mạng BART nhỏ
  (`PeterReid/graphemes_to_phonemes_en_us`, **3 MB**, Apache-2.0) `[fetched]`. Nó cần torch để chạy —
  không chấp nhận được trong bundle — nhưng 3 MB là kích cỡ xuất sang ONNX được, chạy bằng
  onnxruntime đã có sẵn trong app.
- `num2words` (LGPL-2.1) chỉ dùng để đọc số; engine của app đã có `speakable_text` đọc số theo
  ngôn ngữ, nên đưa chữ đã chuẩn hoá vào G2P và không ship num2words — giữ nguyên lời hứa "không
  copyleft trong binary" của `legal/BINARY_DISTRIBUTION.md`.

## 4. Kế hoạch cắm vào app (khi chủ gật)

1. **Engine thứ hai** sau giao diện `SpeechEngine` (VieNeu chỉ là một bản cài của nó): `KokoroSpeechEngine`
   với `voices()`, `stream()`, `cancel()`; tải theo yêu cầu như VieNeu (ghim revision HF, marker sẵn
   sàng, xoá được trong bảng model). Tải về: model fp32 326 MB + 54 file giọng (0,5 MB mỗi giọng) —
   hoặc chỉ tải giọng được chọn.
2. **G2P**: vendor phần tiếng Anh của misaki (Apache-2.0) + spaCy sm; fallback BART xuất ONNX một lần
   lúc phát triển, ship file .onnx 3 MB. Cổng: chạy cuốn Atomic Design không còn từ nào bị nuốt.
3. **Định tuyến**: sách khai `en` → Kokoro; VieNeu vẫn bị cấm đọc tiếng Anh (luật cũ giữ nguyên);
   giọng trả phí vẫn là BYOK.
4. **Giấy phép**: thêm receipt Apache-2.0 (Kokoro, misaki, BART G2P), MIT (spaCy, en_core_web_sm)
   vào payload; audit `--strict` phải xanh; bundle không phình quá +70 MB (spaCy + lexicon), model
   nằm ngoài bundle như VieNeu.
5. **Cổng**: `verify.sh` xanh; đọc offline một chương tiếng Anh từ bản đóng gói; RTF < 0,6 trên
   M1 (cần đo trên máy yếu hơn M4 Max).

## 5. Chủ đã quyết (15/09)

1. Kokoro hay Supertonic — chủ nghe 6 mẫu, **chốt Kokoro** ("kokoro khá tốt nhé").
2. Kèm vào bản phát hành: **có**, dưới dạng tải về theo yêu cầu (không nằm trong app), và
   người dùng **tự chọn mô hình theo ngôn ngữ**.
3. fp32 trước; int8 chưa làm (RTF 0,55 và giọng kém hơn, không đáng 234 MB tiết kiệm).
4. Sách trộn hai thứ tiếng: vẫn chưa có lời giải; cả cuốn mang một ngôn ngữ.
5. **Cùng ngày, sau bản cắm đầu tiên, chủ chốt ba hướng nữa** (nguyên văn rút gọn):
   - "không được bắt buộc user phải tải một model duy nhất nào đó … cho user chọn tải theo yêu cầu"
     → màn đầu tiên không còn ép tải VieNeu: liệt kê cả hai mô hình + khoá API, "Vào thư viện" luôn bấm được.
   - "không cần có cơ chế chặn hay bắt buộc user phải dùng đúng voice. Hãy cho user tự do chọn voice …
     có thêm phần alert ở phần setting chọn voice để gợi ý … nội dung đang là ngôn ngữ gì và đề xuất nên
     dùng model nào" → **bỏ `wrong_language`** ở engine và vỏ (đảo lại luật "không bao giờ đọc tiếng Anh
     bằng VieNeu" của 07/09); bảng giọng đọc hiện câu gợi ý + một nút; chip ở footer mang chấm gợi ý.
   - "chọn trước là họ muốn đọc ở ngôn ngữ nào rồi mới hiển thị các nội dung liên quan … ở ngoài trang chủ
     sẽ có một nút setting để thống kê … đang đọc được ngôn ngữ nào? có các model gì rồi … nhập API"
     → bảng giọng đọc mở bằng bộ chọn Tiếng Việt / Tiếng Anh (đổi tab = đổi sang giọng đã dùng cho tiếng
     đó, nhớ `voice_vi`/`voice_en`, lưu `reading_language`); thêm sheet **Giọng đọc & mô hình** từ nút
     bánh răng trên trang chủ (và từ bảng giọng đọc): mỗi ngôn ngữ một nhóm — dòng "Đọc được / Chưa đọc
     được · bằng gì", các bản mô hình (tải / dùng / xoá), rồi nhóm khoá API.

## 6. Đã cắm (0.1.3) — số đo từ bản đóng gói

- `speech/kokoro.py` — engine thứ hai sau cùng seam `SpeechEngine`; tải từ HF revision
  `1939ad2a…` (model.onnx + tokenizer + 6 gói giọng Mỹ, mỗi file kiểm SHA-256) và từ điển misaki
  từ commit `fba1236…` trên raw.githubusercontent.com (SHA-256 ghim trong code). Marker
  `.kokoro-ready.json` chỉ ghi sau khi mọi file khớp và một câu thử ra tiếng.
- `speech/english/` — port của `misaki/en.py` (Apache-2.0): **giống byte-một** với bản gốc trên
  1.787 đoạn / 40.436 từ sách tiếng Anh thật (fake fallback hai bên); không chữ số nào lọt tới
  model. `numbers.py` thay num2words (LGPL, không ship). `fallback.py` chạy BART
  `PeterReid/graphemes_to_phonemes_en_us` qua onnxruntime (export lúc dev, 3,1 MB trong bundle):
  **301/301** từ ngoài từ điển trùng với torch `generate()` tham lam.
- spaCy 3.8.16 + `en_core_web_sm` 3.8.0 vào bundle: sidecar 223 → **267 MB**. Bản đóng gói tự
  kiểm `--self-test` (tagger + fallback) trong `build-sidecar.sh`.
- Bản đóng gói, M4 Max, câu 12,2 s: lạnh (đọc ngay khi process lên) âm đầu sau **3,7 s** kể từ
  lúc process lên (gồm VieNeu warm, nạp spaCy và session ONNX), đọc xong sau 5,3 s; đã warm nền
  (đọc 8 s sau khi process lên, model đã tải) âm đầu sau **1,56 s** kể từ lệnh đọc, đọc xong sau
  2,76 s, RTF ≈ 0,23. RSS engine sau warm, cùng root/cùng cài đặt fp32, đo 2 lần mỗi bên:
  chỉ VieNeu **1.136 MB**; VieNeu + Kokoro **~1.660 MB** (+525 MB), sau một lượt đọc tiếng Anh
  1.828 MB (+~690 MB). **Chưa đo trên M1.**
- Định tuyến (sau quyết định 15/09 ở §5.5): giọng nào cũng đọc văn bản nào; mã từ chối duy nhất
  còn lại là `model_missing` — giọng của mô hình chưa có trên máy (Kokoro đã xoá, hoặc VieNeu chưa
  từng tải trên máy chỉ tải tiếng Anh). Danh mục giọng bỏ qua mô hình chưa có (không nạp SDK chỉ
  để kể tên giọng); `estimate` trả thêm `language` để màn dán có gì mà gợi ý.
- Shell: sheet **Giọng đọc & mô hình** (màn đầu + bánh răng trang chủ) và bảng giọng đọc theo
  ngôn ngữ (xem §5.5); một lượt tải bị huỷ để lại các tệp đã về nguyên vẹn (tới 326 MB) cho lần
  tải tiếp, hàng đó nói thẳng "Tải chưa xong · N MB đã về máy" với cả **Tải tiếp** lẫn **Xoá**;
  giọng nhớ theo ngôn ngữ (`voice_vi`, `voice_en`); giọng chỉ tự đổi đúng một trường hợp — mô hình
  vừa tải xong cho chính tab đang mở mà giọng đang dùng không hợp tiếng đó — và không bao giờ tự
  nhảy sang giọng trả phí.
- Chưa có: giọng Anh-Anh (cần từ điển gb + vocab riêng), int8, câu trộn hai thứ tiếng.

## Nguồn `[fetched 2026-09-15]`

- Kokoro ONNX files: https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/tree/main/onnx
- misaki (giấy phép, extras, fallback): https://github.com/hexgrad/misaki ·
  https://raw.githubusercontent.com/hexgrad/misaki/main/pyproject.toml
- BART G2P fallback: https://huggingface.co/PeterReid/graphemes_to_phonemes_en_us
- Supertonic 3: https://github.com/supertone-inc/supertonic · https://huggingface.co/Supertone/supertonic-3
- KittenTTS: https://github.com/KittenML/KittenTTS · requirements.txt
- Benchmark độc lập Kokoro vs Supertonic 3: https://heyneo.com/blog/kokoro-tts-vs-supertonic-3-tts
- Bối cảnh 2026: https://offlinetts.com/tts/best-browser-tts/ · https://openvoxai.com/blog/best-free-local-tts-models-2026
