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
| Ngôn ngữ đọc lấy từ đâu | **Chính cuốn sách** khai, đọc từ văn bản của nó; người đọc đặt lại được trong bảng Giọng đọc |
| Giọng tiếng Anh **cục bộ** (không cần khoá, không cần mạng) | **Chưa có** — xem §3 |

Những gì vốn đã không phụ thuộc ngôn ngữ thì giữ nguyên một đường: bỏ dấu chú thích, hạ chữ HOA, bỏ ký tự
đầu dòng, chấm câu cho tiêu đề.

## 2. Ngôn ngữ đọc: cuốn sách tự khai

Lấy theo ngôn ngữ giao diện là câu trả lời **đúng nhưng thủng**: nó bỏ sót đúng người dễ gặp nhất — người
Việt, giao diện tiếng Việt, mở một cuốn sách tiếng Anh. Với người đó luật của chủ sẽ không có hiệu lực.

Nên **cuốn sách được hỏi trực tiếp**, đọc từ chính văn bản của nó (`domain/language.py`): tỷ lệ chữ mang
chính tả tiếng Việt (ăâđêôơư + năm dấu thanh) trên mẫu 20.000 chữ cái, **rải đều từ đầu tới cuối sách**,
ngưỡng 5%.

Vì sao đọc chữ chứ không đọc metadata: EPUB có `dc:language`, PDF không có gì đáng tin, và cả hai sai đủ
thường xuyên để một cuốn sách bị đọc bằng ngôn ngữ không ai chọn. Văn bản là nhân chứng luôn có mặt.

Số đo để chọn ngưỡng (07/09): văn xuôi Việt 28% · Việt lẫn thuật ngữ Anh 12% · một câu tiếng Anh có hai
tên riêng Việt 6% (cả cuốn thì thấp hơn nhiều) · tiếng Anh 0%.

Hai bẫy đã bắt được bằng test:
- **Rải đều, không phải lấy phần đầu cho tới hết ngân sách**: cách sau chỉ bao giờ nhìn thấy phần mở đầu,
  nên một cuốn có đoạn đầu tiếng Anh bị đọc sai. Nay lấy 200 chỗ trải đều, mỗi chỗ cắt bớt theo phần ngân
  sách của nó.
- **Đoạn quá ngắn không là bằng chứng**: số trang, chú thích toàn chữ số ⇒ trả về mặc định, không đoán.

**Văn bản dán và vùng chọn cũng bị hỏi như vậy** — chính đoạn văn là bằng chứng. Nếu chỉ hỏi công tắc giao
diện thì luật của chủ sẽ thủng ở đúng ca thường gặp nhất: người Việt, giao diện tiếng Việt, dán một đoạn
tiếng Anh từ trình duyệt. Chỉ mẩu quá ngắn (dưới 20 chữ cái — "Ok.", một số trang) mới rơi về công tắc, vì
hai chữ thì không phán được gì, và đoán bừa sẽ từ chối đọc một ghi chú tiếng Việt hai từ.

**Biên nhận trên kệ sách thật của chủ (07/09)**, đọc bản sao chỉ-đọc của cơ sở dữ liệu, chỉ in số liệu tổng
hợp, không in tên sách và không in nội dung: **9/9 cuốn ra "vi"**, thấp nhất 13,9% — gấp gần ba lần ngưỡng
5%. Không cuốn nào suýt.

**Chỗ sửa tay (đã làm)**: bảng **Giọng đọc** có một hàng "Cuốn này đọc bằng" ngay trên danh sách giọng —
ngôn ngữ quyết định giọng nào được phép đọc, nên hai thứ đứng cạnh nhau. Lời của người đọc **thắng** kết quả
tự dò; bấm "Để máy tự dò lại" là rút lời đó, và cuốn sách quay về được **đọc lại**, không bị ghim vào câu trả
lời hôm nay (một cuốn nhập lại hoặc sửa lại phải được chấm lại từ đầu). Hàng này chỉ hiện khi đang mở một
cuốn sách: đoạn văn dán được chấm bằng chính chữ của nó ở mỗi lượt đọc, không có gì để nhớ.

Lưu ở bảng phụ `book_languages` — thêm mới, không đổi `SCHEMA_VERSION`, đúng đường mà `annotations` và
`apple_books_links` đã đi, nên bản ReadEase cũ mở thư viện này vẫn chạy và chỉ là không thấy nó. Chỉ cuốn nào
**có người không đồng ý** với máy mới có dòng, nên bảng rỗng với gần như mọi thư viện.

Nhờ đó ca **mất dấu** (PDF quét bằng OCR, hoặc gõ không dấu) hết là ngõ cụt: máy chấm nhầm thành tiếng Anh
thì người đọc đặt lại là xong. Kệ sách hiện tại không có cuốn nào như vậy (9/9 ra "vi").

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
3. Sách trộn hai thứ tiếng thật sự (một chương Việt, một chương Anh) vẫn chưa có câu trả lời: hiện cả cuốn
   mang đúng một ngôn ngữ.

## Nguồn `[fetched 2026-09-07]`
- Kokoro ONNX: https://github.com/thewh1teagle/kokoro-onnx
- Piper giấy phép: https://github.com/rhasspy/piper/discussions/271 · https://www.cekura.ai/discover/piper-tts
