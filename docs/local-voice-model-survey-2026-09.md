# Có model đọc tiếng Việt cục bộ nào hơn model đang dùng không? — khảo sát 07/09/2026

Chủ hỏi: *"có model local nào đọc tiếng Việt chất lượng hơn model local hiện tại của chúng ta không?"*
Mọi số liệu dưới đây lấy từ web ngày **07/09/2026** (`[fetched]`) hoặc từ mã nguồn repo này; chỗ nào là
kiến thức nền chưa kiểm lại thì ghi `[from training — may be stale]`.

## 0. Kết luận ngắn

1. **Không có model cục bộ nào được chứng minh là đọc tiếng Việt hay hơn** VieNeu-TTS v3 Turbo — vì
   **chưa ai đo**. Không có bảng xếp hạng, bài báo hay bài đánh giá độc lập nào đặt VieNeu cạnh một model
   khác. Speech Arena của Artificial Analysis chấm tiếng Anh; bài báo MOS tiếng Việt duy nhất (2025) không
   có VieNeu lẫn F5.
2. Mọi ứng viên "nghe có vẻ mạnh hơn" đều rơi vào một trong bốn ô: **không có tiếng Việt** · **giấy phép
   phi thương mại** · **cần PyTorch/GPU** (ta chạy ONNX thuần trên CPU) · **cùng họ VieNeu nhưng bản to
   hơn, chạy PyTorch/GGUF**.
3. **Chỗ chắc ăn nhất để tăng chất lượng lại nằm trong chính model đang dùng**: tác giả vừa ra
   `vieneu` **3.4.0 → 3.6.3 trong 5 ngày (02–06/09)**, đổi mặc định sang **fp32**, up trọng số mới lên
   đúng repo ta ghim, và sửa lỗi "nói thừa chữ" ở câu ngắn (đo 8 → 0 trên 480 mẫu). Ta đang ghim **3.3.0
   (20/08)** và revision **tháng 7**. Nâng cấp này gần như không tốn công tích hợp.
4. Muốn nói "hay hơn" thì phải **nghe A/B trên cùng đoạn văn** — đúng việc P0 trong
   `reading-intelligence-audit.md` đã đề xuất mà chưa làm. Không có nó, mọi thay đổi là đoán.

## 1. Model hiện tại — ràng buộc thật

| | |
|---|---|
| Model | `pnnbao-ump/VieNeu-TTS-v3-Turbo`, revision `2da0efab…` (`legal/MODEL_PROVENANCE.md`) |
| Kích cỡ | **0.1B** tham số, backbone Qwen3, codec MOSS-Audio-Tokenizer-Nano, g2p `sea-g2p` `[fetched]` |
| Âm thanh | **48 kHz** — cả pipeline (`headless/server.py`) là 48 kHz float32 |
| Runtime | **ONNX Runtime 1.29 thuần** — không có torch trong bundle (`uv pip show vieneu`) |
| Hai bậc trong app | `int8` = "Tiêu chuẩn · 330 MB" (mặc định) · `fp32` = "Cao nhất · 625 MB" (`speech/vieneu.py:29`) |
| Dữ liệu huấn luyện | ~10.000 giờ Anh–Việt, "trained from scratch" `[fetched]` |
| Giấy phép | Apache-2.0 |
| Hiệu năng | "first audio 300 ms, RTF < 1 trên CPU" `[fetched]` |

Hệ quả cứng: một model thay thế phải **(a)** có đường chạy ONNX/CoreML/MLX không kéo PyTorch vào bundle
396 MB, **(b)** giấy phép cho phân phối app, **(c)** ra 48 kHz hoặc chấp nhận resample (đường 24k→48k đã
có sẵn cho giọng ngoài).

## 2. Bảng ứng viên

