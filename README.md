# ReadEase — Thư Âm

ReadEase — Thư Âm là ứng dụng macOS đọc sách tiếng Việt bằng VieNeu-TTS chạy cục
bộ. Ứng dụng mở PDF có lớp văn bản và EPUB, đọc liên tục theo đoạn hoặc chỉ đọc
phần bạn đang quét chọn. Không cần API key và không chạy máy chủ nền.

## Cài từ mã nguồn — cách đơn giản để chia sẻ với bạn bè

Yêu cầu: máy Mac Apple Silicon (M1 trở lên), macOS 15 trở lên, kết nối mạng và
ít nhất 6 GB trống trong lúc cài. Không cần API key.

1. Tải source ZIP từ repository rồi giải nén, hoặc clone repository.
2. Trong thư mục vừa mở, bấm đúp **Install ReadEase.command**. Nếu macOS chặn
   lần đầu, Control-click file, chọn **Open**, rồi xác nhận **Open**.
3. Nếu cửa sổ báo thiếu Xcode Command Line Tools, chạy
   `xcode-select --install`, hoàn tất trình cài của Apple rồi bấm lại file trên.
4. Chờ khoảng 10–25 phút ở lần đầu. Installer tự kiểm tra máy, tải công cụ build
   đã khóa checksum, dựng và kiểm tra app, cài vào
   `~/Applications/ReadEase.app`, rồi mở app. Môi trường build, Python và cache
   tải xuống nằm trong một thư mục tạm và được xóa sau khi app đã cài thành công;
   installer không sửa shell profile và không dùng `sudo`.
5. Trong ReadEase, bấm **Chuẩn bị giọng đọc**. Lần này app tải khoảng 330 MB dữ
   liệu giọng; các lần sau có thể đọc offline.

Muốn nhờ AI làm thay, hãy mở repository trong công cụ AI và gửi đúng câu:

> Hãy chạy `./Install ReadEase.command`, sửa lỗi cài đặt nếu có, rồi xác nhận
> `~/Applications/ReadEase.app` đã mở được. Không publish hay thay dependency.

Có thể kiểm tra tương thích mà chưa build bằng
`./Install\ ReadEase.command --check`. Đây là bản bạn bè tự build cục bộ; không
phải binary đã notarize để phát hành đại trà.

## Cách dùng sau khi cài

1. Mở `ReadEase` trong thư mục Applications.
2. Nếu chưa chuẩn bị giọng đọc ở bước cài đặt, bấm **Chuẩn bị giọng đọc**.
3. Ở màn hình **Thư viện**, bấm **Mở PDF hoặc EPUB** hoặc kéo tệp sách vào
   cửa sổ. Chọn một cuốn sách để mở trình đọc ngay bên trong Thư viện; bấm
   **Quay lại thư viện** để chọn cuốn khác.
4. Ở màn hình **Dán nội dung**, dán tối đa 100.000 ký tự rồi bấm
   **Đọc nội dung**. Bản nháp được giữ khi chuyển qua lại giữa các màn hình,
   nhưng chỉ nằm trong phiên hiện tại và không tạo sách mới.
5. Trong trình đọc của **Thư viện**, chọn chương ở cột trái rồi bấm **Đọc**
   để đọc liên tục. Với EPUB dạng reflowable, ReadEase đặt các hình có ý nghĩa
   đúng theo thứ tự đọc, gắn nhãn **Hình 1, Hình 2…** và nói “Mời bạn xem Hình
   …” khi tới vị trí tương ứng. Ảnh trang trí nhỏ không tạo lời đọc nhiễu.
6. Muốn nghe riêng một phần trong sách đã nhập, quét chọn văn bản rồi bấm
   **Đọc phần đã chọn**.
7. Màn hình **Đọc sách** dành cho Apple Books; màn hình này hiển thị trạng thái
   phím tắt, hướng dẫn, nút mở đúng mục quyền Trợ năng và các phần Apple Books
   đã đọc gần đây trong phiên.
8. Dùng **Trước**, **Sau**, **Dừng**, giọng đọc và tốc độ ở thanh phía dưới.
   Dòng trạng thái cho biết bạn đang ở chương và đoạn thứ bao nhiêu. Khi phần
   được dán hoặc quét chọn dài, ReadEase giữ ranh giới đoạn văn, tự chia thành
   phần vừa đọc và hiển thị tiến độ như **Đang đọc đoạn 2/7**.
9. Muốn nghe lại phần vừa đọc, mở **Lịch sử phiên** trên thanh phát rồi
   chọn nội dung. Menu giữ tối đa 10 mục gần nhất từ **Dán nội dung**,
   phần chọn **Trong sách** và **Apple Books**. Mục được chọn sẽ dùng giọng
   và tốc độ hiện tại; chọn **Xóa lịch sử phiên** nếu muốn xóa ngay. Riêng màn
   hình **Đọc sách** lọc sẵn các mục Apple Books và có nút **Nghe lại phần đã
   chọn** để không phải mở menu chung.

### Đọc phần đang chọn trong Apple Books

1. Mở màn hình **Đọc sách** trong ReadEase để xem hướng dẫn và phím tắt, rồi
   giữ ReadEase đang chạy và mở sách trong Apple Books.
