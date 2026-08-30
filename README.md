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
| Dung lượng trống | Tối thiểu 6 GB **trong lúc** cài đặt. Cài xong app chỉ chiếm ~324 MB, cộng ~331 MB giọng đọc tải một lần; phần còn lại là môi trường build tạm và bị xoá ngay sau khi cài xong. |
| Kết nối mạng | Cần ở lần cài đầu và lần tải giọng đọc đầu tiên |
| Công cụ của Apple | Xcode Command Line Tools; máy chưa có thì installer tự mở trình cài của Apple giúp bạn |

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

4. Installer liệt kê **trước** mọi thứ nó sẽ cài, thay, đóng và dọn, rồi hỏi **đúng một câu**. Đồng ý xong là nó chạy một mạch, không hỏi thêm gì nữa.
5. Chờ khoảng 10–25 phút. Installer in rõ từng bước (`READEASE_STEP 1/5` → `5/5`), cho biết máy đã có bản ReadEase nào chưa, có bản cũ nào sẽ được gỡ, rồi cài vào `~/Applications/ReadEase.app` và tự mở app.
6. Trong ReadEase, bấm **Chuẩn bị giọng đọc**. App tải khoảng 330 MB dữ liệu giọng ở lần đầu; sau đó bạn có thể đọc offline. Ngay trên nút đó có ô **Chất lượng giọng đọc**. App **chỉ tải bản bạn chọn**, không tải cả hai: *Tiêu chuẩn* (mặc định) tốn khoảng 330 MB tổng cộng, *Cao nhất* khoảng 625 MB và đọc chậm hơn chừng 11%. Đổi bản ở thanh phát khi đang đọc thì app hỏi lại trước, nói rõ cần tải bao nhiêu nếu bản đó chưa có trên máy. Sau khi đổi, app báo bản cũ đang chiếm bao nhiêu và cho xoá bằng một nút.

Muốn kiểm tra máy trước mà chưa cài, mở Terminal tại thư mục source và chạy:

```bash
./Install\ ReadEase.command --check
```

Muốn nhờ AI cài giúp, mở thư mục source trong công cụ AI và gửi câu này:

> Hãy chạy `./Install ReadEase.command`, sửa lỗi cài đặt nếu có, rồi xác nhận `~/Applications/ReadEase.app` đã mở được. Không publish hay thay dependency.

## ReadEase làm được gì?

- **Thư viện:** nhập PDF có lớp văn bản và EPUB, lưu tiến độ và tiếp tục đọc ở lần sau.
- **Trình đọc trong app:** chọn chương, đọc liên tục theo đoạn, đọc riêng phần đang quét chọn và điều chỉnh giọng/tốc độ.
- **Đọc có ngắt nghỉ:** ReadEase ngắt theo cấu trúc văn bản chứ không đọc luông tuồng — nghỉ dài nhất khi sang chương, vừa khi hết đoạn, rồi ngắn dần ở tiêu đề, danh sách, dấu chấm, dấu hai chấm và gạch ngang. Cụm chữ viết hoa toàn bộ (chữ trên biển báo, tiêu đề) được đọc như chữ thường để phát âm đúng, nhưng chữ hiển thị vẫn nguyên như tác giả viết. Khoảng nghỉ co lại khi bạn tăng tốc độ đọc.
- **Hình trong EPUB:** đặt hình có ý nghĩa theo thứ tự đọc, đánh số **Hình 1, Hình 2…** và nhắc “Mời bạn xem Hình …” ở đúng vị trí.
- **Dán nội dung:** dán tối đa 100.000 ký tự; ReadEase giữ ranh giới đoạn văn và tự chia nội dung dài thành các phần vừa nghe.
- **Quét đọc ở mọi ứng dụng:** bôi đen chữ ở bất kỳ đâu — trang web, PDF, thư, ghi chú, Apple Books — rồi nhấn phím tắt đọc (mặc định **Option-Command-R**, đổi được trong màn hình **Quét đọc**) để nghe mà không cần chuyển cửa sổ. Phần được trình quản lý mật khẩu đánh dấu bí mật thì app từ chối đọc.
- **Dừng mà không phải rời chỗ đang đọc:** nhấn lại chính phím tắt đó là dừng. Trong lúc đang đọc, ReadEase cũng hiện một biểu tượng nhỏ trên thanh menu — bấm vào là dừng, và nó biến mất khi đọc xong.
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

