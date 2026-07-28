"""Tests for the signals package.

The guard tests are the contract: if analytics can leak, the product's whole
argument goes with it.

Run:  python -m pytest foldok_signals/tests -q
"""

from __future__ import annotations

import pytest

from foldok_signals import (
    Consent,
    Event,
    EventLog,
    Feedback,
    LocalSink,
    SignalRefused,
    Signals,
    failure_summary,
    funnel,
    vocabulary,
)


def sig(**kw) -> Signals:
    return Signals(**kw)


# --- content-free by construction ---------------------------------------
def test_an_unregistered_field_is_refused():
    """There is no field that would accept a file name, so one cannot end up
    in analytics by accident."""
    with pytest.raises(SignalRefused) as exc:
        Event(name="folder_opened", codes={"project_name": "Johan Sverdrup"})
    assert "not a registered code field" in str(exc.value)


def test_an_unregistered_value_is_refused():
    with pytest.raises(SignalRefused) as exc:
        Event(name="extraction_failed", codes={"file_type": "C:/jobs/equinor.pdf"})
    assert "not a permitted value" in str(exc.value)


def test_a_path_shaped_value_is_refused_even_if_the_field_exists():
    with pytest.raises(SignalRefused):
        Event(name="extraction_failed", codes={"reason": "/home/jan/secret.pdf"})


def test_an_unregistered_event_name_is_refused():
    with pytest.raises(SignalRefused) as exc:
        Event(name="user_typed_something")
    assert "not a registered event" in str(exc.value)


def test_counters_must_be_numbers():
    with pytest.raises(SignalRefused) as exc:
        Event(name="folder_opened", counters={"files": "many"})
    assert "must be a number" in str(exc.value)


def test_no_recorded_event_ever_contains_a_free_string():
    s = sig()
    s.folder_opened(files=3)
    s.index_finished(files=3, chunks=40, seconds=1.0, failed=1)
    s.extraction_failed(file_type="pdf", reason="no_text")
    for event in s.log.events():
        for value in event.codes.values():
            assert " " not in value and "/" not in value and "\\" not in value


def test_the_vocabulary_is_publishable():
    """This is what the consent screen shows — the whole list, not a summary."""
    v = vocabulary()
    assert "file names" in v["never_collected"]
    assert "project names" in v["never_collected"]
    assert len(v["events"]) <= 12       # ten-ish on purpose


# --- consent -------------------------------------------------------------
def test_nothing_is_sent_without_consent():
    sink = LocalSink()
    s = sig(sink=sink)
    s.folder_opened(files=1)
    assert s.flush() == 0
    assert sink.sent == []


def test_consent_enables_sending():
    sink = LocalSink()
    s = sig(sink=sink)
    s.grant()
    s.folder_opened(files=1)
    assert s.flush() >= 1
    assert sink.sent


def test_events_are_recorded_locally_even_without_consent():
    """The log is how the product diagnoses itself and how a bug report has a
    trail. Consent governs sending, not recording."""
    s = sig()
    s.folder_opened(files=1)
    assert len(s.log) == 1


def test_revoking_consent_purges_what_was_collected():
    s = sig()
    s.grant()
    s.folder_opened(files=1)
    s.gaps_shown(total=3)
    assert s.revoke() >= 2
    assert len(s.log) == 0
    assert s.consent.install_id == ""        # the pseudonym goes too
    assert s.flush() == 0


def test_the_consent_prompt_lists_everything():
    prompt = Consent.prompt()
    assert "never file names" in prompt.lower()
    assert "turning it off deletes" in prompt


def test_the_install_id_is_random_not_derived():
    a, b = Consent().grant(), Consent().grant()
    assert a.install_id != b.install_id and len(a.install_id) == 16


def test_the_log_persists_and_reloads(tmp_path):
    path = tmp_path / "events.jsonl"
    s = sig(log=path)
    s.folder_opened(files=2)
    again = EventLog(path)
    assert len(again) == 1 and again.events()[0].name == "folder_opened"


# --- the funnel ----------------------------------------------------------
def test_the_funnel_shows_where_people_stop():
    s = sig()
    s.folder_opened(files=10)
    s.index_finished(files=10, chunks=90, seconds=2.0)
    s.gaps_shown(total=12)
    f = funnel(s.log.events())
    assert f.stages["gaps_shown"] == 1
    assert f.stages["document_exported"] == 0
    assert f.worst_step[0] == "gap_resolved"


def test_reaching_a_late_stage_implies_the_earlier_ones():
    s = sig()
    s.document_exported(pages=4)
    f = funnel(s.log.events())
    assert all(f.stages[stage] == 1 for stage in f.stages)


def test_sessions_are_counted_separately():
    a, b = sig(), sig()
    a.folder_opened(files=1)
    b.folder_opened(files=1)
    assert funnel(a.log.events() + b.log.events()).sessions == 2


