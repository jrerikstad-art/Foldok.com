"""Curation — which sources may reach the document at all.

This runs **before** the narrative, and needs nothing from it. Whether a
marketing brochure is admissible is a property of the brochure, not of the story
being told.

    Knowledge → Curation → Narrative → Selection → Author
                ~~~~~~~~~                ~~~~~~~~~
                this file                select.py

The distinction matters because collapsing them breaks the later half: you
cannot know a cable tray cross-section is relevant until there is a section about
separation. Curation is corpus-level and answerable now; selection is
section-level and answerable only after the arc exists.

``DocumentContext`` is the whole admissible corpus, sorted into the kinds a
document is built from, with the excluded material kept rather than dropped. A
curation decision nobody can inspect is indistinguishable from a bug — and this
product has already shipped one of those, when photos in the folder were
reported missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence

SCHEMA_VERSION = 1

AssetKind = Literal["image", "drawing", "diagram", "table", "standard", "document"]

DRAWING_HINTS = ("drawing", "tegning", "plan", "layout", "arrangement", "ga ",
                 "general arrangement", "isometric", "p&id", "single line", "enlinje")
DIAGRAM_HINTS = ("diagram", "skjema", "schematic", "koblingsskjema", "wiring")
TABLE_HINTS = ("table", "tabell", "schedule", "liste", "register", "bom",
               "bill of materials", "stykkliste", "matrix")
STANDARD_HINTS = ("standard", "norm", "iec ", "iso ", "en 5", "nek ", "bs ", "astm",
                  "ieee ", "nema ", "mil-std")

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tif", ".tiff"}
DRAWING_EXT = {".dwg", ".dxf", ".step", ".stp", ".iges", ".igs"}
TABLE_EXT = {".xlsx", ".xls", ".csv", ".tsv", ".ods"}


@dataclass
class Asset:
    """One admissible thing, with the identity a section will cite."""

    id: str                          # short, stable, shown to the model
    file: str
    kind: AssetKind
    title: str = ""
    caption: str = ""
    role: str = "unknown"            # project | reference | unknown
    tags: tuple[str, ...] = ()
    subject: str = ""

    @property
    def name(self) -> str:
        return Path(self.file).name

    def menu_line(self) -> str:
        """How it appears in the numbered inventory the model reads."""
        label = self.title or self.caption or self.name
        return f"{self.id}  {label[:90]}"

    def to_dict(self) -> dict[str, Any]:
        d = {"id": self.id, "file": self.file, "kind": self.kind, "role": self.role}
        for k in ("title", "caption", "subject"):
            if getattr(self, k):
                d[k] = getattr(self, k)
        if self.tags:
            d["tags"] = list(self.tags)
        return d


@dataclass
class Excluded:
    file: str
    reason: str
    role: str = "ignore"

    def to_dict(self) -> dict[str, str]:
        return {"file": self.file, "reason": self.reason, "role": self.role}


@dataclass
class DocumentContext:
    """Everything the document may be built from, and everything it may not."""

    images: list[Asset] = field(default_factory=list)
    drawings: list[Asset] = field(default_factory=list)
    diagrams: list[Asset] = field(default_factory=list)
    tables: list[Asset] = field(default_factory=list)
    standards: list[Asset] = field(default_factory=list)
    documents: list[Asset] = field(default_factory=list)
    excluded: list[Excluded] = field(default_factory=list)

    def all(self) -> list[Asset]:
        return [*self.images, *self.drawings, *self.diagrams,
                *self.tables, *self.standards, *self.documents]

    def of_kind(self, kind: str) -> list[Asset]:
        return {
            "image": self.images, "drawing": self.drawings, "diagram": self.diagrams,
            "table": self.tables, "standard": self.standards, "document": self.documents,
        }.get(kind, [])

    def get(self, asset_id: str) -> Asset | None:
        for a in self.all():
            if a.id == asset_id:
                return a
        return None

    def counts(self) -> dict[str, int]:
        return {
            "images": len(self.images), "drawings": len(self.drawings),
            "diagrams": len(self.diagrams), "tables": len(self.tables),
            "standards": len(self.standards), "documents": len(self.documents),
            "excluded": len(self.excluded),
        }

    def summary(self, *, lang: str = "no") -> str:
        c = self.counts()
        if lang.startswith("no"):
            line = (f"{len(self.all())} kilder tilgjengelig: {c['images']} bilder, "
                    f"{c['drawings']} tegninger, {c['diagrams']} skjema, "
                    f"{c['tables']} tabeller, {c['standards']} standarder")
            if self.excluded:
                line += f"; {len(self.excluded)} utelatt"
            return line
        line = (f"{len(self.all())} sources available: {c['images']} images, "
                f"{c['drawings']} drawings, {c['diagrams']} diagrams, "
                f"{c['tables']} tables, {c['standards']} standards")
        if self.excluded:
            line += f"; {len(self.excluded)} excluded"
        return line

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "counts": self.counts(),
            "images": [a.to_dict() for a in self.images],
            "drawings": [a.to_dict() for a in self.drawings],
            "diagrams": [a.to_dict() for a in self.diagrams],
            "tables": [a.to_dict() for a in self.tables],
            "standards": [a.to_dict() for a in self.standards],
            "documents": [a.to_dict() for a in self.documents],
            "excluded": [e.to_dict() for e in self.excluded],
        }


# ----------------------------------------------------------------------
def build_context(
    index: Iterable[Mapping[str, Any]],
    *,
    roles: Mapping[str, Any] | None = None,
    project_terms: Sequence[str] = (),
    include_reference_images: bool = False,
) -> DocumentContext:
    """The admissible corpus. Takes no narrative, on purpose.

    ``include_reference_images`` defaults off: a photograph from a supplier's
    catalogue is their product shot, not evidence of this installation, and
    putting one in a handover document is a small lie.
    """
    from foldok_role import classify_index

    entries = [e for e in (index or []) if e.get("kind") != "skipped" and e.get("file")]
    report = roles if roles is not None else classify_index(entries, project_terms=project_terms)
    by_file = report.by_file() if hasattr(report, "by_file") else dict(report)

    context = DocumentContext()
    counters: dict[str, int] = {}

    for entry in entries:
        file = str(entry.get("file"))
        classification = by_file.get(file)
        role = getattr(classification, "role", "unknown")

        if role == "ignore":
            context.excluded.append(Excluded(
                file=file, role=role,
                reason=(classification.reasons[0] if classification and classification.reasons
                        else "sales material"),
            ))
            continue

        kind = _kind_of(entry)
        if kind == "image" and role == "reference" and not include_reference_images:
            context.excluded.append(Excluded(
                file=file, role=role,
                reason="a supplier's product photo is not evidence of this installation",
            ))
            continue

        prefix = {"image": "IMG", "drawing": "DWG", "diagram": "DIA",
                  "table": "TBL", "standard": "STD", "document": "DOC"}[kind]
        counters[prefix] = counters.get(prefix, 0) + 1
        asset = Asset(
            id=f"{prefix}{counters[prefix]}",
            file=file,
            kind=kind,
            title=str(entry.get("title") or "").strip(),
            caption=str(entry.get("caption") or "").strip(),
            role=role,
            tags=tuple(str(t) for t in (entry.get("content_tags") or [])),
            subject=str(entry.get("subject") or ""),
        )
        context.of_kind(kind).append(asset)

    return context


def _kind_of(entry: Mapping[str, Any]) -> AssetKind:
    file = str(entry.get("file") or "")
    ext = Path(file).suffix.lower()
    blob = " ".join([
        Path(file).stem, str(entry.get("caption") or ""),
        " ".join(str(t) for t in (entry.get("content_tags") or [])),
        " ".join(str(h) for h in (entry.get("doc_role_hints") or [])),
    ]).lower()

    if str(entry.get("kind") or "").lower() in ("photo", "image") or ext in IMAGE_EXT:
        # A photographed drawing is still a drawing to a reader.
        return "drawing" if any(h in blob for h in DRAWING_HINTS) else "image"
    if ext in DRAWING_EXT:
        return "drawing"
    if any(h in blob for h in DIAGRAM_HINTS):
        return "diagram"
    if ext in TABLE_EXT or any(h in blob for h in TABLE_HINTS):
        return "table"
    if any(h in blob for h in STANDARD_HINTS):
        return "standard"
    if any(h in blob for h in DRAWING_HINTS):
        return "drawing"
    return "document"
