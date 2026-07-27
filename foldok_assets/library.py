"""The library — one query surface over everything Foldok can use.

    lib = AssetLibrary.load(".")
    lib.find(kind="symbol", domain="piping")
    lib.resolve("template.installation_manual")     # what does it need, what is missing
    lib.pack("marine_starter", refs).seal(lib)      # refuses anything unshippable

``seal()`` is the important one.  It is what makes "industry packs" a real
product rather than a legal exposure: a pack cannot be sealed if it contains
content derived from a standard, or content whose origin nobody established.
You ship your own templates, symbols and structural profiles, citing the clause
— you never ship the clause.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from .discover import discover
from .model import SHIPPABLE, Asset, Pack, PackRef, Source


class PackRefused(Exception):
    """A pack cannot be sealed, with the reason and the offending assets."""


@dataclass
class Resolution:
    asset: Asset
    requires: list[Asset] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    provided_by: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.missing

    def __str__(self) -> str:
        head = f"{self.asset.id}: {len(self.requires)} dependency(ies)"
        return head if self.ok else head + f", MISSING {', '.join(self.missing)}"


class AssetLibrary:
    def __init__(self, assets: Iterable[Asset] | None = None, root: str | Path = ".") -> None:
        self.root = Path(root)
        self._assets: dict[str, Asset] = {}
        self._capabilities: dict[str, list[str]] = {}
        for a in assets or ():
            self.add(a)

    # -- loading ---------------------------------------------------------
    @classmethod
    def load(cls, root: str | Path = ".") -> "AssetLibrary":
        return cls(discover(root), root)

    def add(self, asset: Asset) -> Asset:
        self._assets[asset.id] = asset
        for cap in asset.provides:
            self._capabilities.setdefault(cap, []).append(asset.id)
        return asset

    # -- reading ---------------------------------------------------------
    def get(self, asset_id: str) -> Asset | None:
        return self._assets.get(asset_id)

    def all(self) -> list[Asset]:
        return [self._assets[k] for k in sorted(self._assets)]

    def __len__(self) -> int:
        return len(self._assets)

    def find(
        self,
        *,
        kind: str | None = None,
        industry: str | None = None,
        domain: str | None = None,
        jurisdiction: str | None = None,
        text: str | None = None,
    ) -> list[Asset]:
        return [
            a for a in self.all()
            if a.matches(kind=kind, industry=industry, domain=domain,
                         jurisdiction=jurisdiction, text=text)
        ]

    def kinds(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for a in self.all():
            out[a.kind] = out.get(a.kind, 0) + 1
        return dict(sorted(out.items()))

    def industries(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for a in self.all():
            for i in a.industries:
                out[i] = out.get(i, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))

    def providers_of(self, capability: str) -> list[str]:
        return sorted(self._capabilities.get(capability, []))

    def used_by(self, asset_id: str) -> list[str]:
        """Which assets depend on this one.  Answerable only because packs
        reference assets instead of copying them."""
        return sorted(a.id for a in self.all() if asset_id in a.requires)

    # -- dependencies ----------------------------------------------------
    def resolve(self, asset_id: str, *, depth: int = 6) -> Resolution:
        asset = self.get(asset_id)
        if asset is None:
            return Resolution(
                asset=Asset(id=asset_id, kind="template", title="(not found)"),
                missing=[asset_id],
            )
        seen: set[str] = {asset_id}
        needed: list[Asset] = []
        missing: list[str] = []
        provided_by: dict[str, str] = {}
        frontier = list(asset.requires)
        while frontier and depth > 0:
            depth -= 1
            nxt: list[str] = []
            for want in frontier:
                if want in seen:
                    continue
                seen.add(want)
                found = self.get(want)
                if found is None:
                    providers = self.providers_of(want)
                    if providers:
                        provided_by[want] = providers[0]
                        found = self.get(providers[0])
                    else:
                        missing.append(want)
                        continue
                needed.append(found)
                nxt.extend(found.requires)
            frontier = nxt
        return Resolution(asset=asset, requires=needed, missing=sorted(set(missing)),
                          provided_by=provided_by)

    def unsatisfied(self) -> dict[str, list[str]]:
        """Every dependency in the library that nothing provides."""
        out: dict[str, list[str]] = {}
        for a in self.all():
            r = self.resolve(a.id)
            if r.missing:
                out[a.id] = r.missing
        return out

    # -- packs -----------------------------------------------------------
    def pack(
        self,
        pack_id: str,
        asset_ids: Sequence[str],
        *,
        title: str = "",
        industry: str = "",
        jurisdictions: Sequence[str] = (),
        description: str = "",
        version: str = "1",
    ) -> Pack:
        return Pack(
            id=pack_id,
            title=title or pack_id,
            version=version,
            industry=industry,
            jurisdictions=tuple(jurisdictions),
            description=description,
            refs=tuple(PackRef(a) for a in sorted(set(asset_ids))),
            source=Source(origin="foldok", redistribution="own"),
        )

    def seal(self, pack: Pack, *, allow: Sequence[str] = ()) -> Pack:
        """Make a pack shippable, or refuse and say exactly why.

        Three ways to fail, in order of how expensive the mistake is:
          1. an asset that may not be redistributed
          2. an asset the library does not have
          3. a dependency nothing in the pack or the library provides
        """
        allow = set(allow)
        missing: list[str] = []
        blocked: list[tuple[str, str]] = []
        for ref in pack.refs:
            asset = self.get(ref.asset_id)
            if asset is None:
                missing.append(ref.asset_id)
                continue
            if asset.id in allow:
                continue
            if asset.source.redistribution not in SHIPPABLE:
                blocked.append((asset.id, asset.source.redistribution))

        if blocked:
            lines = "\n".join(
                f"  {aid} — {why}" for aid, why in sorted(blocked)
            )
            raise PackRefused(
                f"pack '{pack.id}' cannot be sealed; {len(blocked)} asset(s) may not be "
                f"redistributed:\n{lines}\n"
                "Content derived from a standard is cited, never shipped. Ship your own "
                "structural profile and reference the clause, or clear the licence and "
                "set redistribution='licensed'."
            )
        if missing:
            raise PackRefused(
                f"pack '{pack.id}' references {len(missing)} asset(s) that are not in the "
                f"library: {', '.join(sorted(missing))}"
            )

        holes: dict[str, list[str]] = {}
        inside = set(pack.asset_ids())
        for ref in pack.refs:
            r = self.resolve(ref.asset_id)
            gaps = [m for m in r.missing if m not in inside]
            if gaps:
                holes[ref.asset_id] = gaps
        if holes:
            detail = "; ".join(f"{k} needs {', '.join(v)}" for k, v in sorted(holes.items()))
            raise PackRefused(
                f"pack '{pack.id}' has unresolved dependencies: {detail}. "
                "A pack that installs and then fails at render is worse than one that "
                "refuses to install."
            )

        pack.sealed = True
        return pack

    def install(self, pack: Pack) -> list[Asset]:
        """What a pack actually brings in.  References, not copies."""
        return [a for a in (self.get(r.asset_id) for r in pack.refs) if a is not None]

    # -- serialisation ---------------------------------------------------
    def manifest(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "count": len(self._assets),
            "kinds": self.kinds(),
            "industries": self.industries(),
            "assets": [a.to_dict() for a in self.all()],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.manifest(), indent=indent, ensure_ascii=False)

    def write_manifest(self, path: str | Path) -> Path:
        p = Path(path)
        p.write_text(self.to_json(), encoding="utf-8")
        return p

    @staticmethod
    def from_manifest(data: dict[str, Any]) -> "AssetLibrary":
        return AssetLibrary([Asset.from_dict(a) for a in data.get("assets", [])],
                            root=data.get("root", "."))

    def summary(self) -> str:
        lines = [f"{len(self)} asset(s) across {len(self.kinds())} kind(s)"]
        for kind, n in self.kinds().items():
            lines.append(f"  {n:>4}  {kind}")
        shippable = sum(1 for a in self.all() if a.source.shippable)
        lines.append(f"  {shippable} shippable, {len(self) - shippable} reference-only or unknown")
        return "\n".join(lines)
