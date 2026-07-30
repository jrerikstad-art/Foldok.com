"""Tests for the authoring engine.

The verifier tests are the contract: an invented instruction must not pass.

Run:  python -m pytest foldok_author/tests -q
"""

from __future__ import annotations

import pytest

from foldok_author import (
    AUTHORED_NOT_GENERATED,
    AuthoringEngine,
    Fact,
    IntentRefused,
    Plan,
    Procedure,
    Step,
    compose,
    verify,
)

DECL = [
    Fact("f1", "declarant", "Erikstad Elektro AS"),
    Fact("f2", "product", "Fordelingstavle -DB1"),
    Fact("f3", "serial_no", "DB1-2026-0114"),
    Fact("f4", "directive", "NEK 400:2022 og FEL §12"),
]
COMP = [
    Fact("c1", "name", "Pololu D24V50F5"),
    Fact("c2", "voltage_out", "5", "V", label="utgangsspenning"),
    Fact("c3", "current_max", "5", "A", label="maks strøm"),
]


def plan_for(facts, intent="describe_component"):
    return AuthoringEngine().plan(intent, facts)


# --- the verifier is the contract ---------------------------------------
def test_an_invented_instruction_does_not_pass_as_grounded():
    """The version this replaces marked all three of these grounded, because
    they contain no number and match no fact."""
    draft = ("Disconnect the battery before servicing the hydraulic manifold. "
             "Release the residual pressure by cycling the boom lever. "
             "Remove the counterweight before lifting.")
    result = verify(draft, plan_for(COMP), COMP)
    assert not result.grounded
    assert len(result.gaps) == 3
    assert all("procedure" in c.reason for c in result.claims)


def test_an_invented_number_is_caught():
    result = verify("The unit weighs 42 kg.", plan_for(COMP), COMP)
    assert not result.grounded and "matches no fact" in result.claims[0].reason


def test_an_invented_assertion_without_a_number_is_caught():
    result = verify("The converter is waterproof.", plan_for(COMP), COMP)
    assert not result.grounded


def test_connective_prose_is_unverifiable_not_grounded():
    """'Cannot be checked' and 'checked and fine' are different things, and
    collapsing them is how the first version passed a safety instruction."""
    result = verify("This section covers the following.", plan_for(COMP), COMP)
    assert result.claims[0].status == "unverifiable"
    assert not result.grounded


def test_a_grounded_sentence_passes():
    result = verify("Pololu D24V50F5 leverer 5 A.", plan_for(COMP), COMP)
    assert result.claims[0].status == "grounded"


def test_a_norwegian_date_does_not_split_a_sentence():
    """27.07.2026 was three sentences, so a correct record failed on its date."""
    facts = [Fact("d", "date", "27.07.2026"), Fact("w", "measured_by", "J. R. Erikstad")]
    result = verify("Målingen ble utført 27.07.2026 av J. R. Erikstad.", plan_for(facts), facts)
    assert len(result.claims) == 1 and result.grounded


# --- refusals name the reason -------------------------------------------
@pytest.mark.parametrize("intent", AUTHORED_NOT_GENERATED)
def test_procedural_intents_are_refused_by_name(intent):
    with pytest.raises(IntentRefused) as exc:
        AuthoringEngine().author(intent, COMP)
    assert "not generated from facts" in str(exc.value)


def test_the_refusal_says_what_to_do_instead():
    with pytest.raises(IntentRefused) as exc:
        AuthoringEngine().author("instruct_procedure", COMP)
    assert "Author the steps" in str(exc.value)


def test_an_unknown_intent_lists_what_exists():
    with pytest.raises(IntentRefused) as exc:
        AuthoringEngine().author("write_poem", COMP)
    assert "declare_conformity" in str(exc.value)


# --- deterministic composition ------------------------------------------
def test_a_declaration_reads_like_a_declaration():
    prose = compose("declare_conformity", DECL, lang="no")
    assert prose.startswith("Erikstad Elektro AS erklærer at")
    assert "DB1-2026-0114" in prose


def test_composition_is_reproducible():
    """Same facts, same sentence — a re-issued document must not churn."""
    assert compose("declare_conformity", DECL) == compose("declare_conformity", DECL)


def test_composition_cannot_invent_so_it_verifies_by_construction():
    engine = AuthoringEngine(lang="no")
    for intent, facts in (("declare_conformity", DECL), ("describe_component", COMP)):
        assert engine.author(intent, facts).publishable, intent


def test_parameters_intent_leaves_values_to_the_table():
    """The complaint was pages of tables. The answer is not prose that repeats
    the table."""
    prose = compose("specify_parameters", COMP, lang="no")
    # "5" alone appears inside the model name D24V50F5; what must not appear is
    # a value with its unit, which is the table's job.
    assert "5 A" not in prose and "5 V" not in prose
    assert "tabellen" in prose.lower()


def test_no_facts_produces_nothing_rather_than_filler():
    assert compose("describe_component", []) == ""


def test_a_model_is_only_called_where_phrasing_varies():
    calls: list[str] = []

    def fake(prompt: str) -> str:
        calls.append(prompt)
        return "Pololu D24V50F5 leverer 5 A."

    engine = AuthoringEngine(generate=fake, lang="no")
    engine.author("declare_conformity", DECL)
    assert calls == []                       # formulaic: composed, not generated
    engine.author("describe_component", COMP)
    assert len(calls) == 1


def test_the_prompt_carries_only_the_given_facts():
    prompt = AuthoringEngine().prompt("describe_component", COMP)
    assert "D24V50F5" in prompt
    assert "do not add values" in prompt.lower()


# --- procedures are authored --------------------------------------------
def test_a_procedure_renders_hazards_before_the_step_they_warn_about():
    proc = Procedure(
        title="Bytte hydraulikkfilter", author="J. R. Erikstad",
        tools=("13 mm fastnøkkel",), outcome="Filteret er byttet og systemet er tett.",
        steps=[Step("Koble fra batteriet.", hazard="Uventet bevegelse ved trykk i systemet."),
               Step("Løsne filterhuset med 13 mm fastnøkkel.", tools=("13 mm fastnøkkel",))],
    )
    out = proc.render(lang="no")
    assert out.index("ADVARSEL") < out.index("1. Koble fra batteriet")
    assert proc.issues() == []


def test_a_step_using_an_undeclared_tool_is_flagged():
    proc = Procedure(title="x", author="a", outcome="done",
                     steps=[Step("Løsne bolten.", tools=("momentnøkkel",))])
    assert any("not in the tools list" in i for i in proc.issues())


def test_a_procedure_with_no_outcome_is_flagged():
    proc = Procedure(title="x", author="a", steps=[Step("Gjør noe.")])
    assert any("expected result" in i for i in proc.issues())


def test_an_unsigned_procedure_is_not_evidence():
    proc = Procedure(title="x", outcome="done", steps=[Step("Gjør noe.")])
    assert any("nobody signed" in i for i in proc.issues())


def test_two_actions_in_one_step_are_flagged():
    proc = Procedure(title="x", author="a", outcome="done",
                     steps=[Step("Koble fra batteriet and then fjern dekselet.")])
    assert any("two actions" in i for i in proc.issues())
