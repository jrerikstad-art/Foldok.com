"""Chat language contract + hollow-document honesty."""
from __future__ import annotations

from local_app import editor_chat as ed


def test_resolve_chat_lang_prefers_ui_over_message():
    lang = ed.resolve_chat_lang(
        body={"lang": "en"},
        state={"lang": "no"},
        msg="Filer i mappen er klare for gjennomgang",
        detect_fn=lambda _m: "no",
    )
    assert lang == "en"


def test_hollow_and_language_complaints():
    assert ed.is_hollow_document_complaint("there is no information in the document")
    assert ed.is_language_mix_complaint("the agent is mixin language")
    assert ed.denies_project_context(
        "I don't have access to any document. You haven't shared a document."
    )
    assert ed.reply_violates_policy(
        "I don't have access to any document."
    )


def test_build_the_document_is_regenerate_ask():
    assert ed.is_regenerate_document_ask("build the document")
    assert ed.is_regenerate_document_ask("bygg dokumentet")
    assert ed.is_job_status_ask("are you working")
    assert ed.is_job_status_ask("Jobben kjører?")
    r = ed.format_job_status_reply(
        {"id": "abc123", "status": "running", "done": 2, "total": 8, "detail": "EMC"},
        lang="en",
        pending={"name": "Technical package"},
    )
    assert "running" in r.lower()
    assert "abc123" in r
    assert ed.denies_project_context("I don't have tools that let me do things outside this conversation")
