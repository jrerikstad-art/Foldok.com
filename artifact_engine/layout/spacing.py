"""Vertical rhythm and semantic spacing — theme-driven, points."""
from __future__ import annotations

from dataclasses import dataclass

from artifact_engine.model.theme import Theme


@dataclass(frozen=True)
class Spacing:
    baseline: float
    space_xs: float
    space_sm: float
    space_md: float
    space_lg: float
    space_xl: float
    space_2xl: float
    space_section: float
    after_h1: float
    after_h2: float
    after_h3: float
    after_paragraph: float
    after_block: float
    before_section: float
    after_hero: float

    @classmethod
    def from_theme(cls, theme: Theme) -> "Spacing":
        b = theme.baseline_pt
        return cls(
            baseline=b,
            space_xs=4.0,
            space_sm=8.0,
            space_md=12.0,
            space_lg=20.0,
            space_xl=32.0,
            space_2xl=48.0,
            space_section=56.0,
            after_h1=b * 1.5,
            after_h2=b,
            after_h3=b * 0.75,
            after_paragraph=b,
            after_block=b * 1.25,
            before_section=56.0,
            after_hero=b * 2,
        )

    @classmethod
    def from_design(cls, ds) -> "Spacing":
        b = float(getattr(ds, "baseline", 12.0) or 12.0)
        return cls(
            baseline=b,
            space_xs=float(getattr(ds, "space_xs", 4.0)),
            space_sm=float(getattr(ds, "space_sm", 8.0)),
            space_md=float(getattr(ds, "space_md", 12.0)),
            space_lg=float(getattr(ds, "space_lg", 20.0)),
            space_xl=float(getattr(ds, "space_xl", 32.0)),
            space_2xl=float(getattr(ds, "space_2xl", 48.0)),
            space_section=float(getattr(ds, "space_section", 56.0)),
            after_h1=b * 1.5,
            after_h2=b,
            after_h3=b * 0.75,
            after_paragraph=b,
            after_block=b * 1.25,
            before_section=float(getattr(ds, "space_section", 56.0)),
            after_hero=b * 2,
        )


def section_gap_pt(theme: Theme) -> float:
    return Spacing.from_theme(theme).before_section


def block_gap_pt(theme: Theme) -> float:
    return Spacing.from_theme(theme).after_block
