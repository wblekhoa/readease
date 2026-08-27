"""User-safe book import failures."""


class BookImportError(Exception):
    """Base class for a book the application could not import."""


class UnsupportedBookError(BookImportError):
    """The input is valid but outside the supported MVP formats/features."""


class CorruptBookError(BookImportError):
    """The input is malformed, unsafe, encrypted, or missing reading content."""


class LibraryStorageError(BookImportError):
    """The local managed library could not complete an import."""
