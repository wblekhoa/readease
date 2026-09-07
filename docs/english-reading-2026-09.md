# Đọc tiếng Anh trong ReadEase — đường đi

Chủ đặt bài 07/09/2026: "app sẽ có thể đọc tiếng Anh để phục vụ international", kèm một luật cứng:
**tuyệt đối không dùng model VieNeu cho tiếng Anh** — VieNeu làm riêng cho tiếng Việt.

Web fact ghi `[fetched 07/09/2026]`; kiến thức nền chưa kiểm ghi `[from training — may be stale]`.

## 0. Luật của chủ, viết thành code

VieNeu **có** đọc được văn bản tiếng Anh — đo trên máy này 07/09: "The quick brown fox…" ra 2,88 s audio,
không lỗi. Đó chính là lý do phải chặn: hỏng ở đây là hỏng **nghe được**, không phải hỏng thấy được, nên nếu
không chặn thì nó sẽ lặng lẽ đọc dở suốt cuốn sách.

Nên engine **từ chối bằng tên**, đúng khuôn có sẵn cho giọng trả phí thiếu khoá: `voice_unavailable:
wrong_language`, và vỏ nói ra thành câu ("Giọng trên máy chỉ đọc được tiếng Việt…"). Danh mục giọng khai
`languages: ["vi"]` cho giọng cục bộ, để người đọc thấy TRƯỚC khi bấm, không phải sau.

## 1. Trạng thái sau bản 07/09

| Việc | Trạng thái |
|---|---|
| Giọng ngoài (OpenAI, ElevenLabs, BYOK) đọc tiếng Anh | **Chạy được ngay** — đường định tuyến `provider:model:voice` không hề giả định ngôn ngữ |
| Lời engine tự nói xen vào (cue hình, cue chú thích) | **Theo ngôn ngữ đọc** — "See figure 3." / "Also, …" thay vì "Xem hình 3." / "Nói thêm, …" |
| Số, số La Mã, địa chỉ web | **Theo ngôn ngữ đọc** — "Part two" thay vì "Part hai"; "the address svpg dot com" thay vì "địa chỉ svpg chấm com"; "#1" → "number one" (tiếng Anh nói số, không nói thứ tự) |
| Nhãn hình của sách | Đã nhận sẵn từ tiếng Anh: `Figure 2-4`, `Fig. 7` nằm trong regex từ trước |
| Giọng VieNeu + sách tiếng Anh | **Bị từ chối**, không đọc |
| Ngôn ngữ đọc lấy từ đâu | Tạm lấy theo **ngôn ngữ giao diện** (`ui_language`) — xem §2 |
| Giọng tiếng Anh **cục bộ** (không cần khoá, không cần mạng) | **Chưa có** — xem §3 |

Những gì vốn đã không phụ thuộc ngôn ngữ thì giữ nguyên một đường: bỏ dấu chú thích, hạ chữ HOA, bỏ ký tự
đầu dòng, chấm câu cho tiêu đề.

## 2. Ngôn ngữ đọc: bước sau phải là **theo từng cuốn**

Lấy theo ngôn ngữ giao diện là câu trả lời **đúng nhưng tạm**: nó đúng với người đã chuyển app sang tiếng
Anh, và sai với một thư viện có cả sách Việt lẫn sách Anh.

Bước đúng: **cuốn sách tự khai ngôn ngữ của nó.**
- EPUB có `dc:language` trong OPF — bắt buộc theo đặc tả EPUB `[from training — may be stale]`, đọc lúc nhập.
- PDF không có gì đáng tin ⇒ đoán bằng chữ (tỷ lệ ký tự có dấu tiếng Việt là dấu hiệu rẻ và chắc), hoặc hỏi
  một lần lúc nhập.
- Cần một cột `language` trên bảng sách + migration, và một chỗ trong giao diện để sửa khi đoán sai.
- Cổng kiểm: nhập 9 cuốn thật của chủ ⇒ mỗi cuốn ra đúng ngôn ngữ; một cuốn tiếng Anh đọc bằng giọng ngoài
  không còn câu tiếng Việt nào xen vào.

## 3. Giọng tiếng Anh cục bộ — ứng viên, và cái bẫy giấy phép

Bundle đã mang sẵn `onnxruntime` (44 MB), nên thêm một model ONNX chỉ tốn **trọng số**, không tốn runtime.

| Ứng viên | Giấy phép | Cỡ | G2P (khâu chữ→âm) | Đọc |
|---|---|---|---|---|
| **Kokoro-82M ONNX** | model **Apache-2.0**, runtime `kokoro-onnx` **MIT** `[fetched]` | ~300 MB fp32, **~80 MB q8** `[fetched]` | `misaki` — **phải kiểm xem có kéo espeak-ng không** | 54 giọng, có Mỹ + Anh; nhóm tiếng Anh Mỹ được đánh giá tốt nhất `[fetched]` |
| **Piper** | engine `piper1-gpl` **GPL-3.0**, espeak-ng **GPL**, mỗi giọng một giấy phép riêng `[fetched]` | mỗi giọng 1 file `.onnx` + `.json` `[fetched]` | **espeak-ng, GPL** | Nhiều giọng en_US/en_GB |
| OpenAI / ElevenLabs (BYOK) | dịch vụ | 0 | của họ | **Đã chạy hôm nay** |

**Bẫy**: Piper buộc espeak-ng GPL vào bundle. Với bản GitHub thì còn bàn được; với bản lên App Store/Setapp
(`direction-commercial-2026-09.md`) thì GPL trong một app đóng gói là ngõ cụt. Kokoro sạch giấy phép hơn
**nếu** khâu G2P của nó không kéo espeak-ng theo — đó là câu hỏi phải trả lời trước, không phải sau.

**Việc kế tiếp, theo thứ tự:**
1. Đọc `misaki`: nó phát âm tiếng Anh bằng gì, có cần binary ngoài không, giấy phép ra sao.
   → verify: một script chạy Kokoro q8 offline trong `.venv`, không có espeak-ng trên máy, ra WAV.
2. Nếu sạch: dựng bài nghe A/B — cùng 5 đoạn tiếng Anh qua Kokoro q8 · Kokoro fp32 · OpenAI tts-1 · ElevenLabs
   Flash. Chủ chấm. → verify: bảng 4×5 điểm.
3. Nếu chọn Kokoro: thêm nó thành **engine thứ hai** sau `SpeechEngine` (giao diện đã có sẵn, VieNeu chỉ là
   một bản cài của nó), tải theo yêu cầu như VieNeu, ghim revision + marker sẵn sàng như VieNeu.
   → verify: `verify.sh` xanh; đọc offline một chương tiếng Anh; bundle không phình quá +90 MB.

## 4. Chủ phải quyết
1. Bản phát hành có kèm giọng tiếng Anh cục bộ (thêm ~80–300 MB tải về) hay chỉ dùng giọng từ xa/BYOK.
2. Nếu Kokoro dính espeak-ng GPL: bỏ giọng tiếng Anh cục bộ, hay chấp nhận GPL ở riêng bản GitHub.
3. Ngôn ngữ đọc theo từng cuốn (đúng hơn, tốn migration) hay giữ một công tắc chung.

## Nguồn `[fetched 2026-09-07]`
- Kokoro ONNX: https://github.com/thewh1teagle/kokoro-onnx
- Piper giấy phép: https://github.com/rhasspy/piper/discussions/271 · https://www.cekura.ai/discover/piper-tts
