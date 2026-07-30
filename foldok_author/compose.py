"""Deterministic composition — sentences from facts, with no model in the path.

The complaint was pages of tables. The fix people reach for is a model, but for
most of these intents the prose is close to formulaic, and a deterministic
composer has three properties a model cannot match here:

* it cannot invent, so verification passes by construction
* it costs nothing and is instant
* the same facts always produce the same sentence, so a re-issued document does
  not churn

A model is worth calling for ``describe_component`` and ``summarize_system``,
where phrasing genuinely varies. For a declaration or a test record it adds risk
and latency to a sentence with one correct form.
"""

from __future__ import annotations

from typing import Sequence

from .intents import IntentSpec, get
from .model import Fact

JOIN_NO = {"and": "og", "with": "med", "of": "av"}


def compose(intent_id: str, facts: Sequence[Fact], *, title: str = "", lang: str = "en") -> str:
    spec = get(intent_id)
    ordered = _order(facts, spec)
    if not ordered:
        return ""
    builder = {
        "declare_conformity": _declare,
        "record_evidence": _record,
        "identify_product": _identify,
        "specify_parameters": _specify,
        "describe_component": _describe,
        "summarize_system": _describe,
    }[spec.id]
    return builder(ordered, title=title, lang=lang, spec=spec).strip()


def _order(facts: Sequence[Fact], spec: IntentSpec) -> list[Fact]:
    priority = {k: i for i, k in enumerate(spec.keys_first)}
    return sorted(facts, key=lambda f: (priority.get(f.key, 99), f.key))


def _subject(facts: Sequence[Fact], title: str) -> tuple[str, list[Fact]]:
    for f in facts:
        if f.key in ("name", "product", "model", "declarant"):
            return (str(f.value), [x for x in facts if x is not f])
    return (title or "The unit", list(facts))


def _clause(f: Fact, lang: str) -> str:
    label = (f.label or f.key.replace("_", " ")).lower()
    value = f"{f.value} {f.unit}".strip()
    if lang.startswith("no"):
        return f"{label} er {value}"
    return f"{label} is {value}"


def _describe(facts, *, title, lang, spec) -> str:
    subject, rest = _subject(facts, title)
    if not rest:
        return f"{subject}." if lang.startswith("no") else f"{subject}."
    head = rest[: max(1, spec.max_sentences)]
    tail = rest[max(1, spec.max_sentences):]
    parts = [_clause(f, lang) for f in head]
    if lang.startswith("no"):
        first = f"{subject}: " + ", ".join(parts[:-1]) + (f" og {parts[-1]}" if len(parts) > 1 else parts[0] if parts else "")
        sentence = (f"{subject}: {parts[0]}" if len(parts) == 1
                    else f"{subject}: " + ", ".join(parts[:-1]) + f" og {parts[-1]}")
    else:
        sentence = (f"{subject} — {parts[0]}" if len(parts) == 1
                    else f"{subject} — " + ", ".join(parts[:-1]) + f", and {parts[-1]}")
    out = sentence + "."
    if tail:
        more = ", ".join(_clause(f, lang) for f in tail[:3])
        out += (f" Videre: {more}." if lang.startswith("no") else f" In addition, {more}.")
    return out


def _specify(facts, *, title, lang, spec) -> str:
    subject, rest = _subject(facts, title)
    if lang.startswith("no"):
        return f"Tabellen under angir parametrene for {subject}."
    return f"The table below gives the parameters for {subject}."


def _identify(facts, *, title, lang, spec) -> str:
    subject, rest = _subject(facts, title)
    ids = [f for f in rest if f.key in ("serial_no", "model", "manufacturer", "year", "type")]
    if not ids:
        return _describe(facts, title=title, lang=lang, spec=spec)
    parts = [_clause(f, lang) for f in ids]
    if lang.startswith("no"):
        return f"{subject} er merket med " + ", ".join(parts) + "."
    return f"{subject} is marked with " + ", ".join(parts) + "."


def _record(facts, *, title, lang, spec) -> str:
    by_key = {f.key: f for f in facts}
    test = by_key.get("test") or by_key.get("method")
    result = by_key.get("result")
    instrument = by_key.get("instrument")
    date = by_key.get("date")
    who = by_key.get("measured_by")
    if lang.startswith("no"):
        head = f"{test.value} ble utført" if test else "Målingen ble utført"
        if date:
            head += f" {date.value}"
        if who:
            head += f" av {who.value}"
        if instrument:
            head += f", med {instrument.value}"
        out = head + "."
        if result:
            out += f" Resultat: {result.value} {result.unit}".rstrip() + "."
        return out
    head = f"{test.value} was carried out" if test else "The measurement was carried out"
    if date:
        head += f" on {date.value}"
    if who:
        head += f" by {who.value}"
    if instrument:
        head += f", using {instrument.value}"
    out = head + "."
    if result:
        out += f" Result: {result.value} {result.unit}".rstrip() + "."
    return out


def _declare(facts, *, title, lang, spec) -> str:
    by_key = {f.key: f for f in facts}
    declarant = by_key.get("declarant")
    product = by_key.get("product") or by_key.get("model")
    serial = by_key.get("serial_no")
    directive = by_key.get("directive")
    standard = by_key.get("standard")

    if lang.startswith("no"):
        subject = declarant.value if declarant else "Ansvarlig foretak"
        item = product.value if product else "produktet"
        line = f"{subject} erklærer at {item}"
        if serial:
            line += f" (serienr. {serial.value})"
        if directive:
            line += f" er i samsvar med {directive.value}"
        else:
            line += " er levert som beskrevet"
        out = line + "."
        if standard:
            out += f" Anvendt standard: {standard.value}."
        return out
    subject = declarant.value if declarant else "The responsible undertaking"
    item = product.value if product else "the product"
    line = f"{subject} declares that {item}"
    if serial:
        line += f" (serial no. {serial.value})"
    if directive:
        line += f" conforms to {directive.value}"
    else:
        line += " was supplied as described"
    out = line + "."
    if standard:
        out += f" Standard applied: {standard.value}."
    return out
