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
  "paste.over_limit": ["Nội dung dài hơn giới hạn - hãy bớt lại rồi đọc.", "Longer than the limit - trim it, then read."],
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
  "reader.open_failed": [
    "Không mở được sách này. Sách vẫn còn trong thư viện - lần này ứng dụng chưa đọc được nội dung.",
    "This book would not open. It is still in your library - the app just could not read it this time.",
  ],
  "reader.toc_title": ["Mục lục", "Contents"],
  "reader.toc_hide": ["Ẩn mục lục", "Hide contents"],
  "reader.toc_show": ["Hiện mục lục", "Show contents"],
  "reader.text_smaller": ["Chữ nhỏ hơn", "Smaller text"],
  "reader.text_larger": ["Chữ lớn hơn", "Larger text"],
  "reader.settings": ["Cài đặt đọc", "Reading settings"],
  "reader.search": ["Tìm trong sách", "Search in book"],
  "reader.search_placeholder": ["Tìm từ hoặc câu…", "Find a word or phrase…"],
  "reader.search_hint": ["Gõ ít nhất 2 chữ. Không cần dấu.", "Type at least 2 characters."],
  "reader.search_none": ["Không thấy trong sách này.", "Nothing in this book."],
  "reader.search_count": ["{n} kết quả", "{n} results"],
  "reader.search_capped": ["Hiện {n} kết quả đầu - gõ rõ hơn để thu hẹp.", "Showing the first {n} - type more to narrow down."],
  "settings.text_size": ["Cỡ chữ", "Text size"],
  "settings.text_size_level": ["Cỡ chữ - mức {n}/{total}", "Text size - level {n} of {total}"],
  "settings.appearance": ["Giao diện", "Appearance"],
  "settings.light": ["Sáng", "Light"],
  "settings.dark": ["Tối", "Dark"],
  "settings.system": ["Theo máy", "System"],
  "settings.layout": ["Bố cục", "Layout"],
  "settings.pages": ["Trang", "Pages"],
  "settings.scroll": ["Cuộn", "Scroll"],
  "settings.customize": ["Tuỳ chỉnh", "Customize"],
  "settings.line_spacing": ["Giãn dòng", "Line spacing"],
  "settings.margins": ["Lề", "Margins"],
  "settings.spacing_tight": ["Chặt", "Tight"],
  "settings.spacing_normal": ["Vừa", "Normal"],
  "settings.spacing_loose": ["Thoáng", "Loose"],
  "settings.margin_tight": ["Hẹp", "Narrow"],
  "settings.margin_normal": ["Vừa", "Medium"],
  "settings.margin_loose": ["Rộng", "Wide"],
  "settings.columns": ["Số cột", "Columns"],
  "settings.columns_auto": ["Tự động", "Auto"],
  "settings.columns_pages_only": ["Chỉ dùng được khi đọc theo trang.", "Only applies when reading in pages."],
  "settings.justify": ["Canh đều hai bên", "Justify text"],
  "settings.bold": ["Chữ đậm", "Bold text"],
  "settings.reset": ["Đặt lại mặc định", "Reset to defaults"],
  "reader.follow": ["Về chỗ đang đọc", "Back to reading position"],
  "reader.mode_pages": ["Chuyển sang cuộn", "Switch to scroll"],
  "reader.mode_scroll": ["Chuyển sang lật trang", "Switch to pages"],
  "reader.page_of": ["Trang {page}/{total}", "Page {page} of {total}"],
  "reader.page_info": ["Vị trí đang đọc", "Where you are"],
  "player.settings": ["Cài đặt giọng đọc", "Voice settings"],
  "player.resume_goto": ["Bấm để tới chỗ này", "Go to this passage"],
  "player.play_resume": ["Đọc tiếp", "Continue"],
  "player.play_start": ["Đọc từ đầu", "Read from the start"],
  "player.hint_click": ["Nhấn vào đoạn văn để đọc từ đó", "Click a paragraph to read from there"],
  "player.reading_book": ["Đang đọc: {title}", "Reading: {title}"],
  "player.reading_paste": ["Đang đọc nội dung đã dán", "Reading the pasted text"],
  "player.reading_external": ["Đang đọc phần đã quét", "Reading the scanned selection"],
  "player.return": ["Quay lại", "Go back"],
  "aria.theme_to_light": ["Chuyển sang nền sáng", "Switch to light"],
  "aria.theme_to_dark": ["Chuyển sang nền tối", "Switch to dark"],
  "notes.title": ["Highlight và ghi chú", "Highlights and notes"],
  "notes.empty": ["Sách này chưa có highlight nào.", "Nothing marked in this book yet."],
  "notes.remove_failed": [
    "Chưa xoá được ghi chú này - nó vẫn còn nguyên.",
    "That note could not be removed - it is still here.",
  ],
  "notes.kind_highlight": ["Highlight", "Highlight"],
  "notes.kind_note": ["Highlight kèm ghi chú", "Highlight with a note"],
  "notes.remove": ["Xoá", "Delete"],
  "notes.remove_confirm": ["Xoá hẳn, đồng bộ lại cũng không quay về?", "Delete for good, even on a re-sync?"],
  "notes.open": ["Highlight và ghi chú", "Highlights and notes"],
  "notes.count": ["{count} highlight", "{count} highlights"],
  "reader.note_open": ["Xem ghi chú", "Read this note"],
  "reader.note_edit": ["Sửa ghi chú", "Edit this note"],
  "reader.note_placeholder": ["Ghi chú của bạn…", "Your note…"],
  "reader.note_save": ["Lưu", "Save"],
  "reader.note_cancel": ["Huỷ", "Cancel"],
  "reader.note_save_failed": [
    "Chưa lưu được ghi chú - nội dung cũ vẫn còn nguyên.",
    "The note could not be saved - the old one is still here.",
  ],
  "reader.note_gone": [
    "Highlight này không còn nữa, nên ghi chú không lưu được.",
    "That highlight is gone, so the note could not be saved.",
  ],
  "voices.title": ["Danh sách giọng đọc", "Voices"],
  "voices.caption": ["Nghe thử, rồi bật những giọng bạn muốn đổi nhanh khi đang đọc.", "Listen, then switch on the voices you want to swap between while reading."],
  "voices.manage": ["Quản lý giọng…", "Manage voices…"],
  "voices.in_use": ["đang dùng", "in use"],
  "voices.preview": ["Nghe thử", "Preview"],
  "voices.stop_preview": ["Dừng nghe thử", "Stop preview"],
  "voices.preview_while_reading": ["Đang đọc nên không nghe thử được - máy đọc mỗi lúc một giọng.", "No preview while reading - the engine speaks one thing at a time."],
  "voices.in_switcher": ["Đưa {name} vào danh sách đổi nhanh", "Keep {name} in the quick switcher"],
  "voices.marked": ["Đã chọn {count} giọng để đổi nhanh.", "{count} voices marked for quick switching."],
  "voices.paid": ["Trả phí", "Paid"],
  "voices.pick": ["Chọn giọng…", "Pick a voice…"],
  "voices.search": ["Tìm giọng…", "Search voices…"],
  "voices.filter_provider": ["Nhà cung cấp", "Provider"],
  "voices.filter_all_providers": ["Tất cả nhà cung cấp", "All providers"],
  "voices.filter_all": ["Tất cả", "All"],
  "voices.filter_gender": ["Giới tính", "Gender"],
  "voices.gender_all": ["Tất cả giới tính", "All genders"],
  "voices.gender_male": ["Nam", "Male"],
  "voices.gender_female": ["Nữ", "Female"],
  "voices.speaks_vi": ["Tiếng Việt", "Vietnamese"],
  "voices.speaks_en": ["Tiếng Anh", "English"],
  "voices.group_local": ["Trên máy", "On this Mac"],
  "voices.no_match": [
    "Không có giọng nào khớp \"{query}\".",
    "No voice matches \"{query}\".",
  ],
  "voices.no_filter_match": [
    "Không có giọng nào khớp bộ lọc này.",
    "No voice matches these filters.",
  ],
  "voices.none_api": ["Chưa chọn giọng API nào", "No API voice on your list"],
  "voices.none_api_hint": [
    "Khoá dùng được, nhưng danh sách đọc chưa có giọng nào từ API.",
    "The key works; your reading list just has no API voice on it yet.",
  ],
  "section.keys": ["Khoá API", "API keys"],
  "section.reading_api": ["Đọc bằng API", "Reading with the API"],
  "section.reading_local": ["Đọc trên máy", "Reading on this Mac"],
  "voices.source_local": ["Trên máy", "On this Mac"],
  "voices.source_api": ["API", "API"],
  "voices.source": ["Giọng đọc bằng", "Read with"],
  "key.set": ["Đã có khoá", "Key saved"],
  "key.unset": ["Chưa có khoá", "No key yet"],
  "key.add": ["Thêm khoá", "Add key"],
  "key.change": ["Đổi khoá", "Change key"],
  "key.save": ["Lưu", "Save"],
  "key.cancel": ["Huỷ", "Cancel"],
  "key.placeholder": ["Dán khoá vào đây", "Paste the key here"],
  "key.local_only": [
    "Khoá nằm trên máy này, quyền 0600, và không bao giờ được gửi đi đâu ngoài chính nhà cung cấp đó.",
    "The key stays on this Mac at 0600, and never goes anywhere but that provider.",
  ],
  "key.checking": ["Đang kiểm…", "Checking…"],
  "key.model": ["Mô hình", "Model"],
  "key.model_price": ["{usd}/1k {unit}", "{usd}/1k {unit}"],
  "unit.characters": ["ký tự", "characters"],
  "unit.credits": ["credit", "credits"],
  "key.refused": [
    "Khoá này chưa dùng được - nhà cung cấp không trả về giọng nào.",
    "That key does not work yet - the provider returned no voices.",
  ],
  "key.none_yet": [
    "Thêm khoá của một nhà cung cấp để chọn giọng của họ. Giá hiện ngay trong nút đọc.",
    "Add a provider's key to pick their voices. The price shows in the read button.",
  ],
  "cost.title": ["Giọng trả phí", "Paid voice"],
  "cost.open": ["Chi phí và phạm vi", "Cost and scope"],
  "cost.measuring": ["Đang tính…", "Working it out…"],
  /* The figure is a CEILING for the whole scope, not the cost of this one
     press: a click on a paragraph carries the same scope and can start
     anywhere inside it. Saying "tối đa" is what makes the number true for
     every way of starting a reading (owner chose this, 04/09). */
  "cost.at_most": ["tối đa {usd}", "up to {usd}"],
  "cost.unavailable": ["chưa có giá", "no price yet"],
  "cost.failed": [
    "Chưa tính được giá cho giọng này, nên nút đọc còn khoá - sẽ không có chuyện tiêu tiền mà chưa biết bao nhiêu.",
    "The price for this voice could not be worked out, so the read button stays locked - no spending before you know the sum.",
  ],
  "cost.scope": ["Đọc tới đâu", "How far to read"],
  "cost.scope_chapters": ["{count} chương", "{count} chapters"],
  "cost.scope_one": ["Chương này", "This chapter"],
  "cost.scope_all": ["Hết sách", "To the end"],
  "cost.detail": [
    "Nhiều nhất {chars} ký tự · {chapters} chương · giá tham khảo {date}",
    "At most {chars} characters · {chapters} chapters · price quoted {date}",
  ],
  "cost.detail_text": [
    "{chars} ký tự · giá tham khảo {date}",
    "{chars} characters · price quoted {date}",
  ],
  "cost.units": ["≈ {units} {unit}", "≈ {units} {unit}"],
  "cost.unit_characters": ["ký tự", "characters"],
  "cost.unit_credits": ["credit", "credits"],
  "cost.budget": ["Dừng lại khi đã tiêu", "Stop once spent"],
  "cost.budget_off": ["Không đặt trần", "No ceiling"],
  "cost.spent": ["Phiên này đã tiêu {usd}", "Spent this session: {usd}"],
  "cost.free": ["Giọng trên máy - không tốn gì.", "The voice on this Mac - it costs nothing."],
  "voiceerr.no_key": [
    "Chưa có khoá cho giọng này. Thêm khoá trong phần giọng đọc, hoặc chọn giọng trên máy.",
    "No key for this voice yet. Add one in the voice settings, or pick the voice on this Mac.",
  ],
  "voiceerr.bad_key": [
    "Nhà cung cấp từ chối khoá này. Kiểm tra lại khoá trong phần giọng đọc.",
    "The provider refused this key. Check it in the voice settings.",
  ],
  "voiceerr.quota": [
    "Tài khoản bên đó đã hết lượt. Nạp thêm, hoặc đọc tiếp bằng giọng trên máy.",
    "That account is out of credit. Top it up, or carry on with the voice on this Mac.",
  ],
  "voiceerr.rate_limit": [
    "Gửi hơi nhanh. Đợi một chút rồi đọc tiếp.",
    "Too fast for them. Wait a moment and read on.",
  ],
  "voiceerr.network": [
    "Không nối được tới nhà cung cấp - chưa tốn gì cả.",
    "Could not reach the provider - nothing was charged.",
  ],
  "voiceerr.provider_down": [
    "Nhà cung cấp đang lỗi bên họ. Thử lại sau, hoặc dùng giọng trên máy.",
    "The provider is broken on their side. Try later, or use the voice on this Mac.",
  ],
  "voiceerr.refused": [
    "Nhà cung cấp từ chối đoạn này.",
    "The provider refused this passage.",
  ],
  "voiceerr.wrong_language": [
    "Giọng trên máy chỉ đọc được tiếng Việt. Chọn một giọng đọc được tiếng Anh trong phần giọng đọc.",
    "The voice on this Mac reads Vietnamese only. Pick a voice that reads English in the voice settings.",
  ],
  "voiceerr.budget": [
    "Đã chạm trần chi tiêu bạn đặt. Nâng trần trong phần chi phí, hoặc đọc bằng giọng trên máy.",
    "You have hit the ceiling you set. Raise it under cost, or read with the voice on this Mac.",
  ],
  "voices.unavailable": [
    "Chưa lấy được danh sách giọng đọc - không phải máy này không có giọng nào.",
    "The voice list could not be fetched - this is not the same as having no voices.",
  ],
  "voices.sample": ["Tôi sẽ đọc sách cho bạn nghe bằng giọng này.", "Tôi sẽ đọc sách cho bạn nghe bằng giọng này."],
  "voices.filters": ["Lọc danh sách", "Filter the list"],
  "voices.language": [
    "Cuốn này đọc bằng",
    "This book is read in",
  ],
  "voices.language_vi": ["Tiếng Việt", "Vietnamese"],
  "voices.language_en": ["Tiếng Anh", "English"],
  // What the dot on an option means. A suggestion, not a correction: the
  // reader's choice stands until they tap the other one.
  "voices.language_suggested": [
    "{name}: nội dung cuốn sách đọc ra thứ tiếng này",
    "{name} - the book's own text reads as this",
  ],
  "voices.none_for_language": [
    "Chưa có giọng nào đọc được ngôn ngữ của cuốn này. Giọng trên máy chỉ đọc tiếng Việt; thêm khoá API để dùng giọng từ xa.",
    "No voice here reads this book's language. The voice on this Mac reads Vietnamese only; add an API key for a remote one.",
  ],
  "voices.hidden_for_language": [
    "Đã ẩn {count} giọng không đọc được ngôn ngữ của cuốn này.",
    "{count} voices that do not read this book's language are hidden.",
  ],
  "voices.switch": ["Đổi giọng", "Change voice"],
  "voices.switched": ["Đang đọc tiếp bằng giọng {name}.", "Reading on with {name}."],
  "player.settings_open": ["Cài đặt giọng đọc", "Voice settings"],
  "reader.prev_page": ["Trang trước", "Previous page"],
  "reader.next_page": ["Trang sau", "Next page"],
  "reader.figure_unavailable": ["Không mở được hình này.", "This image could not be loaded."],
  "reader.figure_label": ["Hình {n}", "Figure {n}"],
  "reader.figure_open": ["Xem ảnh lớn", "View larger"],
  "reader.figure_close": ["Đóng ảnh", "Close image"],
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
  "library.progress": ["Đã đọc {percent}%", "{percent}% read"],
  "library.at_chapter": ["Đang ở: {chapter}", "At: {chapter}"],
  "library.open_book": ["Mở {title}", "Open {title}"],
  "library.remove": ["Xoá", "Remove"],
  "library.remove_confirm": ["Xoá khỏi thư viện?", "Remove from the library?"],
  "library.remove_keep": ["Giữ lại", "Keep"],
  "library.removed": ["Đã xoá khỏi thư viện.", "Removed from the library."],
  "library.load_failed": [
    "Không mở được thư viện. Sách trên máy KHÔNG bị xoá - ứng dụng chỉ chưa đọc được danh sách.",
    "Could not open the library. Nothing on this Mac was deleted - the app just could not read the list.",
  ],
  "library.from_apple_books": ["Từ Apple Books · còn cặp nối, đồng bộ ghi chú sẽ tìm đúng cuốn này", "From Apple Books - still paired, so a note sync finds this book"],
  "library.apple_books": ["Từ Apple Books", "From Apple Books"],
  "apple.title": ["Sách trong Apple Books", "Books in Apple Books"],
  "apple.one_way": [
    "Một chiều: chỉ đọc từ Apple Books, không ghi ngược lại.",
    "One way: read from Apple Books, never written back.",
  ],
  "apple.search": ["Tìm theo tên sách, hoặc gõ \"drm\", \"ghi chú\"…", "Search by title, or type \"drm\", \"highlights\"…"],
  "apple.no_match": ["Không có sách nào khớp.", "No book matches."],
  "apple.group_importable": ["Nhập được", "Ready to import"],
  "apple.group_linked": ["Đã có trong thư viện", "Already in the library"],
  "apple.group_blocked": ["Không nhập được", "Cannot be imported"],
  "apple.sync_count": ["Đồng bộ {count} cuốn", "Sync {count} books"],
  "apple.nothing_to_do": ["Mọi thứ đã đồng bộ.", "Everything is in sync."],
  "apple.ready_summary": ["{importable} nhập được · {linked} đã có · {blocked} không nhập được", "{importable} to import · {linked} in library · {blocked} blocked"],
  "apple.sync_all": ["Đồng bộ tất cả", "Sync everything"],
  "apple.import": ["Nhập", "Import"],
  "apple.import_options": ["Tuỳ chọn nhập", "Import options"],
  "apple.import_only": ["Chỉ nhập sách", "Book only"],
  "apple.import_highlights": ["Nhập kèm highlight", "With highlights"],
  "apple.import_notes": ["Nhập kèm ghi chú", "With notes"],
  "apple.import_both": ["Nhập kèm highlight và ghi chú", "With highlights and notes"],
  "apple.sync_options": ["Đồng bộ ghi chú", "Sync highlights"],
  "apple.sync_highlights": ["Chỉ highlight", "Highlights only"],
  "apple.sync_notes_only": ["Chỉ ghi chú", "Notes only"],
  "apple.sync_both": ["Highlight và ghi chú", "Highlights and notes"],
  "apple.default": ["mặc định", "default"],
  "apple.sync_notes": ["Đồng bộ ghi chú", "Sync highlights"],
  "apple.highlights": ["{count} ghi chú", "{count} highlights"],
  "apple.no_highlights": ["Chưa có ghi chú", "No highlights"],
  "apple.status_linked": ["Đã có trong thư viện", "In the library"],
  "apple.paired": ["Ghép với: {title}", "Paired with: {title}"],
  "apple.status_encrypted": ["Có DRM, không sao chép được", "Encrypted, cannot be copied"],
  "apple.status_too_large": ["Quá lớn (trên 200 MB)", "Too large (over 200 MB)"],
  "apple.status_missing": ["Không thấy tệp sách", "Book file not found"],
  "apple.working": ["{done}/{total} · {title}", "{done}/{total} · {title}"],
  "apple.summary": [
    "Đã nhập {imported} sách · {matched} ghi chú khớp · {unmatched} không tìm thấy trong sách",
    "{imported} books imported · {matched} highlights matched · {unmatched} not found in the text",
  ],
  "apple.empty": ["Apple Books chưa có sách nào.", "Apple Books has no books."],
  "apple.error.not_permitted": [
    "macOS chưa cho ReadEase đọc thư mục Apple Books. Cấp quyền Full Disk Access rồi thử lại.",
    "macOS has not let ReadEase read the Apple Books folder. Grant Full Disk Access and try again.",
  ],
  "apple.error.encrypted": ["Sách này có DRM, không sao chép được.", "This book is encrypted and cannot be copied."],
  "apple.error.too_large": ["Sách này quá lớn để nhập.", "This book is too large to import."],
  "apple.error.book_missing": ["Không thấy tệp của sách này.", "This book's file could not be found."],
  "apple.error.not_in_library": ["Nhập sách trước rồi mới đồng bộ ghi chú.", "Import the book first, then sync its highlights."],
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
  "external.history_clear": ["Xoá lịch sử", "Clear history"],
  "external.history_empty": [
    "Chưa có gì. Danh sách này mất khi đóng ReadEase.",
    "Nothing yet. This list is gone when ReadEase closes.",
  ],
  "external.replay": ["Nghe lại phần đã chọn", "Read the selection again"],
  "external.open_text": ["Xem toàn văn", "Show the whole passage"],
  "external.close_text": ["Thu gọn", "Collapse"],
  "external.read_from_here": ["Đọc từ đoạn này", "Read from this part"],
  "external.focus_one": ["Xem riêng đoạn này", "Show only this passage"],
  "external.focus_back": ["Về danh sách", "Back to the list"],
  "external.parts_loading": ["Đang mở nội dung…", "Opening the passage..."],
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
  "model.cancel": ["Huỷ tải", "Cancel download"],
  "model.cancelled": ["Đã huỷ tải. Bản đang dùng giữ nguyên.", "Download cancelled. The build in use is unchanged."],
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
  "transfer.swap": ["Đảo hai cuốn", "Swap the two books"],
  "transfer.pick_two": ["Chọn hai cuốn khác nhau để xem trước.", "Pick two different books to preview."],
  "transfer.kind_note": ["Ghi chú", "Note"],
  "transfer.kind_highlight": ["Đoạn bôi màu", "Highlight"],
  "transfer.no_text": ["(không có chữ kèm theo)", "(no text attached)"],
  "transfer.verdict_same": ["Chuyển được nguyên vẹn", "Carries over as-is"],
  "transfer.verdict_review": ["Chương này khác nhau", "That chapter differs"],
  "transfer.verdict_already": ["Đã có ở cuốn kia", "Already in the other copy"],
  "transfer.count": ["Sẽ chép {count} mục.", "{count} items would be copied."],
  "transfer.truncated": ["Đang hiện {shown} mục đầu.", "Showing the first {shown}."],
  "transfer.left_out": [
    "{count} mục còn lại không được chép.",
    "The other {count} are not copied.",
  ],
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

