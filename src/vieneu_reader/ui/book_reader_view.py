"""Focused in-app reading surface for imported EPUB and PDF books."""

from __future__ import annotations

from PySide6.QtCore import (
    QBuffer,
    QEvent,
    QIODevice,
    QSize,
    QSignalBlocker,
    Qt,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QImageReader,
    QPalette,
    QTextBlock,
    QTextBlockFormat,
    QTextBlockUserData,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextImageFormat,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .controller import ChapterItem, FigureItem, SegmentItem
from .i18n import Localizer


_MAX_SOURCE_IMAGE_PIXELS = 40_000_000
_MAX_CHAPTER_DECODE_BYTES = 64 * 1024 * 1024
_MAX_RENDERED_IMAGE_WIDTH = 600
_MAX_RENDERED_IMAGE_HEIGHT = 900


class _SegmentBlockData(QTextBlockUserData):
    def __init__(self, segment_id: str):
        super().__init__()
        self.segment_id = segment_id


class BookReaderView(QWidget):
    """Own chapter navigation and selectable normalized book text."""

    backRequested = Signal()
    chapterActivated = Signal(str)
    segmentActivated = Signal(str)
    readSelectionRequested = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        localizer: Localizer | None = None,
    ):
        super().__init__(parent)
        self._localizer = localizer or Localizer()
        self.setObjectName("bookReaderView")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self.back_button = QPushButton()
        self.back_button.setObjectName("backToLibraryButton")
        header.addWidget(self.back_button)

        self.active_book_title = QLabel()
        self.active_book_title.setObjectName("activeBookTitle")
        title_font = QFont(self.active_book_title.font())
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        self.active_book_title.setFont(title_font)
        self.active_book_title.hide()
        header.addWidget(self.active_book_title)
        header.addStretch(1)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        chapters = QWidget()
        chapters.setMinimumWidth(250)
        chapters.setMaximumWidth(360)
        chapter_layout = QVBoxLayout(chapters)
        chapter_layout.setContentsMargins(0, 0, 8, 0)
        chapter_layout.setSpacing(8)
        self.chapter_label = QLabel()
        chapter_font = QFont(self.chapter_label.font())
        chapter_font.setBold(True)
        self.chapter_label.setFont(chapter_font)
        chapter_layout.addWidget(self.chapter_label)
        self.chapter_list = QListWidget()
        self.chapter_list.setObjectName("chapterList")
        self.chapter_list.setWordWrap(True)
        self.chapter_list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.chapter_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.chapter_list.setSpacing(3)
        chapter_layout.addWidget(self.chapter_list, 1)
        splitter.addWidget(chapters)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)
        self.reader_text = QTextBrowser()
        self.reader_text.setObjectName("readerText")
        self.reader_text.setReadOnly(True)
        self.reader_text.document().setDocumentMargin(24)
        self.reader_text.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.reader_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        reading_font = QFont(self.reader_text.font())
        reading_font.setPointSize(14)
        self.reader_text.setFont(reading_font)
        content_layout.addWidget(self.reader_text, 1)

        self.read_selection_button = QPushButton()
        self.read_selection_button.setObjectName("readSelectionButton")
        content_layout.addWidget(
            self.read_selection_button,
            alignment=Qt.AlignmentFlag.AlignRight,
        )
        splitter.addWidget(content)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        self._chapter_signature: tuple[tuple[str, str], ...] = ()
        self._segment_signature: tuple[tuple[str, str], ...] = ()
        self._figure_signature: tuple[tuple[object, ...], ...] = ()
        self._selection_allowed = False
        self._rendered_image_width_limit = 0
        self._rendered_segments: tuple[SegmentItem, ...] = ()
        self._rendered_figures: tuple[FigureItem, ...] = ()
        self._rendered_active_segment_id: str | None = None
        self._figure_resize_timer = QTimer(self)
        self._figure_resize_timer.setSingleShot(True)
        self._figure_resize_timer.timeout.connect(self._refresh_figures_after_resize)
        self.reader_text.viewport().installEventFilter(self)
        self.segment_blocks: dict[str, QTextBlock] = {}
        self.chapter_list.currentItemChanged.connect(self._chapter_changed)
        self.reader_text.cursorPositionChanged.connect(self._cursor_segment_changed)
        self.reader_text.selectionChanged.connect(self._update_selection_action)
        self.back_button.clicked.connect(self.backRequested.emit)
        self.read_selection_button.clicked.connect(self._emit_selection_request)
        self.retranslate()
        self._update_selection_action()

    def retranslate(self) -> None:
        self.back_button.setText(self._localizer.text("reader.back"))
        self.back_button.setAccessibleName(
            self._localizer.text("reader.back_accessible")
        )
        self.active_book_title.setAccessibleName(
            self._localizer.text("reader.book_title_accessible")
        )
        self.chapter_label.setText(self._localizer.text("reader.chapters"))
        self.chapter_list.setAccessibleName(
            self._localizer.text("reader.chapter_list_accessible")
        )
        self.reader_text.setAccessibleName(
            self._localizer.text("reader.content_accessible")
        )
        self.read_selection_button.setText(
            self._localizer.text("reader.selection")
        )
        self.read_selection_button.setAccessibleName(
            self._localizer.text("reader.selection_accessible")
        )
        self._update_figure_accessibility(self._rendered_figures)
        if self._rendered_segments:
            self._figure_signature = ()
            self.render_segments(
                self._rendered_segments,
                self._rendered_active_segment_id,
                self._rendered_figures,
            )

    def set_active_book_title(self, title: str) -> None:
        self.active_book_title.setText(title)
        self.active_book_title.setVisible(bool(title))

    def render_chapters(
        self,
        chapters: tuple[ChapterItem, ...],
        active_chapter_id: str | None,
    ) -> None:
        blocker = QSignalBlocker(self.chapter_list)
        signature = tuple((item.id, item.title) for item in chapters)
        if signature != self._chapter_signature:
            self.chapter_list.clear()
            for item in chapters:
                row = QListWidgetItem(item.title)
                row.setData(Qt.ItemDataRole.UserRole, item.id)
                self.chapter_list.addItem(row)
            self._chapter_signature = signature
        self._select_chapter(active_chapter_id)
        del blocker

    def render_segments(
        self,
        segments: tuple[SegmentItem, ...],
        active_segment_id: str | None,
        figures: tuple[FigureItem, ...] = (),
    ) -> None:
        self._rendered_segments = segments
        self._rendered_figures = figures
        self._rendered_active_segment_id = active_segment_id
        blocker = QSignalBlocker(self.reader_text)
        signature = tuple((item.id, item.text) for item in segments)
        image_width_limit = self._image_width_limit()
        figure_signature = tuple(
            (
                figure.id,
                figure.number,
                figure.anchor_segment_id,
                figure.placement,
                figure.alt_text,
                figure.width,
                figure.height,
                len(figure.image_bytes) if figure.image_bytes is not None else None,
            )
            for figure in figures
        )
        if (
            signature != self._segment_signature
            or figure_signature != self._figure_signature
        ):
            document = self.reader_text.document()
            document.clear()
            cursor = QTextCursor(document)
            self.segment_blocks = {}
            before: dict[str, list[FigureItem]] = {}
            after: dict[str, list[FigureItem]] = {}
            for figure in figures:
                target = before if figure.placement == "before" else after
                target.setdefault(figure.anchor_segment_id, []).append(figure)
            has_content = False
            decoded_bytes = 0
            for item in segments:
                for figure in before.get(item.id, ()):
                    has_content, used = self._insert_figure(
                        cursor,
                        figure,
                        has_content=has_content,
                        remaining_bytes=_MAX_CHAPTER_DECODE_BYTES - decoded_bytes,
                        max_rendered_width=image_width_limit,
                    )
                    decoded_bytes += used
                if has_content:
                    cursor.insertBlock()
                block = cursor.block()
                block.setUserData(_SegmentBlockData(item.id))
                cursor.insertText(item.text)
                self.segment_blocks[item.id] = block
                has_content = True
                for figure in after.get(item.id, ()):
                    has_content, used = self._insert_figure(
                        cursor,
                        figure,
                        has_content=has_content,
                        remaining_bytes=_MAX_CHAPTER_DECODE_BYTES - decoded_bytes,
                        max_rendered_width=image_width_limit,
                    )
                    decoded_bytes += used
            self._segment_signature = signature
            self._figure_signature = figure_signature
            self._rendered_image_width_limit = image_width_limit
        self._update_figure_accessibility(figures)
        self._highlight_segment(active_segment_id)
        del blocker
        self._update_selection_action()

    def set_selection_available(self, available: bool) -> None:
        self._selection_allowed = available
        self._update_selection_action()

    def _select_chapter(self, chapter_id: str | None) -> None:
        if chapter_id is None:
            self.chapter_list.setCurrentRow(-1)
            return
        for index in range(self.chapter_list.count()):
            item = self.chapter_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == chapter_id:
                self.chapter_list.setCurrentItem(item)
                return

    def _highlight_segment(self, segment_id: str | None) -> None:
        active_brush = QBrush(self.palette().color(QPalette.ColorRole.AlternateBase))
        for current_id, block in self.segment_blocks.items():
            cursor = QTextCursor(block)
            block_format = QTextBlockFormat(block.blockFormat())
            block_format.setTopMargin(8)
            block_format.setBottomMargin(12)
            block_format.setLineHeight(
                145.0,
                QTextBlockFormat.LineHeightTypes.ProportionalHeight.value,
            )
            block_format.setBackground(
                active_brush if current_id == segment_id else QBrush()
            )
            cursor.setBlockFormat(block_format)
        if (
            segment_id in self.segment_blocks
            and not self.reader_text.textCursor().hasSelection()
        ):
            cursor = QTextCursor(self.segment_blocks[segment_id])
            self.reader_text.setTextCursor(cursor)
            self.reader_text.ensureCursorVisible()

    def _chapter_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is None:
            return
        chapter_id = current.data(Qt.ItemDataRole.UserRole)
        if chapter_id:
            self.chapterActivated.emit(str(chapter_id))

    def _cursor_segment_changed(self) -> None:
        data = self.reader_text.textCursor().block().userData()
        if isinstance(data, _SegmentBlockData):
            self.segmentActivated.emit(data.segment_id)

    def _update_selection_action(self) -> None:
        self.read_selection_button.setEnabled(
            self._selection_allowed and self.reader_text.textCursor().hasSelection()
        )

    def _emit_selection_request(self) -> None:
        self.readSelectionRequested.emit(
            self.reader_text.textCursor().selectedText().replace("\ufffc", " ")
        )

    def _insert_figure(
        self,
        cursor: QTextCursor,
        figure: FigureItem,
        *,
        has_content: bool,
        remaining_bytes: int,
        max_rendered_width: int,
    ) -> tuple[bool, int]:
        if has_content:
            cursor.insertBlock()
        label_block = QTextBlockFormat()
        label_block.setTopMargin(22)
        label_block.setBottomMargin(8)
        cursor.setBlockFormat(label_block)
        label_format = QTextCharFormat()
        label_format.setForeground(QColor("#D42525"))
        label_format.setFontWeight(QFont.Weight.DemiBold)
        cursor.insertText(
            self._localizer.text("reader.figure", number=figure.number),
            label_format,
        )

        cursor.insertBlock()
        image, decoded_bytes = self._decode_figure(
            figure,
            remaining_bytes,
            max_rendered_width=max_rendered_width,
        )
        if image is None:
            placeholder = QTextCharFormat()
            placeholder.setForeground(self.palette().color(QPalette.ColorRole.PlaceholderText))
            cursor.insertText(
                self._localizer.text("reader.figure_unavailable"),
                placeholder,
            )
            return True, 0

        document = cursor.document()
        resource = QUrl(f"readease-figure:{figure.id}")
        document.addResource(QTextDocument.ResourceType.ImageResource, resource, image)
        image_format = QTextImageFormat()
        image_format.setName(resource.toString())
        image_alt = self._localizer.text("reader.figure", number=figure.number)
        if figure.alt_text and not figure.alt_is_generic:
            image_alt = figure.alt_text
            image_format.setToolTip(figure.alt_text)
        image_format.setProperty(QTextFormat.Property.ImageAltText, image_alt)
        image_format.setProperty(
            QTextFormat.Property.ImageTitle,
            self._localizer.text("reader.figure", number=figure.number),
        )
        image_format.setWidth(image.width())
        image_format.setHeight(image.height())
        cursor.insertImage(image_format)
        return True, decoded_bytes

    @staticmethod
    def _decode_figure(
        figure: FigureItem,
        remaining_bytes: int,
        *,
        max_rendered_width: int,
    ) -> tuple[QImage | None, int]:
        if figure.image_bytes is None or remaining_bytes <= 0:
            return None, 0
        buffer = QBuffer()
        buffer.setData(figure.image_bytes)
        if not buffer.open(QIODevice.OpenModeFlag.ReadOnly):
            return None, 0
        reader = QImageReader(buffer)
        reader.setDecideFormatFromContent(True)
        size = reader.size()
        if (
            not size.isValid()
            or size.width() <= 0
            or size.height() <= 0
            or size.width() * size.height() > _MAX_SOURCE_IMAGE_PIXELS
        ):
            return None, 0
        scale = min(
            1.0,
            max_rendered_width / size.width(),
            _MAX_RENDERED_IMAGE_HEIGHT / size.height(),
        )
        target = QSize(
            max(1, round(size.width() * scale)),
            max(1, round(size.height() * scale)),
        )
        decoded_bytes = target.width() * target.height() * 4
        if decoded_bytes > remaining_bytes:
            return None, 0
        if target != size:
            reader.setScaledSize(target)
        image = reader.read()
        if image.isNull():
            return None, 0
        return image, decoded_bytes

    def _image_width_limit(self) -> int:
        document_margin = round(self.reader_text.document().documentMargin())
        available = self.reader_text.viewport().width() - (2 * document_margin) - 4
        return max(1, min(_MAX_RENDERED_IMAGE_WIDTH, available))

    def _update_figure_accessibility(
        self,
        figures: tuple[FigureItem, ...],
    ) -> None:
        if not figures:
            self.reader_text.setAccessibleDescription(
                self._localizer.text("reader.content_description")
            )
            return
        descriptions = []
        for figure in figures:
            label = self._localizer.text("reader.figure", number=figure.number)
            if figure.alt_text and not figure.alt_is_generic:
                label = f"{label}: {figure.alt_text}"
            descriptions.append(label)
        self.reader_text.setAccessibleDescription(
            self._localizer.text(
                "reader.figures_description",
                count=len(figures),
                figures="; ".join(descriptions),
            )
        )

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._schedule_figure_resize_refresh()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if (
            watched is self.reader_text.viewport()
            and event.type() == QEvent.Type.Resize
        ):
            self._schedule_figure_resize_refresh()
        return super().eventFilter(watched, event)

    def _schedule_figure_resize_refresh(self) -> None:
        if not self._rendered_figures or self._figure_resize_timer.isActive():
            return
        self._figure_resize_timer.start(0)

    def _refresh_figures_after_resize(self) -> None:
        if (
            not self._rendered_figures
            or self._image_width_limit() == self._rendered_image_width_limit
        ):
            return
        cursor = self.reader_text.textCursor()
        selection = (
            (cursor.anchor(), cursor.position()) if cursor.hasSelection() else None
        )
        scroll_value = self.reader_text.verticalScrollBar().value()
        blocker = QSignalBlocker(self.reader_text)
        self._figure_signature = ()
        self.render_segments(
            self._rendered_segments,
            self._rendered_active_segment_id,
            self._rendered_figures,
        )
        if selection is not None:
            maximum = max(0, self.reader_text.document().characterCount() - 1)
            restored = QTextCursor(self.reader_text.document())
            restored.setPosition(min(selection[0], maximum))
            restored.setPosition(
                min(selection[1], maximum),
                QTextCursor.MoveMode.KeepAnchor,
            )
            self.reader_text.setTextCursor(restored)
        self.reader_text.verticalScrollBar().setValue(scroll_value)
        del blocker
        self._update_selection_action()
