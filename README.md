# ReadEase — Thư Âm

Ứng dụng macOS đọc PDF, EPUB và văn bản tiếng Việt bằng **VieNeu-TTS chạy cục bộ**. ReadEase không cần API key, không gửi nội dung sách lên máy chủ và có thể đọc offline sau khi chuẩn bị giọng lần đầu.

> **English documentation:** [README.en.md](README.en.md)

## Tải và cài ngay

### [⬇️ Tải ReadEase — Source ZIP](https://github.com/wblekhoa/readease/archive/refs/heads/main.zip)

Liên kết trên tải trực tiếp bản mới nhất từ nhánh `main`. Đây là bản cài từ mã nguồn dành cho Mac, chưa phải file `.dmg` hoặc binary đã notarize.

> [!IMPORTANT]
> macOS có thể báo **“Install ReadEase.command” Not Opened** vì bản source chưa được Apple notarize. Hãy bấm **Done** — không bấm **Move to Trash** — rồi mở **System Settings → Privacy & Security → Security → Open Anyway**. Xem [hướng dẫn cài đặt đầy đủ](INSTALL.md), gồm ảnh hưởng của Gatekeeper và cách xử lý lỗi.

### Máy của bạn cần có gì?

| Yêu cầu | Chi tiết |
| --- | --- |
| Máy Mac | Apple Silicon: M1, M2, M3, M4 hoặc mới hơn |
| macOS | macOS 15 trở lên |
| Dung lượng trống | Tối thiểu 6 GB trong lúc cài đặt |
| Kết nối mạng | Cần ở lần cài đầu và lần tải giọng đọc đầu tiên |
| Công cụ của Apple | Xcode Command Line Tools; installer sẽ báo nếu máy còn thiếu |

Bạn **không cần** API key, Homebrew, Python, `uv` hay kiến thức lập trình. Installer tự tải môi trường build đã khóa phiên bản và checksum, sau đó dọn môi trường tạm khi cài thành công.

### Cách cài đơn giản

Có hai cách. **Cách A không bao giờ bị macOS chặn** vì nguồn lấy bằng `git` không bị gắn cờ kiểm dịch — nên hãy dùng cách này nếu bạn mở được Terminal.

#### Cách A — dùng Terminal (khuyên dùng, không bị chặn)

Mở **Terminal**, dán nguyên khối lệnh sau rồi nhấn Enter:

```bash
git clone https://github.com/wblekhoa/readease.git ~/Downloads/readease && "$HOME/Downloads/readease/Install ReadEase.command"
```

Nếu máy chưa có công cụ của Apple, macOS sẽ tự hiện cửa sổ cài **Command Line Tools** — hoàn tất rồi chạy lại lệnh trên.

#### Cách B — tải ZIP và bấm đúp

