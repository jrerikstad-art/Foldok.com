"""Console bridge — shred proposals become queue Findings; never auto-applied.

    from foldok_shred.console_bridge import probe_shred, proposals_as_findings

Accept is a separate deliberate call (local_only). Measuring is not accepting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .model import Shred, ShredProposal
from .shredder import Shredder, ShredRefused


def proposals_as_findings(proposals: Iterable[ShredProposal], *, area: str = "shred") -> list[dict[str, Any]]:
    """Map shred proposals to console Finding kwargs (not applied)."""
    out: list[dict[str, Any]] = []
    for p in proposals:
        action = {
            "skeleton": "accept as a local section shell — or discard",
            "design": "accept as a local composition/design default — or discard",
            "requirement": "accept citations into foldok_learn lessons — or discard",
        }.get(p.kind, "accept into the local knowledge bay — or discard")
        out.append({
            "code": f"shred_{p.kind}",
            "title": p.title,
            "health": "warn",
            "detail": p.detail,
            "action": action,
            "effort": "minutes",
            "impact": 3 if p.kind == "requirement" else 2,
            "evidence": {
                "kind": p.kind,
                "confidence": p.confidence,
                "source": p.source,
                "payload": p.payload,
            },
            "area": area,
        })
    return out


def probe_shred(
    root: str | Path,
    *,
    bay: str | Path | None = None,
    grade: str = "exemplary",
) -> Any:
    """Console panel: optional knowledge-bay folder of reference docs.

    Failure-tolerant: missing bay or missing package → empty/warn panel, never crash.
    """
    try:
        from foldok_console.model import Panel
    except ImportError:  # pragma: no cover
        return None

    panel = Panel(area="shred", title="Shredder bay")
    root = Path(root)
    bay_path = Path(bay) if bay else root / ".foldok" / "shred_bay"
    panel.metrics["bay"] = str(bay_path.relative_to(root)) if bay_path.is_relative_to(root) else str(bay_path)

    if not bay_path.exists():
        panel.note = "no shred bay yet — drop exemplary references under .foldok/shred_bay/"
        return panel.settle()

    files = [
        p for p in bay_path.rglob("*")
        if p.is_file() and p.suffix.lower() in {".pdf", ".docx", ".md", ".txt"}
    ]
    panel.metrics["files"] = len(files)
    if not files:
        panel.note = "shred bay is empty"
        return panel.settle()

    shredder = Shredder()
    shreds: list[Shred] = []
    for path in files[:12]:
        try:
            shreds.append(shredder.shred(path, grade=grade))  # type: ignore[arg-type]
        except ShredRefused as exc:
            panel.add(
                "shred_refused", f"could not shred {path.name}",
                health="warn", impact=2, effort="minutes", detail=str(exc),
                action="fix the file or convert/OCR, then shred again",
            )

    panel.metrics["shredded"] = len(shreds)
    proposals = [p for s in shreds for p in s.proposals]
    panel.metrics["proposals"] = len(proposals)
    for kwargs in proposals_as_findings(proposals)[:8]:
        panel.add(**{k: v for k, v in kwargs.items() if k != "area"})

    if not proposals and shreds:
        panel.note = (
            "measured, but grade learns nothing — regrade bay files as exemplary "
            "if you want proposals"
        )
    return panel.settle()
