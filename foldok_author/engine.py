"""The authoring engine.

    engine = AuthoringEngine()                     # deterministic, no model
    result = engine.author("declare_conformity", facts)

    engine = AuthoringEngine(generate=call_model)  # model for varied phrasing
"""

from __future__ import annotations

from typing import Callable, Sequence

from .compose import compose
from .intents import IntentSpec, available, get
from .model import Fact, IntentRefused, Plan, Result
from .verify import verify


class AuthoringEngine:
    def __init__(
        self,
        generate: Callable[[str], str] | None = None,
        *,
        lang: str = "en",
    ) -> None:
        self.generate = generate
        self.lang = lang

    def plan(self, intent_id: str, facts: Sequence[Fact], *, title: str = "") -> Plan:
        spec = get(intent_id)
        priority = {k: i for i, k in enumerate(spec.keys_first)}
        must = [f.id for f in facts if f.key in priority] or [f.id for f in facts[:6]]
        return Plan(
            intent=spec.id,
            beats=[f"Reader should: {spec.reader_goal}", spec.hint],
            fact_ids=[f.id for f in facts],
            must_include=must,
            style=[f"voice: {spec.voice}", spec.hint],
        )

    def author(
        self,
        intent_id: str,
        facts: Sequence[Fact],
        *,
        title: str = "",
        draft: str | None = None,
    ) -> Result:
        """Deterministic by default. A model only where phrasing varies."""
        plan = self.plan(intent_id, facts, title=title)
        if draft is None:
            spec = get(intent_id)
            if self.generate is not None and spec.id in ("describe_component", "summarize_system"):
                draft = self.generate(self.prompt(intent_id, facts, title=title))
            else:
                draft = compose(intent_id, facts, title=title, lang=self.lang)
        return verify(draft, plan, list(facts))

    def prompt(self, intent_id: str, facts: Sequence[Fact], *, title: str = "") -> str:
        spec = get(intent_id)
        lines = [f"{f.id}: {f.phrase()}" + (f" [{f.citation}]" if f.citation else "")
                 for f in facts]
        language = "Norwegian (Bokmål)" if self.lang.startswith("no") else "English"
        return (
            f"Write {language} technical prose.\n"
            f"INTENT: {spec.id} — the reader should {spec.reader_goal}.\n"
            f"VOICE: {spec.voice}. {spec.hint}\n"
            f"AT MOST {spec.max_sentences} sentences.\n"
            f"SUBJECT: {title or '(from the facts)'}\n\n"
            "FACTS — you may use only these. Do not add values, names, steps or "
            "hazards that are not listed:\n" + "\n".join(lines) + "\n\n"
            "Write continuous prose. No headings, no bullet lists, no tables."
        )

    @staticmethod
    def intents() -> dict[str, str]:
        return available()