1. Bấm [**Tải ReadEase — Source ZIP**](https://github.com/wblekhoa/readease/archive/refs/heads/main.zip), rồi mở file ZIP vừa tải.
2. Trong thư mục `readease-main`, bấm đúp **Install ReadEase.command**.
3. macOS **sẽ chặn lần mở đầu tiên** — đây là điều bình thường với bản chưa notarize. Bấm **Done** (không bấm **Move to Trash**), rồi vào **System Settings → Privacy & Security → Security → Open Anyway**. Chi tiết ở [INSTALL.md](INSTALL.md).

   Muốn bỏ qua bước này, mở Terminal và gỡ cờ kiểm dịch cho thư mục vừa giải nén:

   ```bash
   xattr -d com.apple.quarantine ~/Downloads/readease-main
   ```

#### Sau đó, cả hai cách đều giống nhau

4. Nếu installer báo thiếu công cụ của Apple, mở Terminal, chạy `xcode-select --install`, hoàn tất rồi chạy lại.
5. Chờ khoảng 10–25 phút. Installer in rõ từng bước (`READEASE_STEP 1/5` → `5/5`), cho biết máy đã có bản ReadEase nào chưa, có bản cũ nào sẽ được gỡ, rồi cài vào `~/Applications/ReadEase.app` và tự mở app.
6. Trong ReadEase, bấm **Chuẩn bị giọng đọc**. App tải khoảng 330 MB dữ liệu giọng ở lần đầu; sau đó bạn có thể đọc offline.

Muốn kiểm tra máy trước mà chưa cài, mở Terminal tại thư mục source và chạy:

```bash
./Install\ ReadEase.command --check
```

Muốn nhờ AI cài giúp, mở thư mục source trong công cụ AI và gửi câu này:

> Hãy chạy `./Install ReadEase.command`, sửa lỗi cài đặt nếu có, rồi xác nhận `~/Applications/ReadEase.app` đã mở được. Không publish hay thay dependency.

## ReadEase làm được gì?

- **Thư viện:** nhập PDF có lớp văn bản và EPUB, lưu tiến độ và tiếp tục đọc ở lần sau.
- **Trình đọc trong app:** chọn chương, đọc liên tục theo đoạn, đọc riêng phần đang quét chọn và điều chỉnh giọng/tốc độ.
- **Hình trong EPUB:** đặt hình có ý nghĩa theo thứ tự đọc, đánh số **Hình 1, Hình 2…** và nhắc “Mời bạn xem Hình …” ở đúng vị trí.
- **Dán nội dung:** dán tối đa 100.000 ký tự; ReadEase giữ ranh giới đoạn văn và tự chia nội dung dài thành các phần vừa nghe.
- **Đọc từ Apple Books:** quét chọn văn bản rồi nhấn phím tắt đọc (mặc định **Control-Option-Command-R**, đổi được trong màn hình **Đọc sách**) để nghe mà không cần chuyển cửa sổ.
- **Lịch sử phiên:** nghe lại tối đa 10 nội dung gần nhất từ sách, nội dung dán hoặc Apple Books. Lịch sử biến mất khi thoát app.
- **Riêng tư và local-first:** sách, tiến độ, mô hình và cache audio ở trên máy; không có telemetry hay máy chủ nền.
- **Giao diện song ngữ:** chuyển tức thời giữa `🇻🇳 Tiếng Việt` và `🇬🇧 English`; lựa chọn được lưu cho lần mở sau. VieNeu vẫn là mô hình giọng đọc tiếng Việt.

## Cách dùng

### 1. Đọc PDF hoặc EPUB trong Thư viện

1. Mở **ReadEase** trong `~/Applications`.
2. Chọn **Thư viện** → **Mở PDF hoặc EPUB**, hoặc kéo tệp sách vào cửa sổ.
3. Chọn sách và chương, rồi bấm **Đọc** để đọc liên tục.
4. Quét chọn một phần trong trình đọc và bấm **Đọc phần đã chọn** nếu chỉ muốn nghe đoạn đó.
5. Dùng **Trước**, **Sau**, **Dừng**, giọng đọc và tốc độ ở thanh phát phía dưới.

Với EPUB dạng reflowable, ReadEase hiển thị văn bản và ảnh raster cục bộ theo thứ tự đọc. Ảnh trang trí nhỏ được bỏ qua để tránh lời nhắc thừa.

### 2. Đọc nội dung bạn dán

1. Chọn **Dán nội dung**.
2. Dán văn bản, chọn giọng và tốc độ.
3. Bấm **Đọc nội dung**. Với văn bản dài, trạng thái sẽ hiển thị tiến độ như **Đang đọc đoạn 2/7**.

Bản nháp chỉ tồn tại trong phiên hiện tại, không tạo sách mới và không thay đổi tiến độ của sách trong Thư viện.

### 3. Đọc phần đang chọn trong Apple Books

1. Mở màn hình **Đọc sách** trong ReadEase để xem trạng thái phím tắt.
2. Mở Apple Books và quét chọn đoạn muốn nghe.
3. Nhấn phím tắt đọc hiển thị trong màn hình **Đọc sách** (mặc định **Control-Option-Command-R**).
4. Ở lần đầu, cho phép ReadEase trong **Cài đặt hệ thống → Quyền riêng tư & Bảo mật → Trợ năng**. Nếu chưa có quyền, bấm **Mở Cài đặt quyền** trong ReadEase để đi thẳng tới đúng mục.

Trong mỗi lần dùng phím tắt, ReadEase giữ bản sao clipboard trong bộ nhớ, gửi lệnh sao chép tới Apple Books rồi khôi phục từng item/type/byte trước khi đọc. Nếu không xác nhận được việc khôi phục, app dừng trước khi đọc. App không theo dõi màn hình ở chế độ nền.

Mặc định ReadEase cũng **không** xem clipboard: chỉ khi bạn tự bật **Đọc ngay khi sao chép trong Apple Books** trong màn hình **Đọc sách**, app mới kiểm tra bộ đếm thay đổi của clipboard vài lần mỗi giây và đọc nội dung vừa sao chép **khi Apple Books đang ở phía trước**. ReadEase chỉ đọc khi Apple Books ở phía trước ở cả hai lần kiểm tra liên tiếp, và bỏ qua mục được đánh dấu ẩn (trình quản lý mật khẩu dùng dấu này). macOS không ghi lại ứng dụng nào đã sao chép, nên vẫn còn khe hở: sao chép ở app khác rồi chuyển sang Apple Books trong cùng một phần giây thì nội dung đó có thể bị đọc. Tắt công tắc là app ngừng xem clipboard. Chi tiết trong [`PRIVACY.md`](PRIVACY.md).

### 4. Nghe lại nội dung gần đây

Mở **Lịch sử phiên** trên thanh phát để nghe lại nội dung. Các mục trùng chính xác được gộp; bạn có thể xóa lịch sử ngay, và toàn bộ lịch sử tự mất khi thoát ReadEase.

## Dữ liệu và quyền riêng tư

ReadEase lưu sách đã nhập, vị trí đọc, mô hình và audio cache tại:

```text
~/Library/Application Support/VieNeu Reader/
```

Tên thư mục cũ được giữ để người dùng nâng cấp không mất thư viện và tiến độ. Nội dung dán hoặc quét chọn không được thêm vào Thư viện, không ghi log và không lưu audio cache. Lần chuẩn bị mô hình đầu tiên cần mạng; sau đó việc đọc diễn ra cục bộ.

## Giới hạn hiện tại

- PDF scan chỉ chứa ảnh cần OCR trước khi nhập; ReadEase chưa tích hợp OCR.
- Chưa hỗ trợ PDF đặt mật khẩu, EPUB có DRM hoặc tệp bị hỏng.
- Trình đọc EPUB chưa tái tạo toàn bộ CSS/layout của sách, fixed-layout, SVG tương tác, bảng phức tạp hoặc mô tả ảnh bằng AI.
- Phím tắt đọc phần chọn hiện chỉ dành cho Apple Books.
- Bản source này được build và ký ad-hoc trên máy của bạn; chưa phải binary có Developer ID và notarization để phát hành đại trà.

## Chạy local để phát triển

Ngoài các yêu cầu hệ thống ở trên, contributor nên dùng `uv` và Python 3.13 được khóa bởi dự án:

```bash
git clone https://github.com/wblekhoa/readease.git
cd readease
uv sync --locked --managed-python --python 3.13
./scripts/verify.sh
```

`uv.lock` là nguồn sự thật cho dependency. Đừng thêm model weights, sách có bản quyền, audio sinh ra, database, cache hoặc dữ liệu người dùng vào repository. Xem [CONTRIBUTING.md](CONTRIBUTING.md) để biết quy ước đóng góp.

## Khi app không mở được

1. Mở lại app một lần.
2. Nếu lỗi khi chuẩn bị giọng, kiểm tra mạng rồi bấm **Thử lại**.
3. Mở lại cùng tệp nếu quá trình nhập sách bị gián đoạn; app không xóa sách gốc.
4. Nếu vẫn lỗi, giữ báo cáo crash mới nhất trong `~/Library/Logs/DiagnosticReports/` để chẩn đoán.

## Giấy phép

Phần mã nguồn, tài liệu và khung ứng dụng first-party được chia sẻ theo [PolyForm Noncommercial 1.0.0](LICENSE): được dùng, sửa và chia sẻ cho mục đích phi thương mại theo điều khoản giấy phép; không được thương mại hóa ReadEase, bản sửa đổi hoặc sản phẩm dựa trên khung này nếu chưa có giấy phép riêng bằng văn bản từ chủ sở hữu bản quyền áp dụng. Đây là source-available, không phải giấy phép open-source theo định nghĩa OSI.

Model VieNeu, codec MOSS và các dependency giữ giấy phép riêng của nhà cung cấp. Xem [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), thư mục [`legal/`](legal/) và [PRIVACY.md](PRIVACY.md). Mỗi bản source/app mang provenance ID tĩnh `READEASE-THU-AM-NC-2026-01`; marker này không chứa thông tin người dùng, không kết nối mạng và không theo dõi.

---

<a id="english"></a>

# English

ReadEase — Thư Âm is a local-first macOS app that reads PDFs, EPUBs and pasted text with Vietnamese VieNeu-TTS. It requires no API key and can work offline after the first voice-model setup.

## Download and install

### [⬇️ Download ReadEase — Source ZIP](https://github.com/wblekhoa/readease/archive/refs/heads/main.zip)

> [!IMPORTANT]
> Because this source build is not Apple-notarized, macOS may show **“Install ReadEase.command” Not Opened**. Click **Done**, not **Move to Trash**, then go to **System Settings → Privacy & Security → Security → Open Anyway**. See the [full installation guide](INSTALL.md#english).

Requirements:

- Apple Silicon Mac (M1 or newer)
- macOS 15 or newer
- At least 6 GB of free disk space during installation
- Internet access for the first build and first voice-model download
- Xcode Command Line Tools (`xcode-select --install` if the installer reports they are missing)

You do **not** need an API key, Homebrew, Python or `uv`. Extract the ZIP, open the `readease-main` folder and double-click **Install ReadEase.command**. If Gatekeeper blocks it, follow the **Open Anyway** steps above. The first build usually takes 10–25 minutes and installs the app at `~/Applications/ReadEase.app`. In the app, click **Chuẩn bị giọng đọc** once to download about 330 MB of voice data.

This is a local source build, not a notarized `.dmg` or public binary release.

## Main features

- Import and read text-based PDFs and reflowable EPUBs.
- Preserve local library progress and show meaningful EPUB images in reading order.
- Read pasted text and automatically segment long passages.
- Read selected text from Apple Books with a configurable shortcut (**Control-Option-Command-R** by default) after granting Accessibility permission.
- Replay up to 10 recent items during the current session.
- Keep books, model data, progress and audio cache on the Mac; no API key, telemetry or background server.

## Local development

```bash
git clone https://github.com/wblekhoa/readease.git
cd readease
uv sync --locked --managed-python --python 3.13
./scripts/verify.sh
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for development rules. Scanned-image PDFs require OCR; DRM-protected books, password-protected PDFs and complex fixed-layout EPUBs are not supported.

## License

First-party source, documentation and application framework are available under [PolyForm Noncommercial 1.0.0](LICENSE) for permitted noncommercial use. Commercial use requires a separate written license from the applicable copyright owner. VieNeu, MOSS and other dependencies retain their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [`legal/`](legal/).
