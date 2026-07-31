"""Tests for the operator console.

Two things matter: the release checks catch what was previously caught by hand,
and no probe can take the console down. A dashboard that crashes is a dashboard
nobody opens, and that is how two blockers survived five builds.

Run:  python -m pytest foldok_console/tests -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from foldok_console import Console, Finding, Panel, check_release, merge, probe_engines


def site(tmp_path: Path, html: str, *, extra: dict[str, str] | None = None) -> Path:
    root = tmp_path / "build"
    (root / "public").mkdir(parents=True)
    (root / "public" / "index.html").write_text(html, encoding="utf-8")
    (root / "vercel.json").write_text('{"outputDirectory": "public"}', encoding="utf-8")
    (root / "VERSION").write_text("1.0.0", encoding="utf-8")
    for name, body in (extra or {}).items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return root


# --- release checks ------------------------------------------------------
def test_a_link_to_a_file_that_does_not_ship_is_a_blocker(tmp_path):
    """The exact bug that survived 0.73 to 0.78: a button opening a 404 tab."""
    root = site(tmp_path, '<button onclick=\'window.open("/diagram.html")\'>x</button>')
    panel = check_release(root)
    dead = [f for f in panel.findings if f.code == "dead_link"]
    assert dead and dead[0].health == "fail"
    assert "/diagram.html" in dead[0].detail


def test_a_link_to_a_file_that_does_ship_is_fine(tmp_path):
    root = site(tmp_path, '<a href="/about.html">x</a>', extra={"public/about.html": "<p>hi"})
    assert [f for f in check_release(root).findings if f.code == "dead_link"] == []


def test_api_calls_are_not_treated_as_dead_links(tmp_path):
    """They have a marketing-mode fallback; flagging them would be noise."""
    root = site(tmp_path, '<script>fetch("/api/account/usage")</script>')
    assert [f for f in check_release(root).findings if f.code == "dead_link"] == []


def test_a_clickable_localhost_link_is_a_blocker(tmp_path):
    root = site(tmp_path, '<a href="http://127.0.0.1:8766/">run it</a>')
    hit = [f for f in check_release(root).findings if f.code == "localhost_on_production"]
    assert hit and hit[0].health == "fail"


def test_localhost_as_plain_text_only_warns(tmp_path):
    root = site(tmp_path, "<code>http://127.0.0.1:8766/</code>")
    hit = [f for f in check_release(root).findings if f.code == "localhost_on_production"]
    assert hit and hit[0].health == "warn"


def test_a_shareable_page_without_an_og_image_is_flagged(tmp_path):
    root = site(tmp_path, '<meta property="og:title" content="Foldok"/>')
    assert [f for f in check_release(root).findings if f.code == "no_og_image"]


def test_a_page_that_is_not_shareable_is_not_nagged(tmp_path):
    root = site(tmp_path, "<p>plain page</p>")
    assert [f for f in check_release(root).findings if f.code == "no_og_image"] == []


def test_a_js_heavy_page_reports_how_little_a_crawler_sees(tmp_path):
    body = "<script>" + ("x" * 400_000) + "</script><p>hi</p>"
    root = site(tmp_path, body)
    hit = [f for f in check_release(root).findings if f.code == "js_heavy_page"]
    assert hit and "markup" in hit[0].detail


def test_a_key_in_the_repo_is_the_highest_impact_finding(tmp_path):
    root = site(tmp_path, "<p>ok</p>",
                extra={"config.py": 'KEY = "sk-ant-' + "a" * 40 + '"'})
    hit = [f for f in check_release(root).findings if f.code == "secret_in_repo"]
    assert hit and hit[0].impact == 5
    assert "rotate" in hit[0].action


def test_an_example_file_is_not_treated_as_a_leak(tmp_path):
    root = site(tmp_path, "<p>ok</p>",
                extra={".env.example": "ANTHROPIC_API_KEY=sk-ant-your-key-here"})
    assert [f for f in check_release(root).findings if f.code == "secret_in_repo"] == []


def test_disagreeing_version_strings_are_caught(tmp_path):
    root = site(tmp_path, "<p>ok</p>",
                extra={"public/VERSION": "1.0.0", "site-meta.json": '{"version": "0.9.0"}'})
    hit = [f for f in check_release(root).findings if f.code == "version_mismatch"]
    assert hit and "0.9.0" in hit[0].detail


def test_a_missing_output_directory_fails_loudly(tmp_path):
    root = tmp_path / "b"
    root.mkdir()
    (root / "vercel.json").write_text('{"outputDirectory": "nope"}', encoding="utf-8")
    assert check_release(root).health == "fail"


# --- probes are unkillable ----------------------------------------------
def test_a_missing_engine_is_reported_not_raised(tmp_path):
    panel = probe_engines(tmp_path)
    assert panel.health in ("warn", "fail")
    assert [f for f in panel.findings if f.code == "engine_missing"]


def test_every_probe_survives_an_empty_directory(tmp_path):
    snap = Console(tmp_path).snapshot()
    assert snap.panels
    assert isinstance(snap.report(), str)


def test_the_console_runs_against_a_real_build(tmp_path):
    root = site(tmp_path, '<meta property="og:title" content="x"/>')
    snap = Console(root).snapshot()
    assert snap.version == "1.0.0"
    assert snap.panel("release") is not None


# --- decisions, not metrics ---------------------------------------------
def test_quick_high_impact_work_ranks_above_slow_low_impact_work():
    panel = Panel(area="a", title="A")
    panel.add("slow", "big rewrite", health="warn", impact=4, effort="days")
    panel.add("quick", "one-line fix", health="fail", impact=4, effort="minutes")
    order = [f.code for f in merge([panel]).decisions()]
    assert order[0] == "quick"


def test_healthy_findings_never_enter_the_queue():
    panel = Panel(area="a", title="A")
    panel.add("fine", "all good", health="ok", impact=5, effort="minutes")
    assert merge([panel]).decisions() == []


def test_an_empty_queue_says_something_useful():
    assert "talk to a customer" in merge([Panel(area="a", title="A")]).report()


def test_overall_health_is_the_worst_panel():
    a, b = Panel(area="a", title="A"), Panel(area="b", title="B")
    a.add("x", "x", health="ok")
    b.add("y", "y", health="fail")
    assert merge([a, b]).health == "fail"


def test_a_panel_with_no_findings_settles_to_ok():
    assert merge([Panel(area="a", title="A")]).panels[0].health == "ok"


# --- the ship gate -------------------------------------------------------
def test_the_gate_blocks_on_any_failure(tmp_path):
    root = site(tmp_path, '<button onclick=\'window.open("/gone.html")\'>x</button>')
    ok, blockers = Console(root).gate(with_tests=False)
    assert not ok and any("dead link" in b.lower() or "do not ship" in b for b in blockers)


def test_the_gate_passes_a_clean_build(tmp_path):
    root = site(tmp_path, "<p>a plain, honest page</p>")
    ok, blockers = Console(root).gate(with_tests=False)
    assert ok, blockers


# --- output --------------------------------------------------------------
def test_json_output_is_machine_readable(tmp_path):
    root = site(tmp_path, "<p>ok</p>")
    data = json.loads(Console(root).json())
    assert data["schema_version"] == 1
    assert "panels" in data and "decisions" in data


def test_the_report_leads_with_health_and_ends_with_actions(tmp_path):
    root = site(tmp_path, '<a href="http://localhost:8766/">x</a>')
    text = Console(root).report()
    assert text.startswith("FOLDOK CONSOLE")
    assert "WORTH YOUR TUESDAY" in text


def test_no_usage_data_is_itself_the_finding(tmp_path):
    root = site(tmp_path, "<p>ok</p>")
    snap = Console(root).snapshot()
    usage = snap.panel("signals")
    assert usage and [f for f in usage.findings if f.code == "no_usage_data"]
    assert any("drive to" in f.action for f in usage.findings)