/** A number with two decimals, parted the way the reading language parts one.
 * Vietnamese writes 1,70; English writes 1.70. A control should not know
 * this, so it takes the string already written (see `Slider`). */
export function decimal(value: number, places = 2): string {
  return value.toFixed(places).replace(".", currentLanguage() === "vi" ? "," : ".");
}

export function text(key: TextKey,
                     values: Record<string, string | number> = {}): string {
  let result: string = TEXT[key][current === "vi" ? 0 : 1];
  for (const [name, value] of Object.entries(values)) {
    result = result.replace(`{${name}}`, String(value));
  }
  return result;
}


/* ---------------------------------------------------------------------------
 * What the ENGINE says, in the reader's language.
 *
 * The table above is the shell's own wording. This one is not: these are the
 * sentences the Python engine writes - an EPUB that will not parse, a PDF with
 * no text layer, a library written by a newer build - and the engine writes
 * every one of them in Vietnamese, whatever language the interface is set to.
 * They were ported verbatim from the Qt shell's ui/i18n.py, the same way the
 * static table above was, and for the same reason: the shell that ships is the
 * one that has to say them.
 *
 * They reach the screen through a transport wrapper. `engine.rs` formats a
 * refusal as `engine refused <method>: <what the engine said>`, and nothing on
 * this side ever took that apart - so a reader met
 * `engine refused library.import: PDF không có lớp văn bản; …`, with the
 * plumbing showing, in Vietnamese, in an English interface. Stripping the
 * wrapper is not cosmetic here: an exact-match lookup can never fire while the
 * sentence is still wearing it.
 *
 * Lookup order mirrors the Python `Localizer.runtime`: exact table first, then
 * the patterns, then the message unchanged. An unrecognised sentence keeps its
 * own words - a message nobody wrote a translation for is still a true message,
 * and must not be swallowed.
 * ------------------------------------------------------------------------ */

