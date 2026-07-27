"""One asset model over the registries that already exist.

The observation behind this file is right: Foldok now has six places that define
"a thing the engine uses" — ``registry/document-types``, ``registry/knowledge``,
``registry/materials``, ``templates/``, ``diagram_engine/symbols/``, plus the
requirement packs and layout templates that live in Python.  Three file formats,
no shared versioning, no way to say "this template needs those symbols", and no
way to ask "what do I have for piping?"

Two decisions that differ from the obvious approach, and both matter:

**Index, do not migrate.**  Assets stay exactly where they are.  ``discover()``
builds one index across all six registries.  Moving ~170 files into a new tree
buys a nicer directory listing and costs a week of merge pain, broken imports,
and every open branch rebased.  The index gives the whole benefit — one query
surface, dependencies, versioning — with no file moves.

**Redistribution is a required field, and packing enforces it.**  A pack named
"IEC" or "DNV" or "ABB" cannot ship.  Those are copyrighted standards and
trademarked names; bundling their requirements as an installable product is a
licensing problem that arrives as a letter, not as a bug.  So every asset
declares where it came from and whether it may be redistributed, and
``Pack.seal()`` refuses anything that has not cleared that bar.  Enforced in
code, like the evidential guard — for the same reason: a rule that lives only in
someone's memory is not a rule.

What you *can* ship is your own work: structural profiles, your templates, your
symbols, and knowledge you wrote, with a citation to the standard rather than a
copy of it.  That is also the honest position, and it is already the position
``registry/knowledge/_knowledge_schema.yaml`` takes with
``legal_compliance_claimed: false``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

SCHEMA_VERSION = 1

AssetKind = Literal[
    "template",          # templates/*.json — document templates
    "document_type",     # registry/document-types/*.yaml
    "symbol",            # diagram_engine/symbols/**/*.yaml
    "material",          # registry/materials/**
    "section_profile",   # registry/sections/**
    "knowledge",         # registry/knowledge/**
    "calculation",       # registry/calculations/**
    "framework",         # registry/frameworks/**
    "requirement_pack",  # foldok_gaps packs
    "layout_template",   # foldok_boxes templates
    "theme",             # artifact_engine themes
    "component",         # composable document blocks
    "table",             # reusable table shapes
    "skill",             # skills/*
]

KINDS: tuple[str, ...] = (
    "template", "document_type", "symbol", "material", "section_profile",
    "knowledge", "calculation", "framework", "requirement_pack",
    "layout_template", "theme", "component", "table", "skill",
)

# How an asset may travel.  Only the first two can go in a shipped pack.
Redistribution = Literal[
    "own",             # Foldok wrote it; ship freely
    "licensed",        # third-party content with a licence that permits it
    "reference_only",  # derived from a standard: cite it, never reproduce it
    "unknown",         # provenance not established — treated as unshippable
]

SHIPPABLE: tuple[str, ...] = ("own", "licensed")


@dataclass(frozen=True)
class Source:
    """Where an asset came from.  ``redistribution`` is the load-bearing part."""

    origin: str = "foldok"                       # "foldok" | "user" | vendor name
    redistribution: Redistribution = "own"
    licence: str = ""                            # "CC-BY-4.0", "proprietary", ...
    cites: tuple[str, ...] = ()                  # "NEK 400:2022 §8-1" — citation, not content
    note: str = ""

    @property
    def shippable(self) -> bool:
        return self.redistribution in SHIPPABLE

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"origin": self.origin, "redistribution": self.redistribution}
        if self.licence:
            d["licence"] = self.licence
        if self.cites:
            d["cites"] = list(self.cites)
        if self.note:
            d["note"] = self.note
        return d


@dataclass
class Asset:
    id: str                                      # "symbol.piping.valve_ball"
    kind: AssetKind
    title: str = ""
    version: str = "1"
    path: str = ""                               # where it lives NOW; never moved
    fmt: str = "yaml"                            # yaml | json | python | svg | md
    industries: tuple[str, ...] = ()             # tags, never folders — see below
    domains: tuple[str, ...] = ()
    jurisdictions: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()               # asset ids
    provides: tuple[str, ...] = ()               # capability strings
    source: Source = field(default_factory=Source)
    preview: str = ""
    checksum: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    # Industries are tags because a ball valve is used in marine, process, water
    # and building services. A folder per industry copies it four times and the
    # copies drift.

    @property
    def namespace(self) -> str:
        return self.id.split(".", 1)[0]

    def matches(
        self,
        *,
        kind: str | None = None,
        industry: str | None = None,
        domain: str | None = None,
        jurisdiction: str | None = None,
        text: str | None = None,
    ) -> bool:
        if kind and self.kind != kind:
            return False
        if industry and industry not in self.industries:
            return False
        if domain and domain not in self.domains:
            return False
        if jurisdiction and self.jurisdictions and jurisdiction not in self.jurisdictions:
            return False
        if text:
            hay = f"{self.id} {self.title} {' '.join(self.industries)} {' '.join(self.domains)}".lower()
            if text.lower() not in hay:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "version": self.version,
            "path": self.path,
            "format": self.fmt,
        }
        for name, value in (
            ("industries", self.industries),
            ("domains", self.domains),
            ("jurisdictions", self.jurisdictions),
            ("requires", self.requires),
            ("provides", self.provides),
        ):
            if value:
                d[name] = list(value)
        d["source"] = self.source.to_dict()
        if self.preview:
            d["preview"] = self.preview
        if self.checksum:
            d["checksum"] = self.checksum
        if self.meta:
            d["meta"] = dict(sorted(self.meta.items()))
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Asset":
        src = d.get("source") or {}
        return Asset(
            id=d["id"],
            kind=d["kind"],
            title=d.get("title", ""),
            version=str(d.get("version", "1")),
            path=d.get("path", ""),
            fmt=d.get("format", "yaml"),
            industries=tuple(d.get("industries", ())),
            domains=tuple(d.get("domains", ())),
            jurisdictions=tuple(d.get("jurisdictions", ())),
            requires=tuple(d.get("requires", ())),
            provides=tuple(d.get("provides", ())),
            source=Source(
                origin=src.get("origin", "foldok"),
                redistribution=src.get("redistribution", "own"),
                licence=src.get("licence", ""),
                cites=tuple(src.get("cites", ())),
                note=src.get("note", ""),
            ),
            preview=d.get("preview", ""),
            checksum=d.get("checksum", ""),
            meta=dict(d.get("meta", {})),
        )


def asset_id(kind: str, *parts: str) -> str:
    tail = ".".join(p.strip().replace(" ", "_").lower() for p in parts if p)
    return f"{kind}.{tail}"


def checksum_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


# ----------------------------------------------------------------------
@dataclass
class PackRef:
    asset_id: str
    version: str = "*"

    def satisfied_by(self, asset: Asset) -> bool:
        return asset.id == self.asset_id and (self.version == "*" or asset.version == self.version)

    def to_dict(self) -> dict[str, str]:
        return {"asset_id": self.asset_id, "version": self.version}


@dataclass
class Pack:
    """A named bundle of asset ids — the "industry pack" idea, made shippable.

    A pack references assets; it does not copy them.  That keeps one definition
    of each asset and makes "which packs use this symbol" answerable.
    """

    id: str
    title: str = ""
    version: str = "1"
    industry: str = ""
    jurisdictions: tuple[str, ...] = ()
    description: str = ""
    refs: tuple[PackRef, ...] = ()
    source: Source = field(default_factory=Source)
    sealed: bool = False

    def asset_ids(self) -> list[str]:
        return sorted(r.asset_id for r in self.refs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "id": self.id,
            "title": self.title,
            "version": self.version,
            "industry": self.industry,
            "jurisdictions": list(self.jurisdictions),
            "description": self.description,
            "assets": [r.to_dict() for r in sorted(self.refs, key=lambda r: r.asset_id)],
            "source": self.source.to_dict(),
            "sealed": self.sealed,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Pack":
        src = d.get("source") or {}
        return Pack(
            id=d["id"],
            title=d.get("title", ""),
            version=str(d.get("version", "1")),
            industry=d.get("industry", ""),
            jurisdictions=tuple(d.get("jurisdictions", ())),
            description=d.get("description", ""),
            refs=tuple(PackRef(a["asset_id"], a.get("version", "*")) for a in d.get("assets", [])),
            source=Source(
                origin=src.get("origin", "foldok"),
                redistribution=src.get("redistribution", "own"),
                licence=src.get("licence", ""),
                cites=tuple(src.get("cites", ())),
                note=src.get("note", ""),
            ),
            sealed=bool(d.get("sealed", False)),
        )