# --- refusals are feedback ----------------------------------------------
class CallRefused(Exception):
    pass


class PackRefused(Exception):
    pass


class LayoutRefused(Exception):
    pass


def test_a_refusal_becomes_a_counter():
    s = sig()
    s.on_refusal(CallRefused("42,000 bytes exceeds the 12,000 byte budget"))
    assert s.log.counts()["call_refused"] == 1
    assert s.log.events()[0].codes["reason"] == "over_budget"


def test_the_refusal_message_itself_is_never_recorded():
    """Refusal messages quote the user's content on purpose — that is what makes
    them good UX and unfit for analytics."""
    s = sig()
    s.on_refusal(CallRefused("cannot seal pack for Equinor Johan Sverdrup: redistribution"))
    blob = str([e.to_dict() for e in s.log.events()])
    assert "Equinor" not in blob and "Johan" not in blob


def test_each_engine_refusal_maps_to_its_own_reason():
    s = sig()
    s.on_refusal(PackRefused("may not be redistributed"))
    s.on_refusal(LayoutRefused("is a locked block"))
    reasons = {e.codes.get("reason") for e in s.log.events()}
    assert {"redistribution", "locked_block"} <= reasons


def test_an_unknown_exception_is_ignored_rather_than_guessed_at():
    s = sig()
    assert s.on_refusal(ValueError("something else entirely")) is None
    assert len(s.log) == 0


def test_blocked_me_is_one_tap():
    s = sig()
    s.blocked_me(reason="no_resolver", surface="gaps")
    assert s.log.counts()["blocked_me"] == 1


def test_failures_group_by_reason_for_a_solo_founder_to_act_on():
    s = sig()
    s.extraction_failed(file_type="pdf", reason="no_text")
    s.extraction_failed(file_type="pdf", reason="no_text")
    s.extraction_failed(file_type="docx", reason="corrupt")
    summary = failure_summary(s.log.events())
    assert summary["extraction_failed"]["no_text"] == 2


# --- feedback ------------------------------------------------------------
def test_feedback_does_not_need_telemetry_consent():
    """The user typed it and pressed send. Requiring analytics consent to report
    a bug would be the wrong trade in both directions."""
    s = sig()
    fb = s.feedback("bug", "The gap list is empty after indexing")
    assert s.send_feedback(fb, approved=True)


def test_feedback_must_be_previewed_before_it_sends():
    s = sig()
    fb = s.feedback("bug", "something broke")
    with pytest.raises(SignalRefused) as exc:
        s.send_feedback(fb)
    assert "preview" in str(exc.value)


def test_an_empty_report_is_refused():
    s = sig()
    with pytest.raises(SignalRefused):
        s.send_feedback(s.feedback("bug", "   "), approved=True)


def test_the_attached_history_is_content_free_and_shown():
    s = sig()
    s.folder_opened(files=5)
    s.extraction_failed(file_type="pdf", reason="no_text")
    fb = s.feedback("bug", "indexing missed my drawings")
    panel = fb.preview()
    assert "WHAT THIS REPORT SENDS" in panel
    assert "extraction_failed" in panel
    for row in fb.context:
        assert "session" not in row


def test_contact_is_optional_and_the_panel_says_so():
    s = sig()
    assert "cannot reply" in s.feedback("idea", "add DWG support").preview()
    assert s.feedback("idea", "x", contact="jan@example.no").has_contact


# --- bug reports ---------------------------------------------------------
def test_a_bug_report_cannot_attach_the_vault(tmp_path):
    s = sig()
    vault = tmp_path / "job.vault"
    vault.write_text("secret", encoding="utf-8")
    report = tmp_path / "render.log"
    report.write_text("log", encoding="utf-8")
    with pytest.raises(Exception) as exc:
        s.bug_report("crash on export", files=[report, vault])
    assert "vault" in str(exc.value).lower() or "machine" in str(exc.value).lower()


def test_a_bug_report_with_safe_attachments_is_built():
    s = sig()
    fb, files = s.bug_report("crash on export", contact="jan@example.no")
    assert fb.kind == "bug" and fb.has_contact and files == []


# --- the activity panel --------------------------------------------------
def test_the_activity_panel_is_safe_to_show_anyone():
    s = sig()
    s.folder_opened(files=9)
    s.on_refusal(CallRefused("images blocked"))
    panel = s.activity()
    assert panel["consent"]["granted"] is False
    assert panel["funnel"]["folder_opened"] == 1
    assert "never_collected" in panel["vocabulary"]
    blob = str(panel)
    assert "Equinor" not in blob


def test_the_report_reads_like_something_you_would_act_on():
    s = sig()
    s.folder_opened(files=9)
    s.index_finished(files=9, chunks=80, seconds=3.0, failed=1)
    text = s.report()
    assert "Biggest drop" in text
    assert "Telemetry: off" in text
