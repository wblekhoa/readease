# Cài đặt ReadEase — Thư Âm

Dành cho người muốn cài ReadEase lên máy Mac mà không cần biết lập trình. Không mất phí, không cần tài khoản, không cần API key.

> **English:** [INSTALL.en.md](INSTALL.en.md) · **Giới thiệu app:** [README.md](README.md)

## Máy của bạn cần có gì

| Yêu cầu | Chi tiết |
| --- | --- |
| Máy Mac | Apple Silicon: M1, M2, M3, M4 hoặc mới hơn. Máy Intel chưa được hỗ trợ. |
| macOS | macOS 15 trở lên |
| Dung lượng trống | Khoảng 220 MB cho app, cộng giọng đọc tải một lần: *Tiêu chuẩn* ~330 MB hoặc *Cao nhất* ~625 MB |
| Kết nối mạng | Chỉ cần lúc tải app và lúc chuẩn bị giọng đọc lần đầu. Sau đó đọc offline. |

## Cài đặt từng bước

### Bước 1 — Tải app

Vào trang [**Releases**](https://github.com/wblekhoa/readease/releases/latest) và tải file `ReadEase-<phiên bản>-arm64.dmg`. Bấm đúp để mở — cửa sổ hiện `ReadEase.app` cạnh thư mục Applications, kéo app vào đó. (Cũng có `.zip`: bấm đúp để giải nén rồi kéo `ReadEase.app` vào Applications.)

### Bước 2 — Kéo vào Applications

Kéo `ReadEase.app` vào thư mục **Applications** (hoặc `~/Applications`). Xong. Không cần Terminal, không cần cài thêm gì.

### Bước 3 — Mở lần đầu

Bấm đúp `ReadEase.app` và dùng như mọi app khác. Từ bản 0.1.2, app được ký bằng chứng chỉ Apple Developer ID và đã qua kiểm tra notarize của Apple, nên macOS mở thẳng, không hỏi gì. Máy vẫn kiểm tra chữ ký một lần lúc mở, nên lần đầu có thể chậm vài giây.

> **Bản 0.1.0 hoặc 0.1.1 tải trước ngày 15/09/2026** chưa có chứng chỉ, nên macOS chặn với dòng *"Apple could not verify ReadEase is free of malware"*. Cách gọn nhất là tải bản mới ở trang Releases. Nếu vẫn muốn mở bản cũ: bấm **chuột phải** vào `ReadEase.app` → **Open** → **Open**. Lỡ bấm đúp và thấy nút **Move to Trash** thì bấm **Done**, vào **System Settings → Privacy & Security**, kéo xuống phần **Security** và bấm **Open Anyway**. Thao tác này chỉ tạo ngoại lệ cho đúng app đó.

> Nếu hộp thoại nói app **"is damaged and can't be opened"** thì file tải về bị đổi sau khi tải (trình duyệt hoặc phần mềm diệt virus can thiệp). Xoá và tải lại từ trang Releases chính thức; đừng dùng lệnh `xattr` hay tắt bảo mật.

### Bước 4 — Chuẩn bị giọng đọc

Mở app, bấm **Chuẩn bị giọng đọc**. App tải mô hình giọng tiếng Việt về máy — *Tiêu chuẩn* khoảng 330 MB, hoặc *Cao nhất* khoảng 625 MB nếu bạn chọn ở ô **Chất lượng giọng đọc** ngay phía trên (đọc hay hơn một chút, chậm hơn chừng 11%). App chỉ tải đúng bản bạn chọn. Sau bước này mọi thứ chạy trên máy, không cần mạng.

### Bước 5 (tuỳ chọn) — Quét đọc ở app khác

Muốn bôi đen chữ ở trang web, PDF, Apple Books… rồi nhấn phím tắt để nghe, ReadEase cần quyền **Accessibility** (Trợ năng). Lần đầu dùng tính năng **Quét đọc**, macOS sẽ hỏi; bạn bật cho ReadEase trong **System Settings → Privacy & Security → Accessibility**. Không dùng tính năng này thì không cần cấp quyền.

## Nâng cấp, gỡ, dữ liệu ở đâu

- **Nâng cấp:** từ 0.1.10, app tự báo khi có bản mới (menu ReadEase › *Kiểm tra bản mới…*) và tự cài; hoặc tải bản mới, kéo `ReadEase.app` đè lên bản cũ. Tài liệu, tiến độ, ghi chú và giọng đã tải **không mất** — chúng nằm ngoài app, ở `~/Library/Application Support/VieNeu Reader/`. Nâng cấp từ 0.1.0/0.1.1 lên 0.1.2 thì quyền **Accessibility** phải bật lại một lần (chữ ký app đổi từ ad-hoc sang Developer ID); từ 0.1.2 trở đi quyền giữ nguyên qua các bản.
- **Gỡ:** kéo `ReadEase.app` vào Thùng rác. Muốn xoá cả tài liệu và giọng đã tải thì xoá thêm thư mục ở trên.
- **Chi phí:** không có. Giọng trên máy miễn phí vĩnh viễn. Chỉ khi **bạn tự** nhập khoá OpenAI/ElevenLabs để dùng giọng AI trả phí thì bạn trả cho nhà cung cấp đó, theo giá hiện sẵn trong nút đọc; app không thu gì.

## Lỗi thường gặp

| Bạn thấy | Nghĩa là | Làm gì |
| --- | --- | --- |
| "Apple could not verify…" | Bản cũ (trước 0.1.2) chưa có chứng chỉ | Tải bản mới, hoặc xem ghi chú ở Bước 3 |
| "…is damaged and can't be opened" | File tải về bị đổi sau khi tải | Xoá, tải lại từ Releases |
| App không mở trên máy Intel | Bản này chỉ dựng cho Apple Silicon | Chưa hỗ trợ |
| "Requires macOS 15" | Máy đang chạy macOS cũ hơn | Cập nhật macOS |
| Phím tắt Quét đọc không đọc gì | Chưa cấp quyền Accessibility | Bước 5 |
| Giọng đọc chưa sẵn sàng | Chưa tải mô hình | Bước 4 |

Vẫn kẹt? Mở issue tại <https://github.com/wblekhoa/readease/issues> kèm phiên bản macOS và dòng chữ macOS hiện ra.

## App được kiểm tra thế nào?

Từ 0.1.2, mỗi bản phát hành được ký bằng chứng chỉ Apple Developer ID của tác giả và gửi Apple notarize (Apple quét mã độc rồi cấp vé đính kèm vào app). Bạn tự kiểm được: mở Terminal, gõ `spctl -a -t exec -vv /Applications/ReadEase.app`, dòng trả lời phải có `accepted` và `Notarized Developer ID`. Mã nguồn vẫn công khai để ai cũng tự kiểm tra rằng app không gửi sách của bạn đi đâu.
