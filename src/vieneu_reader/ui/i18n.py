"""Small dependency-free localization layer for the desktop UI."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
import re

from vieneu_reader.settings import load_settings, update_settings


class Language(str, Enum):
    VIETNAMESE = "vi"
    ENGLISH = "en"

    @classmethod
    def parse(cls, value: object) -> "Language":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value))
        except ValueError:
            return cls.VIETNAMESE


_TEXT: dict[str, tuple[str, str]] = {
    "language.label": ("Ngôn ngữ", "Language"),
    "language.accessible": ("Chọn ngôn ngữ ứng dụng", "Choose app language"),
    "model.title": ("Chuẩn bị giọng đọc tiếng Việt", "Set up Vietnamese voice"),
    "model.description": (
        "ReadEase cần tải khoảng 330 MB dữ liệu giọng đọc ở lần đầu. Sau đó bạn có thể đọc sách hoàn toàn offline và không cần API key.",
        "ReadEase downloads about 330 MB of Vietnamese voice data the first time. After that, you can read fully offline without an API key.",
    ),
    "model.ready_to_download": ("Sẵn sàng tải giọng đọc.", "Ready to download voice data."),
    "model.prepare": ("Chuẩn bị giọng đọc", "Set up voice"),
    "model.prepare_accessible": (
        "Chuẩn bị giọng đọc tiếng Việt",
        "Set up the Vietnamese voice",
    ),
    "model.cancel": ("Hủy", "Cancel"),
    "model.cancel_accessible": (
        "Hủy chuẩn bị giọng đọc",
        "Cancel Vietnamese voice setup",
    ),
    "model.retry": ("Thử lại", "Try again"),
    "model.preparing": ("Đang chuẩn bị giọng đọc…", "Preparing voice data…"),
    "model.stopping": (
        "Đang dừng sau bước tải hiện tại…",
        "Stopping after the current download step…",
    ),
    "model.cancelled": ("Đã hủy chuẩn bị giọng đọc.", "Voice setup was cancelled."),
    "toolbar.open": ("Mở PDF hoặc EPUB", "Open PDF or EPUB"),
    "toolbar.open_accessible": (
        "Mở thêm sách PDF hoặc EPUB",
        "Open another PDF or EPUB book",
    ),
    "toolbar.paste": ("Dán nội dung", "Paste text"),
    "toolbar.paste_accessible": ("Dán nội dung để đọc", "Paste text to read"),
    "nav.accessible": ("Chọn tính năng ReadEase", "Choose a ReadEase feature"),
    "nav.library": ("Thư viện", "Library"),
    "nav.paste": ("Dán nội dung", "Paste text"),
    "nav.external": ("Đọc sách", "Read books"),
    "library.title": ("Thư viện sách", "Book library"),
    "library.description": (
        "Mở sách EPUB hoặc PDF có lớp văn bản. Sách được giữ cục bộ để bạn có thể tiếp tục từ vị trí đang đọc.",
        "Open an EPUB or a PDF with a text layer. Books stay on this Mac so you can continue from your saved position.",
    ),
    "library.list_accessible": ("Danh sách sách trong thư viện", "Books in your library"),
    "library.open_accessible": ("Mở sách PDF hoặc EPUB", "Open a PDF or EPUB book"),
    "library.paste_accessible": (
        "Chuyển sang màn hình dán nội dung",
        "Go to the paste-text view",
    ),
    "nav.transfer": ("Chuyển ghi chú", "Move notes"),
    "transfer.ambiguous": (
        "Apple Books đang có nhiều mục trùng mã cho cuốn này, nên chưa chọn được "
        "chắc chắn. Hãy mở lại Apple Books rồi thử lại.",
        "Apple Books lists more than one entry under this book's id, so it cannot "
        "be chosen safely. Reopen Apple Books and try again.",
    ),
    "transfer.book_gone": (
        "Cuốn sách này không còn trong thư viện Apple Books. Mở lại mục này để làm mới.",
        "That book is no longer in the Apple Books library. Reopen this tab to refresh.",
    ),
    "transfer.preview_accessible": (
        "Xem trước ghi chú chuyển được",
        "Preview the notes that carry over",
    ),
    "transfer.not_permitted": (
        "ReadEase chưa được phép đọc thư mục Apple Books. Cấp quyền trong "
        "Cài đặt hệ thống rồi mở lại mục này.",
        "ReadEase has not been allowed to read the Apple Books folder. Grant "
        "access in System Settings, then open this tab again.",
    ),
    "transfer.unsupported": (
        "Không đọc được thư viện Apple Books trên máy này.",
        "The Apple Books library could not be read on this Mac.",
    ),
    "transfer.title": (
        "Xem trước rồi chuyển ghi chú sang bản sách kia",
        "Preview your notes, then move them to the other copy",
    ),
    "transfer.description": (
        "Chọn hai bản của cùng một cuốn sách. ReadEase sao lưu trước khi ghi và "
        "không đụng tới cuốn nguồn.",
        "Pick two copies of the same book. ReadEase backs up before writing and "
        "never touches the book they came from.",
    ),
    "transfer.source": ("Lấy ghi chú từ", "Take notes from"),
    "transfer.target": ("Chuyển sang", "Move them to"),
    "transfer.preview": ("Xem trước", "Preview"),
    "transfer.pick_two": (
        "Chọn hai cuốn khác nhau để xem trước.",
        "Pick two different books to preview.",
    ),
    "transfer.table_accessible": (
        "Danh sách ghi chú có thể chuyển được sang bản kia",
        "List of notes that could carry over to the other copy",
    ),
    "transfer.column_kind": ("Loại", "Kind"),
    "transfer.column_text": ("Nội dung", "Content"),
    "transfer.column_verdict": ("Kết quả", "Outcome"),
    "transfer.kind_note": ("Ghi chú", "Note"),
    "transfer.kind_bookmark": ("Đánh dấu trang", "Bookmark"),
    "transfer.no_text": ("(không có chữ kèm theo)", "(no text attached)"),
    "transfer.kind_highlight": ("Đoạn bôi màu", "Highlight"),
    "transfer.verdict_same": ("Chuyển được nguyên vẹn", "Carries over as-is"),
    "transfer.verdict_review": ("Chương này khác nhau", "That chapter differs"),
    "transfer.some_need_review": (
        "{count} mục nằm ở chương mà hai bản khác nhau nên không chép.",
        "{count} sit in a chapter that differs between the copies, so they are "
        "not copied.",
    ),
    "transfer.none_safe": (
        "Cả {count} mục đều nằm ở chương mà hai bản sách khác nhau. Chép sang sẽ "
        "tô nhầm chỗ, nên ReadEase không chép.",
        "All {count} sit in chapters that differ between the two copies. Copying "
        "them would highlight the wrong words, so ReadEase does not.",
    ),
    "transfer.verdict_already": ("Đã có ở cuốn kia", "Already in the other copy"),
    "transfer.count": ("Sẽ chép {count} mục.", "{count} items would be copied."),
    "transfer.some_already_there": (
        "{count} mục đã có sẵn nên sẽ bỏ qua.",
        "{count} are already there and will be skipped.",
    ),
    "transfer.all_already_there": (
        "Cả {count} mục đều đã có ở cuốn kia, không còn gì để chép.",
        "All {count} are already in the other copy; there is nothing to copy.",
    ),
    "transfer.no_notes": (
        "Cuốn này chưa có ghi chú hay đoạn bôi màu nào trong Apple Books.",
        "This book has no notes or highlights in Apple Books yet.",
    ),
    "transfer.different_edition": (
        "Hai bản này khác nhau, nên vị trí từng đoạn cần được kiểm lại.",
        "These are different editions, so each position needs checking.",
    ),
    "transfer.truncated": (
        "Đang hiện {shown} mục đầu.",
        "Showing the first {shown}.",
    ),
    "transfer.copy": ("Chép sang", "Copy across"),
    "transfer.already_there": (
        "Những ghi chú này đã có sẵn ở cuốn kia rồi, nên không chép thêm gì.",
        "These notes are already in the other copy, so nothing was copied.",
    ),
    "transfer.copy_accessible": (
        "Chép các ghi chú vừa xem trước sang bản sách kia",
        "Copy the previewed notes into the other copy of the book",
    ),
    "transfer.confirm_title": ("Chép ghi chú sang bản kia?", "Copy notes across?"),
    "transfer.confirm_body": (
        "ReadEase sẽ chép {count} mục sang “{book}”. Cuốn nguồn giữ nguyên, và bản "
        "sao lưu dữ liệu Apple Books được tạo trước khi ghi.",
        "ReadEase will copy {count} items into “{book}”. The book they came from is "
        "left untouched, and your Apple Books data is backed up before anything is "
        "written.",
    ),
    "transfer.confirm_icloud": (
        "Nếu bạn bật đồng bộ iCloud cho Apple Books, các ghi chú này sẽ xuất hiện "
        "trên những thiết bị khác.",
        "If iCloud syncing is on for Apple Books, these notes will appear on your "
        "other devices too.",
    ),
    "transfer.copied": (
        "Đã chép {count} mục sang “{book}”. Mở Apple Books để kiểm tra.",
        "Copied {count} items into “{book}”. Open Apple Books to check them.",
    ),
    "transfer.books_open": (
        "Apple Books đang mở nên chưa chép được. Hãy thoát Apple Books rồi thử lại.",
        "Apple Books is open, so nothing was copied. Quit Apple Books and try again.",
    ),
    "transfer.copy_failed": (
        "Không chép được; dữ liệu Apple Books giữ nguyên như trước. Bản sao lưu ở {path}.",
        "Nothing was copied and your Apple Books data is exactly as it was. The "
        "backup is at {path}.",
    ),
    "transfer.backup_failed": (
        "Không tạo được bản sao lưu nên ReadEase không ghi gì cả.",
        "The backup could not be made, so ReadEase wrote nothing.",
    ),
    "paste.title": ("Dán nội dung để đọc", "Paste text to read"),
    "paste.description": (
        "Dán đoạn văn hoặc bài viết vào đây. Nội dung chỉ dùng trong phiên đọc này: không thêm vào thư viện và không được lưu vào cache.",
        "Paste a passage or article here. It is used only for this session, is not added to your library and is not stored in the audio cache.",
    ),
    "paste.editor_accessible": ("Nội dung cần đọc", "Text to read"),
    "paste.placeholder": ("Dán nội dung tiếng Việt vào đây…", "Paste text here…"),
    "paste.count_accessible": ("Số ký tự nội dung đã dán", "Pasted character count"),
    "paste.read": ("Đọc nội dung", "Read text"),
    "paste.read_accessible": (
        "Bắt đầu đọc nội dung đã dán",
        "Start reading the pasted text",
    ),
    "paste.count": ("{count} / {limit} ký tự", "{count} / {limit} characters"),
    "paste.over_limit": (
        "Vượt giới hạn {limit} ký tự · hiện có {count}",
        "Over the {limit}-character limit · currently {count}",
    ),
    "reader.back": ("Quay lại thư viện", "Back to library"),
    "reader.back_accessible": (
        "Quay lại danh sách sách đã nhập",
        "Return to the imported-book list",
    ),
    "reader.book_title_accessible": ("Tên sách đang đọc", "Current book title"),
    "reader.chapters": ("Chương", "Chapters"),
    "reader.chapter_list_accessible": ("Danh sách chương", "Chapter list"),
    "reader.content_accessible": ("Nội dung sách có thể chọn", "Selectable book content"),
    "reader.selection": ("Đọc phần đã chọn", "Read selection"),
    "reader.selection_accessible": (
        "Đọc phần nội dung đang chọn trong sách",
        "Read the selected text in this book",
    ),
    "reader.figure": ("Hình {number}", "Figure {number}"),
    "reader.figure_unavailable": (
        "Không thể hiển thị hình này.",
        "This figure cannot be displayed.",
    ),
    "reader.content_description": (
        "Nội dung sách có thể chọn và đọc bằng ReadEase.",
        "Book content can be selected and read with ReadEase.",
    ),
    "reader.figures_description": (
        "Nội dung sách có thể chọn và đọc bằng ReadEase. Chương này có {count} hình: {figures}.",
        "Book content can be selected and read with ReadEase. This chapter has {count} figures: {figures}.",
    ),
    "external.title": ("Đọc từ Apple Books", "Read from Apple Books"),
    "external.status_accessible": (
        "Trạng thái đọc từ Apple Books",
        "Apple Books reading status",
    ),
    "external.detail_accessible": (
        "Chi tiết trạng thái đọc từ Apple Books",
        "Apple Books reading status details",
    ),
    "external.description": (
        "Giữ ReadEase đang chạy, quét chọn đoạn văn trong Apple Books, rồi dùng phím tắt bên dưới để nghe bằng giọng Việt cục bộ.",
        "Keep ReadEase running, select text in Apple Books, then use the shortcut below to hear it with the local Vietnamese voice.",
    ),
    "external.steps": (
        "1. Mở sách trong Apple Books.\n2. Quét chọn đúng phần bạn muốn nghe.\n3. Nhấn phím tắt; ReadEase sẽ đọc mà không đưa cửa sổ này lên trước.",
        "1. Open a book in Apple Books.\n2. Select the text you want to hear.\n3. Press the shortcut; ReadEase reads it without bringing this window forward.",
    ),
    "external.steps_accessible": (
        "Hướng dẫn đọc phần đã chọn trong Apple Books",
        "How to read selected text from Apple Books",
    ),
    "external.shortcut": ("Phím tắt", "Keyboard shortcut"),
    "external.shortcut_accessible": (
        "Phím tắt đọc phần đã chọn: {shortcut}",
        "Read-selection shortcut: {shortcut}",
    ),
    "external.shortcut_change": ("Đổi phím tắt", "Change shortcut"),
    "external.shortcut_change_accessible": (
        "Đổi phím tắt đọc phần đã chọn từ Apple Books",
        "Change the shortcut that reads the Apple Books selection",
    ),
    "external.shortcut_recording": (
        "Nhấn tổ hợp phím mới…",
        "Press the new combination…",
    ),
    "external.shortcut_hint": (
        "Giữ ít nhất một trong Control, Option hoặc Command rồi nhấn một phím. Nhấn Esc để giữ nguyên phím tắt cũ.",
        "Hold at least one of Control, Option or Command, then press a key. Press Esc to keep the current shortcut.",
    ),
    "external.permission_note": (
        "Lần đầu sử dụng, macOS cần cho phép ReadEase điều khiển thao tác sao chép trong Apple Books. Bạn có thể mở đúng mục Trợ năng tại đây.",
        "The first time you use this feature, macOS must allow ReadEase to issue the copy command in Apple Books. Open the correct Accessibility settings here.",
    ),
    "external.open_settings": ("Mở Cài đặt quyền", "Open permission settings"),
    "external.open_settings_accessible": (
        "Mở cài đặt quyền Trợ năng của macOS cho ReadEase",
        "Open macOS Accessibility settings for ReadEase",
    ),
    "external.read_on_copy": (
        "Đọc ngay khi sao chép trong Apple Books",
        "Read as soon as you copy in Apple Books",
    ),
    "external.read_on_copy_accessible": (
        "Bật hoặc tắt việc đọc ngay khi bạn sao chép trong Apple Books",
        "Turn reading on copy in Apple Books on or off",
    ),
    "external.privacy_note": (
        "ReadEase chỉ xử lý khi bạn bấm phím tắt trong Apple Books. Mục đọc-khi-sao-chép đang tắt, nên ReadEase không xem clipboard và không theo dõi màn hình ở chế độ nền.",
        "ReadEase acts only when you press the shortcut in Apple Books. Read-on-copy is off, so ReadEase does not look at your clipboard and does not monitor your screen in the background.",
    ),
    "external.privacy_note_on": (
        "Mục đọc-khi-sao-chép đang bật: ReadEase xem bộ đếm thay đổi của clipboard vài lần mỗi giây, chỉ đọc khi Apple Books ở phía trước cả ở lần kiểm tra thấy nội dung mới lẫn lần kiểm tra ngay trước đó, và bỏ qua mục được đánh dấu là ẩn — cách trình quản lý mật khẩu yêu cầu công cụ clipboard đừng đụng tới. macOS không ghi lại ứng dụng nào đã sao chép, nên nếu bạn sao chép ở ứng dụng khác rồi chuyển sang Apple Books trong cùng một phần giây, nội dung đó vẫn có thể bị đọc. Tắt công tắc này để ReadEase ngừng xem clipboard.",
        "Read-on-copy is on: ReadEase checks the clipboard's change counter a few times a second, reads only when Apple Books is in front both at the check that notices new text and at the check before it, and skips items marked concealed — how password managers ask clipboard tools to leave them alone. macOS does not record which app did the copying, so text you copy elsewhere and follow with a switch to Apple Books inside the same fraction of a second could still be read. Turn this switch off and ReadEase stops looking at the clipboard.",
    ),
    "external.recent_title": (
        "Đã đọc từ Apple Books trong phiên",
        "Read from Apple Books this session",
    ),
    "external.history_empty": (
        "Chưa có đoạn nào. Phần bạn đọc bằng phím tắt sẽ xuất hiện ở đây và tự mất khi đóng ReadEase.",
        "Nothing here yet. Text read with the shortcut appears here and disappears when ReadEase closes.",
    ),
    "external.history_accessible": (
        "Các phần đã đọc từ Apple Books trong phiên",
        "Text read from Apple Books this session",
    ),
    "external.replay": ("Nghe lại phần đã chọn", "Replay selected item"),
    "external.replay_accessible": (
        "Nghe lại phần Apple Books đang chọn trong lịch sử phiên",
        "Replay the selected Apple Books item from session history",
    ),
    "external.starting": ("Đang chuẩn bị phím tắt…", "Preparing the shortcut…"),
    "external.ready": ("Sẵn sàng đọc từ Apple Books", "Ready to read from Apple Books"),
    "external.received": ("Đã nhận phần chọn gần nhất", "Latest selection received"),
    "external.permission_required": ("Cần quyền Trợ năng", "Accessibility permission required"),
    "external.failed": ("Chưa thể đọc phần đã chọn", "Could not read the selection"),
    "player.previous": ("Trước", "Previous"),
    "player.previous_accessible": ("Đọc đoạn trước", "Read the previous paragraph"),
    "player.play": ("Đọc", "Read"),
    "player.play_accessible": (
        "Bắt đầu đọc hoặc tạm dừng",
        "Start reading or pause playback",
    ),
    "player.pause": ("Tạm dừng", "Pause"),
    "player.resume": ("Tiếp tục", "Resume"),
    "player.stop": ("Dừng", "Stop"),
    "player.stop_accessible": ("Dừng đọc", "Stop reading"),
    "player.next": ("Sau", "Next"),
    "player.next_accessible": ("Đọc đoạn tiếp theo", "Read the next paragraph"),
    "player.history": ("Lịch sử phiên", "Session history"),
    "player.history_accessible": (
        "Mở lịch sử nội dung đã đọc trong phiên",
        "Open content read during this session",
    ),
    "player.history_count": (
        "Mở {count} nội dung gần đây",
        "Open {count} recent items",
    ),
    "player.history_empty": (
        "Chưa có nội dung đã đọc trong phiên",
        "No content has been read this session",
    ),
    "player.history_clear": ("Xóa lịch sử phiên", "Clear session history"),
    "player.source.paste": ("Dán nội dung", "Pasted text"),
    "player.source.book_selection": ("Trong sách", "In-book selection"),
    "player.source.apple_books": ("Apple Books", "Apple Books"),
    "player.voice": ("Giọng", "Voice"),
    "player.voice_accessible": ("Chọn giọng đọc", "Choose a voice"),
    "player.speed": ("Tốc độ", "Speed"),
    "player.speed_accessible": ("Chọn tốc độ đọc", "Choose reading speed"),
    "status.ready": ("Sẵn sàng.", "Ready."),
    "status.location_accessible": ("Vị trí đọc trong sách", "Reading position in the book"),
    "permission.open": ("Mở Cài đặt quyền", "Open permission settings"),
    "permission.open_accessible": (
        "Mở cài đặt quyền Trợ năng của macOS",
        "Open macOS Accessibility settings",
    ),
    "dialog.open_title": ("Mở sách", "Open a book"),
    "dialog.open_filter": (
        "Sách (*.pdf *.epub);;PDF (*.pdf);;EPUB (*.epub)",
        "Books (*.pdf *.epub);;PDF (*.pdf);;EPUB (*.epub)",
    ),
}


_RUNTIME_EN: dict[str, str] = {
    'ReadEase chưa được phép đọc thư mục Apple Books.': "ReadEase has not been allowed to read the Apple Books folder.",
    "Mở sách hoặc dán nội dung để bắt đầu.": "Open a book or paste text to begin.",
    "Không thể mở sách.": "Could not open the book.",
    "Sách đã được thêm nhưng chưa thể tải lại. Hãy mở lại ứng dụng.": "The book was added but could not be reloaded. Reopen the app.",
    "Đã thêm sách nhưng chưa thể tải lại.": "Book added but not reloaded.",
    "Không thể tải thư viện cục bộ. Hãy mở lại ứng dụng.": "Could not load the local library. Reopen the app.",
    "Không thể tải thư viện cục bộ.": "Could not load the local library.",
    "Sách đã có trong thư viện; đã mở lại.": "This book is already in the library and has been reopened.",
    "Đã thêm sách vào thư viện.": "Book added to the library.",
    "Không thể tải sách từ thư viện cục bộ. Hãy mở lại ứng dụng.": "Could not load the book from the local library. Reopen the app.",
    "Không tìm thấy sách trong thư viện.": "The book was not found in the library.",
    "Sách không có đoạn văn có thể đọc.": "This book has no readable paragraphs.",
    "Sẵn sàng đọc.": "Ready to read.",
    "Không thể lưu vị trí đọc. Sách vẫn có thể mở lại.": "Could not save the reading position. The book can still be reopened.",
    "Không thể lưu vị trí đọc.": "Could not save the reading position.",
    "Không thể lưu tùy chọn đọc. Sách vẫn có thể mở lại.": "Could not save reading preferences. The book can still be reopened.",
    "Không thể lưu tùy chọn đọc.": "Could not save reading preferences.",
    "Hãy mở một cuốn sách trước khi bấm đọc.": "Open a book before pressing Read.",
    "Hãy chọn một phần nội dung để đọc.": "Select some text to read.",
    "Nội dung dán vượt quá giới hạn 100.000 ký tự.": "Pasted text exceeds the 100,000-character limit.",
    "Hãy dán nội dung trước khi bấm đọc.": "Paste some text before pressing Read.",
    "Phần đã chọn vượt quá giới hạn 100.000 ký tự.": "The selection exceeds the 100,000-character limit.",
    "Không thể đọc phần đã chọn.": "Could not read the selection.",
    "Không tìm thấy nội dung đang chọn trong Apple Books.": "No selected text was found in Apple Books.",
    "ReadEase cần quyền Trợ năng để gửi lệnh sao chép tới Apple Books. Hãy bật ReadEase trong Cài đặt hệ thống > Quyền riêng tư & Bảo mật > Trợ năng rồi thử lại.": "ReadEase needs Accessibility permission to send the copy command to Apple Books. Enable ReadEase in System Settings > Privacy & Security > Accessibility, then try again.",
    "Không tìm thấy nội dung đang chọn. Hãy chọn chữ trong Apple Books rồi nhấn phím tắt đọc.": "No selected text was found. Select text in Apple Books, then press the read shortcut.",
    "Phím tắt đọc nhanh hiện chỉ hỗ trợ Apple Books.": "The read-selection shortcut currently supports Apple Books only.",
    "Không đăng ký được phím tắt này; macOS hoặc ứng dụng khác đang dùng nó. Hãy chọn tổ hợp khác.": "This shortcut could not be registered; macOS or another app is already using it. Choose a different combination.",
    "ReadEase không thể xác nhận đã khôi phục clipboard nên đã dừng trước khi đọc.": "ReadEase could not confirm that the clipboard was restored, so it stopped before reading.",
    "Phím tắt đọc từ Apple Books chưa sẵn sàng. Hãy mở lại ReadEase.": "The Apple Books shortcut is not ready. Reopen ReadEase.",
    "Phần nội dung đã chọn vượt quá 100.000 ký tự.": "The selected text exceeds 100,000 characters.",
    "Nội dung này không còn trong lịch sử phiên.": "This item is no longer in session history.",
    "Đang chuẩn bị giọng đọc…": "Preparing voice data…",
    "Đang đọc": "Reading",
    "Đã tạm dừng": "Paused",
    "Không thể tiếp tục đọc.": "Could not continue reading.",
    "Đang kiểm tra giọng đọc…": "Checking the voice…",
    "Đang tải mô hình…": "Downloading the model…",
    "Đang kiểm tra…": "Checking…",
    "Sẵn sàng.": "Ready.",
    "Mô hình đọc tiếng Việt đã sẵn sàng.": "The Vietnamese voice model is ready.",
    "Đang tải mô hình đọc tiếng Việt lần đầu…": "Downloading the Vietnamese voice model for the first time…",
    "Đang tải bộ giải mã âm thanh…": "Downloading the audio decoder…",
    "Đang kiểm tra bộ đọc tiếng Việt…": "Checking the Vietnamese voice engine…",
    "Không thể chuẩn bị mô hình đọc tiếng Việt. Hãy kiểm tra mạng và thử lại.": "Could not prepare the Vietnamese voice model. Check your connection and try again.",
    'Không tìm thấy dữ liệu Apple Books trên máy này.': 'No Apple Books data was found on this Mac.',
    'Không đọc được dữ liệu Apple Books. Hãy thử lại sau.': 'Could not read the Apple Books data. Try again in a moment.',
    'Chưa có bản sao lưu, nên không thể hoàn tác nếu sai.': 'No backup was taken, so a mistake could not be undone.',
    'Apple Books đang mở. Hãy thoát Apple Books rồi thử lại.': 'Apple Books is open. Quit Apple Books, then try again.',
    "Không thể chuẩn bị giọng đọc. Hãy kiểm tra kết nối mạng và Thử lại.": "Could not prepare the voice. Check your connection and try again.",
    "Vui lòng chọn tệp PDF hoặc EPUB.": "Choose a PDF or EPUB file.",
    "Không tìm thấy tệp sách đã chọn.": "The selected book file was not found.",
    "Không thể kiểm tra tệp sách đã chọn.": "Could not inspect the selected book file.",
    "Tệp sách vượt giới hạn dung lượng 200 MiB.": "The book exceeds the 200 MiB size limit.",
    "Không thể chuẩn bị thư viện để sao chép sách.": "Could not prepare the library to copy the book.",
    "Không thể cập nhật thư viện cục bộ; sách chưa được thêm.": "Could not update the local library; the book was not added.",
    "Không thể sao chép sách vào thư viện cục bộ.": "Could not copy the book into the local library.",
    "PDF có tiêu đề quá dài.": "The PDF title is too long.",
    "PDF chứa quá nhiều khối văn bản.": "The PDF contains too many text blocks.",
    "PDF có nội dung đọc quá dài.": "The PDF contains too much readable text.",
    "PDF được bảo vệ bằng mật khẩu nên không thể đọc.": "Password-protected PDFs are not supported.",
    "Không thể đọc tệp PDF bị hỏng.": "The damaged PDF could not be read.",
    "PDF có số trang không hợp lệ hoặc vượt giới hạn.": "The PDF page count is invalid or exceeds the limit.",
    "PDF không có lớp văn bản; bản MVP chưa hỗ trợ OCR.": "This PDF has no text layer; OCR is not supported yet.",
    "EPUB được mã hóa nên không thể đọc.": "Encrypted EPUB files are not supported.",
    "EPUB không có nội dung đọc trong spine.": "The EPUB spine contains no readable content.",
    "Không thể đọc tệp EPUB bị hỏng.": "The damaged EPUB could not be read.",
    "Không thể đọc hình ảnh trong EPUB.": "An EPUB image could not be read.",
    "Sẵn sàng tải giọng đọc.": "Ready to download voice data.",
    "Đang dừng sau bước tải hiện tại…": "Stopping after the current download step…",
    "Đã hủy chuẩn bị giọng đọc.": "Voice setup was cancelled.",
    "EPUB chứa đường dẫn không an toàn.": "The EPUB contains an unsafe path.",
    "EPUB chứa quá nhiều thành phần.": "The EPUB contains too many entries.",
    "EPUB không có mục lục ZIP hợp lệ.": "The EPUB has no valid ZIP directory.",
    "EPUB có mục lục ZIP không nhất quán.": "The EPUB ZIP directory is inconsistent.",
    "EPUB nhiều phần không được hỗ trợ.": "Multi-part EPUB archives are not supported.",
    "EPUB ZIP64 không được hỗ trợ trong bản MVP.": "ZIP64 EPUB files are not supported yet.",
    "Mục lục EPUB vượt giới hạn an toàn.": "The EPUB directory exceeds the safety limit.",
    "Mục lục EPUB không hợp lệ.": "The EPUB directory is invalid.",
    "Mục lục EPUB khai báo số thành phần không nhất quán.": "The EPUB directory declares an inconsistent entry count.",
    "Một thành phần EPUB vượt giới hạn an toàn.": "An EPUB entry exceeds the safety limit.",
    "EPUB chứa đường dẫn nội dung không an toàn.": "The EPUB contains an unsafe content path.",
    "EPUB có tiêu đề quá dài.": "The EPUB title is too long.",
    "EPUB chứa mục tệp trùng lặp.": "The EPUB contains duplicate file entries.",
    "EPUB vượt giới hạn dung lượng an toàn.": "The EPUB exceeds the safe size limit.",
    "Một thành phần EPUB bị hỏng.": "An EPUB entry is damaged.",
    "EPUB chứa đường dẫn nội dung không hợp lệ.": "The EPUB contains an invalid content path.",
    "EPUB thiếu đường dẫn package.": "The EPUB package path is missing.",
    "EPUB manifest chứa quá nhiều mục.": "The EPUB manifest contains too many items.",
    "EPUB spine chứa quá nhiều mục đọc.": "The EPUB spine contains too many reading items.",
    "EPUB tạo ra quá nhiều chương.": "The EPUB produces too many chapters.",
    "EPUB tạo ra quá nhiều đoạn đọc.": "The EPUB produces too many readable paragraphs.",
    "EPUB có nội dung đọc quá dài.": "The EPUB contains too much readable text.",
    "EPUB chứa đường dẫn hình ảnh từ xa.": "The EPUB contains a remote image path.",
    "Nội dung hình ảnh EPUB không còn khớp với bản sách đã nhập.": "The EPUB image content no longer matches the imported book.",
    "Chương EPUB chứa quá nhiều hình ảnh.": "The EPUB chapter contains too many images.",
    "EPUB chứa đường dẫn hình ảnh không hợp lệ.": "The EPUB contains an invalid image path.",
    "EPUB tạo ra quá nhiều hình ảnh đọc.": "The EPUB produces too many readable images.",
    "Nguồn EPUB được quản lý không còn an toàn.": "The managed EPUB source is no longer safe.",
    "Spine EPUB không còn khớp bản sách đã nhập.": "The EPUB spine no longer matches the imported book.",
    "Nguồn EPUB được quản lý đã thay đổi.": "The managed EPUB source has changed.",
    "Nguồn EPUB không khớp bản sách đã nhập.": "The EPUB source does not match the imported book.",
    "Không thể dọn dẹp bản sao nhập tạm trong thư viện.": "Could not clean up the temporary imported copy in the library.",
    "Thư viện có bản sao chưa hoàn tất; cần sửa thư viện trước khi nhập lại.": "The library contains an incomplete copy; repair the library before importing again.",
    "Không thể dọn dẹp bản sao nhập tạm; lần nhập sau sẽ thử lại.": "Could not clean up the temporary imported copy; the next import will try again.",
    "Không thể khóa thư viện cục bộ để nhập sách.": "Could not lock the local library for import.",
    "Không thể đóng tệp khóa import sau lỗi chính.": "Could not close the import lock file after the primary error.",
    "Không thể truy cập dữ liệu thư viện cục bộ.": "Could not access the local library data.",
    "Không thể mở dữ liệu thư viện cục bộ.": "Could not open the local library data.",
    "Dữ liệu sách trong thư viện cục bộ bị hỏng.": "The book data in the local library is damaged.",
    "Không thể lưu cuốn sách đang mở.": "Could not save which book is open.",
    "Dữ liệu cuốn sách đang mở trong thư viện cục bộ bị hỏng.": "The record of the open book in the local library is damaged.",
    "Dữ liệu tiến độ đọc trong thư viện cục bộ bị hỏng.": "The reading-progress data in the local library is damaged.",
    "Không thể tạo giọng đọc cho đoạn này.": "Could not create the voice for this paragraph.",
    "Mô hình đọc tiếng Việt chưa được chuẩn bị.": "The Vietnamese voice model has not been prepared yet.",
    "Máy đã hết dung lượng trống nên chưa tải xong giọng đọc. Hãy giải phóng bớt dung lượng rồi thử lại.": "This Mac ran out of free space before the voice finished downloading. Free up some space, then try again.",
}


_RUNTIME_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"^Chương (\d+)/(\d+) · Đoạn (\d+)/(\d+)$"),
        r"Chapter \1/\2 · Paragraph \3/\4",
    ),
    (re.compile(r"^Đang chuẩn bị đoạn (\d+)/(\d+)…$"), r"Preparing part \1/\2…"),
    (re.compile(r"^Đang đọc đoạn (\d+)/(\d+)$"), r"Reading part \1/\2"),
    (re.compile(r"^Đã tạm dừng · Đoạn (\d+)/(\d+)$"), r"Paused · Part \1/\2"),
    (re.compile(r"^(.+) có XML quá phức tạp\.$"), r"\1 contains XML that is too complex."),
    (re.compile(r"^(.+) chứa khai báo XML không an toàn\.$"), r"\1 contains unsafe XML declarations."),
    (re.compile(r"^(.+) không phải XML hợp lệ\.$"), r"\1 is not valid XML."),
    (re.compile(r"^EPUB thiếu thành phần bắt buộc: (.+)\.$"), r"The EPUB is missing a required component: \1."),
    (re.compile(r"^(.+) - Nam Bộ$"), r"\1 - Southern Vietnamese"),
    (re.compile(r"^(.+) - Bắc Bộ$"), r"\1 - Northern Vietnamese"),
)


class Localizer:
    def __init__(self, language: Language = Language.VIETNAMESE):
        self._language = Language.parse(language)

    @property
    def language(self) -> Language:
        return self._language

    def set_language(self, language: Language | str) -> None:
        self._language = Language.parse(language)

    def text(self, key: str, **values: object) -> str:
        vietnamese, english = _TEXT[key]
        template = english if self._language is Language.ENGLISH else vietnamese
        return template.format(**values)

    def runtime(self, message: str | None) -> str:
        if message is None or self._language is Language.VIETNAMESE:
            return message or ""
        translated = _RUNTIME_EN.get(message)
        if translated is not None:
            return translated
        for pattern, replacement in _RUNTIME_PATTERNS:
            if pattern.fullmatch(message):
                return pattern.sub(replacement, message)
        return message


class LanguagePreferenceStore:
    """Persist one non-sensitive UI preference beside other local app data."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> Language:
        return Language.parse(load_settings(self.path).get("language"))

    def save(self, language: Language | str) -> bool:
        selected = Language.parse(language)
        return update_settings(self.path, {"language": selected.value})
