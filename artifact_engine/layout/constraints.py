"""Hard layout rules — never guessed by the LLM."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LayoutConstraints:
    min_widow_lines: int = 2
    min_orphan_lines: int = 2
    keep_with_next: bool = True
    min_space_after_heading: float = 8.0
    max_image_height_ratio: float = 0.45
    table_header_repeat: bool = True
    allow_section_split: bool = True
    force_page_break_before: bool = False
