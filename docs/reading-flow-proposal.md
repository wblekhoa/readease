# Flow nghe sách - nghiên cứu và đề xuất hoàn thiện (2026-09-02)

Mục tiêu sản phẩm: **nghe sách tiếng Việt** - người dùng phần lớn thời gian KHÔNG nhìn màn
hình. Mọi đề xuất dưới đây xét theo hành trình một buổi nghe, và mỗi mục ghi rõ: đã có gì
(kiểm bằng lệnh, không tin doc), còn thiếu gì, đề xuất gì, và cần chủ quyết gì.

Cách các app nghe-sách tốt xử lý (Apple Books đọc-to, Audible, Voice Dream, Speechify - mẫu hình
ổn định nhiều năm, không phải tính năng theo phiên bản): tiếp tục đúng chỗ + lùi một nhịp cho
có ngữ cảnh · phím media và Now Playing để điều khiển không cần mở app · luôn biết đang ở đâu
và còn bao lâu · hẹn giờ ngủ · nội dung phi-văn-xuôi (hình, bảng, chú thích) được BÁO chứ
không đọc bừa hay lặng lẽ bỏ qua.

## Hành trình một buổi nghe, đối chiếu với hiện trạng

### A. Mở sách và tiếp tục
- **Đã có**: nhớ vị trí theo segment (`save_progress`), mở lại đúng chỗ; "Đang đọc dở" ở thư viện.
- **Thiếu**: (1) tiếp tục sau tạm dừng/mở lại là nhảy THẲNG vào giữa câu - tai mất ngữ cảnh;
  (2) không biết đang ở đâu trong sách và còn bao lâu.
- **Đề xuất**:
  - *Lùi một câu khi tiếp tục*: resume sau pause hoặc mở lại sách thì bắt đầu từ ĐẦU câu hiện
    tại (hoặc câu trước đó nếu đã nghe >80% câu). Mẫu hình chuẩn của audiobook; rẻ vì engine đã
    tách câu sẵn.
  - *Một dòng định vị* trong header màn đọc: "Chương 3 · 41% · còn ~52 phút". Thời gian ước từ
    số ký tự còn lại ÷ tốc độ đọc thực đo (ký tự/phút của giọng đang dùng, nhân tốc độ). Đo
    được từ chính lượt đọc đang chạy nên tự chỉnh dần, không cần hằng số.
- **Giá trị/công**: cao/thấp. **Quyết định**: không cần.

### B. Điều khiển khi đang nghe
- **Đã có**: Đọc/Tạm dừng/Dừng/Trước/Sau (icon) · Space · phím tắt toàn cục ⌥⌘R · menu bar
  một-click-dừng · huỷ-rồi-đọc không xếp hàng (đã đo).
- **Thiếu**: **phím media** (F8 / AirPods / bàn phím ngoài) và **Now Playing** - đây là kỳ vọng
  mặc định của MỌI app phát tiếng trên Mac; hiện bấm tai nghe không có tác dụng. Trước/Sau chỉ
  nhảy theo ĐOẠN, không nhảy chương bằng phím.
- **Đề xuất**: nhận phím media qua `MPRemoteCommandCenter` + đăng ký `MPNowPlayingInfoCenter`
  (tên sách, chương, tiến độ) - làm bằng cầu ObjC như cầu chọn-văn-bản đã có, build.rs biên
  dịch sẵn. Bàn phím: ←/→ = đoạn, ⌥←/→ = chương.
- **Giá trị/công**: **cao nhất** về cảm giác "app thật"/trung bình. **Quyết định**: không cần.

### C. Nội dung không phải văn xuôi
- **Đã có**: nghỉ theo vai trò khối (tiêu đề/đoạn/gạch đầu dòng/trích dẫn/chú thích), hạ chữ
  hét, bỏ ký tự đầu dòng, tiêu đề được thêm dấu chấm; chú thích ảnh ĐƯỢC đọc.
- **Thiếu**:
  1. **Hình không được báo** khi giọng đi qua (P2 - chủ đã nêu). Engine đã tính `number` +
     `alt_is_generic` nhưng không gửi qua giao thức; alt rác "Image" đang hiển thị.
  2. **Bảng**: importer không có nhánh nào cho `<table>` (grep = 0) ⇒ bảng lặng lẽ biến mất
     hoặc thành chuỗi ô dính nhau.
  3. **Chú thích cuối trang / số tham chiếu**: không có xử lý ⇒ "…như Krug đã nói1." đọc thành
     "nói một".
  4. **URL** đọc từng ký tự; **số trang** rác của EPUB chuyển từ PDF.
