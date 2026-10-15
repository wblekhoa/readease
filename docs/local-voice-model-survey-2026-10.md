# Có model đọc tiếng Việt mới nào hay hơn model đang dùng không? — khảo sát lại 13/10/2026

> [!NOTE]
> **Tài liệu nghiên cứu, nối tiếp `local-voice-model-survey-2026-09.md` (07/09).** Chỉ ghi những gì
> thay đổi từ 07/09 đến 13/10/2026. Số liệu web là `[fetched 2026-10-13]`; kiến thức nền chưa kiểm lại
> ghi `[from training — may be stale]`. Không phải mô tả hiện trạng app — đọc mã nguồn cho việc đó.

Chủ hỏi: *"trong cộng đồng có model AI mới, chất lượng đọc tiếng Việt tốt hơn model chúng ta đang dùng không?"*

## 0. Kết luận ngắn

1. **Vẫn chưa có model mở nào được chứng minh đọc tiếng Việt hay hơn VieNeu-TTS v3 Turbo** mà chạy được
   trong ReadEase (Mac, CPU, không PyTorch, máy 8 GB). Vẫn chưa có bài nghe mù hay bảng MOS tiếng Việt
   độc lập nào đặt các model cạnh nhau.
2. **Thứ hay hơn rõ ràng đã có nhưng đóng:** **VieNeu-TTS v4** — tác giả công bố là độc quyền, chỉ chạy qua
   API / vieneu.io, **không mở mã**. Một bản **VieNeu-TTS v3 (không Turbo)** "Coming soon" nhưng chỉ chạy
   PyTorch/GPU.
3. **Đã nghe A/B (§5): trọng số mới không hay hơn — hoà (3,17 vs 3,21/5).** Trước khi nghe, giả thuyết là:
   **việc đáng làm nhất vẫn nằm trong chính model đang dùng:** từ 02–16/09 tác giả đã đưa **trọng số v3
   Turbo mới** (`update/`) vào cả bản fp32 (`onnx_update`) lẫn **bản int8 xuất lại ngày 16/09** — đúng bản
   "Tiêu chuẩn" ReadEase tải mặc định. ReadEase vẫn ghim revision **`2da0efab` (21/08)**, *trước* trọng số
   mới. Thêm SDK `vieneu` đã lên **3.8.3** (ta 3.6.3).
4. Ứng viên mới ngoài họ VieNeu đáng **nghe thử** chỉ có **Supertonic 3** (nhỏ, ONNX, CPU, có tiếng Việt) —
   nhưng số đo duy nhất (WER 4,49 %) kém xa VoxCPM2/OmniVoice và repo đã **archive**. Khả năng nó hay hơn
   VieNeu thấp; giá trị chính là một bậc siêu nhẹ.

## 1. Mốc so sánh (đọc từ repo, 13/10)

| | |
|---|---|
| Model | `pnnbao-ump/VieNeu-TTS-v3-Turbo`, `MODEL_REVISION = 2da0efab…` (21/08) — `src/vieneu_reader/speech/vieneu.py:24` |
| Mặc định | `int8` ("Tiêu chuẩn · 330 MB"); `fp32` = "Cao nhất · 625 MB" |
| SDK | `vieneu==3.6.3` (`pyproject.toml`) |

## 2. Họ VieNeu — thay đổi từ 07/09 `[fetched 2026-10-13]`

Trọng số trên Hugging Face (`api/models/pnnbao-ump/VieNeu-TTS-v3-Turbo/commits/main`):

| Ngày | Commit | Nội dung |
|---|---|---|
| 05/09 | `8b7e9cf` | Khôi phục trọng số mới (`onnx_update/*` 02/09 + `update/model.safetensors` 04/09) sau một lần revert |
| **16/09** | `5f2a3e9` | **`onnx_int8`: re-export from current `update/` weights** (backbone int8 + acoustic int8) |
| 23/09 | `a9a4e58`, `552dc77`, `ca58dac`, `61b85e3` | GGUF q8_0 / bf16 cho audio.cpp, 25 giọng preset đóng gói |

⇒ Từ 16/09, **cả hai bậc** int8 và fp32 của revision mới đều dùng trọng số mới. Revision ta ghim không có.

SDK `vieneu` 3.6.3 → **3.8.3** (PyPI; GitHub `compare/v3.6.3...v3.8.3`), các mục chạm tới ta:

