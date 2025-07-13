class LargeFileError(Exception):
    """Base exception for largefile operations."""

    pass


class FileAccessError(LargeFileError):
    """File cannot be read/written."""

    pass


class SearchError(LargeFileError):
    """Search operation failed."""

    pass


class EditError(LargeFileError):
    """Edit operation failed."""

    pass


class TreeSitterError(LargeFileError):
    """Tree-sitter parsing failed."""

    pass
