# Cơ chế đọc - audit và đề xuất nâng cấp (2026-09-02)

Chủ đặt bài: giọng đọc thông minh hơn - nhắc khi tới hình, đánh số hình tự động, ngắt nghỉ
theo nội dung, giọng có lên xuống chứ không ngang. Tài liệu này soi cơ chế HIỆN CÓ trước,
rồi đề xuất theo thứ tự giá trị. Mọi khẳng định đều dẫn mã nguồn.

## 1. Ràng buộc gốc: model giọng nhận được gì

`VieNeuEngine.stream()` gọi `sdk.infer_stream(text, voice, temperature, top_k, top_p,
max_chars, repetition_penalty)`. **Không có núm cao độ, không SSML, không thẻ ngắt.**
Tốc độ do `TimeStretcher` xử lý SAU khi tổng hợp (giữ nguyên cao độ).

⇒ Mọi thứ gọi là "ngữ điệu" chỉ đến được từ ba đường: **chữ đưa vào**, **cách gom câu**,
và **tham số lấy mẫu**. Đề xuất nào hứa "chỉnh cao độ" là hứa sai.

## 2. Những gì đã có (đừng dựng lại)

- Tách câu tiếng Việt có xử lý viết tắt (`ts`, `gs`, `tp`, `mr`…), ranh giới mệnh đề theo
  dấu hai chấm và gạch ngang, có chặn "1975—1980" và "10:30".
- Nghỉ theo VAI TRÒ của khối: tiêu đề 700/800ms · đoạn 450 · gạch đầu dòng 300 · trích dẫn
  550 · chương 1200. Nghỉ giữa hai câu trong cùng đoạn 100ms.
- `speakable_text`: hạ chữ hét, bỏ ký tự đầu dòng (một probe từng đọc "•" mất bốn giây),
  thêm dấu chấm cho tiêu đề không có dấu kết.
- Khoảng lặng là số 0 thật, co giãn theo tốc độ bằng số học nên không méo.
- Bộ nhớ đệm âm thanh khoá theo giá trị nghỉ (`READING_REVISION`) - sửa nghỉ là tự vô hiệu
  đúng phần bị ảnh hưởng.

Nói cách khác: phần "ngắt nghỉ theo cấu trúc" đã khá tốt. Chỗ còn ngang nằm ở nơi khác.

## 3. Sáu phát hiện

**F1 - Số thứ tự hình đã tính rồi nhưng không ra khỏi engine.**
`FigureRef` có sẵn `number: int` và `alt_is_generic: bool`. `book.open` chỉ chép **4 trong 11
trường** (`id`, `anchor_segment_id`, `placement`, `alt`). Vỏ mới vì thế không thể nói "Hình 3",
cũng không phân biệt được chú thích thật với alt rác kiểu "image1.png".

**F2 - Người nghe không hề biết có hình.** Không có tín hiệu nào khi lượt đọc đi qua một hình.
Chú thích thì CÓ được đọc (figcaption → kind `caption`), nên người nghe nhận một câu chú thích
lơ lửng không biết thuộc về cái gì.

**F3 - Mỗi câu được tổng hợp RIÊNG LẺ** (`for sentence in sentences: engine.stream(sentence)`).
Model tự hồi quy nên mỗi lần gọi là bắt đầu lại đường ngữ điệu từ mốc trung tính: không có
đường đi xuống dần trong đoạn, câu nào cũng mở và đóng ở cùng một cao độ. **Đây là nguyên nhân
cấu trúc của "giọng ngang"**, không phải do thiếu núm chỉnh.

**F4 - Mảnh cắt giữa câu không có dấu kết.** Khi một câu dài quá 240 ký tự, `split_paragraph`
cắt ở mệnh đề hoặc khoảng trắng. Mảnh đó vào model **không có dấu chấm** (chỉ tiêu đề mới được
thêm), nên model không có tín hiệu đóng câu - đây là ca nghe phẳng nhất.

**F5 - Một bộ tham số cho mọi loại chữ.** temperature 0.8 / top_k 25 / top_p 0.95 dùng chung
cho tiêu đề, thân bài, trích dẫn, chú thích. Núm biểu cảm DUY NHẤT model có thì không ai vặn.

**F6 - Không có cách nào phán xử.** Mọi thay đổi ngữ điệu đều phải nghe mới biết, mà chưa có
bộ so sánh A/B trên cùng một đoạn ⇒ chỉnh là đoán.

## 4. Đề xuất, xếp theo thứ tự nên làm

