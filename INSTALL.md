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

Vào trang [**Releases**](https://github.com/wblekhoa/readease/releases/latest) và tải file `ReadEase-<phiên bản>-arm64.zip`. Bấm đúp file zip để giải nén — bạn có `ReadEase.app`.

### Bước 2 — Kéo vào Applications

Kéo `ReadEase.app` vào thư mục **Applications** (hoặc `~/Applications`). Xong. Không cần Terminal, không cần cài thêm gì.

### Bước 3 — Mở lần đầu: qua cảnh báo của macOS

Bản này **không mua chứng chỉ Apple Developer** và không notarize, nên lần mở đầu tiên macOS sẽ chặn với dòng *"Apple could not verify ReadEase is free of malware"*. Đây là cơ chế Gatekeeper cho app của nhà phát triển chưa đăng ký, không phải app bị lỗi. Chỉ phải làm **một lần**.

**Cách nhanh:** bấm **chuột phải** (hoặc Control-click) vào `ReadEase.app` → chọn **Open** → trong hộp thoại bấm **Open** lần nữa.

**Nếu bạn lỡ bấm đúp** và thấy hộp thoại có nút **Move to Trash**:

1. Bấm **Done**. **Không bấm Move to Trash.**
2. Mở **System Settings** → **Privacy & Security**.
3. Kéo xuống phần **Security**, tìm dòng *"ReadEase" was blocked…*
4. Bấm **Open Anyway**, xác nhận bằng Touch ID hoặc mật khẩu đăng nhập Mac.
5. Mở lại app; khi hỏi lần nữa, bấm **Open**.

Nút **Open Anyway** chỉ hiện trong khoảng một giờ sau lần bị chặn. Không thấy thì bấm đúp app thêm một lần rồi quay lại **Privacy & Security**. Apple mô tả cùng quy trình tại [Open a Mac app from an unknown developer](https://support.apple.com/guide/mac-help/mh40616/mac). Thao tác này chỉ tạo ngoại lệ cho đúng app này, không tắt Gatekeeper toàn hệ thống.

> Nếu hộp thoại nói app **"is damaged and can't be opened"** thì đó là chuyện khác: file zip bị đổi sau khi tải (trình duyệt hoặc phần mềm diệt virus can thiệp). Xoá và tải lại từ trang Releases chính thức; đừng dùng lệnh `xattr` hay tắt bảo mật.

### Bước 4 — Chuẩn bị giọng đọc

Mở app, bấm **Chuẩn bị giọng đọc**. App tải mô hình giọng tiếng Việt về máy — *Tiêu chuẩn* khoảng 330 MB, hoặc *Cao nhất* khoảng 625 MB nếu bạn chọn ở ô **Chất lượng giọng đọc** ngay phía trên (đọc hay hơn một chút, chậm hơn chừng 11%). App chỉ tải đúng bản bạn chọn. Sau bước này mọi thứ chạy trên máy, không cần mạng.

### Bước 5 (tuỳ chọn) — Quét đọc ở app khác

Muốn bôi đen chữ ở trang web, PDF, Apple Books… rồi nhấn phím tắt để nghe, ReadEase cần quyền **Accessibility** (Trợ năng). Lần đầu dùng tính năng **Quét đọc**, macOS sẽ hỏi; bạn bật cho ReadEase trong **System Settings → Privacy & Security → Accessibility**. Không dùng tính năng này thì không cần cấp quyền.

## Nâng cấp, gỡ, dữ liệu ở đâu

- **Nâng cấp:** tải zip mới, kéo `ReadEase.app` đè lên bản cũ. Sách, tiến độ, ghi chú và giọng đã tải **không mất** — chúng nằm ngoài app, ở `~/Library/Application Support/VieNeu Reader/`.
- **Gỡ:** kéo `ReadEase.app` vào Thùng rác. Muốn xoá cả sách và giọng đã tải thì xoá thêm thư mục ở trên.
- **Chi phí:** không có. Giọng trên máy miễn phí vĩnh viễn. Chỉ khi **bạn tự** nhập khoá OpenAI/ElevenLabs để dùng giọng AI trả phí thì bạn trả cho nhà cung cấp đó, theo giá hiện sẵn trong nút đọc; app không thu gì.

## Lỗi thường gặp

| Bạn thấy | Nghĩa là | Làm gì |
| --- | --- | --- |
| "Apple could not verify…" | Gatekeeper, app chưa đăng ký với Apple | Bước 3 ở trên |
| "…is damaged and can't be opened" | File zip bị đổi sau khi tải | Xoá, tải lại từ Releases |
| App không mở trên máy Intel | Bản này chỉ dựng cho Apple Silicon | Chưa hỗ trợ |
| "Requires macOS 15" | Máy đang chạy macOS cũ hơn | Cập nhật macOS |
| Phím tắt Quét đọc không đọc gì | Chưa cấp quyền Accessibility | Bước 5 |
| Giọng đọc chưa sẵn sàng | Chưa tải mô hình | Bước 4 |

Vẫn kẹt? Mở issue tại <https://github.com/wblekhoa/readease/issues> kèm phiên bản macOS và dòng chữ macOS hiện ra.

## Tại sao có cảnh báo lần đầu?

Để app mở như mọi app khác mà không cần bước Open Anyway, bản phát hành phải được ký bằng chứng chỉ Apple Developer ID và gửi Apple notarize. ReadEase là dự án cá nhân, miễn phí, chưa làm việc đó; đổi lại bạn có toàn bộ mã nguồn để tự kiểm tra rằng app không gửi sách của bạn đi đâu.