### 3. Quét đọc phần đang chọn ở bất kỳ ứng dụng nào

1. Mở màn hình **Quét đọc** trong ReadEase để xem trạng thái phím tắt.
2. Sang ứng dụng bất kỳ — trình duyệt, Preview, Mail, Apple Books — và bôi đen đoạn muốn nghe.
3. Nhấn phím tắt đọc hiển thị trong màn hình **Quét đọc** (mặc định **Option-Command-R**).
4. Ở lần đầu, cho phép ReadEase trong **Cài đặt hệ thống → Quyền riêng tư & Bảo mật → Trợ năng**. Nếu chưa có quyền, bấm **Mở Cài đặt quyền** trong ReadEase để đi thẳng tới đúng mục.

Trong mỗi lần dùng phím tắt, ReadEase giữ bản sao clipboard trong bộ nhớ, gửi lệnh sao chép tới ứng dụng đang ở trước rồi khôi phục từng item/type/byte trước khi đọc. Nếu không xác nhận được việc khôi phục, app dừng trước khi đọc. App không theo dõi màn hình ở chế độ nền. Vì phím tắt dùng được ở mọi ứng dụng, app đọc **đúng thứ bạn đang bôi đen** — nó không phân biệt được đâu là nội dung nhạy cảm; phần nào được đánh dấu bí mật thì bị từ chối, còn lại thì không.

ReadEase **không bao giờ** tự xem clipboard. App chỉ đọc đúng lúc bạn bấm phím tắt, và chỉ đọc phần bạn đang bôi đen lúc đó. Chi tiết trong [`PRIVACY.md`](PRIVACY.md).

### 4. Nghe lại nội dung gần đây

Mở **Lịch sử phiên** trên thanh phát để nghe lại nội dung. Các mục trùng chính xác được gộp; bạn có thể xóa lịch sử ngay, và toàn bộ lịch sử tự mất khi thoát ReadEase.


### 5. Chuyển ghi chú sang bản sách khác

Mục **Chuyển ghi chú** đọc thư viện Apple Books để cho biết ghi chú và đoạn bôi màu nào chuyển được sang bản kia của cùng cuốn sách. Xem trước xong, bấm **Chép sang** là ReadEase chuyển chúng thật. ReadEase chỉ đọc khi bạn mở mục đó, và chỉ ghi khi bạn tự bấm nút — sau khi xem trước đúng cặp sách đó và xác nhận số mục. ReadEase chỉ chép những ghi chú nằm ở chương **giống hệt nhau** giữa hai bản — hai file có thể cùng edition mà nội dung vẫn khác, và chép nhầm thì highlight sẽ rơi sai chỗ; những mục còn lại vẫn hiện trong danh sách nhưng không được chép. Trước khi ghi, app sao lưu dữ liệu Apple Books vào `~/Library/Application Support/VieNeu Reader/AppleBooksBackups/`; app chỉ **thêm** vào cuốn đích, không sửa hay xoá gì, và không đụng tới cuốn nguồn. Phải thoát Apple Books thì mới chép được. Nếu bạn bật iCloud cho Apple Books thì các ghi chú này cũng hiện trên thiết bị khác. Chi tiết trong [`PRIVACY.md`](PRIVACY.md).

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
- Xcode Command Line Tools (the installer opens Apple's own installer for you if they are missing)

You do **not** need an API key, Homebrew, Python or `uv`. Extract the ZIP, open the `readease-main` folder and double-click **Install ReadEase.command**. If Gatekeeper blocks it, follow the **Open Anyway** steps above. The first build usually takes 10–25 minutes and installs the app at `~/Applications/ReadEase.app`. In the app, click **Chuẩn bị giọng đọc** once to download about 330 MB of voice data.

This is a local source build, not a notarized `.dmg` or public binary release.

## Main features

- Import and read text-based PDFs and reflowable EPUBs.
- Pause where the writing does: longest between chapters, then paragraphs, headings, list items, full stops, colons and dashes, instead of running the text together. Words written in capitals for emphasis are spoken as ordinary words so they are pronounced rather than announced, while the page keeps what the author wrote. Pauses shorten as the reading speed rises.
- Preserve local library progress and show meaningful EPUB images in reading order.
- Read pasted text and automatically segment long passages.
- Read selected text from any app with a configurable shortcut (**Option-Command-R** by default) after granting Accessibility permission.
- Stop without leaving what you are reading: press the same shortcut again, or click the menu bar item that appears while a reading is under way.
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
