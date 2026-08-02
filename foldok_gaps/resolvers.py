"""Resolvers — turning a gap into an artifact.

The whole feature turns on one rule, and it is enforced here in code rather
than asked for in a prompt:

    A model may draft what someone *intends*.
    A model may never author what someone *observed*.

Method statements, scope text, procedure descriptions, a principle schematic:
draft away.  Insulation resistance readings, a photo of the actual installation,
serial numbers, as-built deviations, signatures: the engine produces the empty
form and the instruction, and a person fills it in.

If that line is crossed once, Foldok has shipped fabricated evidence with a
tradesperson's name on it.  So ``generates_content`` is a property of the
resolver, ``evidence`` is a property of the requirement, and the registry
refuses to bind one to the other.  Test ``test_evidential_guard_*`` is the
contract; do not relax it to make a demo smoother.

The pleasant side effect is that it sells.  "Foldok will not invent your test
results" is a sentence an inspector wants to hear.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, runtime_checkable

from .document import Artifact, Document, Entry, Provenance
from .gaps import Gap, GapState
from .requirements import ArtifactKind, Requirement


class EvidentialGuard(Exception):
    """Raised when a content-generating resolver is aimed at evidence."""


class ResolverRefused(Exception):
    """Raised when a resolver cannot do what was asked, with the reason."""


@dataclass
class Resolution:
    gap_id: str
    resolver_id: str
    state: GapState
    message: str
    artifact: Artifact | None = None
    follow_up: tuple[str, ...] = ()

    def __str__(self) -> str:
        return f"{self.resolver_id} -> {self.state}: {self.message}"


@runtime_checkable
class Resolver(Protocol):
    id: str
    produces: ArtifactKind
    generates_content: bool
    label: str

    def can_handle(self, requirement: Requirement) -> bool: ...

    def resolve(self, gap: Gap, document: Document, **kwargs: Any) -> Resolution: ...


# ----------------------------------------------------------------------
# drafting hook — the model lives behind this, not inside the resolvers
# ----------------------------------------------------------------------
@runtime_checkable
class Drafter(Protocol):
    def draft(self, prompt: str, context: dict[str, Any]) -> str: ...


class NullDrafter:
    """Default.  Fails loudly rather than quietly producing nothing."""

    def draft(self, prompt: str, context: dict[str, Any]) -> str:
        raise ResolverRefused(
            "no drafter is wired in; pass a Drafter to the resolver, or resolve this gap by hand"
        )


def _artifact_id(gap: Gap, suffix: str = "") -> str:
    return f"art_{gap.id}{suffix}"


# ----------------------------------------------------------------------
# resolvers that never author content
# ----------------------------------------------------------------------
class NotApplicableResolver:
    """The most-used resolver in any real project, and the one most often
    forgotten.  If the only exit from a gap is 'produce an artifact', people
    will manufacture one.  N/A with a reason and a name is a real resolution."""

    id = "not_applicable"
    produces: ArtifactKind = "none"
    generates_content = False
    label = "Not applicable"

    def can_handle(self, requirement: Requirement) -> bool:
        return requirement.allow_not_applicable

    def resolve(self, gap: Gap, document: Document, **kwargs: Any) -> Resolution:
        reason = str(kwargs.get("reason", "")).strip()
        signed_by = str(kwargs.get("signed_by", "")).strip()
        if not gap.requirement.allow_not_applicable:
            raise ResolverRefused(
                f"'{gap.requirement.title}' cannot be waived"
                + (f" ({gap.requirement.authority})" if gap.requirement.authority else "")
            )
        if not reason:
            raise ResolverRefused("a reason is required — 'not applicable' with no reason is not a record")
        if not signed_by:
            raise ResolverRefused("a name is required; someone has to stand behind the judgement")
        document.put(
            Entry(
                requirement_key=gap.requirement.key,
                subject=gap.subject,
                not_applicable=True,
                reason=reason,
                signed_by=signed_by,
            )
        )
        return Resolution(gap.id, self.id, "not_applicable", f"not applicable: {reason}")


class MeasurementFormResolver:
    """Builds the empty form.  Never a value."""

    id = "measurement_form"
    produces: ArtifactKind = "measurement"
    generates_content = False
    label = "Create measurement form"

    def can_handle(self, requirement: Requirement) -> bool:
        return requirement.kind == "measurement"

    def resolve(self, gap: Gap, document: Document, **kwargs: Any) -> Resolution:
        req = gap.requirement
        if not req.fields:
            raise ResolverRefused(f"'{req.key}' declares no fields, so there is no form to build")
        art = Artifact(
            id=_artifact_id(gap),
            kind="measurement",
            title=gap.title,
            data={},
            pending_fields=tuple(f.key for f in req.fields if f.required),
            instruction=req.description or f"Record {req.title.lower()} on site",
            produced_by=self.id,
            provenance=Provenance(source="engine", note="empty form; values must be measured"),
        )
        _attach(document, gap, art)
        fields = ", ".join(f"{f.label} ({f.unit})" if f.unit else f.label for f in req.fields)
        return Resolution(
            gap.id, self.id, "in_progress",
            f"form ready — fill in on site: {fields}",
            artifact=art,
            follow_up=("measure and fill in", "confirm with a name"),
        )


class TableFormResolver:
    id = "table_form"
    produces: ArtifactKind = "table"
    generates_content = False
    label = "Create table"

    def can_handle(self, requirement: Requirement) -> bool:
        return requirement.kind == "table"

    def resolve(self, gap: Gap, document: Document, **kwargs: Any) -> Resolution:
        req = gap.requirement
        columns = [f.key for f in req.fields] or ["item", "value"]
        rows = kwargs.get("rows") or []
        art = Artifact(
            id=_artifact_id(gap),
            kind="table",
            title=gap.title,
            data={"columns": columns, "rows": rows},
            pending_fields=() if rows else ("rows",),
            instruction=req.description or "Add the rows",
            produced_by=self.id,
            provenance=Provenance(
                source="import" if rows else "engine",
                ref=kwargs.get("ref"),
            ),
        )
        _attach(document, gap, art)
        state: GapState = "resolved" if rows and kwargs.get("ref") else "in_progress"
        return Resolution(gap.id, self.id, state, f"table with columns {columns}", artifact=art)


class PhotoCaptureResolver:
    id = "photo_capture"
    produces: ArtifactKind = "photo"
    generates_content = False
    label = "Create capture task"

    def can_handle(self, requirement: Requirement) -> bool:
        return requirement.kind == "photo"

    def resolve(self, gap: Gap, document: Document, **kwargs: Any) -> Resolution:
        req = gap.requirement
        lang = str(kwargs.get("lang") or "no")
        instruction = req.capture_prompt or f"Photograph: {req.title}"
        candidates: list[dict[str, Any]] = []
        # foldok_role — offer photos already in the folder before "go take it"
        index = kwargs.get("index")
        if index is not None:
            try:
                from foldok_role import offers_for
                offers = offers_for([gap], index)
                if offers:
                    offer = offers[0]
                    candidates = [c.to_dict() for c in offer.candidates]
                    if offer.has_candidates:
                        instruction = offer.message(lang=lang)
            except Exception:
                pass
        art = Artifact(
            id=_artifact_id(gap),
            kind="photo",
            title=gap.title,
            instruction=instruction,
            pending_fields=("path",),
            produced_by=self.id,
            provenance=Provenance(source="engine", note="capture task"),
            data={"photo_candidates": candidates} if candidates else {},
        )
        _attach(document, gap, art)
        follow = ("take the photo on site",)
        if candidates:
            follow = ("confirm which folder photo matches, or take a new one",)
        return Resolution(
            gap.id, self.id, "in_progress", art.instruction, artifact=art,
            follow_up=follow,
        )


class UploadResolver:
    id = "upload"
    produces: ArtifactKind = "file"
    generates_content = False
    label = "Attach a file"

    def can_handle(self, requirement: Requirement) -> bool:
        # Measurements included on purpose: people have instrument printouts and
        # test reports already. Attaching one is evidence; it is not authoring.
        return requirement.kind in ("file", "photo", "table", "text", "diagram", "measurement")

    def resolve(self, gap: Gap, document: Document, **kwargs: Any) -> Resolution:
        path = kwargs.get("path")
        art = Artifact(
            id=_artifact_id(gap),
            kind=gap.requirement.kind if gap.requirement.kind != "none" else "file",
            title=gap.title,
            path=path,
            pending_fields=() if path else ("path",),
            instruction="Attach the document you already have",
            produced_by=self.id,
            provenance=Provenance(source="import", ref=path, confirmed_by=kwargs.get("by")),
        )
        _attach(document, gap, art)
        return Resolution(
            gap.id, self.id,
            "resolved" if (path and kwargs.get("by")) else "in_progress",
            f"attached {path}" if path else "waiting for a file",
            artifact=art,
        )


class SignatureResolver:
    id = "signature"
    produces: ArtifactKind = "signature"
    generates_content = False
    label = "Sign"

    def can_handle(self, requirement: Requirement) -> bool:
        return requirement.kind == "signature"

    def resolve(self, gap: Gap, document: Document, **kwargs: Any) -> Resolution:
        by = str(kwargs.get("by", "")).strip()
        art = Artifact(
            id=_artifact_id(gap),
            kind="signature",
            title=gap.title,
            instruction="Sign to confirm",
            produced_by=self.id,
            provenance=Provenance(source="user"),
        )
        if by:
            art.provenance.confirm(by)
        _attach(document, gap, art)
        return Resolution(
            gap.id, self.id, "resolved" if by else "in_progress",
            f"signed by {by}" if by else "waiting for a signature",
            artifact=art,
        )


class DiagramScaffoldResolver:
    """Evidential-safe diagram.

    Seeds a canvas from components the document already has a source for — a
    BOM row, a photo — and nothing else.  It never invents a component or a
    connection, so it can be pointed at an as-built requirement.  The user
    places and connects; the artifact stays in progress until they confirm.
    """

    id = "diagram_scaffold"
    produces: ArtifactKind = "diagram"
    generates_content = False
    label = "Start a diagram from the BOM"

    def can_handle(self, requirement: Requirement) -> bool:
        return requirement.kind == "diagram"

    def resolve(self, gap: Gap, document: Document, **kwargs: Any) -> Resolution:
        seeds = kwargs.get("seed_components")
        if seeds is None:
            seeds = _bom_for(document, gap)
        graph_dict = _seed_graph(gap, document, seeds)
        svg = _try_render(graph_dict, kwargs.get("profile_id", "wiring"))
        art = Artifact(
            id=_artifact_id(gap),
            kind="diagram",
            title=gap.title,
            body=svg,
            data={"graph": graph_dict, "profile": kwargs.get("profile_id", "wiring")},
            pending_fields=("layout_confirmed",),
            instruction=(
                f"{len(seeds)} component(s) placed from the parts list, with no connections "
                "assumed. Connect them as installed, then confirm."
            ),
            produced_by=self.id,
            provenance=Provenance(source="engine", note="scaffold seeded from sourced parts only"),
        )
        _attach(document, gap, art)
        return Resolution(
            gap.id, self.id, "in_progress", art.instruction, artifact=art,
            follow_up=("connect the components as installed", "confirm the drawing"),
        )


class DeferResolver:
    id = "defer"
    produces: ArtifactKind = "none"
    generates_content = False
    label = "Not now"

    def can_handle(self, requirement: Requirement) -> bool:
        return True

    def resolve(self, gap: Gap, document: Document, **kwargs: Any) -> Resolution:
        document.put(
            Entry(
                requirement_key=gap.requirement.key,
                subject=gap.subject,
                deferred=True,
                note=str(kwargs.get("note", "deferred")),
            )
        )
        return Resolution(gap.id, self.id, "deferred", "parked; it will come back in review")


# ----------------------------------------------------------------------
# resolvers that DO author content — expository only
# ----------------------------------------------------------------------
class TextDraftResolver:
    id = "text_draft"
    produces: ArtifactKind = "text"
    generates_content = True
    label = "Draft with Foldok"

    def __init__(self, drafter: Drafter | None = None) -> None:
        self.drafter = drafter or NullDrafter()

    def can_handle(self, requirement: Requirement) -> bool:
        return requirement.kind == "text" and requirement.evidence == "expository"

    def resolve(self, gap: Gap, document: Document, **kwargs: Any) -> Resolution:
        req = gap.requirement
        if req.evidence != "expository":
            raise EvidentialGuard(
                f"'{req.key}' records what was observed; Foldok drafts intent, not evidence"
            )
        context = {
            "document": document.title,
            "segment": document.segment,
            "jurisdiction": document.jurisdiction,
            "subject": gap.subject.label or gap.subject.id,
            "authority": req.authority,
            "facts": dict(sorted(document.facts.items())),
        }
        prompt = req.template or (
            f"Write the '{req.title}' section for a {document.segment} job. "
            f"{req.description}".strip()
        )
        body = self.drafter.draft(prompt, context)
        art = Artifact(
            id=_artifact_id(gap),
            kind="text",
            title=gap.title,
            body=body,
            instruction="Read it and confirm, or edit it first",
            produced_by=self.id,
            provenance=Provenance(source="ai", note="draft; unconfirmed"),
        )
        _attach(document, gap, art)
        return Resolution(
            gap.id, self.id, "in_progress",
            "drafted — nothing drafted by Foldok counts as complete until a person confirms it",
            artifact=art,
            follow_up=("read and confirm",),
        )


class DiagramDraftResolver:
    """A principle or typical schematic — expository.  Not an as-built."""

    id = "diagram_draft"
    produces: ArtifactKind = "diagram"
    generates_content = True
    label = "Propose a diagram"

    def __init__(self, proposer: Callable[[Gap, Document], dict[str, Any]] | None = None) -> None:
        self.proposer = proposer

    def can_handle(self, requirement: Requirement) -> bool:
        return requirement.kind == "diagram" and requirement.evidence == "expository"

    def resolve(self, gap: Gap, document: Document, **kwargs: Any) -> Resolution:
        if gap.requirement.evidence != "expository":
            raise EvidentialGuard(
                f"'{gap.requirement.key}' is an as-built record; use the scaffold resolver"
            )
        graph_dict = kwargs.get("graph")
        if graph_dict is None:
            if self.proposer is None:
                raise ResolverRefused("no proposer wired in and no graph supplied")
            graph_dict = self.proposer(gap, document)
        svg = _try_render(graph_dict, kwargs.get("profile_id", "wiring"))
        art = Artifact(
            id=_artifact_id(gap),
            kind="diagram",
            title=gap.title,
            body=svg,
            data={"graph": graph_dict, "profile": kwargs.get("profile_id", "wiring")},
            instruction="Check every component and connection against the installation, then confirm",
            produced_by=self.id,
            provenance=Provenance(source="ai", note="proposed; unconfirmed"),
        )
        _attach(document, gap, art)
        return Resolution(
            gap.id, self.id, "in_progress", "diagram proposed — confirm it before it counts",
            artifact=art, follow_up=("check against the installation", "confirm"),
        )


# ----------------------------------------------------------------------
# registry
# ----------------------------------------------------------------------
class ResolverRegistry:
    def __init__(self, resolvers: list[Resolver] | None = None) -> None:
        self._by_id: dict[str, Resolver] = {}
        for r in resolvers or ():
            self.register(r)

    def register(self, resolver: Resolver) -> None:
        self._by_id[resolver.id] = resolver

    def get(self, resolver_id: str) -> Resolver:
        try:
            return self._by_id[resolver_id]
        except KeyError as exc:
            raise ResolverRefused(
                f"no resolver '{resolver_id}'; known: {sorted(self._by_id)}"
            ) from exc

    def all(self) -> list[Resolver]:
        return [self._by_id[k] for k in sorted(self._by_id)]

    def check(self, resolver: Resolver, requirement: Requirement) -> None:
        """The guard.  One place, always called."""
        if requirement.evidence == "evidential" and resolver.generates_content:
            raise EvidentialGuard(
                f"'{resolver.id}' authors content, and '{requirement.key}' records evidence"
                + (f" ({requirement.authority})" if requirement.authority else "")
                + ". Foldok can build the empty form and tell you what to capture; "
                "it will not write down what was measured."
            )

    def for_requirement(self, requirement: Requirement) -> list[Resolver]:
        """Offerable resolvers, best first.  Never includes a guarded one."""
        allowed: list[Resolver] = []
        for r in self.all():
            if not r.can_handle(requirement):
                continue
            try:
                self.check(r, requirement)
            except EvidentialGuard:
                continue
            allowed.append(r)

        preference = {rid: i for i, rid in enumerate(requirement.resolvers)}
        return sorted(
            allowed,
            key=lambda r: (
                preference.get(r.id, 500),
                0 if r.produces == requirement.kind else 1,
                r.id,
            ),
        )

    def default_for(self, requirement: Requirement) -> Resolver | None:
        options = [r for r in self.for_requirement(requirement) if r.id not in ("defer", "not_applicable")]
        return options[0] if options else None


def default_registry(drafter: Drafter | None = None) -> ResolverRegistry:
    return ResolverRegistry(
        [
            NotApplicableResolver(),
            MeasurementFormResolver(),
            TableFormResolver(),
            PhotoCaptureResolver(),
            UploadResolver(),
            SignatureResolver(),
            DiagramScaffoldResolver(),
            DiagramDraftResolver(),
            TextDraftResolver(drafter),
            DeferResolver(),
        ]
    )


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def _attach(document: Document, gap: Gap, artifact: Artifact) -> Entry:
    return document.put(
        Entry(
            requirement_key=gap.requirement.key,
            subject=gap.subject,
            artifact=artifact,
        )
    )


def _bom_for(document: Document, gap: Gap) -> list[dict[str, Any]]:
    """Parts the document already has a source for, filtered to this subject."""
    rows = document.facts.get("bom") or []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        owner = row.get("subject")
        if owner and owner != gap.subject.key() and owner != gap.subject.id:
            continue
        if not row.get("ref"):
            continue          # unsourced parts do not get placed
        out.append(row)
    return out


def _seed_graph(gap: Gap, document: Document, seeds: list[dict[str, Any]]) -> dict[str, Any]:
    domain = "piping" if gap.requirement.tags and "piping" in gap.requirement.tags else "electrical"
    kind = "fluid" if domain == "piping" else "electrical"
    components = []
    for row in seeds:
        cid = str(row.get("id") or row.get("tag") or f"C{len(components) + 1}")
        components.append(
            {
                "id": cid,
                "type": row.get("type", "terminal"),
                "domain": row.get("domain", domain),
                "label": row.get("label", ""),
                "tag": row.get("tag"),
                "ports": row.get("ports")
                or [
                    {"id": "a", "name": "a", "side": "left", "kind": kind, "order": 0},
                    {"id": "b", "name": "b", "side": "right", "kind": kind, "order": 1},
                ],
                "provenance": {"source": "import", "ref": row["ref"]},
            }
        )
    return {
        "schema_version": 2,
        "id": f"scaffold_{gap.id}",
        "title": gap.title,
        "subtitle": "Scaffold — connections not yet drawn",
        "domain": domain,
        "jurisdiction": document.jurisdiction or "NO_IT_230",
        "notes": ["Components placed from sourced parts only. No connection has been assumed."],
        "components": components,
        "connections": [],
    }


def _try_render(graph_dict: dict[str, Any], profile_id: str) -> str | None:
    """Render through the diagram engine if it is installed."""
    try:
        from foldok_diagram import DiagramStyle, figure
        from foldok_diagram import profile as profiles
        from foldok_diagram.model import Graph
    except ImportError:  # pragma: no cover - engine optional
        return None
    try:
        graph = Graph.from_dict(graph_dict)
        prof = profiles.get(profile_id)
        return figure(graph, prof, DiagramStyle()).svg
    except Exception:  # pragma: no cover - never let a render fail a resolve
        return None