| Bản | Thay đổi | Ảnh hưởng tới ReadEase |
|---|---|---|
| 3.6.5 (15/09) | Cắt mảnh dài theo từ chia đều, không xẻ đôi con số; giảm tải CPU đường clone | Ta tự chia câu — phải kiểm có đụng `infer_stream` không |
| 3.7.x (15/09) | Server streaming chuẩn OpenAI, CUDA graph | Không (ta dùng CPU/ONNX) |
| 3.8.0 (16/09) | 25 giọng preset (thêm Adam bựa, Thiền Tâm Đức; Trúc Ly clip mới); sửa encoder nối thừa 455 khung đệm vào clip tham chiếu (#198) | Giọng mới để chọn; sửa lỗi clone |
| 3.8.1 (16/09) | **Đổi tên Minh Quân → Minh Quân Pro** (giữ "Minh Quân" làm alias) | ID giọng ta lưu — phải kiểm |
| 3.8.2 (23/09) | **Đổi tên giọng: Hải Đăng, Thiện Minh, Quốc Tuấn** | **Rủi ro**: tiến độ lưu `voice_id` theo tên — phải có bảng ánh xạ trước khi nâng |

README hiện tại (13/10) còn nói thêm:
- v4: *"proprietary and will not be open-sourced … exclusively through the VieNeu API / vieneu.io"*.
- *"VieNeu-TTS v3 Turbo remains the latest open-source version."* Bảng model: **VieNeu-TTS-v3 · Coming soon ·
  PyTorch · GPU.**
- Mặc định CPU của SDK là **fp32**; int8 nhanh ~1,6× nhưng *"requires a CPU with VNNI … on older CPUs int8 can
  produce garbled audio"*. Apple Silicon là ARM, không có VNNI — onnxruntime dùng đường int8 của ARM. ReadEase
  đã chạy int8 trên M-series từ trước mà không gặp audio vỡ; nhưng khi nâng lên int8 xuất lại 16/09 phải nghe
  lại trên Mac thật.

## 3. Ứng viên ngoài họ VieNeu — mới hoặc cập nhật sau 07/09

| Model | Tiếng Việt | Giấy phép | Chạy trong ReadEase? | Bằng chứng chất lượng | Kết luận |
|---|---|---|---|---|---|
| **Supertonic 3** (Supertone, 29/04/2026) | ✓ (1/31) | Model **OpenRAIL-M** (thương mại được, kèm điều khoản cấm dùng sai mục đích `[from training — may be stale]`), code MIT | **Có**: ~99M tham số, **ONNX trên CPU**, 44,1 kHz | WER tiếng Việt **4,49 %** vs VoxCPM2 1,48 % vs OmniVoice 0,79 % (bảng của chính Supertone); bài tổng hợp nhận xét "không mạnh về diễn cảm" | **Nghe thử được**, khó hơn VieNeu; repo **đã archive**, không clone giọng miễn phí |
| **VoxCPM2** (OpenBMB, 04/2026) | ✓ (1/30) | Apache-2.0 | **Không thực tế**: 2B tham số, PyTorch+CUDA ~8 GB VRAM; bản cộng đồng MLX int8 ~3 GB, Core AI ~4,9 GB RAM | Không có số tiếng Việt riêng ngoài WER 1,48 % ở bảng Supertone | Mạnh nhất nhóm giấy phép mở, nhưng quá nặng cho mức sàn M1/8 GB |
| OmniVoice (k2-fsa) + G-OmniVoice (bản tinh chỉnh tiếng Việt) | ✓ | Code Apache-2.0, **trọng số CC-BY-NC** | PyTorch | WER 0,79 % (bảng Supertone) | **Loại** — phi thương mại |
| Fish Audio S2 Pro (03/2026) | ✓ (nhóm phụ) | Fish Audio Research License — thương mại phải mua | ~5B, GPU | Không số tiếng Việt | **Loại** |
| Higgs TTS 3 4B (Boson, 06/2026) | ✓ (nhóm WER/CER < 5) | Research & Non-Commercial; nhúng vào app cần giấy phép riêng | ~4B, GPU | Không số riêng | **Loại** |
| V-TTS / Valtec (04/2026) | ✓ | CC BY-NC 4.0 | PyTorch, có ONNX | Không số | **Loại** — phi thương mại |
| sanoTTS `vi-vais1000` | ✓ | GPL-3.0 | numpy thuần, 22,05 kHz, 1,46M tham số | Chưa đo tiếng Việt; chưng cất từ Piper/VITS | Không — chất lượng cỡ Piper |
| F5-TTS tiếng Việt (zalopay, EraX, hynt, ViVoice-ViNV…) | ✓ | zalopay CC-BY-4.0; phần lớn còn lại NC | PyTorch | Không MOS | Như 07/09 — chỉ zalopay sạch giấy phép |
| Qwen3-TTS (mở) | ✗ | — | — | — | Tiếng Việt chỉ có ở **Qwen-Audio-3.0-TTS** — bản **API**, không mở trọng số |
| Kokoro, Chatterbox, CosyVoice 3, IndexTTS-2.5, VibeVoice, Breeze-TTS-2, KittenTTS 2 | ✗ | — | — | — | Không khai báo tiếng Việt |
| VLSP 2026 | — | — | — | Chưa tìm thấy kết quả công bố cho mảng TTS | Theo dõi khi có |

## 4. Việc nên làm (theo thứ tự, mỗi bước có cổng kiểm)

1. **Bài nghe A/B trong họ VieNeu** — cùng 5 đoạn cố định (tiêu đề 1 từ · "Vâng." · đoạn dài nhiều mệnh đề ·
   câu chen từ tiếng Anh · chú thích hình), 4 cấu hình: `2da0efab-int8` (hiện tại) · `2da0efab-fp32` ·
   `mới-int8 (5f2a3e9)` · `mới-fp32`. Chạy trên **bản sao** thư mục `Models/`, không đụng thư viện thật.
   → verify: `probe/<cấu hình>/<đoạn>.wav` đủ 20 file, không file rỗng; chủ chấm một bảng 4×5.
2. **Nếu trọng số mới thắng:** dời `MODEL_REVISION` sang commit ≥ `5f2a3e9`, nâng `vieneu` 3.8.3 kèm **bảng
   ánh xạ tên giọng cũ → mới** (Minh Quân → Minh Quân Pro, 3 giọng đổi tên ở 3.8.2) cho tiến độ đã lưu.
   → verify: `./scripts/verify.sh` xanh; tiến độ cũ mở lại đúng giọng; nghe int8 mới trên Mac thật.
3. **Tuỳ chọn — Supertonic 3 vào cùng bài nghe** như bậc siêu nhẹ (~99M, ONNX). Chỉ đáng làm nếu muốn một
   lựa chọn tải nhỏ, đọc nhanh cho máy yếu; khó thay VieNeu ở chất lượng.
   → verify: đọc kỹ file LICENSE OpenRAIL-M trước khi bundle.
4. **Theo dõi:** VieNeu-TTS v3 (bản không Turbo) — nếu có đường ONNX/CPU thì quay lại; kết quả VLSP 2026.

## 5. Kết quả bài nghe A/B (13/10, chủ chấm mù)

Cách làm: 6 đoạn (§4 bước 1, thêm câu hỏi/cảm thán) × 2 giọng (Adam — mặc định app, Ngọc Linh) × 4 cấu hình, mỗi
cấu hình **một lần render**, đi đúng đường gọi của app (từng câu; ≤3 từ qua `infer`, dài hơn qua `infer_stream`;
sampling mặc định của app; onnxruntime 1.29 cả hai bên). Cũ = `2da0efab` + SDK 3.6.3; mới = `61b85e3` + SDK 3.8.3
(kéo `sea-g2p` 0.10.0). Trọng số cũ/mới khác hash ở cả `backbone_shared.data`, `v3_heads.npz`,
`acoustic_cached.onnx`. Trang nghe mù dựng riêng cho chủ chấm (không công khai).

| Cấu hình | Adam | Ngọc Linh | Trung bình (12 mẫu) |
|---|---|---|---|
| Cũ · int8 (app hiện tại) | 3,17 | 3,00 | 3,08 |
| Cũ · fp32 | 3,17 | **3,50** | **3,33** |
| Mới · int8 | 3,17 | 3,33 | 3,25 |
| Mới · fp32 | 3,00 | 3,17 | 3,08 |

- **Cũ 3,21 · mới 3,17** (24 mẫu mỗi bên): **hoà**. Khoảng cách giữa các cấu hình (≤0,25) nhỏ hơn nhiều độ lệch giữa
  các đoạn trong cùng một cấu hình (1→5). Với một lần render và sampling nhiệt độ 0,8, đây là nhiễu, không phải tín hiệu.
- **Điểm yếu thật, chung cả hai phiên bản: câu cực ngắn.** "Vâng." trung bình 2,62 (thấp nhất), điểm nhảy 1→5 giữa các
  lần render — cùng một câu khi hay khi hỏng. Câu ngắn của trọng số mới không ổn định hơn cũ.
- Chú thích có số đạt cao nhất (3,75).

**Quyết định đề xuất:** **không** nâng trọng số/SDK vì chất lượng — không có bằng chứng tai nghe thấy hơn, mà nâng
kéo theo đổi tên giọng (Minh Quân, Anh Khôi, Mạnh Dũng biến mất khỏi danh sách 3.8.3). Hướng đáng đầu tư là **độ ổn
định của câu ngắn** (đo được không cần tai: render N lần, đếm bản lệch thời lượng/âm tiết), trong khi giữ model hiện tại.

## 6. Đo câu ngắn bằng máy (13/10)

Cách làm: 10 câu ngắn hay gặp trong sách ("Vâng.", "Không.", "Mở đầu.", "Chương một.", "Lời nói đầu.",
"Kết luận.", "Hình 3.", "Phần hai.", "Cảm ơn.", "Tóm tắt.") × 2 giọng × **10 lần đọc**, đúng đường của app cho câu
≤3 từ (`sdk.infer`, có bộ chặn "nói thừa" của SDK, sinh lại tối đa 2 lần). Mỗi bản được **Whisper large-v3-turbo
(MLX)** nghe lại, tiếng Việt, greedy; "đúng" = nghe ra đúng chữ sau khi chuẩn hoá (số ↔ chữ, bỏ dấu câu).
Hiệu chuẩn: giọng macOS "Linh" đọc cùng 10 câu → Whisper đúng 9/10; sai duy nhất "Tóm tắt." nên câu này bị loại
khỏi tỉ lệ dưới đây.

Trọng số cũ `2da0efab`, int8 (mặc định app), SDK 3.6.3, chỉ đổi `temperature` (app đang dùng 0,8):

| temperature | Đúng chữ (180 bản) | Adam | Ngọc Linh | Lặp / thừa chữ | Whisper bịa câu¹ | Chạm trần thời lượng² |
|---|---|---|---|---|---|---|
| **0,8 (hiện tại)** | **61 %** | 59 % | 63 % | 9 | 10 | 9 |
| 0,5 | 69 % | 67 % | 72 % | 4 | 7 | 5 |
| 0,3 | 71 % | 63 % | 79 % | 7 | 3 | 4 |
| 0,1 | **74 %** | 63 % | **86 %** | 6 | 0 | 4 |

¹ Câu kiểu "Hãy subscribe cho kênh…" — Whisper bịa khi audio lạ/gần như câm; với giọng macOS: 0 lần.
² Bản kéo dài tới trần khung của model (1 tiếng = 1,04 s, 2 tiếng = 1,28 s): dấu hiệu nói thừa rồi bị cắt.

- Ở 0,8, fp32 không khá hơn int8 (115 vs 111/200 trước khi bỏ "Tóm tắt.").
- Lỗi thật thường gặp: **lặp** ("Cảm ơn, cảm ơn." — Adam 4/10 ở int8), **sai dấu** ("Mở đầu" → "Mở đâu?",
  "Lời nói đầu" → "Lời nói đâu"), **sai phụ âm đầu** ("Kết luận" → "Tiết luận", "Hình 3" → "Ảnh 3").
- Hạ temperature cho câu ngắn: **61 % → 74 %** (khác biệt có ý nghĩa thống kê, z ≈ 3 giữa 0,8 và 0,1); Whisper bịa
  10 → 0; chạm trần 9 → 4. **Ngọc Linh hưởng lợi rõ (63 → 86 %), Adam gần như không (59 → 63 %)** — giọng mặc định
  của app yếu nhất ở câu ngắn.
- Giới hạn: Whisper cũng nghe nhầm câu cực ngắn (trần đo được ~90 %); temperature thấp có thể làm giọng **đều,
  máy móc** — chưa nghe bằng tai.

**Đề xuất:** câu ≤3 từ (đã đi riêng qua `infer` ở `speech/vieneu.py`) dùng temperature thấp (0,3 – một chỗ sửa),
nhưng **nghe mù trước** 0,8 vs 0,3 trên các câu này để chắc không bị đều giọng. Riêng Adam cần thêm biện pháp (ví dụ
sinh 2 bản, chọn bản không chạm trần / không thừa cụm âm) hoặc cân nhắc giọng mặc định khác.

## 7. Chọn giọng mặc định (15/10)

Cùng cách đo (Whisper large-v3-turbo, VieNeu 3.6.3 int8, câu ngắn ở nhiệt độ 0,3), sáu đoạn của bài A/B, mỗi giọng 3 lượt.

| Giọng | Câu ngắn nghe đúng | Lỗi từ trung bình (6 đoạn) | Chỉ đoạn dài (3–6) |
|---|---|---|---|
| Đức Trí (Nam · Nam · đọc truyện) | 96 % | 5,7 % | 8,6 % |
| Mai Anh (Nữ · Bắc · tin tức) | 98 % | 8,9 % | 9,2 % |
| Trúc Ly (Nữ · Bắc · tự nhiên) | 96 % | 12,3 % | 10,2 % |
| Ngọc Linh (Nữ · Bắc · kể chuyện) | 71 % | 23,6 % | 10,5 % |
| Adam (Nam · Nam · tự nhiên, mặc định cũ) | 64 % | 24,5 % | 11,8 % |

Đoạn dài chênh ít; khác biệt chủ yếu nằm ở câu ngắn ("Vâng." của Adam ra "Văng"/"Văn" cả 3 lượt). Whisper nghiêng về giọng Bắc mà Đức Trí là giọng Nam, nên xếp hạng còn bất lợi cho Đức Trí mà vẫn đứng đầu. Quyết định: mặc định đổi sang Đức Trí (RE-VOICE-009, `docs/product/decisions.md` 15/10).

## 8. Gói phát âm dựng sẵn — đo trước khi làm (15/10)

20 thuật ngữ (AI, CEO, KPI, USB, PDF, Wi-Fi, iPhone, email, Facebook, YouTube, Google, Zalo, app, online, OK, laptop, website, MacBook, ChatGPT, TikTok), mỗi từ đặt trong câu "Hôm nay tôi muốn nói về … với các bạn.", đọc nguyên văn và đọc theo cách viết kiểu Việt ("kây pi ai", "phây búc"…), 3 lượt mỗi cách, giọng Đức Trí. Whisper nghe lại; tính đúng khi nghe ra từ gốc hoặc cách viết kiểu Việt.

- Nguyên văn: **54/60** · viết kiểu Việt: **49/60**.
- Viết kiểu Việt làm hỏng: KPI 3/3 → 0/3, online 3/3 → 1/3, ChatGPT 3/3 → 1/3, USB 3/3 → 2/3.
- Chỉ "OK" được lợi: 0/3 ("ô ca") → 3/3. Zalo 0/3 cả hai cách (Whisper nghe "gia lô", có thể do máy nghe).

Kết luận: không làm gói chung; sửa riêng "OK" ở tầng chuẩn hoá (RE-PLAY-019).

## Nguồn `[fetched 2026-10-13]`

- VieNeu: https://github.com/pnnbao97/VieNeu-TTS (README, `compare/v3.6.3...v3.8.3`, releases) ·
  https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo (commits) · https://pypi.org/project/vieneu/
- Supertonic 3: https://huggingface.co/Supertone/supertonic-3 · https://github.com/supertone-inc/supertonic
- VoxCPM2: https://huggingface.co/openbmb/VoxCPM2 · https://huggingface.co/aufklarer/voxcpm2-mlx-int8 ·
  https://huggingface.co/mlboydaisuke/VoxCPM2-CoreAI · https://voxcpm.readthedocs.io/en/latest/deployment/mlx_audio.html
- OmniVoice: https://huggingface.co/k2-fsa/omnivoice · https://huggingface.co/g-group-ai-lab/g-omnivoice
- Fish Audio S2 Pro: https://huggingface.co/fishaudio/s2-pro · Higgs TTS 3: https://huggingface.co/bosonai/higgs-tts-3-4b
- V-TTS/Valtec: https://github.com/tronghieuit/valtec-tts · sanoTTS: https://huggingface.co/ampixa/sanoTTS
- Qwen: https://github.com/QwenLM/Qwen3-TTS · https://www.alibabacloud.com/blog/qwen-audio-3-0-tts-more-multilingual-easier-to-direct_603379
- F5 tiếng Việt: https://huggingface.co/zalopay/vietnamese-tts · https://huggingface.co/erax-ai/EraX-Smile-Female-F5-V1.0 ·
  https://huggingface.co/trinhtrantran122/F5-TTS-Vietnamese-ViVoice-ViNV-NV-B2
- Danh sách model TTS trên Hugging Face: `api/models?pipeline_tag=text-to-speech` (sắp theo trending/mới/tải về), kiểm `cardData.language` từng model.
