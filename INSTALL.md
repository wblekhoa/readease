# Cài đặt ReadEase — Thư Âm

Hướng dẫn này dành cho người muốn cài ReadEase từ mã nguồn trên máy Mac mà không cần biết lập trình.

> **English installation guide:** [INSTALL.en.md](INSTALL.en.md)

## Trước khi bắt đầu

ReadEase hiện được chia sẻ dưới dạng **source build**. File cài chưa được ký bằng Apple Developer ID và chưa được Apple notarize, nên macOS có thể chặn `Install ReadEase.command` ở lần mở đầu tiên. Đây là cơ chế Gatekeeper của macOS, không phải thông báo app bị crash.

Chỉ tiếp tục nếu bạn tải source từ repository chính thức:

- Repository: <https://github.com/wblekhoa/readease>
- Tải trực tiếp: <https://github.com/wblekhoa/readease/archive/refs/heads/main.zip>

## Yêu cầu hệ thống

| Yêu cầu | Chi tiết |
| --- | --- |
| Máy Mac | Apple Silicon: M1, M2, M3, M4 hoặc mới hơn |
| macOS | macOS 15 trở lên |
| Dung lượng trống | Tối thiểu 6 GB trong lúc build và cài đặt |
| Kết nối mạng | Cần cho lần build đầu và lần tải giọng đọc đầu tiên |
| Công cụ của Apple | Xcode Command Line Tools |

Bạn không cần API key, Homebrew, Python hoặc `uv`. Installer tự chuẩn bị môi trường build đã khóa phiên bản và checksum, không dùng `sudo`, không sửa shell profile và dọn môi trường tạm sau khi cài thành công.

## Cài đặt từng bước

### Bước 1 — Tải source

