"""Document-scoped editor chat — Temabrief ≠ Installasjonsmanual transcript."""
from __future__ import annotations

from local_app.editor_chat import (
    append_turn,
    conversation_for_document,
    get_chat_pending,
    set_chat_pending,
)


def test_turns_do_not_cross_documents():
    state = {"conversation": [], "project_id": "p1", "chat_pendings": {}}
    append_turn(state, "user", "regen temabrief", project_id="p1", template="topic_brief.json")
    append_turn(state, "bot", "starter temabrief", project_id="p1", template="topic_brief.json")
    append_turn(state, "user", "ja", project_id="p1", template="installation_manual.json")
    append_turn(
        state, "bot", "Installasjonsmanual venter", project_id="p1",
        template="installation_manual.json",
    )

    tb = conversation_for_document(state, "p1", "topic_brief.json")
    im = conversation_for_document(state, "p1", "installation_manual.json")
    assert len(tb) == 2
    assert all("temabrief" in (t.get("text") or "").lower() or t["role"] == "bot" for t in tb)
    assert "Installasjonsmanual" not in " ".join(t.get("text") or "" for t in tb)
    assert len(im) == 2
    assert "Installasjonsmanual" in (im[1].get("text") or "")


def test_pending_isolated_per_document():
    state = {"chat_pendings": {}, "chat_pending": None}
    set_chat_pending(
        state, "installation_manual.json",
        {"action": "run_generate", "template_key": "installation_manual"},
    )
    assert get_chat_pending(state, "topic_brief.json") is None
    pend = get_chat_pending(state, "installation_manual.json")
    assert pend and pend.get("action") == "run_generate"

    set_chat_pending(state, "topic_brief.json", {"action": "run_generate", "template": "topic_brief.json"})
    assert get_chat_pending(state, "installation_manual.json")["action"] == "run_generate"
    assert get_chat_pending(state, "topic_brief.json")["action"] == "run_generate"

    set_chat_pending(state, "topic_brief.json", None)
    assert get_chat_pending(state, "topic_brief.json") is None
    assert get_chat_pending(state, "installation_manual.json") is not None


def test_legacy_unscoped_pending_hidden_from_doc_chat():
    state = {
        "chat_pending": {"action": "run_generate", "template_key": "installation_manual"},
        "chat_pendings": {},
    }
    assert get_chat_pending(state, "topic_brief.json") is None