const RUNTIME_EN: Record<string, string> = {
  "không": "zero",
  "một": "one",
  "bốn": "four",
  "năm": "five",
  "sáu": "six",
  "bảy": "seven",
  "tám": "eight",
  "chín": "nine",
  "mười": "ten",
  " mươi": "-ty",
  "mốt": "one",
  "tư": "four",
  "lăm": "five",
  "thứ ": "number ",
  "thứ nhất": "first",
  "thứ tư": "fourth",
  "ReadEase chưa được phép đọc thư mục Apple Books.": "ReadEase has not been allowed to read the Apple Books folder.",
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
  "Không tìm thấy nội dung đang chọn.": "No selected text was found.",
  "ReadEase cần quyền Trợ năng để gửi lệnh sao chép tới ứng dụng bạn đang dùng. Hãy bật ReadEase trong Cài đặt hệ thống > Quyền riêng tư & Bảo mật > Trợ năng rồi thử lại.": "ReadEase needs Accessibility permission to send the copy command to the app you are using. Enable ReadEase in System Settings > Privacy & Security > Accessibility, then try again.",
  "Không tìm thấy nội dung đang chọn. Hãy bôi đen phần muốn nghe rồi nhấn phím tắt đọc.": "No selected text was found. Select the text you want to hear, then press the read shortcut.",
  "Không quét đọc được từ cửa sổ này. Hãy chuyển sang ứng dụng có phần chữ bạn muốn nghe rồi thử lại.": "A selection cannot be read from this window. Switch to the app holding the text you want to hear, then try again.",
  "Phần đang chọn được đánh dấu là nội dung bí mật nên ReadEase không đọc.": "The selection is marked as concealed content, so ReadEase does not read it.",
  "Không đăng ký được phím tắt này; macOS hoặc ứng dụng khác đang dùng nó. Hãy chọn tổ hợp khác.": "This shortcut could not be registered; macOS or another app is already using it. Choose a different combination.",
  "ReadEase không thể xác nhận đã khôi phục clipboard nên đã dừng trước khi đọc.": "ReadEase could not confirm that the clipboard was restored, so it stopped before reading.",
  "Phím tắt quét đọc chưa sẵn sàng. Hãy mở lại ReadEase.": "The read-selection shortcut is not ready. Reopen ReadEase.",
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
  "Không tìm thấy dữ liệu Apple Books trên máy này.": "No Apple Books data was found on this Mac.",
  "Không đọc được dữ liệu Apple Books. Hãy thử lại sau.": "Could not read the Apple Books data. Try again in a moment.",
  "Chưa có bản sao lưu, nên không thể hoàn tác nếu sai.": "No backup was taken, so a mistake could not be undone.",
  "Apple Books đang mở. Hãy thoát Apple Books rồi thử lại.": "Apple Books is open. Quit Apple Books, then try again.",
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
  "EPUB có quá nhiều chú thích.": "The EPUB contains too many footnotes.",
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
};