Bấm [**Tải ReadEase — Source ZIP**](https://github.com/wblekhoa/readease/archive/refs/heads/main.zip). Mở file ZIP vừa tải để giải nén thành thư mục `readease-main`.

### Bước 2 — Mở installer

Trong thư mục `readease-main`, bấm đúp **Install ReadEase.command**.

Nếu cửa sổ Terminal mở và installer bắt đầu kiểm tra máy, chuyển tới [Bước 4](#bước-4--cài-công-cụ-của-apple-nếu-còn-thiếu).

### Bước 3 — Nếu macOS báo “Not Opened”

Bạn có thể thấy thông báo:

> “Install ReadEase.command” Not Opened
>
> Apple could not verify “Install ReadEase.command” is free of malware…

Làm theo đúng thứ tự sau:

1. Bấm **Done**. **Không bấm Move to Trash**.
2. Mở **System Settings**.
3. Chọn **Privacy & Security** (**Quyền riêng tư & Bảo mật**).
4. Kéo xuống phần **Security**. Tìm thông báo `Install ReadEase.command was blocked…`.
5. Bấm **Open Anyway** (**Vẫn mở**).
6. Xác nhận bằng Touch ID hoặc mật khẩu đăng nhập Mac.
7. Khi cảnh báo xuất hiện lại, bấm **Open**.

`Open Anyway` thường chỉ xuất hiện trong khoảng một giờ sau lần macOS chặn file. Nếu chưa thấy nút này, thử bấm đúp `Install ReadEase.command` thêm một lần rồi quay lại **Privacy & Security**.

Nếu bạn đã bấm **Move to Trash**, hãy khôi phục file/thư mục từ Trash hoặc tải ZIP lại từ repository chính thức rồi làm lại các bước trên.

Apple mô tả cùng quy trình tại [Open a Mac app from an unknown developer](https://support.apple.com/guide/mac-help/mh40616/mac). Chỉ dùng **Open Anyway** cho source bạn tin tưởng; thao tác này tạo ngoại lệ cho đúng file, không yêu cầu tắt Gatekeeper toàn hệ thống.

### Bước 4 — Cài công cụ của Apple nếu còn thiếu

Nếu installer báo `missing_xcode_tools`, mở Terminal và chạy:

```bash
xcode-select --install
```

Hoàn tất cửa sổ cài đặt của Apple, sau đó bấm lại **Install ReadEase.command**. Bạn không cần cài toàn bộ ứng dụng Xcode.

### Bước 5 — Chờ app được build và cài

Lần đầu thường mất khoảng 10–25 phút. Installer sẽ:

1. Kiểm tra kiến trúc máy, phiên bản macOS, dung lượng và công cụ build.
2. Tải công cụ build đã khóa checksum nếu máy chưa có bản phù hợp.
3. Build và kiểm tra ReadEase ngay trên máy của bạn.
4. Cài app vào `~/Applications/ReadEase.app`.
5. Tự mở ReadEase khi hoàn tất.

Đừng đóng cửa sổ Terminal trong lúc cài. Khi thành công, cửa sổ sẽ hiện:

```text
READEASE_SOURCE_INSTALL PASS target=.../Applications/ReadEase.app
```

### Bước 6 — Chuẩn bị giọng đọc

Trong ReadEase, bấm **Chuẩn bị giọng đọc**. App tải khoảng 330 MB dữ liệu giọng ở lần đầu. Sau khi hoàn tất, việc đọc diễn ra cục bộ và có thể dùng offline.

## Kiểm tra máy mà chưa cài

Mở Terminal tại thư mục `readease-main` và chạy:

```bash
./Install\ ReadEase.command --check
```

Kết quả tương thích sẽ chứa:

```text
READEASE_PREFLIGHT PASS
```

## Nhờ AI cài giúp

Mở thư mục `readease-main` trong công cụ AI có quyền chạy Terminal và gửi:

> Hãy chạy `./Install ReadEase.command`, sửa lỗi cài đặt nếu có, rồi xác nhận `~/Applications/ReadEase.app` đã mở được. Không publish hay thay dependency.

## Xử lý lỗi thường gặp

### Không thấy Open Anyway

- Bấm đúp installer để macOS ghi nhận lần chặn mới.
- Ngay sau đó mở **System Settings → Privacy & Security** và kéo xuống phần **Security**.
- Nút có thể bị ẩn sau khoảng một giờ hoặc không khả dụng trên máy do công ty/trường học quản lý. Với máy được quản lý, hãy liên hệ quản trị viên.

### `Permission denied`

Mở Terminal tại thư mục source và chạy:

```bash
chmod u+x "Install ReadEase.command"
./Install\ ReadEase.command
```

Lệnh này chỉ khôi phục quyền chạy cho installer; nó không tắt Gatekeeper.

### `unsupported_arch`

Máy đang dùng Intel. Bản ReadEase hiện tại chỉ hỗ trợ Apple Silicon.

### `unsupported_macos`

Cập nhật lên macOS 15 trở lên rồi thử lại.

### `insufficient_disk`

Giải phóng để có ít nhất 6 GB trống rồi chạy lại installer.

### Cài đặt dừng giữa chừng

Giữ nguyên toàn bộ nội dung cửa sổ Terminal và gửi cho người hỗ trợ hoặc trợ lý AI. Khi cài thất bại, installer in đường dẫn `READEASE_BUILD_PRESERVED` để giữ môi trường chẩn đoán; khi cài thành công, môi trường tạm được dọn tự động.

## Tại sao không thể bỏ hoàn toàn cảnh báo này ngay?

Để tất cả người dùng có thể mở app theo cách thông thường mà không cần **Open Anyway**, bản phát hành phải được ký bằng chứng chỉ Apple Developer ID, bật hardened runtime, gửi Apple notarize và đóng gói thành artifact phát hành. Bản source build hiện tại chỉ được ký ad-hoc trên máy người dùng, nên hướng dẫn Gatekeeper ở trên vẫn cần thiết.

---

<a id="english"></a>

# Install ReadEase

ReadEase is currently distributed as a local **source build**, not a Developer ID-signed and Apple-notarized binary. macOS Gatekeeper may therefore block `Install ReadEase.command` the first time you open it.

Only proceed with source downloaded from:

- Repository: <https://github.com/wblekhoa/readease>
- Direct ZIP: <https://github.com/wblekhoa/readease/archive/refs/heads/main.zip>

## Requirements

- Apple Silicon Mac (M1 or newer)
- macOS 15 or newer
- At least 6 GB of free disk space during installation
- Internet access for the first build and first voice-model download
- Xcode Command Line Tools

No API key, Homebrew, Python or `uv` installation is required.

## Installation

1. [Download the source ZIP](https://github.com/wblekhoa/readease/archive/refs/heads/main.zip) and extract `readease-main`.
2. Double-click **Install ReadEase.command**.
3. If macOS shows **“Install ReadEase.command” Not Opened**, click **Done**, not **Move to Trash**.
4. Open **System Settings → Privacy & Security**, scroll to **Security**, and click **Open Anyway** next to the blocked installer message.
5. Authenticate with Touch ID or your Mac password, then click **Open** when prompted again.
6. If the installer reports missing Xcode Command Line Tools, run `xcode-select --install`, finish Apple’s installer and open **Install ReadEase.command** again.
7. Wait about 10–25 minutes. ReadEase will be built, checked, installed at `~/Applications/ReadEase.app` and opened automatically.
8. In ReadEase, click **Chuẩn bị giọng đọc** once to download about 330 MB of voice data.

The **Open Anyway** option is normally available for about one hour after the blocked launch. If it is missing, double-click the installer again and immediately revisit **Privacy & Security**. Apple documents this flow in [Open a Mac app from an unknown developer](https://support.apple.com/guide/mac-help/mh40616/mac).

You can run a compatibility-only check from Terminal:

```bash
./Install\ ReadEase.command --check
```

If installation fails, keep the full Terminal output for support. A successfully installed build cleans its temporary environment automatically; a failed build prints a `READEASE_BUILD_PRESERVED` path for diagnosis.
