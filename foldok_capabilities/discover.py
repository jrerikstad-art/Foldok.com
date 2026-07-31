"""Discovery — what the product can actually do, read from the product.

Every capability here is counted from something real: symbol files on disk,
requirement packs in code, profiles in the diagram engine, page sizes in the
layout engine.  Nothing is typed by hand, because the whole failure was a
hand-typed manifest falling behind the code.

The limits are written by hand, and that is deliberate.  A limit is a judgement —
"we do installation diagrams, not board-level electronics" is a product decision,
not something derivable from a symbol count.  What the code guarantees is that a
limit always travels attached to the capability it qualifies.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable

from .model import Capability, Limit


def _try(fn: Callable[[], Any], default: Any = None) -> Any:
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return default


def diagram_capability(root: str | Path) -> Capability | None:
    """The one that was missing. Counted from the symbol files themselves."""
    lib = _try(lambda: importlib.import_module("foldok_assets").AssetLibrary.load(str(root)))
    symbols = lib.find(kind="symbol") if lib else []
    if not symbols:
        symbols = [
            p for p in Path(root, "diagram_engine", "symbols").rglob("*.yaml")
        ]  # fall back to the files on disk
        domains = sorted({p.parent.name for p in symbols})
        counts = {d: sum(1 for p in symbols if p.parent.name == d) for d in domains}
    else:
        domains = sorted({d for a in symbols for d in a.domains})
        counts = {d: sum(1 for a in symbols if d in a.domains) for d in domains}
    if not symbols:
        return None

    profiles = _try(
        lambda: sorted(importlib.import_module("foldok_diagram").PROFILES), []
    ) or []

    return Capability(
        id="diagrams",
        anchors=("diagram", "schematic", "koblingsskjema", "enlinjeskjema", "single-line"),
        verb="produce",
        object="single-line, interconnection and piping diagrams",
        summary=(
            "Produce single-line, interconnection and piping diagrams as print-ready SVG, "
            "from a component graph you can edit on canvas"
        ),
        domains=tuple(domains),
        produces=("svg", "pdf"),
        limits=(
            Limit(
                "board-level electronics are out of scope",
                "there are no microcontroller, header-pin, bus or GPIO symbols in the pack; "
                "for those Foldok produces a structured pin table instead",
            ),
            Limit(
                "native CAD files are not read or written",
                "DWG and STEP are not parsed; a drawing PDF can be indexed as evidence",
            ),
            Limit("no 3D modelling", "the engine is 2D on a page grid"),
        ),
        evidence={
            "symbols": len(symbols),
            "by_domain": counts,
            "profiles": profiles,
            "engine": "foldok_diagram + diagram_engine",
        },
        engine="foldok_diagram",
    )


def gap_capability(root: str | Path) -> Capability | None:
    packs = _try(lambda: importlib.import_module("foldok_gaps").PACKS)
    if not packs:
        return None
    total = sum(len(p.requirements) for p in packs.values())
    return Capability(
        id="gaps",
        anchors=("gap", "mangler", "avvik", "missing", "krav"),
        verb="check",
        object="what a document is still missing",
        summary=(
            "Check a document against a requirement pack and list every gap, per circuit, "
            "machine or cage, with the clause it comes from"
        ),
        domains=tuple(sorted({p.segment for p in packs.values()})),
        produces=("md", "pdf"),
        limits=(
            Limit(
                "completeness is not compliance",
                "Foldok can say every item is resolved; whether the installation complies "
                "is a judgement for someone with a licence",
            ),
            Limit(
                "measured values are never generated",
                "the engine builds the empty form and says what to capture",
            ),
        ),
        evidence={
            "packs": sorted(packs),
            "requirements": total,
            "segments": sorted({p.segment for p in packs.values()}),
        },
        engine="foldok_gaps",
    )


def layout_capability(root: str | Path) -> Capability | None:
    module = _try(lambda: importlib.import_module("foldok_boxes"))
    if module is None:
        return None
    return Capability(
        id="layout",
        anchors=("layout", "ombrekk", "pagination", "sidebrytning"),
        verb="produce",
        object="paginated documents on a column grid",
        summary=(
            "Lay out and paginate a document on a 12-column grid, with every block "
            "resizable by hand and the PDF matching the canvas exactly"
        ),
        produces=("pdf", "html"),
        limits=(
            Limit("free pixel positioning is not offered",
                  "boxes sit on the page grid so pagination and reflow keep working"),
        ),
        evidence={"page_sizes": sorted(module.PAGE_SIZES), "engine": "foldok_boxes"},
        engine="foldok_boxes",
    )


def index_capability(root: str | Path) -> Capability | None:
    module = _try(lambda: importlib.import_module("foldok_index"))
    if module is None:
        return None
    return Capability(
        id="index",
        anchors=("index", "indeks", "søk", "search"),
        verb="read",
        object="a project folder",
        summary=(
            "Index a project folder locally and answer questions from it, with a citation "
            "for every fact and a list of files it could not read"
        ),
        produces=("md",),
        limits=(
            Limit("scanned documents need OCR first",
                  "a PDF with no text layer is reported as unreadable rather than skipped"),
            Limit("native CAD is not parsed", "DWG and STEP are indexed as files, not content"),
        ),
        evidence={
            "formats": _try(module.supported_suffixes, [])[:16],
            "engine": "foldok_index",
        },
        engine="foldok_index",
    )


def capture_capability(root: str | Path) -> Capability | None:
    if _try(lambda: importlib.import_module("foldok_capture")) is None:
        return None
    return Capability(
        id="capture",
        anchors=("capture", "kamera", "photo capture", "bildeoppdrag"),
        verb="collect",
        object="site photographs against open requirements",
        summary=(
            "Send open photo requirements to the Capture app and close them automatically "
            "when the pictures come back, each citing the file and the moment"
        ),
        produces=("jpg",),
        limits=(
            Limit("photographs are never sent to a model unless you approve each one",
                  "an image cannot be masked"),
        ),
        evidence={"engine": "foldok_capture"},
        engine="foldok_capture",
    )


def privacy_capability(root: str | Path) -> Capability | None:
    module = _try(lambda: importlib.import_module("foldok_private"))
    if module is None:
        return None
    return Capability(
        id="privacy",
        anchors=("masking", "maskering", "what leaves", "trust boundary"),
        verb="show",
        object="exactly what leaves the machine",
        summary=(
            "Show every model request before it is sent, with client and project names "
            "replaced by tokens and restored locally afterwards"
        ),
        limits=(
            Limit("masking hides identifiers, not findings",
                  "a failed test stays legible once the names are removed"),
        ),
        evidence={"purposes": list(module.PURPOSES), "engine": "foldok_private"},
        engine="foldok_private",
    )


DISCOVERERS: tuple[Callable[[str | Path], Capability | None], ...] = (
    diagram_capability,
    gap_capability,
    layout_capability,
    index_capability,
    capture_capability,
    privacy_capability,
)


def discover(root: str | Path = ".") -> list[Capability]:
    """Capabilities of the tree at ``root`` — not of whatever happens to be
    importable.

    ``importlib`` finds installed engines wherever they live, so checking a
    build that does not contain them would report capabilities it cannot
    possibly have. The engine has to be present in the tree being checked.
    """
    root = Path(root)
    out: list[Capability] = []
    for fn in DISCOVERERS:
        capability = _try(lambda f=fn: f(root))
        if capability is None:
            continue
        engine = capability.engine
        if engine and not (root / engine).exists():
            continue
        out.append(capability)
    return sorted(out, key=lambda c: c.id)