/** Sentences carrying a number or a title, so they cannot be looked up whole.
 *
 * Ported from Python `re` to JS `RegExp`: the sources are identical, the
 * replacements changed `\1` to `$1`. Written with `new RegExp` rather than a
 * literal because four of them contain `/`. Matching emulates Python's
 * `fullmatch` (the whole string, not a part of it) by checking the match
 * covers everything - anchors are already in the sources, and this holds even
 * if one day one is not. */
const RUNTIME_PATTERNS: ReadonlyArray<readonly [RegExp, string]> = [
  [new RegExp("^Chương (\\d+)/(\\d+) · Đoạn (\\d+)/(\\d+)$"), "Chapter $1/$2 · Paragraph $3/$4"],
  [new RegExp("^Đang chuẩn bị đoạn (\\d+)/(\\d+)…$"), "Preparing part $1/$2…"],
  [new RegExp("^Đang đọc đoạn (\\d+)/(\\d+)$"), "Reading part $1/$2"],
  [new RegExp("^Đã tạm dừng · Đoạn (\\d+)/(\\d+)$"), "Paused · Part $1/$2"],
  [new RegExp("^(.+) có XML quá phức tạp\\.$"), "$1 contains XML that is too complex."],
  [new RegExp("^(.+) chứa khai báo XML không an toàn\\.$"), "$1 contains unsafe XML declarations."],
  [new RegExp("^(.+) không phải XML hợp lệ\\.$"), "$1 is not valid XML."],
  [new RegExp("^EPUB thiếu thành phần bắt buộc: (.+)\\.$"), "The EPUB is missing a required component: $1."],
  [new RegExp("^Thư viện này được tạo bởi bản ReadEase mới hơn \\(dữ liệu v(\\d+), bản này đọc tới v(\\d+)\\)\\. Hãy cài lại bản mới nhất\\.$"), "This library was written by a newer ReadEase (data v$1, this build reads up to v$2). Please install the latest version."],
  [new RegExp("^Không có bước nâng cấp dữ liệu lên v(\\d+)\\.$"), "No upgrade step to data v$1."],
  [new RegExp("^Nâng cấp dữ liệu từ v(\\d+) lên v(\\d+) không xong; thư viện được giữ nguyên như cũ\\.$"), "Upgrading data from v$1 to v$2 did not finish; the library was left exactly as it was."],
  [new RegExp("^(.+) - Nam Bộ$"), "$1 - Southern Vietnamese"],
  [new RegExp("^(.+) - Bắc Bộ$"), "$1 - Northern Vietnamese"],
];

