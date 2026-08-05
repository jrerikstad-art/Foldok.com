"""Bridge: workbench index / disk folder → foldok_sense Draft.

``sense_from_index`` uses cached captions (fast, thin).
``sense_from_folder`` runs the full chain the audit measures:

    scan → extract → reflow → tier → claims → sense

That is what the app must call for generate — captions alone cannot invent
topics that only live in page text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .assemble import Draft, assemble, passages_from


def sense_from_index(
    index: Sequence[Mapping[str, Any]] | None,
    *,
    lang: str = "no",
    expected: Iterable[str] = (),
    title: str = "",
    include_candidates: bool = True,
    role: str = "project",
) -> Draft:
    """Make sense of an indexed folder (cache prose only)."""
    try:
        from foldok_tier import tier_report_from_index
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("foldok_tier is required for sense_from_index") from exc

    report = tier_report_from_index(index or [])
    passages = passages_from(
        report, role=role, include_candidates=include_candidates,
    )

    figures: list[dict[str, Any]] = []
    files: set[str] = set()
    for entry in index or []:
        if entry.get("kind") == "skipped":
            continue
        src = Path(str(entry.get("file") or "")).name
        if not src:
            continue
        files.add(src)
        for fig in entry.get("embedded_figures") or []:
            if not isinstance(fig, dict):
                continue
            row = dict(fig)
            row.setdefault("source", src)
            figures.append(row)

    return assemble(
        passages,
        figures=figures,
        title=title,
        files_read=len(files),
        sentences_seen=len(report.sentences),
        expected=expected,
        lang=lang,
    )


def sense_from_folder(
    folder: str | Path,
    *,
    lang: str = "no",
    expected: Iterable[str] = (),
    title: str = "",
    max_files: int = 200,
) -> Draft:
    """Full chain over files on disk — same path as ``python -m foldok_sense.audit``."""
    from .audit import audit

    root = Path(folder)
    result = audit(root, lang=lang, max_files=max_files)
    draft = result.draft
    if draft is None:
        return assemble([], title=title or root.name, lang=lang, expected=expected)

    # Re-run assemble with expected hopes if audit did not take them
    if expected:
        from .audit import audit as _audit  # noqa: F401 — keep import path stable
        # Patch absent list onto existing draft via re-assemble from passages
        passages = []
        for group in draft.groups:
            passages.extend(group.passages)
        figures = []
        for group in draft.groups:
            figures.extend(group.figures)
        figures.extend(draft.orphan_figures)
        draft = assemble(
            passages,
            figures=figures,
            title=title or draft.title or root.name,
            files_read=draft.files_read,
            sentences_seen=draft.sentences_seen,
            expected=expected,
            lang=lang,
        )
        # Preserve corroboration flag from the audit assemble when possible
        if result.draft is not None:
            draft.corroborated = bool(getattr(result.draft, "corroborated", True))
    elif title and not draft.title:
        draft.title = title
    return draft


def sense_markdown(
    index: Sequence[Mapping[str, Any]] | None = None,
    *,
    folder: str | Path | None = None,
    lang: str = "no",
    expected: Iterable[str] = (),
    title: str = "",
) -> str:
    """Convenience: draft markdown from folder (preferred) or index cache."""
    if folder:
        return sense_from_folder(
            folder, lang=lang, expected=expected, title=title,
        ).markdown(lang=lang)
    return sense_from_index(
        index, lang=lang, expected=expected, title=title,
    ).markdown(lang=lang)
