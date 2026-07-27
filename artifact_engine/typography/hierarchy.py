"""Type hierarchy — sizes come only from Theme (never from the LLM)."""
from __future__ import annotations

from artifact_engine.model.theme import Theme


def heading_size(theme: Theme, level: int) -> float:
    return {1: theme.h1, 2: theme.h2, 3: theme.h3}.get(level, theme.h2)


def body_size(theme: Theme, style: str = "body") -> float:
    if style == "lead":
        return theme.body + 1
    if style in ("caption", "note"):
        return theme.caption
    return theme.body