/** The transport wrapper `engine.rs` puts around a refusal.
 *
 * Method names carry dots (`library.import`), hence `[\w.]`. Only the refusal
 * shape is stripped: `engine timeout on …`, `spawn engine: …` and `bad
 * payload: …` are this side's own words, already English, and are left alone
 * so a transport failure never gets dressed up as an engine sentence. */
const ENGINE_REFUSAL = /^engine refused [\w.]+: /;

/** One engine sentence, said in the language the interface is set to. */
export function runtime(message: string): string {
  if (currentLanguage() === "vi") return message;
  const exact = RUNTIME_EN[message];
  if (exact !== undefined) return exact;
  for (const [pattern, replacement] of RUNTIME_PATTERNS) {
    const found = pattern.exec(message);
    if (found && found[0] === message) return message.replace(pattern, replacement);
  }
  return message;
}

/** What to put in front of a person when an engine call was rejected.
 *
 * Takes the rejection whatever shape it arrived in, drops the transport
 * wrapper, and says the rest in their language. Both halves matter to both
 * languages: a Vietnamese reader stops seeing `engine refused library.import:`
 * in front of a sentence written for them, and an English one stops seeing the
 * sentence in Vietnamese. */
export function engineMessage(error: unknown): string {
  return runtime(String(error).replace(ENGINE_REFUSAL, ""));
}