- **Đề xuất**:
  - P2 *Báo hình*: tới hình thì đọc "Xem hình N." + nghỉ 600ms, phát sự kiện để màn đọc cuộn tới
    và nháy hình; dưới hình hiện "Hình N" thay cho alt rác. (Quyết định: xem §Cần chủ chốt.)
  - *Bảng*: đọc "Bảng N, M cột K hàng." rồi đọc từng hàng theo "tên cột: giá trị" - hoặc chỉ báo
    có bảng và mời xem. Cần xem sách thật có bao nhiêu bảng trước khi chọn.
  - *Tham chiếu chú thích*: nhận diện `epub:type="noteref"` / `<sup>` đứng sát chữ → KHÔNG đọc,
    vẫn hiển thị. Chú thích cuối chương đọc sau chương, có báo "Chú thích 1".
  - *URL*: đọc "đường dẫn" (hoặc tên miền), không đánh vần.
- **Giá trị/công**: P2 cao/thấp · bảng trung bình/trung bình · chú thích cao/trung bình.

### D. Giọng đọc
- **Đã có**: probe đo được (`scripts/probe-prosody.py`), bằng chứng gom câu cho giọng có đường
  đi xuống qua đoạn (độ trôi -0.26 → -1.84), 3 file wav đã giao.
- **Thiếu**: tai chủ chưa phán a hay b.
- **Đề xuất**: P3 gom câu ~180 ký tự nếu chủ chọn b · P4 mảnh cắt phải có dấu kết · P5 tham số
  lấy mẫu theo vai trò (chỉ sau khi có probe A/B).
- **Quyết định**: chủ nghe a/b.

### E. Nghe dài
- **Thiếu**: hẹn giờ ngủ · dừng-cuối-chương · tự hạ tiếng dần trước khi dừng.
- **Đề xuất**: menu "Dừng sau: hết chương / 15 / 30 / 60 phút" ở thanh phát; 10 giây cuối hạ
  tiếng dần (fade) để không cắt phựt khi đang ngủ.
- **Giá trị/công**: trung bình/thấp. **Quyết định**: không cần.

### F. Mắt và tai
- **Đã có**: hai vị trí (scroll-spy theo mắt, `band` theo tai), tự cuộn chỉ khi mắt còn ở đó,
  viên "Về chỗ đang đọc", lightbox ảnh, cỡ chữ 5 nấc.
- **Không đề xuất thêm** ở vòng này.

## Thứ tự nên làm

| # | Việc | Vì sao đứng đây |
|---|---|---|
| 1 | **P2 Báo hình + số hình + ẩn alt rác** | Chủ đã nêu; nửa dữ liệu có sẵn; sách đang đọc có 195 hình |
| 2 | **Phím media + Now Playing** | Kỳ vọng mặc định của app audio; hiện bấm tai nghe = không gì |
| 3 | **Lùi một câu khi tiếp tục + dòng định vị "còn ~N phút"** | Rẻ, cảm nhận rõ mỗi lần nghe |
| 4 | **Chú thích/URL/số trang không đọc bừa** | Chất lượng nghe; cần xem EPUB thật đánh dấu thế nào |
| 5 | Hẹn giờ ngủ + dừng cuối chương | Nghe dài |
| 6 | P3/P4/P5 giọng | Chờ tai chủ |
| 7 | Bảng | Hiếm trong sách đang đọc; làm sau khi đo tần suất |

## Cần chủ chốt (cho mục 1)

1. **Câu báo**: đề nghị **"Xem hình 3."** - ngắn, đúng chữ chủ dùng, giọng đọc dễ.
2. **Đánh số**: đề nghị **theo chương** ("Hình 3" đặt lại mỗi chương). Theo sách thì cuốn 195
   hình sẽ ra "Hình 187" - dài, khó nhớ khi chỉ nghe.
3. **Báo hình nào**: đề nghị **báo tất cả** ở bản đầu. Cuốn đang đọc toàn ảnh nội dung (ảnh
   chụp mà văn bản nhắc tới); lọc "chỉ hình có chú thích thật" sẽ hụt vì chú thích ở sách này là
   đoạn văn rời "Chú giải ảnh: …", không phải `<figcaption>`. Có thể thêm công tắc tắt sau.
4. **Alt rác "Image"**: đề nghị **ẩn** (không hiện, không đọc); có `alt_is_generic` sẵn.

Chủ gật bốn dòng trên là mục 1 làm được ngay, không còn chỗ nào phải đoán.
