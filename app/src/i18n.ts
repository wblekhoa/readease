/** Strings ported verbatim from the Qt shell's ui/i18n.py - the wording was
 * already reviewed there (de-bias rounds included); this file only changes
 * the container, never the words. */

export type Language = "vi" | "en";

export const TEXT = {
  "aria.workspace": ["Khu vực làm việc", "Work area"],
  "aria.language": ["Ngôn ngữ", "Language"],
  "aria.close": ["Đóng", "Close"],
  "nav.library": ["Thư viện", "Library"],
  "nav.paste": ["Dán nội dung", "Paste text"],
  "nav.external": ["Quét đọc", "Read a selection"],
  "nav.transfer": ["Chuyển ghi chú", "Move notes"],
  "paste.title": ["Dán nội dung để đọc", "Paste text to read"],
  "paste.description": [
    "Chỉ dùng cho phiên này - không lưu vào thư viện.",
    "For this session only - nothing is added to your library.",
  ],
  "paste.placeholder": ["Dán nội dung tiếng Việt vào đây…", "Paste text here…"],
  "paste.read": ["Đọc nội dung", "Read text"],
  "paste.count": ["{count} / {limit} ký tự", "{count} / {limit} characters"],
  "player.quality": ["Chất lượng", "Quality"],
  "player.voice": ["Giọng", "Voice"],
  "player.speed": ["Tốc độ", "Speed"],
  "player.play": ["Đọc", "Read"],
  "player.pause": ["Tạm dừng", "Pause"],
  "player.resume": ["Tiếp tục", "Resume"],
  "player.stop": ["Dừng", "Stop"],
  "library.title": ["Thư viện sách", "Book library"],
  "reader.back": ["Quay lại thư viện", "Back to library"],
  "player.previous": ["Trước", "Previous"],
  "player.next": ["Sau", "Next"],
  "toolbar.open": ["Mở PDF hoặc EPUB", "Open PDF or EPUB"],
  "library.description": [
    "PDF phải có lớp văn bản - sách scan chưa đọc được.",
    "A PDF needs a text layer - a scanned book cannot be read yet.",
  ],
  "library.imported": ["Đã thêm sách vào thư viện.", "Book added to the library."],
  "library.duplicate": [
    "Sách này đã có trong thư viện.",
    "This book is already in the library.",
  ],
  "library.importing": ["Đang nhập sách…", "Importing…"],
  "library.drop_hint": ["Thả tệp để nhập sách", "Drop the file to import it"],
  "library.chapter_count": ["{count} chương", "{count} chapters"],
  "library.imported_on": ["Nhập {date}", "Imported {date}"],
  "library.in_progress": ["Đang đọc dở", "In progress"],
  "library.remove": ["Xoá", "Remove"],
  "library.remove_confirm": ["Xoá khỏi thư viện?", "Remove from the library?"],
  "library.remove_keep": ["Giữ lại", "Keep"],
  "library.removed": ["Đã xoá khỏi thư viện.", "Removed from the library."],
  "external.title": ["Quét đọc", "Read a selection"],
  "external.steps": [
    "1. Mở ứng dụng có phần chữ bạn muốn nghe.\n2. Bôi đen đúng phần đó.\n3. Nhấn phím tắt; ReadEase sẽ đọc mà không đưa cửa sổ này lên trước.",
    "1. Open whatever app has the text you want to hear.\n2. Select exactly that text.\n3. Press the shortcut; ReadEase reads it without bringing this window forward.",
  ],
  "external.shortcut": ["Phím tắt", "Keyboard shortcut"],
  "external.permission_note": [
    "Lần đầu, macOS cần cho phép ReadEase gửi lệnh sao chép trong ứng dụng bạn đang dùng.",
    "The first time, macOS must let ReadEase send the copy command in the app you are using.",
  ],
  "external.permission_granted": [
    "Đã có quyền Trợ năng.",
    "Accessibility permission granted.",
  ],
  "external.permission_restart": [
    "Sau khi bật quyền, hãy thoát ReadEase rồi mở lại để phím tắt hoạt động.",
    "After granting, quit ReadEase and reopen it so the shortcut can work.",
  ],
  "external.open_system_settings": ["Cài đặt hệ thống", "System Settings"],
  "external.open_settings": ["Mở Cài đặt quyền", "Open permission settings"],
  "external.recent_title": ["Đã quét đọc trong phiên", "Read from a selection this session"],
  "external.history_empty": [
    "Chưa có gì. Danh sách này mất khi đóng ReadEase.",
    "Nothing yet. This list is gone when ReadEase closes.",
  ],
  "external.replay": ["Nghe lại phần đã chọn", "Read the selection again"],
  "external.reading": ["Đang đọc phần bạn vừa chọn…", "Reading your selection…"],
  "status.permission_required": [
    "ReadEase cần quyền Trợ năng để gửi lệnh sao chép tới ứng dụng bạn đang dùng. Hãy bật ReadEase trong Cài đặt hệ thống > Quyền riêng tư & Bảo mật > Trợ năng rồi thử lại.",
    "ReadEase needs Accessibility permission to send the copy command. Enable ReadEase under System Settings > Privacy & Security > Accessibility, then try again.",
  ],
  "status.no_selection": [
    "Không tìm thấy nội dung đang chọn. Hãy bôi đen phần muốn nghe rồi nhấn phím tắt đọc.",
    "No selection found. Select the text you want to hear, then press the shortcut.",
  ],
  "status.unsupported_source": [
    "Không quét đọc được từ cửa sổ này. Hãy chuyển sang ứng dụng có phần chữ bạn muốn nghe rồi thử lại.",
    "This window cannot be read from. Switch to the app with the text you want, then try again.",
  ],
  "status.concealed_source": [
    "Phần đang chọn được đánh dấu là nội dung bí mật nên ReadEase không đọc.",
    "The selection is marked concealed, so ReadEase will not read it.",
  ],
  "status.clipboard_restore_failed": [
    "ReadEase không thể xác nhận đã khôi phục clipboard nên đã dừng trước khi đọc.",
    "ReadEase could not confirm the clipboard was restored, so it stopped before reading.",
  ],
  "status.unavailable": [
    "Phím tắt quét đọc chưa sẵn sàng. Hãy mở lại ReadEase.",
    "The read-selection shortcut is not ready. Reopen ReadEase.",
  ],
  "external.shortcut_change": ["Đổi phím tắt", "Change shortcut"],
  "external.shortcut_recording": ["Nhấn tổ hợp phím mới…", "Press the new combination…"],
  "external.shortcut_hint": [
    "Giữ ít nhất một trong Control, Option hoặc Command rồi nhấn một phím. Nhấn Esc để giữ nguyên phím tắt cũ.",
    "Hold at least one of Control, Option or Command, then press a key. Press Esc to keep the current shortcut.",
  ],
  "external.shortcut_taken": [
    "Không đăng ký được phím tắt này; macOS hoặc ứng dụng khác đang dùng nó. Hãy chọn tổ hợp khác.",
    "This shortcut could not be registered; macOS or another app is using it. Pick a different combination.",
  ],
  "model.quality_standard": ["Tiêu chuẩn", "Standard"],
  "model.quality_maximum": ["Cao nhất", "Highest"],
  "model.quality": ["Chất lượng giọng đọc", "Voice quality"],
  "model.build_standard": ["Tiêu chuẩn · 330 MB", "Standard · 330 MB"],
  "model.build_maximum": ["Cao nhất · 625 MB", "Highest · 625 MB"],
  "model.in_use": ["Đang dùng", "In use"],
  "model.use_build": ["Dùng bản này", "Use this build"],
  "model.not_downloaded": ["Chưa tải", "Not downloaded"],
  "model.switch_restart": [
    "Đổi chất lượng sẽ khởi động lại giọng đọc. Bản chưa tải sẽ được tải trước khi dùng.",
    "Switching restarts the voice. A build that is not downloaded yet is fetched first.",
  ],
  "model.spare_remove": ["Xoá để lấy lại dung lượng", "Remove it to reclaim the space"],
  "model.preparing": ["Đang tải giọng đọc…", "Downloading the voice…"],
  "model.restarting": ["Đang khởi động lại giọng đọc…", "Restarting the voice…"],
  "transfer.title": [
    "Xem trước rồi chuyển ghi chú sang bản sách kia",
    "Preview your notes, then move them to the other copy",
  ],
  "transfer.description": [
    "Sao lưu trước khi ghi; không đụng cuốn nguồn.",
    "Backed up before writing; the source book is untouched.",
  ],
  "transfer.pick_book": ["Chọn sách…", "Choose a book…"],
  "transfer.source": ["Lấy ghi chú từ", "Take notes from"],
  "transfer.target": ["Chuyển sang", "Move them to"],
  "transfer.preview": ["Xem trước", "Preview"],
  "transfer.pick_two": ["Chọn hai cuốn khác nhau để xem trước.", "Pick two different books to preview."],
  "transfer.kind_note": ["Ghi chú", "Note"],
  "transfer.kind_highlight": ["Đoạn bôi màu", "Highlight"],
  "transfer.no_text": ["(không có chữ kèm theo)", "(no text attached)"],
  "transfer.verdict_same": ["Chuyển được nguyên vẹn", "Carries over as-is"],
  "transfer.verdict_review": ["Chương này khác nhau", "That chapter differs"],
  "transfer.verdict_already": ["Đã có ở cuốn kia", "Already in the other copy"],
  "transfer.count": ["Sẽ chép {count} mục.", "{count} items would be copied."],
  "transfer.truncated": ["Đang hiện {shown} mục đầu.", "Showing the first {shown}."],
  "transfer.copy": ["Chép sang", "Copy across"],
  "transfer.confirm_title": ["Chép ghi chú sang bản kia?", "Copy notes across?"],
  "transfer.confirm_body": [
    "ReadEase sẽ chép {count} mục sang “{book}”. Cuốn nguồn giữ nguyên, và bản sao lưu dữ liệu Apple Books được tạo trước khi ghi.",
    "ReadEase will copy {count} items into “{book}”. The book they came from is left untouched, and your Apple Books data is backed up before anything is written.",
  ],
  "transfer.confirm_icloud": [
    "Nếu bạn bật đồng bộ iCloud cho Apple Books, các ghi chú này sẽ xuất hiện trên những thiết bị khác.",
    "If iCloud syncing is on for Apple Books, these notes will appear on your other devices too.",
  ],
  "transfer.keep": ["Chưa chép", "Not yet"],
  "outcome.copied": [
    "Đã chép {count} mục sang “{book}”. Mở Apple Books để kiểm tra.",
    "Copied {count} items into “{book}”. Open Apple Books to check them.",
  ],
  "outcome.no_notes": [
    "Cuốn này chưa có ghi chú hay đoạn bôi màu nào trong Apple Books.",
    "This book has no notes or highlights in Apple Books yet.",
  ],
  "outcome.all_already_there": [
    "Cả {count} mục đều đã có ở cuốn kia, không còn gì để chép.",
    "All {count} are already in the other copy; there is nothing to copy.",
  ],
  "outcome.already_there": [
    "Những ghi chú này đã có sẵn ở cuốn kia rồi, nên không chép thêm gì.",
    "These notes are already in the other copy, so nothing was copied.",
  ],
  "outcome.books_open": [
    "Apple Books đang mở nên chưa chép được. Hãy thoát Apple Books rồi thử lại.",
    "Apple Books is open, so nothing was copied. Quit Apple Books and try again.",
  ],
  "outcome.backup_failed": [
    "Không tạo được bản sao lưu nên ReadEase không ghi gì cả.",
    "The backup could not be made, so ReadEase wrote nothing.",
  ],
  "outcome.copy_failed": [
    "Không chép được; dữ liệu Apple Books giữ nguyên như trước. Bản sao lưu ở {path}.",
    "Nothing was copied and your Apple Books data is exactly as it was. The backup is at {path}.",
  ],
  "outcome.unsupported": [
    "Không đọc được thư viện Apple Books trên máy này.",
    "The Apple Books library could not be read on this Mac.",
  ],
  "noteserr.not_permitted": [
    "ReadEase chưa được phép đọc thư mục Apple Books. Cấp quyền trong Cài đặt hệ thống rồi mở lại mục này.",
    "ReadEase has not been allowed to read the Apple Books folder. Grant access in System Settings, then open this tab again.",
  ],
  "noteserr.ambiguous": [
    "Apple Books đang có nhiều mục trùng mã cho cuốn này, nên chưa chọn được chắc chắn. Hãy mở lại Apple Books rồi thử lại.",
    "Apple Books lists more than one entry under this book's id, so it cannot be chosen safely. Reopen Apple Books and try again.",
  ],
  "noteserr.book_gone": [
    "Cuốn sách này không còn trong thư viện Apple Books. Mở lại mục này để làm mới.",
    "That book is no longer in the Apple Books library. Reopen this tab to refresh.",
  ],
  "setup.title": ["Chuẩn bị giọng đọc tiếng Việt", "Set up Vietnamese voice"],
  "setup.description": ["Tải một lần, sau đó đọc hoàn toàn offline.", "Download once, then read fully offline."],
  "setup.quality": ["Chất lượng giọng đọc", "Voice quality"],
  "setup.ready": ["Sẵn sàng tải giọng đọc.", "Ready to download voice data."],
  "setup.prepare": ["Chuẩn bị giọng đọc", "Set up voice"],
  "reader.selection": ["Đọc phần đã chọn", "Read selection"],
  "player.warming": ["Đang chuẩn bị giọng đọc…", "Preparing the voice…"],
  "engine.starting": ["Đang chuẩn bị giọng đọc…", "Preparing the voice…"],
  "milestone.later": [
    "Màn hình này sang bản Tauri ở mốc sau.",
    "This screen moves to the Tauri build in a later milestone.",
  ],
} as const;

export type TextKey = keyof typeof TEXT;

// One module-level language: every screen reads it through text(), and the
// app re-renders the whole tree (key={language}) when it changes - the same
// retranslate-everything shape the Qt shell used.
let current: Language = "vi";

export function setLanguage(language: Language): void {
  current = language;
}

export function currentLanguage(): Language {
  return current;
}

export function text(key: TextKey,
                     values: Record<string, string | number> = {}): string {
  let result: string = TEXT[key][current === "vi" ? 0 : 1];
  for (const [name, value] of Object.entries(values)) {
    result = result.replace(`{${name}}`, String(value));
  }
  return result;
}
