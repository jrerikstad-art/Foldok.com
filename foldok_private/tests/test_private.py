"""Tests for the private-call layer.

The leak tests are the contract. Everything else is convenience.

Run:  python -m pytest foldok_private/tests -q
"""

from __future__ import annotations

import pytest

from foldok_private import (
    OFFLINE,
    AuditLog,
    CallRefused,
    EchoTransport,
    EntityVault,
    ImageRef,
    LeakRefused,
    Policy,
    PrivateClient,
    detect,
    enterprise,
    populate,
    review,
)

FACTS = [
    {"key": "client_name", "value": "Equinor ASA"},
    {"key": "project_name", "value": "Johan Sverdrup"},
    {"key": "vendor", "value": "Aker Solutions AS"},
    {"key": "signed_by", "value": "Jan Rune Erikstad"},
]

TEXT = (
    "Equinor ASA confirmed that Aker Solutions AS delivered the unit for Johan Sverdrup. "
    "Contact jan.rune@example.no or +47 51 22 33 44. Signed by Jan Rune Erikstad."
)


def vault() -> EntityVault:
    v = EntityVault()
    populate(v, text=TEXT, facts=FACTS)
    return v


def client(**kw) -> PrivateClient:
    kw.setdefault("transport", EchoTransport())
    kw.setdefault("vault", EntityVault())
    kw.setdefault("model", "claude-sonnet-4-6")
    return PrivateClient(**kw)


# --- masking -------------------------------------------------------------
def test_real_values_do_not_survive_masking():
    m = vault().mask(TEXT)
    for secret in ("Equinor", "Aker Solutions", "Johan Sverdrup", "Jan Rune", "example.no"):
        assert secret not in m.text
    assert m.clean


def test_the_shape_of_the_sentence_survives():
    m = vault().mask(TEXT)
    assert "confirmed that" in m.text and "delivered the unit for" in m.text


def test_longer_names_are_masked_before_shorter_ones():
    v = EntityVault()
    v.add("Aker Solutions AS", "vendor")
    v.add("Aker", "client")
    m = v.mask("Aker Solutions AS reports to Aker.")
    assert "Solutions" not in m.text
    assert m.text.count("_") >= 2


def test_possessives_and_case_variants_are_caught():
    v = EntityVault()
    v.add("Equinor", "client")
    m = v.mask("equinor's cable and EQUINOR's drawing")
    assert "quinor" not in m.text.lower()


def test_aliases_map_to_the_same_token():
    v = EntityVault()
    e = v.add("Equinor ASA", "client", aliases=["Equinor", "EQNR"])
    m = v.mask("EQNR and Equinor ASA are the same company")
    assert m.text.count(e.token) == 2


def test_the_leak_guard_catches_a_real_value_in_outbound_text():
    """The last line of defence: whatever produced the text, re-scan it."""
    v = EntityVault()
    v.add("Equinor", "client")
    with pytest.raises(LeakRefused):
        v.assert_no_leak("Equinor signed it")
    v.assert_no_leak("CLIENT_A signed it")          # masked text passes


def test_a_masked_result_reports_leaks_when_not_running_strict():
    v = EntityVault()
    v.add("Equinor", "client")
    m = v.mask("Equinor signed it", strict=False)
    assert m.clean and "Equinor" not in m.text


def test_tokens_are_stable_across_sessions():
    a, b = vault(), vault()
    assert a.mask(TEXT).text == b.mask(TEXT).text


def test_the_vault_persists_and_reloads(tmp_path):
    v = vault()
    path = v.save(tmp_path / "vault.jsonl")
    again = EntityVault.load(path)
    assert len(again) == len(v)
    assert again.mask(TEXT).text == v.mask(TEXT).text


# --- unmasking -----------------------------------------------------------
def test_real_values_come_back_exactly():
    v = vault()
    m = v.mask(TEXT)
    u = v.unmask(m.text)
    assert "Equinor ASA" in u.text and "Jan Rune Erikstad" in u.text


def test_an_entity_the_model_invented_is_reported_not_passed_through():
    v = vault()
    u = v.unmask("CLIENT_A approved it, and so did CLIENT_Z.")
    assert "CLIENT_Z" in u.unknown_tokens
    assert not u.ok


def test_a_token_that_never_came_back_is_reported():
    v = vault()
    m = v.mask(TEXT)
    u = v.unmask("CLIENT_A only.", sent=[e.token for e in m.entities])
    assert u.missing_tokens


# --- detection -----------------------------------------------------------
def test_deterministic_patterns_find_the_obvious_identifiers():
    kinds = {c.kind for c in detect("jan@x.no +47 51223344 NO 923 609 016 https://x.no/a")}
    assert {"email", "phone", "org_no", "url"} <= kinds


def test_ambiguous_tags_are_offered_for_review_not_assumed():
    """Masking the word 'K3' out of ordinary prose makes the output worse for
    no privacy gain, so uncertain candidates need confirming."""
    assert any(c.kind == "tag" for c in review("Circuit K3 feeds the pump"))
    v = EntityVault()
    populate(v, text="Circuit K3 feeds the pump")
    assert "K3" in v.mask("Circuit K3 feeds the pump").text


def test_uncertain_detection_can_be_switched_on():
    v = EntityVault()
    populate(v, text="Circuit K3 feeds the pump", include_uncertain=True)
    assert "K3" not in v.mask("Circuit K3 feeds the pump").text


