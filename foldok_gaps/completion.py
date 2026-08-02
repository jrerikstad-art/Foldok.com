"""CompletionSession — the API behind "click the missing thing and make it".

Everything the UI needs is here:

    session.gaps()                     what is missing
    session.batches()                  the same thing missing across five circuits
    session.options(gap_id)            what Foldok can offer for this one
    session.resolve(gap_id, ...)       do it
    session.resolve_batch(req_key)     do all thirty
    session.gate()                     can this be exported, and as what

Batch resolution defaults to non-generative resolvers only.  Creating thirty
empty measurement forms in one click is the feature.  Drafting thirty pieces of
prose in one click, which nobody will read before signing, is not — that needs
``include_generative=True`` and an explicit action in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import policy as policy_mod
from .document import Artifact, Document
from .gaps import Batch, Gap, GapSet, evaluate
from .policy import Gate, Mode
from .requirements import RequirementPack
from .resolvers import (
    EvidentialGuard,
    Resolution,
    Resolver,
    ResolverRefused,
    ResolverRegistry,
    default_registry,
)


@dataclass
class Offer:
    """One thing Foldok can do about a gap, in the words the user should see."""

    resolver_id: str
    label: str
    generates_content: bool
    produces: str
    caution: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = {
            "resolver_id": self.resolver_id,
            "label": self.label,
            "produces": self.produces,
            "generates_content": self.generates_content,
        }
        if self.caution:
            d["caution"] = self.caution
        return d


class CompletionSession:
    def __init__(
        self,
        document: Document,
        pack: RequirementPack,
        registry: ResolverRegistry | None = None,
        mode: Mode | str | None = None,
        *,
        index: list | None = None,
    ) -> None:
        self.document = document
        self.pack = pack
        self.registry = registry or default_registry()
        self.index = index  # project index — used by foldok_role photo offers
        if mode is not None:
            self.set_mode(mode)
        self.document.pack_id = pack.id
        self.history: list[Resolution] = []
        self._gaps: GapSet | None = None

    # -- state ----------------------------------------------------------
    @property
    def mode(self) -> Mode:
        return policy_mod.get(self.document.mode)

    def set_mode(self, mode: Mode | str) -> Mode:
        m = policy_mod.get(mode) if isinstance(mode, str) else mode
        self.document.mode = m.id
        self.invalidate()
        return m

    def invalidate(self) -> None:
        self._gaps = None

    def gaps(self) -> GapSet:
        if self._gaps is None:
            self._gaps = evaluate(self.document, self.pack)
        return self._gaps

    def gap(self, gap_id: str) -> Gap:
        g = self.gaps().get(gap_id)
        if g is None:
            raise KeyError(f"no gap '{gap_id}' in this document")
        return g

    def batches(self) -> list[Batch]:
        return self.gaps().batches()

    def summary(self) -> dict[str, Any]:
        return self.gaps().summary()

    def progress(self) -> dict[str, Any]:
        return policy_mod.progress(self.document, self.pack, self.mode)

    def gate(self) -> Gate:
        return policy_mod.gate(self.document, self.pack, self.mode, self.gaps())

    # -- offers ---------------------------------------------------------
    def photo_offers(self, index: list | None = None) -> list[Any]:
        """Photos already in the folder, ranked against open photo gaps.

        Nothing is bound automatically — Foldok ranks; a person confirms.
        """
        idx = index if index is not None else self.index
        if idx is None:
            return []
        try:
            from foldok_role import offers_for
            return offers_for(self.gaps().open(), idx)
        except Exception:
            return []

    def options(self, gap_id: str) -> list[Offer]:
        gap = self.gap(gap_id)
        offers: list[Offer] = []
        # Prefer confirming an existing photo before "go take it"
        if gap.requirement.kind == "photo" and self.index is not None:
            try:
                from foldok_role import offers_for
                role_offers = offers_for([gap], self.index)
                if role_offers and role_offers[0].has_candidates:
                    n = len(role_offers[0].candidates)
                    offers.append(
                        Offer(
                            resolver_id="photo_capture",
                            label=f"Confirm folder photo ({n} candidate(s))",
                            generates_content=False,
                            produces="photo",
                            caution="Nothing is bound automatically — you confirm which file.",
                        )
                    )
            except Exception:
                pass
        for r in self.registry.for_requirement(gap.requirement):
            if any(o.resolver_id == r.id and "candidate" in (o.label or "").lower() for o in offers):
                # already surfaced the confirm-folder path for photo_capture
                if r.id == "photo_capture":
                    continue
            caution = ""
            if r.generates_content:
                caution = "Foldok writes a draft; it does not count until you confirm it."
            elif gap.evidential and r.produces != "none":
                caution = "Foldok builds the empty form. The values have to come from site."
            offers.append(
                Offer(
                    resolver_id=r.id,
                    label=r.label,
                    generates_content=r.generates_content,
                    produces=r.produces,
                    caution=caution,
                )
            )
        return offers

    def default_resolver(self, gap_id: str) -> Resolver | None:
        return self.registry.default_for(self.gap(gap_id).requirement)

    # -- doing ----------------------------------------------------------
    def resolve(self, gap_id: str, resolver_id: str | None = None, **kwargs: Any) -> Resolution:
        gap = self.gap(gap_id)
        if resolver_id is None:
            resolver = self.registry.default_for(gap.requirement)
            if resolver is None:
                raise ResolverRefused(
                    f"nothing can resolve '{gap.requirement.key}' automatically; "
                    "attach a file or mark it not applicable"
                )
        else:
            resolver = self.registry.get(resolver_id)
        self.registry.check(resolver, gap.requirement)     # the guard, always
        if not resolver.can_handle(gap.requirement):
            raise ResolverRefused(
                f"'{resolver.id}' cannot handle a {gap.requirement.kind} requirement"
            )
        if resolver.id == "defer" and not self.mode.allow_defer:
            raise ResolverRefused(f"items cannot be parked in {self.mode.title.lower()} mode")

        resolve_kw = dict(kwargs)
        if self.index is not None and "index" not in resolve_kw:
            resolve_kw["index"] = self.index
        resolution = resolver.resolve(gap, self.document, **resolve_kw)
        self.history.append(resolution)
        self.invalidate()
        return resolution

    def resolve_batch(
        self,
        requirement_key: str,
        resolver_id: str | None = None,
        *,
        include_generative: bool = False,
        **kwargs: Any,
    ) -> list[Resolution]:
        """Resolve one requirement across every subject where it is open."""
        targets = [
            g for g in self.gaps().gaps if g.requirement.key == requirement_key and g.open
        ]
        if not targets:
            return []
        probe = resolver_id or (
            self.registry.default_for(targets[0].requirement).id
            if self.registry.default_for(targets[0].requirement)
            else None
        )
        if probe is None:
            raise ResolverRefused(f"nothing can resolve '{requirement_key}' automatically")
        resolver = self.registry.get(probe)
        if resolver.generates_content and not include_generative:
            raise ResolverRefused(
                f"'{resolver.id}' writes content; batching it would put {len(targets)} drafts "
                "into the document that nobody has read. Pass include_generative=True if that "
                "is really what you want."
            )
        out: list[Resolution] = []
        for gap in targets:
            out.append(self.resolve(gap.id, resolver.id, **kwargs))
        return out

    def prepare_everything(self) -> list[Resolution]:
        """One click: create every empty form, capture task and scaffold that
        can be created without authoring content.  This is the demo — thirty
        mangler become thirty concrete things to do."""
        out: list[Resolution] = []
        for gap in list(self.gaps().open()):
            if gap.state == "in_progress":
                continue
            resolver = self.registry.default_for(gap.requirement)
            if resolver is None or resolver.generates_content:
                continue
            try:
                out.append(self.resolve(gap.id, resolver.id))
            except (ResolverRefused, EvidentialGuard):
                continue
        return out

    # -- convenience wrappers -------------------------------------------
    def mark_not_applicable(self, gap_id: str, reason: str, signed_by: str) -> Resolution:
        return self.resolve(gap_id, "not_applicable", reason=reason, signed_by=signed_by)

    def defer(self, gap_id: str, note: str = "") -> Resolution:
        return self.resolve(gap_id, "defer", note=note)

    def attach(self, gap_id: str, path: str, by: str | None = None) -> Resolution:
        return self.resolve(gap_id, "upload", path=path, by=by)

    def fill(self, artifact_id: str, values: dict[str, Any], by: str) -> Artifact:
        art = self.document.artifact(artifact_id)
        if art is None:
            raise KeyError(f"no artifact '{artifact_id}'")
        art.fill(values, by=by)
        self.invalidate()
        return art

    def confirm(self, artifact_id: str, by: str) -> Artifact:
        art = self.document.artifact(artifact_id)
        if art is None:
            raise KeyError(f"no artifact '{artifact_id}'")
        art.provenance.confirm(by)
        if art.pending_fields and not art.data and art.kind in ("diagram",):
            art.pending_fields = ()
        self.invalidate()
        return art

    # -- reporting -------------------------------------------------------
    def report(self) -> str:
        gaps = self.gaps()
        prog = self.progress()
        gate = self.gate()
        lines = [
            f"# {self.document.title or self.document.id}",
            "",
            f"Pack: {self.pack.title} ({self.pack.id} v{self.pack.version})",
            f"Mode: {self.mode.title} — {self.mode.hint}",
            f"Progress: {prog['closed']}/{prog['total']} ({prog['percent']}%)",
            "",
        ]
        for section_id, section_gaps in gaps.by_section(self.pack):
            section = self.pack.section(section_id)
            lines.append(f"## {section.title if section else section_id}")
            for g in sorted(section_gaps, key=lambda g: (g.state, g.requirement.key, g.subject.key())):
                mark = {
                    "resolved": "x",
                    "not_applicable": "-",
                    "in_progress": "~",
                    "deferred": ".",
                    "open": " ",
                }[g.state]
                extra = f" — {g.detail}" if g.detail and g.state != "resolved" else ""
                lines.append(f"- [{mark}] {g.title}{extra}")
            lines.append("")
        if gaps.notices:
            lines.append("## Setup problems")
            lines += [f"- {n}" for n in gaps.notices]
            lines.append("")
        lines.append("## Export")
        lines.append(("PASS — " if gate.ok else "BLOCKED — ") + gate.statement)
        if gate.watermark:
            lines.append(f"Watermark: {gate.watermark}")
        return "\n".join(lines)
