"""Intents that ship, and the ones that do not.

An intent is a writing contract: what the reader should get, in what voice, in
what shape. Only intents whose content genuinely lives in the fact base are
here. The rest are refused by name, with the reason and the alternative, because
a refusal that explains itself is a feature and a silent omission is a bug.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .model import AUTHORED_NOT_GENERATED, IntentId, IntentRefused


@dataclass(frozen=True)
class IntentSpec:
    id: IntentId
    reader_goal: str
    voice: str
    lead: str                       # how the first sentence opens
    max_sentences: int = 4
    integrate_values: bool = True
    prefer_table: bool = False
    keys_first: tuple[str, ...] = ()
    hint: str = ""


INTENTS: dict[str, IntentSpec] = {
    "describe_component": IntentSpec(
        id="describe_component",
        reader_goal="know what the unit is and its main ratings",
        voice="active indicative, present tense",
        lead="subject",
        keys_first=("name", "model", "type", "manufacturer"),
        hint="State ratings inside sentences, not as a list.",
    ),
    "specify_parameters": IntentSpec(
        id="specify_parameters",
        reader_goal="look a value up quickly",
        voice="minimal",
        lead="subject",
        max_sentences=2,
        integrate_values=False,
        prefer_table=True,
        hint="One sentence naming the subject. The table carries the values.",
    ),
    "declare_conformity": IntentSpec(
        id="declare_conformity",
        reader_goal="read a formal statement they can sign",
        voice="formal, fixed",
        lead="declarant",
        max_sentences=3,
        keys_first=("declarant", "product", "model", "serial_no", "directive", "standard"),
        hint="Say only what the facts support. No elaboration.",
    ),
    "record_evidence": IntentSpec(
        id="record_evidence",
        reader_goal="see what was measured or observed, and by whom",
        voice="record style, past tense",
        lead="action",
        keys_first=("test", "method", "result", "instrument", "date", "measured_by"),
        hint="Neutral record. No interpretation of the result.",
    ),
    "identify_product": IntentSpec(
        id="identify_product",
        reader_goal="identify the product from its markings",
        voice="label-oriented",
        lead="subject",
        max_sentences=3,
        keys_first=("name", "model", "serial_no", "manufacturer", "year"),
        hint="Be exact with identifiers. Never round or reformat them.",
    ),
    "summarize_system": IntentSpec(
        id="summarize_system",
        reader_goal="form a mental model of the whole",
        voice="overview, present tense",
        lead="subject",
        max_sentences=4,
        keys_first=("name", "purpose", "scope"),
        hint="High level. Do not restate every parameter.",
    ),
}

WHY_NOT: dict[str, str] = {
    "instruct_procedure": (
        "a procedure needs an action, an order, a precondition and a failure branch. "
        "None of those are in a (key, value, unit) fact, and none are in a datasheet — "
        "the procedure is in the builder's head. Author the steps; Foldok will number, "
        "cross-reference and verify them (see foldok_author.procedure)"
    ),
    "warn_hazard": (
        "an invented hazard reads exactly like a real one. Hazards come from a risk "
        "assessment or the supplier's instructions, both of which are documents to cite, "
        "not text to generate"
    ),
    "troubleshoot": (
        "symptom-to-remedy is procedural knowledge and is not extractable from "
        "specifications"
    ),
    "explain_process": (
        "how a system behaves over time is not stated in its parameters; it needs a "
        "described sequence, which is authored"
    ),
}


def get(intent_id: str) -> IntentSpec:
    if intent_id in INTENTS:
        return INTENTS[intent_id]
    if intent_id in AUTHORED_NOT_GENERATED:
        raise IntentRefused(
            f"'{intent_id}' is not generated from facts: {WHY_NOT[intent_id]}."
        )
    raise IntentRefused(
        f"unknown intent '{intent_id}'; generated: {', '.join(sorted(INTENTS))}; "
        f"authored instead: {', '.join(AUTHORED_NOT_GENERATED)}"
    )


def available() -> dict[str, str]:
    return {k: v.reader_goal for k, v in sorted(INTENTS.items())}
