"""foldok_shred — measure documents; keep structure and numbers, never body text.

    from foldok_shred import Shredder
    shred = Shredder().shred("some_manual.pdf", grade="exemplary")
    print(shred.report())
    shred.proposals  # offered to the console queue, never applied

Flow (order is the product):
    read bytes → measure → build proposals → **drop the text** → return
"""

from .model import (
    GRADE_LEARNS,
    DesignProfile,
    Grade,
    Shred,
    ShredProposal,
    Skeleton,
)
from .shredder import Shredder, ShredRefused, consensus

__all__ = [
    "GRADE_LEARNS",
    "DesignProfile",
    "Grade",
    "Shred",
    "ShredProposal",
    "ShredRefused",
    "Shredder",
    "Skeleton",
    "consensus",
]

__version__ = "0.82.0"