def test_facts_are_the_high_value_path():
    """No NER model needed: the fact base already knows who the client is."""
    v = EntityVault()
    populate(v, facts=FACTS)
    assert len(v) == 4
    assert all(e.source.startswith("fact:") for e in v.entities())


# --- the envelope --------------------------------------------------------
def test_the_preview_shows_what_leaves_and_nothing_secret():
    c = client()
    env = c.prepare("generate_section_prose", TEXT, facts=FACTS)
    panel = env.preview()
    assert "WHAT LEAVES THIS MACHINE" in panel
    assert "bytes" in panel
    for secret in ("Equinor", "Johan Sverdrup", "Jan Rune"):
        assert secret not in panel


def test_the_envelope_reports_byte_count_and_tokens():
    c = client()
    env = c.prepare("generate_section_prose", TEXT, facts=FACTS)
    assert env.bytes > 0
    assert env.tokens_used
    assert env.digest


# --- policy --------------------------------------------------------------
def test_images_are_blocked_by_default():
    c = client()
    env = c.prepare("index_file", "see photo", images=[ImageRef("nameplate.jpg", 240_000)])
    with pytest.raises(CallRefused) as exc:
        c.send(env)
    assert "cannot be masked" in str(exc.value)


def test_an_approved_image_may_be_sent():
    c = client(policy=Policy(allow_images=True))
    env = c.prepare("index_file", "see photo",
                    images=[ImageRef("nameplate.jpg", 1000, approved=True)])
    assert c.send(env).envelope.bytes > 1000


def test_a_byte_budget_is_enforced():
    c = client(policy=Policy(max_bytes=50))
    env = c.prepare("generate_section_prose", "x" * 500)
    with pytest.raises(CallRefused) as exc:
        c.send(env)
    assert "budget" in str(exc.value)


def test_only_the_four_engine_purposes_are_permitted():
    c = client()
    with pytest.raises(CallRefused) as exc:
        c.prepare("summarise_everything", "hello")
    assert "runs locally" in str(exc.value)


def test_offline_policy_sends_nothing():
    c = client(policy=OFFLINE)
    env = c.prepare("index_file", "hello")
    with pytest.raises(CallRefused):
        c.send(env)


def test_a_policy_can_require_human_approval_per_call():
    c = client(policy=Policy(require_preview=True))
    env = c.prepare("index_file", "hello")
    with pytest.raises(CallRefused):
        c.send(env)
    assert c.send(env, approved=True).ok


# --- the whole loop ------------------------------------------------------
def test_the_model_never_sees_a_real_identifier_but_the_caller_gets_one_back():
    seen: list[str] = []

    class Spy:
        id = "spy"

        def send(self, envelope):
            seen.append(envelope.text)
            return "CLIENT_A confirmed the delivery for PROJECT_A."

    c = PrivateClient(transport=Spy(), vault=EntityVault(), model="test")
    result = c.call("generate_section_prose", TEXT, facts=FACTS)

    assert "Equinor" not in seen[0] and "Johan Sverdrup" not in seen[0]
    assert "Equinor ASA" in result.text and "Johan Sverdrup" in result.text
    assert result.ok


def test_the_audit_log_records_the_call_and_none_of_the_content():
    c = client()
    c.call("generate_section_prose", TEXT, facts=FACTS)
    for record in c.audit.records():
        blob = str(record.to_dict())
        for secret in ("Equinor", "Johan", "Jan Rune", "confirmed"):
            assert secret not in blob
    assert c.audit.totals()["sent"] == 1


def test_a_refused_call_is_logged_as_refused():
    c = client(policy=Policy(max_bytes=10))
    with pytest.raises(CallRefused):
        c.call("index_file", "x" * 200)
    assert c.audit.totals()["refused"] == 1


def test_the_receipt_says_nothing_left_when_nothing_left():
    assert "Nothing left this machine" in client().receipt()


def test_the_receipt_counts_what_did_leave():
    c = client()
    c.call("index_file", TEXT, facts=FACTS)
    r = c.receipt()
    assert "1 call(s) left this machine" in r and "identifier(s) replaced" in r


# --- enterprise ----------------------------------------------------------
def test_bring_your_own_endpoint_is_a_transport_swap_and_nothing_else():
    """A company on its own Anthropic or Azure deployment changes one object.
    Same masking, same audit log, and Foldok is not in the data path."""
    class CustomerEndpoint:
        id = "equinor-azure"

        def send(self, envelope):
            return "CLIENT_A signed."

    c = enterprise(CustomerEndpoint(), vault=EntityVault(), model="customer")
    result = c.call("generate_section_prose", TEXT, facts=FACTS)
    assert result.text.startswith("Equinor ASA")
    assert c.summary()["transport"] == "equinor-azure"


def test_masking_still_applies_on_a_customers_own_endpoint():
    seen: list[str] = []

    class CustomerEndpoint:
        id = "byo"

        def send(self, envelope):
            seen.append(envelope.text)
            return envelope.text

    c = enterprise(CustomerEndpoint(), vault=EntityVault())
    c.call("index_file", TEXT, facts=FACTS)
    assert "Equinor" not in seen[0]


def test_summary_is_safe_to_show_an_it_department():
    c = client()
    c.call("index_file", TEXT, facts=FACTS)
    blob = str(c.summary())
    for secret in ("Equinor", "Johan", "Jan Rune"):
        assert secret not in blob
