"""The content-pattern detectors, one receipt per kind."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from vieneu_reader.domain.content_patterns import (
    Finding, audit_book, audit_chapter, figure_references, is_image_annotation,
    is_short_block,
)
from vieneu_reader.domain.models import BookDocument, Chapter, Segment


def chapter(*blocks: tuple[str, str]) -> Chapter:
    segments = tuple(
        Segment(f"s{i}", "ch", i, text, kind)  # type: ignore[arg-type]
        for i, (text, kind) in enumerate(blocks)
    )
    return Chapter("ch", "Một", 0, segments)


def figure(fid: str, anchor: str, **extra) -> SimpleNamespace:
    base = dict(
        id=fid, anchor_segment_id=anchor, placement="after", alt_text="Sơ đồ",
        alt_is_generic=False, label=None, caption_segment_id=None, duplicate_of=None,
    )
    base.update(extra)
    return SimpleNamespace(**base)


def kinds(findings: list[Finding]) -> list[str]:
    return [f.kind for f in findings]


class DetectorTests(unittest.TestCase):
    def test_a_plain_captioned_figure_raises_nothing(self) -> None:
        ch = chapter(("Đoạn.", "paragraph"), ("Hình 1. Sơ đồ.", "caption"))
        found = audit_chapter(ch, [figure("f", "s0", caption_segment_id="s1", label="Hình 1")])
        self.assertEqual(found, [])

    def test_duplicate_is_a_rule_finding(self) -> None:
        ch = chapter(("Đoạn.", "paragraph"), ("Hình 1. Sơ đồ.", "caption"))
        found = audit_chapter(ch, [
            figure("f", "s0", caption_segment_id="s1", label="Hình 1"),
            figure("g", "s1", caption_segment_id="s1", label="Hình 1", duplicate_of="f"),
        ])
        self.assertEqual(kinds(found), ["figure_duplicate"])
        self.assertTrue(found[0].is_rule)

    def test_short_blocks_above_the_picture_are_reported_not_acted_on(self) -> None:
        ch = chapter(
            ("Đoạn dài kết thúc bằng dấu chấm.", "paragraph"),
            ("Trải nghiệm", "quote"), ("Phần cứng", "quote"),
            ("Hình 1.3. Sơ đồ.", "caption"),
        )
        found = audit_chapter(ch, [figure("f", "s2", caption_segment_id="s3", label="Hình 1.3")])
        self.assertEqual(kinds(found), ["short_block_before_figure"])
        self.assertEqual(found[0].segment_ids, ("s1", "s2"))
        self.assertEqual(found[0].detail, "Trải nghiệm | Phần cứng")
        self.assertFalse(found[0].is_rule)

    def test_annotation_alt_duplicate_generic_and_uncaptioned_are_reported(self) -> None:
        ch = chapter(
            ("Đoạn.", "paragraph"),
            ("Hình 1. Sơ đồ.", "caption"),
            ("Chú giải ảnh: ba lớp.", "paragraph"),
            ("Đoạn hai.", "paragraph"),
        )
        found = audit_chapter(ch, [
            figure("f", "s0", caption_segment_id="s1", label="Hình 1", alt_text="Hình 1. Sơ đồ."),
            figure("g", "s3", alt_text="Image", alt_is_generic=True),
        ])
        self.assertEqual(
            sorted(kinds(found)),
            ["alt_equals_caption", "generic_alt", "image_annotation", "uncaptioned_figure"],
        )

    def test_a_reference_to_a_missing_numbered_figure_is_reported(self) -> None:
        ch = chapter(("Xem thêm (xem Hình 8.1) ở đây.", "paragraph"), ("Hình 8.2. Sơ đồ.", "caption"))
        book = BookDocument(id="b", title="Sách", source_format="epub", source_hash="h", chapters=(ch,))
        presentation = SimpleNamespace(chapter=lambda cid: SimpleNamespace(
            figures=(figure("f", "s0", caption_segment_id="s1", label="Hình 8.2"),),
        ))
        found = audit_book(book, presentation)
        self.assertEqual(kinds(found), ["dangling_figure_reference"])
        self.assertEqual(found[0].detail, "8.1")

    def test_an_unnumbered_book_has_no_dangling_references(self) -> None:
        ch = chapter(("Nhìn (xem hình 3) nhé.", "paragraph"),)
        book = BookDocument(id="b", title="Sách", source_format="epub", source_hash="h", chapters=(ch,))
        presentation = SimpleNamespace(chapter=lambda cid: SimpleNamespace(figures=()))
        self.assertEqual(audit_book(book, presentation), [])

    def test_helpers(self) -> None:
        self.assertTrue(is_image_annotation("Chú giải ảnh: gì đó"))
        self.assertFalse(is_image_annotation("Chú giải ảnh bằng tiếng Việt."))
        self.assertEqual(figure_references("A (xem Hình 1.3) và (Hình 2)."), ["1.3", "2"])
        self.assertTrue(is_short_block(Segment("s", "c", 0, "Phần cứng", "quote")))
        self.assertFalse(is_short_block(Segment("s", "c", 0, "Phần cứng.", "paragraph")))
        self.assertFalse(is_short_block(Segment("s", "c", 0, "Một", "heading")))


if __name__ == "__main__":
    unittest.main()