| Model | Tiếng Việt | Giấy phép | Runtime / CPU | Bằng chứng chất lượng | Kết luận |
|---|---|---|---|---|---|
| **VieNeu-TTS-v3-Turbo, revision mới + SDK 3.6.3** | ✓ | Apache-2.0 | ONNX thuần, như hiện tại | Tác giả tự đo: babble 8→0/480 câu ngắn; mặc định đổi sang fp32 `[fetched]` | **Làm ngay** — §3 |
| VieNeu-TTS-v3-Nano (preview, 04/09) | ✓ | Apache-2.0 | ONNX, 24 kHz, RTF 0.11–0.22 | Tác giả: "trades quality for speed", yếu tiếng Anh | Không — thấp hơn |
| VieNeu-TTS-v2 (0.3B) / VieNeu-TTS (0.5–0.6B) | ✓ | Apache-2.0 | **PyTorch** (GPU/lmdeploy) hoặc **GGUF** (cần `llama-cpp-python`) | Tác giả tự chấm ⭐⭐⭐⭐⭐ vs Turbo ⭐⭐⭐⭐, không số | Chỉ đáng nếu chịu thêm runtime GGUF; cần nghe thử |
| **zalopay/vietnamese-tts** (F5-TTS, ~200 h) | ✓ | **CC-BY-4.0** (thương mại OK) | PyTorch; có đường **F5-TTS-ONNX** (Apache-2.0) chưa kiểm với fine-tune; 24 kHz; diffusion ⇒ RTF CPU chưa biết | Không có MOS/WER `[fetched]` | Ứng viên **duy nhất** sạch giấy phép để đưa vào bài nghe A/B |
| hynt/F5-TTS-Vietnamese-ViVoice (1000 h) | ✓ | **CC-BY-NC-SA-4.0** | PyTorch | Không số | **Loại** — phi thương mại |
| capleaf/viXTTS (XTTS-v2 fine-tune) | ✓ | **Coqui CPML** — thương mại phải xin | PyTorch, nặng | Bài báo 2025: **kém hơn XTTS-v2 gốc** trên viVoice (MOS 3.48 vs 3.98; WER 12.54 vs 8.32) | **Loại** |
| dangvansam/viet-tts | ✓ | code Apache, **weights CC-BY-NC** | PyTorch | Không số | **Loại** |
| facebook/mms-tts-vie (VITS, 2023) | ✓ | CC-BY-NC-4.0 `[from training]` | ONNX được, 16 kHz, 1 giọng | Chất lượng máy móc `[from training]` | **Loại** |
| **Piper** `vi_VN-vais1000-medium` | ✓ | MIT | **ONNX thuần**, rất nhẹ, 22.05 kHz | VITS đời cũ, không clone `[from training]` | Chỉ hợp làm bậc siêu nhẹ, không phải "hay hơn" |
| **NVIDIA Magpie TTS Multilingual 357M** | ✓ (1/12 ngôn ngữ) | NVIDIA Open Model License — **thương mại OK**, phải ghi credit | **NeMo + PyTorch, GPU** (L4…H100); 22.05 kHz; không clone; 5 giọng, không giọng nào ghi là Việt | Elo 1056 Speech Arena (tiếng Anh); không số tiếng Việt | Không phù hợp app CPU |
| Kokoro-82M (v2602) | **✗** | — | — | — | Không có tiếng Việt (issue #153 còn mở) |
| Qwen3-TTS · CosyVoice 3 · Fish Speech/OpenAudio S1 · Chatterbox Multilingual · Breeze TTS 2 | **✗** | — | — | — | Không liệt kê tiếng Việt `[fetched]` |
| XTTS-v2 + PhoAudiobook (bài báo arXiv 2506.01322) | ✓ | dataset CC-BY-NC-ND; **weights không phát hành** | — | MOS 4.20 trên test in-domain — con số MOS tiếng Việt công khai duy nhất tìm được | Không lấy được |

Bài học từ hàng viXTTS: **"fine-tune cho tiếng Việt" không đồng nghĩa "hay hơn"** — bản fine-tune bằng dữ
liệu YouTube chưa chuẩn hoá kém hơn model gốc trên cả MOS lẫn WER. Đây là lý do không được chọn model bằng
mô tả; phải nghe.

## 3. Việc nên làm đầu tiên: nâng cấp trong họ VieNeu

Những gì đã đổi phía tác giả kể từ bản ta ghim (`[fetched]`, GitHub releases + HF commits):

| Ngày | Gì | Ảnh hưởng tới ta |
|---|---|---|
| 02/09 | **3.4.0** — "v3 Turbo **mặc định fp32**" + sửa watermark/UI; folder `onnx_update` được up lại | Ta mặc định **int8**. Tác giả coi fp32 là chuẩn ⇒ cần A/B int8 vs fp32 trước khi giữ mặc định |
| 04/09 | Up `model.safetensors` (bản `update/` 248 MB) — trọng số mới; sau đó revert rồi **khôi phục** (8b7e9cf) | Revision ta ghim (`2da0efab`, tháng 7) **không có** trọng số này |
| 04/09 | 3.5.0 — v3 Nano preview | Không liên quan |
| 05/09 | 3.6.0 — LoRA fine-tune cho v3 Turbo | Mở đường tinh chỉnh giọng riêng sau này |
| 06/09 | **3.6.1** — chống "nói thừa chữ" ở câu ≤2–3 âm tiết (chạm trần khung hoặc nhiều burst hơn âm tiết ⇒ sinh lại); trần khung theo **âm tiết** thay vì theo từ (hết cụt "notification"); **ONNX bị ảnh hưởng ngang GPU (~5% câu 1 âm tiết)**; A/B 480 câu: 8 → 0 | **Trực tiếp** — ta tổng hợp **từng câu riêng lẻ** (audit F3) nên câu cực ngắn (tiêu đề một từ, "Vâng.", nhãn) là ca thường gặp |
| 06/09 | **3.6.2** — cue đứng riêng (`[cười]`…) bị trần 1 s; **mặc định đổi giọng Adam → Minh Quân** | Ta lưu `voice_id` theo tên (`"adam"`) trong Progress; phải kiểm ID không đổi |
| 26/08 | `sea-g2p` 0.9.0 → **0.9.1** (SDK 3.6.3 yêu cầu ≥0.9.1) | Tầng phát âm; changelog trống, phải nghe |

Chi phí: `vieneu` 3.6.3 vẫn ONNX thuần (`torch` chỉ trong extras `legacy/cuda/finetune`), Python ≥3.10 (ta
3.13), `onnxruntime>=1.20` (ta 1.29). Bề mặt SDK ta chạm: `Vieneu(backbone_repo=…)`, `infer_stream`,
`list_preset_voices` — 3.6.1 ghi rõ "`infer_stream` is unchanged".

**Quy trình đề xuất (có cổng kiểm):**
1. Dựng **bộ probe A/B** (P0 của audit): 5 đoạn cố định — tiêu đề một từ · câu ngắn "Vâng." · đoạn dài
   có mệnh đề · câu có từ tiếng Anh · chú thích hình — render ra WAV cho mỗi cấu hình.
   → verify: thư mục `probe/<cấu hình>/<đoạn>.wav`, tổng thời lượng, không file rỗng.
2. Ghim `vieneu==3.6.3`, `sea-g2p==0.9.1`, đổi `MODEL_REVISION` sang commit `8b7e9cf`; chạy
   `./scripts/verify.sh` (933+ test) và probe. → verify: gate xanh; `list_preset_voices()` vẫn trả `adam`
   (hoặc ghi bảng đổi tên); cache tự vô hiệu vì key có `model_revision`.
3. Nghe 4 cấu hình trên cùng 5 đoạn: `cũ-int8` · `cũ-fp32` · `mới-int8` · `mới-fp32`. Chủ chấm.
   → verify: một bảng 4×5 điểm + quyết định mặc định.
4. Nếu chọn fp32 mặc định: đổi `DEFAULT_PRECISION`, sửa nhãn "Tiêu chuẩn/Cao nhất" cho khớp (330 MB không
   còn là mặc định), cân nhắc thời gian tải lần đầu.

**Kết quả 07/09 (bước 1–2 đã làm):**
- Ghim `vieneu==3.6.3` (kéo `sea-g2p` 0.9.1; `perth` rời lock — watermark giờ là extra, SDK tự tắt khi
  thiếu). `ENGINE_VERSION` 3.6.3 ⇒ cache audio cũ tự vô hiệu. Gate `verify.sh` 941 test xanh.
- **Bản vá 3.6.1 không tới đường ta gọi.** Bộ chống nói thừa nằm trong `infer()`; `infer_stream()` đúng là
  "unchanged" như changelog ghi. Đo 100 render × 3 nhánh, 10 câu 1–3 từ, giọng Adam, fp32, thước đo của
  SDK (`count_speech_bursts` > âm tiết): 3.3.0 stream **33 %** · 3.6.3 stream **31 %** · 3.6.3 `infer`
  **4 %**. Ta sửa phía ta: câu ≤3 từ đi qua `infer`, trả nguyên mẩu. Giá: âm đầu tiên của câu ngắn tới muộn hơn (0,14–0,50 s thay vì 0,06 s qua sidecar) vì phải sinh trọn câu, có khi sinh lại — hàng đợi chạy trước tai che được, trừ câu mở đầu lượt đọc. Lesson
  `an-upstream-fix-lands-only-on-the-path-you-call`.
- Marker sẵn sàng không còn gate theo `engine_version` (chỉ codec + model revision): nâng SDK không kéo cài
  đặt offline về "chưa sẵn sàng". Biên nhận: sidecar 3.6.3 chạy trên bản sao thư mục `Models/` thật (marker
  vẫn ghi 3.3.0) báo `ready: true`, đọc "Được không?" ra audio, không tải gì.
- **Chưa** dời `MODEL_REVISION` sang 8b7e9cf: trọng số mới là quyết định nghe riêng (bước 3–4 vẫn mở). Trên
  đĩa máy này chỉ có build `onnx_update` (fp32), nên bài nghe int8 vs fp32 cần tải thêm 158 MB trước.

## 4. Nếu vẫn muốn thử model ngoài họ

Chỉ **zalopay/vietnamese-tts** đáng đưa vào bài nghe ở bước 3: giấy phép sạch, kiến trúc F5 khác hẳn
(diffusion, không tự hồi quy ⇒ có thể **không** bị "giọng ngang do reset ngữ điệu mỗi câu" — audit F3).
Rào cản thật: cần export qua **F5-TTS-ONNX** (chưa ai xác nhận với fine-tune), RTF trên CPU chưa đo, 200 h
dữ liệu so với 10.000 h, và 24 kHz. Đây là thí nghiệm nửa ngày, không phải kế hoạch đổi model.

Không theo đuổi: Magpie (GPU, không giọng Việt bản địa), viXTTS / F5-ViVoice / VietTTS / MMS (giấy phép).

## 5. Điều còn chưa biết

- Trọng số `update/` mới có **nghe** khác gì bản tháng 7 không — chỉ nghe mới biết.
- ID giọng có đổi theo 3.6.2 không — kiểm bằng `list_preset_voices()` sau khi nâng cấp.
- 3.4.0 / 3.5.0 / 3.6.0 / 3.6.3 là **tag không có release notes** (kiểm qua `gh api releases`: chỉ 3.6.1
  và 3.6.2 có). Sự kiện "mặc định fp32" lấy từ thông điệp tag 3.4.0 (`v3 Turbo mac dinh fp32 + sua
  watermark/UI theo issue #191`) và commit `onnx_update` 02/09 trên HF — chưa có lời giải thích của tác giả
  vì sao đổi mặc định; hỏi trong issue #191 nếu cần.

## Nguồn `[fetched 2026-09-07]`

- VieNeu v3 Turbo card · repo cha · profile tác giả · commits · PyPI `vieneu` · GitHub releases 3.6.1/3.6.2
  — https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo · https://github.com/pnnbao97/VieNeu-TTS ·
  https://pypi.org/project/vieneu/
- XTTS-v2 + PhoAudiobook, MOS/WER tiếng Việt — https://arxiv.org/html/2506.01322v1
- Magpie TTS Multilingual — https://huggingface.co/nvidia/magpie_tts_multilingual_357m ·
  https://huggingface.co/blog/nvidia/magpie-tts-multilingual-voice-agents ·
  https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/
- F5 Việt — https://huggingface.co/zalopay/vietnamese-tts · https://huggingface.co/hynt/F5-TTS-Vietnamese-ViVoice ·
  https://github.com/DakeQQ/F5-TTS-ONNX
- viXTTS — https://huggingface.co/capleaf/viXTTS · VietTTS — https://huggingface.co/dangvansam/viet-tts
- Piper — https://github.com/rhasspy/piper/blob/master/VOICES.md
- Không có tiếng Việt: Kokoro https://github.com/hexgrad/kokoro/issues/153 · CosyVoice https://github.com/FunAudioLLM/CosyVoice ·
  Fish Speech https://github.com/fishaudio/fish-speech · Chatterbox https://huggingface.co/ResembleAI/chatterbox ·
  Qwen3-TTS https://github.com/QwenLM/Qwen3-TTS · Breeze TTS 2 https://huggingface.co/BreezeBlue/Breeze-TTS-2
- Speech Arena — https://artificialanalysis.ai/text-to-speech/arena
