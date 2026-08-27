from vieneu_reader.domain.models import BookDocument, Chapter, Segment, stable_id


def sample_book(seed: str = "one") -> BookDocument:
    source_hash = stable_id("source", seed)
    book_id = stable_id(source_hash, "epub")
    chapter_id = stable_id(book_id, "chapter", "0")
    segments = (
        Segment(stable_id(chapter_id, "segment", "0"), chapter_id, 0, "Xin chào."),
        Segment(stable_id(chapter_id, "segment", "1"), chapter_id, 1, "Tiếng Việt."),
    )
    return BookDocument(
        id=book_id,
        title=f"Sách {seed}",
        source_format="epub",
        source_hash=source_hash,
        chapters=(Chapter(chapter_id, "Chương một", 0, segments),),
    )