| # | Việc | Vì sao trước/sau | Rủi ro |
|---|---|---|---|
| **P0** | **Bộ probe ngữ điệu**: render cùng một đoạn ra N file .wav theo N biến thể để chủ nghe một lần rồi chốt | Không có nó thì P3-P6 là đoán mò; có nó thì mỗi thay đổi thành một câu hỏi trả lời được | Thấp |
| **P1** | Mang `number` + `alt_is_generic` qua giao thức | 4 dòng; mở khoá "Hình 3" cho cả mắt lẫn tai; alt rác thì ẩn thay vì đọc lên | Rất thấp |
| **P2** | **Nhắc hình**: tới chỗ hình thì đọc "Hình 3." + một nhịp nghỉ riêng, đồng thời bắn sự kiện để giao diện cuộn tới và nháy sáng | Đúng bài chủ đặt; dùng lại hạ tầng vị trí sẵn có | Thấp - **cần chủ chốt cách xưng và có luôn nhắc hay chỉ nhắc hình có chú thích thật** |
| **P3** | **Gom câu ngắn liền nhau vào một lượt tổng hợp** (~150-180 ký tự) thay vì mỗi câu một lượt | Đòn bẩy lớn nhất cho "không ngang": cho model một quãng đủ dài để có đường ngữ điệu | Trung bình - lượt dài hơn thì audio đầu tiên ra chậm hơn; đã có lookahead đỡ |
| **P4** | Bảo đảm mảnh nào cũng có dấu kết (F4), hoặc chỉ cắt ở ranh giới câu | Sửa đúng ca nghe phẳng nhất | Trung bình - cần P0 xác nhận model chịu được câu dài |
| **P5** | Tham số lấy mẫu theo vai trò (tiêu đề chắc hơn, thân bài biến thiên hơn) | Vặn đúng núm model thật sự có | Trung bình - chỉ làm sau khi P0 chứng minh nghe ra khác biệt |
| **P6** | Probe cách model đọc số, viết tắt, phần trăm ("1975", "TP.HCM", "30%") | Nếu sai thì cần lớp chuẩn hoá; nếu đúng thì khỏi đụng | Thấp (chỉ là khảo sát) |

## 5. Không đề xuất, và vì sao

- **Chỉnh cao độ / SSML**: SDK không nhận. Bất kỳ đề xuất nào theo hướng này là bịa.
- **Đổi model giọng**: ngoài phạm vi, và người dùng đã chọn chất lượng qua panel Chất lượng.
- **Nghỉ dài hơn cho "tự nhiên"**: phần nghỉ theo cấu trúc đã đo đạc kỹ; kéo dài thêm chỉ làm
  chậm chứ không hết ngang - cái ngang nằm ở F3/F4.

## 6. Kết quả P0 - probe ngữ điệu (2026-09-02)

`scripts/probe-prosody.py --render` dựng **cùng một đoạn 6 câu** qua **model thật** (Minh Đức,
fp32) theo ba cách gom câu; mọi thứ khác giữ nguyên. Nghe ở `output/prosody-probe/`.

**Thước đo được kiểm định TRƯỚC khi đem đo giọng** (đây là điều kiện để các con số dưới có
nghĩa): đơn âm phẳng 200Hz → đo ra 200.0Hz, biên độ 0.00 nửa cung, độ trôi 0.000; tín hiệu quét
150→250Hz → biên độ 6.78, độ trôi +11.7. Đúng chiều ở cả hai ca.

| Biến thể | Lượt gọi model | Biên độ cao độ (nửa cung) | Độ trôi (nửa cung/100 khung) | Audio đầu tiên |
|---|---:|---:|---:|---:|
| a - mỗi câu một lượt (**hiện tại**) | 6 | 10.68 | **-0.26** | 0.29s |
| b - gom tới 180 ký tự | 3 | **12.87** | **-1.84** | 0.08s |
| c - gom tới 240 ký tự | 2 | 12.13 | -0.41 | 0.10s |

**Đọc số này thế nào**

- **Biên độ** = giọng đi lên xuống bao nhiêu. Gom câu làm nó tăng ~20% (10.68 → 12.87).
- **Độ trôi** = có đường đi xuống dần qua cả đoạn hay không - thứ tai nghe ra là "một mạch văn"
  thay vì "sáu câu rời". Bản hiện tại gần như KHÔNG có (-0.26); gom tới 180 có rõ rệt (-1.84,
  gấp bảy lần). Đây chính là F3 hiện ra thành số: mỗi lượt gọi là một lần model đặt lại đường
  ngữ điệu.