2. Quét chọn đoạn muốn nghe.
3. Nhấn **Control-Option-Command-R**. Ở lần đầu, cho phép ReadEase trong
   **Cài đặt hệ thống > Quyền riêng tư & Bảo mật > Trợ năng** khi macOS hỏi.
   Nếu quyền chưa bật, màn hình **Đọc sách** chuyển sang trạng thái **Cần quyền
   Trợ năng**; bấm **Mở Cài đặt quyền** tại đó để mở thẳng đúng mục này.
4. ReadEase đọc đoạn đã chọn nhưng không đưa cửa sổ app lên trước. Phím tắt chỉ
   nhận Apple Books và không theo dõi màn hình hay clipboard ở chế độ nền.

Trong đúng giao dịch phím tắt, ReadEase giữ bản sao clipboard hiện tại trong
bộ nhớ, gửi Command-C tới Apple Books, rồi khôi phục từng item/type/byte trước
khi chuyển văn bản sang giọng đọc. Nếu không xác nhận được bước khôi phục, app
dừng trước khi đọc. Văn bản chọn không được ghi log, lưu thư viện hay audio
cache. Clipboard manager hoặc Universal Clipboard vẫn có thể nhận thấy lần
sao chép rất ngắn do đây là giới hạn của phương án copy/read/restore.

Vị trí đọc, sách đã nhập, mô hình và audio cache được giữ cục bộ trong
`~/Library/Application Support/VieNeu Reader/`. ReadEase chủ động giữ tên thư
mục cũ để toàn bộ thư viện và tiến độ đã có tiếp tục hoạt động. Phần văn bản
quét chọn hoặc dán không được thêm vào thư viện và không thay đổi tiến độ đọc
liên tục. Audio của hai chế độ tạm thời này không được lưu vào cache.
Lịch sử phiên cũng chỉ nằm trong bộ nhớ: nội dung trùng chính xác được gộp
thành một mục, và toàn bộ danh sách tự biến mất khi thoát ReadEase.

## Giới hạn của bản đầu tiên

- PDF scan chỉ chứa ảnh chưa được OCR; app sẽ giải thích thay vì nhập một cuốn
  sách rỗng.
- Trình đọc EPUB ưu tiên nội dung reflowable, văn bản và ảnh raster cục bộ; chưa
  tái tạo toàn bộ CSS/layout của sách, fixed-layout, SVG tương tác, bảng phức tạp
  hoặc mô tả ảnh bằng AI. Nếu ảnh lỗi, văn bản và tiến độ đọc vẫn hoạt động.
- Tệp DRM, PDF đặt mật khẩu và EPUB hỏng không được hỗ trợ.
- Lần chuẩn bị mô hình đầu tiên cần mạng. Sau khi hoàn tất, việc đọc không cần
  mạng.

## Khi app không mở được

1. Mở lại app một lần.
2. Nếu đang chuẩn bị mô hình, kiểm tra mạng rồi bấm **Thử lại**.
3. Sách gốc không bị app xóa. Có thể mở lại cùng tệp để app tập trung vào bản đã
   có trong thư viện.
4. Nếu vẫn lỗi, giữ báo cáo crash mới nhất trong
   `~/Library/Logs/DiagnosticReports/` để chẩn đoán.

## Ghi chú đóng gói

Người dùng thông thường không cần phần này. Bản `.app` được tạo bằng đường dẫn
chính thức `pyside6-deploy`/Nuitka, ký ad-hoc, kiểm tra arm64, metadata, launch
và socket trước khi cài. Build dùng Python 3.13 do `uv` quản lý, Nuitka 4.1.1 và
toàn bộ dependency trong `uv.lock`; PDF dùng QtPdf đã nằm trong PySide6. Không
publish binary ra ngoài khi chưa hoàn tất gói giấy phép, ký Developer ID và
notarization.

## Giấy phép mã nguồn và phát hành

Phần mã nguồn, tài liệu và khung ứng dụng do ReadEase sở hữu được chia sẻ theo
`PolyForm-Noncommercial-1.0.0`: bạn có thể dùng, sửa và chia sẻ cho các mục đích
phi thương mại mà giấy phép cho phép. Không được thương mại hóa ReadEase, bản
sửa đổi hoặc sản phẩm dựa trên khung first-party này nếu chưa có giấy phép riêng
bằng văn bản từ chủ sở hữu bản quyền áp dụng. Lê Khoa là chủ sở hữu first-party
hiện tại được ghi trong bản phát hành này; contributor độc lập trong tương lai
giữ quyền của họ nếu không có thỏa thuận chuyển giao riêng. Đây là
source-available, không phải giấy phép open-source theo định nghĩa OSI;
`LICENSE` là văn bản có hiệu lực.

Mỗi bản source và app có provenance ID tĩnh
`READEASE-THU-AM-NC-2026-01`. Marker này giống nhau trong mọi bản, không chứa
thông tin user/máy/cài đặt, không kết nối mạng và không theo dõi. Model VieNeu,
codec MOSS cùng các dependency vẫn giữ giấy phép riêng của bên cung cấp;
`THIRD_PARTY_NOTICES.md`, `legal/` và manifest sinh từ compilation report ghi
lại ranh giới đó.

Trước khi chia sẻ mã nguồn, hãy dùng một clean squash export theo
`PUBLIC_RELEASE_CHECKLIST.md`; lịch sử workspace hiện tại có metadata nội bộ và
không phải lịch sử public. Một binary public còn cần Developer ID,
notarization và legal review riêng, dù source audit đã xanh.
