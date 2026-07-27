"""Discovery — one index over six registries, without moving a file.

Each adapter reads a registry in its own format and emits Assets.  Adding a
seventh registry means adding one function here, not a migration.

Deliberately forgiving: a malformed file becomes an Asset with a note rather
than an exception, because a library that refuses to load because one YAML is
broken is worse than one that tells you which YAML is broken.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable

from .model import Asset, Source, asset_id, checksum_of

try:  # pyyaml is in requirements.txt, but the library must not need it to load
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


def _read(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    if path.suffix in (".yaml", ".yml"):
        if yaml is None:
            return {}, checksum_of(raw)
        try:
            return (yaml.safe_load(text) or {}), checksum_of(raw)
        except Exception:  # noqa: BLE001
            return {"_error": "unparseable YAML"}, checksum_of(raw)
    if path.suffix == ".json":
        try:
            return (json.loads(text) or {}), checksum_of(raw)
        except Exception:  # noqa: BLE001
            return {"_error": "unparseable JSON"}, checksum_of(raw)
    return {}, checksum_of(raw)


def _tuple(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(v) for v in value)


def _own(note: str = "") -> Source:
    return Source(origin="foldok", redistribution="own", note=note)


# ----------------------------------------------------------------------
def document_types(root: Path) -> list[Asset]:
    out: list[Asset] = []
    folder = root / "registry" / "document-types"
    for p in sorted(folder.glob("*.yaml")):
        d, sums = _read(p)
        did = str(d.get("id") or p.stem)
        structure = d.get("structure") or {}
        required = _tuple(structure.get("required"))
        out.append(
            Asset(
                id=asset_id("document_type", did),
                kind="document_type",
                title=str(d.get("name") or did),
                version=str(d.get("version", "1")),
                path=str(p.relative_to(root)),
                fmt="yaml",
                industries=_tuple(d.get("industries")),
                domains=_tuple(d.get("domains")),
                jurisdictions=_tuple(d.get("regions")),
                provides=tuple(f"section:{s}" for s in required),
                source=_own(),
                checksum=sums,
                meta={
                    "aliases": list(_tuple(d.get("aliases"))),
                    "evidence_types": list(_tuple(d.get("evidence_types"))),
                    "required_sections": len(required),
                    "error": d.get("_error", ""),
                },
            )
        )
    return out


def templates(root: Path) -> list[Asset]:
    out: list[Asset] = []
    for p in sorted((root / "templates").glob("*.json")):
        d, sums = _read(p)
        key = str(d.get("template_key") or p.stem)
        sections = d.get("sections") or []
        # A template needs the sections it declares; that is a real dependency
        # and it is why a template can fail at install instead of at render.
        needs = tuple(
            f"section:{s.get('key')}" for s in sections
            if isinstance(s, dict) and s.get("key")
        )
        out.append(
            Asset(
                id=asset_id("template", key),
                kind="template",
                title=str(d.get("name") or key),
                version=str(d.get("version", "1")),
                path=str(p.relative_to(root)),
                fmt="json",
                industries=(),
                domains=_tuple(d.get("applies_to")),
                requires=(),
                provides=needs,
                source=_own(),
                checksum=sums,
                meta={
                    "name_no": d.get("name_no", ""),
                    "section_count": len(sections),
                    "price_tier": d.get("export_price_tier", ""),
                    "error": d.get("_error", ""),
                },
            )
        )
    return out


def symbols(root: Path) -> list[Asset]:
    out: list[Asset] = []
    base = root / "diagram_engine" / "symbols"
    for p in sorted(base.rglob("*.yaml")):
        d, sums = _read(p)
        sid = str(d.get("id") or p.stem)
        domain = str(d.get("domain") or p.parent.name)
        svg = d.get("svg")
        out.append(
            Asset(
                id=asset_id("symbol", domain, sid),
                kind="symbol",
                title=str(d.get("label") or sid),
                version=str(d.get("version", "1")),
                path=str(p.relative_to(root)),
                fmt="yaml",
                domains=(domain,),
                provides=(f"symbol:{sid}",),
                preview=str((p.parent / svg).relative_to(root)) if svg else "",
                source=_own(),
                checksum=sums,
                meta={
                    "ports": len(d.get("ports") or []),
                    "has_svg": bool(svg and (p.parent / svg).exists()),
                    "error": d.get("_error", ""),
                },
            )
        )
    return out


def _yaml_tree(root: Path, folder: str, kind: str, title_key: str = "name") -> list[Asset]:
    out: list[Asset] = []
    base = root / "registry" / folder
    if not base.exists():
        return out
    for p in sorted(base.rglob("*.yaml")):
        if p.name.startswith("_"):
            continue                      # schema and template files, not assets
        d, sums = _read(p)
        ident = str(d.get("id") or p.stem)
        group = p.parent.name if p.parent != base else ""
        out.append(
            Asset(
                id=asset_id(kind, group, ident) if group else asset_id(kind, ident),
                kind=kind,                                   # type: ignore[arg-type]
                title=str(d.get(title_key) or d.get("title") or ident),
                version=str(d.get("version", "1")),
                path=str(p.relative_to(root)),
                fmt="yaml",
                industries=_tuple(d.get("industries")),
                domains=_tuple(d.get("domains") or ([group] if group else ())),
                jurisdictions=_tuple(d.get("regions") or d.get("jurisdictions")),
                source=Source(
                    origin=str(d.get("origin") or "foldok"),
                    redistribution=str(d.get("redistribution") or "own"),  # type: ignore[arg-type]
                    licence=str(d.get("licence") or ""),
                    cites=_tuple(d.get("cites") or d.get("standards") or d.get("references")),
                ),
                checksum=sums,
                meta={
                    "status": d.get("status", ""),
                    "legal_compliance_claimed": d.get("legal_compliance_claimed", False),
                    "error": d.get("_error", ""),
                },
            )
        )
    return out


def knowledge(root: Path) -> list[Asset]:
    return _yaml_tree(root, "knowledge", "knowledge", title_key="title")


def materials(root: Path) -> list[Asset]:
    return _yaml_tree(root, "materials", "material")


def section_profiles(root: Path) -> list[Asset]:
    return _yaml_tree(root, "sections", "section_profile")


def calculations(root: Path) -> list[Asset]:
    return _yaml_tree(root, "calculations", "calculation")


def frameworks(root: Path) -> list[Asset]:
    return _yaml_tree(root, "frameworks", "framework")


def skills(root: Path) -> list[Asset]:
    out: list[Asset] = []
    base = root / "skills"
    if not base.exists():
        return out
    for p in sorted(base.iterdir()):
        if not p.is_dir():
            continue
        readme = p / "SKILL.md"
        blob = readme.read_bytes() if readme.exists() else p.name.encode()
        out.append(
            Asset(
                id=asset_id("skill", p.name),
                kind="skill",
                title=p.name.replace("-", " ").title(),
                path=str(p.relative_to(root)),
                fmt="md",
                source=_own(),
                checksum=checksum_of(blob),
                meta={"files": len(list(p.rglob("*")))},
            )
        )
    return out


def python_packs(root: Path) -> list[Asset]:
    """Requirement packs and layout templates that live in code, not files.

    They are assets too — they have ids, versions and dependencies — and leaving
    them out of the index is how you end up with two libraries again.
    """
    out: list[Asset] = []
    try:
        from foldok_gaps import packs as gap_packs  # noqa: PLC0415

        for pack in gap_packs.PACKS.values():
            out.append(
                Asset(
                    id=asset_id("requirement_pack", pack.id),
                    kind="requirement_pack",
                    title=pack.title,
                    version=str(pack.version),
                    path="foldok_gaps/packs.py",
                    fmt="python",
                    industries=(pack.segment,),
                    jurisdictions=(pack.jurisdiction,) if pack.jurisdiction else (),
                    provides=tuple(f"requirement:{r.key}" for r in pack.requirements[:40]),
                    source=Source(
                        origin="foldok",
                        # Requirements derived from a standard are reference_only:
                        # cite the clause, never redistribute the text.
                        redistribution="reference_only" if pack.standards else "own",
                        cites=tuple(pack.standards),
                    ),
                    meta={"requirements": len(pack.requirements), "segment": pack.segment},
                )
            )
    except ImportError:  # pragma: no cover
        pass

    try:
        from foldok_boxes.template import compliance_a4  # noqa: PLC0415

        t = compliance_a4()
        out.append(
            Asset(
                id=asset_id("layout_template", t.id),
                kind="layout_template",
                title=t.title,
                version=str(t.version),
                path="foldok_boxes/template.py",
                fmt="python",
                provides=(f"layout:{t.page_size}/{t.columns}",),
                source=_own(),
                meta={"columns": t.columns, "page_size": t.page_size},
            )
        )
    except ImportError:  # pragma: no cover
        pass
    return out


ADAPTERS: tuple[Callable[[Path], list[Asset]], ...] = (
    document_types, templates, symbols, knowledge, materials,
    section_profiles, calculations, frameworks, skills, python_packs,
)


def discover(root: str | Path, adapters: Iterable[Callable[[Path], list[Asset]]] | None = None) -> list[Asset]:
    root = Path(root)
    out: list[Asset] = []
    for adapter in (adapters if adapters is not None else ADAPTERS):
        try:
            out.extend(adapter(root))
        except Exception as exc:  # noqa: BLE001 - one broken registry must not blind the rest
            out.append(
                Asset(
                    id=asset_id("framework", f"_adapter_error_{adapter.__name__}"),
                    kind="framework",
                    title=f"adapter {adapter.__name__} failed",
                    source=Source(origin="foldok", redistribution="own"),
                    meta={"error": f"{type(exc).__name__}: {exc}"},
                )
            )
    return sorted(out, key=lambda a: a.id)