- **Độ trễ: không thấy bị phạt, nhưng ĐỪNG đọc con số tuyệt đối.** Ba số 0.29 / 0.08 / 0.10
  giây bị nhiễu hai lần: biến thể `a` chạy ĐẦU nên gánh phần khởi động mà hai bản sau không
  phải gánh, và cả ba đo dưới **load 21.7**. Kết luận an toàn duy nhất: ở n=1 không thấy dấu
  hiệu gom câu làm chậm audio đầu tiên. (Đề xuất ban đầu đoán "gom thì chờ lâu hơn" — probe
  KHÔNG xác nhận, nhưng cũng chưa đủ sạch để bác. Muốn chắc thì chạy lại với thứ tự biến thể
  đảo ngược, trên máy rảnh.)
- **c không tốt hơn b**: gom tới trần 240 lại ít trôi hơn gom 180. Chưa giải thích được -
  n=1 đoạn, 1 giọng. Đừng suy ra "càng dài càng tốt".

**Thước đo này KHÔNG quyết được gì**

- Nó đo giọng có CHUYỂN ĐỘNG hay không, không đo chuyển động ấy có ĐÚNG CHỖ và DỄ NGHE hay
  không. Một giọng lên xuống loạn xạ cũng cho biên độ cao. Quyết định cuối là tai chủ.
- **Tiếng Việt có thanh điệu**, nên phần lớn 10-12 nửa cung kia là do thanh của TỪ, không phải
  ngữ điệu của CÂU. Con số tuyệt đối vì thế vô nghĩa; chỉ có phần CHÊNH giữa ba biến thể là
  đọc được, và nó đọc được chính vì cả ba dùng đúng một đoạn văn, một giọng, một bộ tham số.
- Độ trôi hiện tính bằng MỘT đường hồi quy trên cả bản ghép, nên trộn lẫn "đi xuống trong một
  nhóm" với "đặt lại giữa hai nhóm". Muốn sạch hơn thì tính độ trôi từng nhóm rồi lấy trung
  bình - để dành, chưa cần cho quyết định này.

**Khuyến nghị**: nghe a và b liền nhau. Nếu b nghe liền mạch hơn thì P3 (gom câu ~180 ký tự
trong `_speak`) là thay đổi một chỗ, có số đo hậu thuẫn và không tốn độ trễ. Chạy lại probe
bất cứ lúc nào bằng `python3 scripts/probe-prosody.py --render`.

## 7. Ký hiệu liệt kê "(a)(b)(c)" - phân tích, phản biện, A/B (2026-09-02)

Chủ hỏi: bỏ chữ cái hay đọc kèm nghỉ? Đo trước: model ĐANG đọc thành tiếng mỗi ký hiệu (~0,5s).
Đề xuất đầu là **xoá** (giữ trên trang). Tự phản biện: thiên kiến tiền lệ (khớp với luật bỏ
ký tự đầu dòng) + thiên kiến trôi chảy; **mâu thuẫn** với "#1 → thứ nhất" vừa được duyệt (một thứ
in ra thì chuyển, một thứ thì xoá); thua ở hai tiêu chí cốt lõi của người nghe (cảm nhận cấu
trúc, tham chiếu về sau). Bằng chứng thư viện: 31 ký hiệu, **31/31 liệt kê mở cụm từ, 0 tham
chiếu**. Kết luận: **CHANGED → không xoá, chuyển thành ký hiệu nói được**; hình thức ("một là /
hai là" hay "a, … b, …") là biến chưa đo → render 4 wav từ chính câu trong ảnh của chủ
(`output/prosody-probe/enumerators/`: hiện tại 8,56s · xoá 7,68s · một-là 8,32s · chữ-cái 8,24s)
cho tai chủ chốt. Sẽ lật lại "xoá" nếu cả hai dạng nói đều nặng hơn im lặng trong văn dày.
**Chủ chốt (02/09): "3-chu-cai-nghi"** → `speak_enumerators`; test chốt so khớp từng ký tự với văn bản của bản render đã nghe.

## 8. Quét "rác" trong lời đọc trên thư viện thật (2026-09-02)

3 sách · 6.722 đoạn, qua giao thức engine đã cài. Chỉ một lớp vừa rõ vừa an toàn: **siêu chỉ số
chú thích (6)** → bỏ khỏi lời nói (`drop_note_marks`), trang giữ. Các lớp khác: tiền văn
(URL/ISBN/©, 29) không sửa - người đọc vào thẳng chương; tiêu đề số "01…100" (203) và lời dẫn
`[…]` (12) là nội dung, chờ tai. Nguyên tắc rút ra: sửa lời nói theo BẰNG CHỨNG đếm được trong
thư viện của chủ, không theo danh sách rác tưởng tượng (`[N]` 0 ca → không viết luật).

