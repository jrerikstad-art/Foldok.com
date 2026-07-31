"""The diagram route for ``hub_chat``.

``hub_chat`` is a keyword router, not a tool-using agent — there is no model in
that path and no tool loop to register anything with.  So the fix is not a tool
definition, it is a **route**: one more branch beside ``is_privacy_question`` and
``is_catalog_question`` that recognises a diagram request and calls the engine.

Two things this file also has to undo, both in ``match_cannot``:

``"modellere"`` and ``"tegne hus"`` sit in the CAD refusal tuple, and ``"3d"`` is
matched as a bare substring.  Between them they catch requests that have nothing
to do with CAD, and the reply that comes back — *"I can build documentation
around drawing PDFs and photos you have"* — is the canned CAD answer, which is
why it reads as a capability denial when it is really a misrouted question.

``apply_patch`` removes exactly those triggers and leaves ``dwg``, ``step``,
``solidworks``, ``native cad`` and ``3d model`` alone, because those refusals are
true.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

# Words that mean "show me how this connects". Norwegian first: the users are.
DIAGRAM_WORDS: tuple[str, ...] = (
    "koblingsskjema", "koblingsjema", "kobleskjema", "enlinjeskjema", "enlinje",
    "skjema", "diagram", "schematic", "wiring diagram", "wiring",
    "hvordan kobler", "hvordan kobles", "hvordan koble", "koble sammen",
    "how do i connect", "how to connect", "how are they connected",
    "connection diagram", "interconnection", "single line", "single-line",
    "prinsippskisse", "koblingstegning",
)

# Words that mean the request is about a *file* of a diagram, not drawing one.
NOT_DRAWING: tuple[str, ...] = (
    "dwg", "step", "solidworks", "native cad", "3d model", "3d-modell",
    "importer tegning", "import drawing", "les tegningen", "read the drawing",
)


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.lower()).strip()


def is_diagram_request(question: str) -> bool:
    """Does this ask for a drawing, rather than about one?"""
    q = _fold(question)
    if any(w in q for w in NOT_DRAWING):
        return False
    return any(_fold(w) in q for w in DIAGRAM_WORDS)


@dataclass
class RouteResult:
    handled: bool
    reply: str = ""
    svg: str = ""
    spec_needed: bool = False
    missing: tuple[str, ...] = ()
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"handled": self.handled, "reply": self.reply}
        if self.svg:
            d["svg"] = self.svg
        if self.spec_needed:
            d["spec_needed"] = True
            d["missing"] = list(self.missing)
        if self.warnings:
            d["warnings"] = self.warnings
        return d


def handle(
    question: str,
    *,
    spec: Mapping[str, Any] | None = None,
    components: Sequence[Mapping[str, Any]] = (),
    lang: str = "no",
) -> RouteResult:
    """Route a diagram request.

    With a spec, draw it. Without one, ask for the connections — and say what is
    already known, because "I need more information" with no list is the same
    dead end as "I have no tool".
    """
    if not is_diagram_request(question):
        return RouteResult(handled=False)

    if spec:
        try:
            from foldok_diagram_tool import run
        except ImportError:  # pragma: no cover
            return RouteResult(
                handled=True,
                reply=(
                    "Diagramtegning er ikke installert i denne byggingen."
                    if lang == "no"
                    else "The diagram engine is not installed in this build."
                ),
            )
        try:
            result = run(dict(spec))
        except Exception as exc:  # noqa: BLE001 - the message is written for a person
            return RouteResult(handled=True, reply=str(exc))
        return RouteResult(
            handled=True,
            reply=_drawn_reply(result, lang),
            svg=result.svg,
            warnings=list(result.warnings),
        )

    known = [str(c.get("label") or c.get("id")) for c in components][:12]
    return RouteResult(
        handled=True,
        spec_needed=True,
        missing=("connections",),
        reply=_ask_reply(known, lang),
    )


def _drawn_reply(result: Any, lang: str) -> str:
    n_c = len(result.graph.components)
    n_w = len(result.graph.connections)
    if lang == "no":
        line = (
            f"Tegnet koblingsskjema med {n_c} komponent(er) og {n_w} forbindelse(r). "
            "Figuren er lagt inn i dokumentet."
        )
        if result.modules_drawn:
            line += (
                f" {len(result.modules_drawn)} av dem er tegnet som merkede bokser med "
                "pinnenavn, slik det gjøres for moduler og breakout-kort."
            )
        return line
    line = (
        f"Drew a wiring diagram with {n_c} component(s) and {n_w} connection(s). "
        "The figure is in the document."
    )
    if result.modules_drawn:
        line += (
            f" {len(result.modules_drawn)} are drawn as labelled boxes with their pins, "
            "which is the normal convention for modules and breakout boards."
        )
    return line


def _ask_reply(known: Sequence[str], lang: str) -> str:
    if lang == "no":
        head = "Jeg kan tegne koblingsskjemaet. Jeg trenger å vite hva som kobles til hva."
        if known:
            head += "\n\nKomponenter jeg allerede har fra prosjektet:\n" + "\n".join(
                f"  - {k}" for k in known
            )
            head += (
                "\n\nSi hvilke som kobles sammen, for eksempel «5V fra buck til Pi, "
                "SDA/SCL fra Pi via nivåskifter til PWM-kortet»."
            )
        return head
    head = "I can draw the wiring diagram. I need to know what connects to what."
    if known:
        head += "\n\nComponents already in the project:\n" + "\n".join(f"  - {k}" for k in known)
        head += (
            "\n\nTell me which connect to which — for example \"5V from the buck to the Pi, "
            "SDA/SCL from the Pi through the level shifter to the PWM board\"."
        )
    return head


# ----------------------------------------------------------------------
# the patch to match_cannot
# ----------------------------------------------------------------------
OLD_TRIGGER = (
    '(("3d", "tegne hus", "modellere", "dwg", "step", "solidworks", "native cad",\n'
    '          "draw my house", "3d model"),'
)
NEW_TRIGGER = (
    '(("dwg", "step", "solidworks", "native cad", "3d model", "3d-modell",\n'
    '          "tegne hus", "draw my house"),'
)


def apply_patch(path: str | Path, *, dry_run: bool = False) -> tuple[bool, str]:
    """Narrow the CAD refusal so it stops catching diagram requests.

    Removes ``"modellere"`` and the bare ``"3d"`` substring; keeps every refusal
    that is actually true. Idempotent, and it reports rather than guesses when
    the file has moved on.
    """
    p = Path(path)
    if not p.exists():
        return (False, f"{p} does not exist")
    text = p.read_text(encoding="utf-8", errors="replace")
    newline = "\r\n" if "\r\n" in text else "\n"
    flat = text.replace("\r\n", "\n")

    if NEW_TRIGGER in flat:
        return (True, "already patched")
    if OLD_TRIGGER not in flat:
        return (
            False,
            "the CAD trigger tuple in match_cannot does not look the way it did — "
            "patch it by hand: drop \"modellere\" and the bare \"3d\", keep dwg/step/"
            "solidworks/native cad/3d model",
        )

    patched = flat.replace(OLD_TRIGGER, NEW_TRIGGER, 1)
    if dry_run:
        return (True, "would patch match_cannot")
    p.write_text(patched.replace("\n", newline), encoding="utf-8")
    return (True, "patched match_cannot: 'modellere' and bare '3d' no longer refuse")


ROUTE_SNIPPET = '''
# --- diagram route -------------------------------------------------------
# hub_chat is a keyword router, so a drawing capability needs a route, not a
# tool registration. Place this branch BEFORE the match_cannot check, or the
# CAD refusal answers first.
import foldok_route.diagram_route as diagram_route

if diagram_route.is_diagram_request(message):
    routed = diagram_route.handle(
        message,
        spec=pending_diagram_spec,        # None until the user describes connections
        components=project_components,    # from the index, for the "what I know" list
        lang=lang,
    )
    if routed.handled:
        return {"reply": routed.reply, "svg": routed.svg or None}
'''
