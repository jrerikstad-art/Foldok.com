"""Selection — which asset supports this section.

Runs **after** the narrative, because it needs one. And it never asks a model to
browse.

The failure this replaces: the engine reported a photograph missing while the
photograph sat in the folder. That is what happens when "does an image exist?" is
delegated to something that cannot look. A language model asked an open question
about a filesystem will answer confidently either way, and both answers are
guesses.

So the model is handed a menu:

    Available images for "Montering av kabelbro":
      IMG1  Hovedtavle DB1 med deksel av, merking synlig
      IMG2  Kabelbro i gangen, festet til betong
      IMG3  Kabelgjennomføring i brannskille

    Which of these supports this section? Reply with ids, or NONE.

That is a bounded choice, and models are good at bounded choices. It also makes
the empty case safe: when the menu is empty the engine says so and the model is
never in a position to invent an image, because it was never asked whether one
exists.

``Selection`` carries what was chosen *and* what was offered, so a section citing
nothing can be told apart from a section that had nothing to cite.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .context import Asset, DocumentContext

STOP = {
    "the", "and", "for", "with", "this", "that", "från", "og", "av", "til", "med",
    "som", "det", "den", "der", "en", "et", "i", "på", "om", "seksjon", "section",
    "kapittel", "chapter", "dokument", "document",
}

MAX_MENU = 12


@dataclass
class MenuItem:
    asset: Asset
    hint: str = ""                   # why it was shortlisted, shown to the model

    def line(self) -> str:
        base = self.asset.menu_line()
        return f"{base}   [{self.hint}]" if self.hint else base


@dataclass
class Menu:
    section: str
    kind: str
    items: list[MenuItem] = field(default_factory=list)
    offered_from: int = 0            # how many existed before shortlisting

    @property
    def empty(self) -> bool:
        return not self.items

    def prompt(self, *, lang: str = "no") -> str:
        """The bounded question. Never 'is there an image?'"""
        label = {
            "image": ("bilder", "images"), "drawing": ("tegninger", "drawings"),
            "diagram": ("skjema", "diagrams"), "table": ("tabeller", "tables"),
            "standard": ("standarder", "standards"), "document": ("dokumenter", "documents"),
        }[self.kind][0 if lang.startswith("no") else 1]

        if self.empty:
            return (
                f"Ingen {label} er tilgjengelig for «{self.section}». "
                "Ikke vis til noen."
                if lang.startswith("no") else
                f"No {label} are available for \"{self.section}\". Do not refer to any."
            )
        head = (
            f"Tilgjengelige {label} for «{self.section}»:"
            if lang.startswith("no") else
            f"Available {label} for \"{self.section}\":"
        )
        tail = (
            "Hvilke av disse støtter denne seksjonen? Svar med id-er, eller INGEN. "
            "Ikke vis til noe som ikke står i listen."
            if lang.startswith("no") else
            "Which of these support this section? Reply with ids, or NONE. "
            "Do not refer to anything not in the list."
        )
        return head + "\n" + "\n".join(f"  {i.line()}" for i in self.items) + "\n" + tail

    def ids(self) -> list[str]:
        return [i.asset.id for i in self.items]


@dataclass
class Selection:
    section: str
    chosen: list[Asset] = field(default_factory=list)
    offered: list[str] = field(default_factory=list)
    invented: list[str] = field(default_factory=list)   # ids the model made up

    @property
    def had_nothing(self) -> bool:
        return not self.offered

    @property
    def declined(self) -> bool:
        """Offered assets and chose none — different from having none."""
        return bool(self.offered) and not self.chosen

    def to_dict(self) -> dict[str, Any]:
        return {
            "section": self.section,
            "chosen": [a.to_dict() for a in self.chosen],
            "offered": list(self.offered),
            "invented": list(self.invented),
            "had_nothing": self.had_nothing,
            "declined": self.declined,
        }


# ----------------------------------------------------------------------
def menu_for(
    context: DocumentContext,
    *,
    section: str,
    kind: str = "image",
    purpose: str = "",
    subject: str = "",
    limit: int = MAX_MENU,
) -> Menu:
    """Shortlist, ranked, but never empty when assets exist.

    Everything of the right kind is offerable. Shortlisting only reorders and
    caps — an asset with no keyword overlap is still an asset the section could
    use, and the engine has no business deciding otherwise before the model has
    seen the section.
    """
    assets = context.of_kind(kind)
    want = _terms(f"{section} {purpose} {subject}")

    scored: list[tuple[float, str, Asset]] = []
    for asset in assets:
        have = _terms(f"{asset.title} {asset.caption} {' '.join(asset.tags)} {asset.name}")
        shared = want & have
        score = len(shared) + (1.5 if subject and _terms(subject) & have else 0.0)
        hint = ", ".join(sorted(shared)[:3]) if shared else ""
        scored.append((score, hint, asset))

    scored.sort(key=lambda t: (-t[0], t[2].id))
    return Menu(
        section=section, kind=kind, offered_from=len(assets),
        items=[MenuItem(asset=a, hint=h) for _, h, a in scored[:limit]],
    )


def parse_reply(reply: str, menu: Menu, context: DocumentContext) -> Selection:
    """Read the model's answer against the menu it was given.

    Anything it names that was not offered is recorded as invented rather than
    silently dropped — a model citing IMG7 when six were offered is a signal, not
    a typo.
    """
    text = (reply or "").upper()
    selection = Selection(section=menu.section, offered=menu.ids())

    if re.search(r"\b(NONE|INGEN|INGENTING)\b", text):
        return selection

    named = set(re.findall(r"\b(?:IMG|DWG|DIA|TBL|STD|DOC)\s?\d{1,3}\b", text))
    named = {n.replace(" ", "") for n in named}
    offered = set(menu.ids())

    for asset_id in sorted(named):
        if asset_id in offered:
            asset = context.get(asset_id)
            if asset is not None:
                selection.chosen.append(asset)
        else:
            selection.invented.append(asset_id)
    return selection


def select_for_section(
    context: DocumentContext,
    *,
    section: str,
    kind: str = "image",
    purpose: str = "",
    subject: str = "",
    ask: Any = None,
    lang: str = "no",
) -> Selection:
    """One section, one kind, one bounded question.

    ``ask`` is any callable taking a prompt and returning a reply. Without one
    this returns the empty selection with the menu recorded, which is the right
    default: no model, no guess.
    """
    menu = menu_for(context, section=section, kind=kind, purpose=purpose, subject=subject)
    if menu.empty or ask is None:
        return Selection(section=section, offered=menu.ids())
    return parse_reply(str(ask(menu.prompt(lang=lang))), menu, context)


def caption_note(selection: Selection, *, lang: str = "no") -> str:
    """What the section says about its own illustrations.

    A section that had nothing must not read like a section that chose nothing.
    """
    if selection.chosen:
        names = ", ".join(a.name for a in selection.chosen)
        return (f"Illustrasjoner: {names}." if lang.startswith("no")
                else f"Illustrations: {names}.")
    if selection.had_nothing:
        return ("Ingen illustrasjoner er tilgjengelige for denne seksjonen."
                if lang.startswith("no")
                else "No illustrations are available for this section.")
    return ("Tilgjengelige illustrasjoner passet ikke denne seksjonen."
            if lang.startswith("no")
            else "Available illustrations did not fit this section.")


def _terms(text: str) -> set[str]:
    return {
        w.lower() for w in re.findall(r"[A-Za-zÆØÅæøå0-9]{3,}", text or "")
    } - STOP
