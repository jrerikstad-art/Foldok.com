"""Foldok scan — why isn't my file in the index?

    print(scan("/path/to/project").report())

Built after a folder reported "51 files found, 6 indexed" and explained none of
the other 45. Recursion was never the problem; the filters were, and none of
them announced itself.
"""

from .scan import (
    CAD_EXT,
    DOC_EXT,
    NEVER,
    PHOTO_EXT,
    RECOVERABLE,
    SKIP_DIRS,
    Entry,
    ScanReport,
    compare,
    scan,
    widened_doc_ext,
)

__all__ = [
    "CAD_EXT", "DOC_EXT", "Entry", "NEVER", "PHOTO_EXT", "RECOVERABLE",
    "SKIP_DIRS", "ScanReport", "compare", "scan", "widened_doc_ext",
]

__version__ = "0.91.0"
