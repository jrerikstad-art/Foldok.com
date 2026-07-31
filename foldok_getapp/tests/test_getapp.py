"""Tests for the "get the Capture app" control.

Run:  python -m pytest foldok_getapp/tests -q
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from foldok_getapp import Copy, QRStyle, landing_note, module_count, qr_svg, widget
from foldok_getapp.__main__ import main

URL = "https://foldok.com/capture"


# --- the QR --------------------------------------------------------------
def test_the_svg_makes_no_external_request():
    """A hosted QR image would be a third-party request on every page view, with
    the referrer attached — on this site of all sites."""
    svg = qr_svg(URL)
    for token in ("href=", "src=", "url(", "@import", "<image"):
        assert token not in svg


def test_the_svg_is_self_contained_and_inline():
    svg = qr_svg(URL)
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert "xmlns=" in svg and "viewBox=" in svg


def test_generation_is_deterministic():
    assert qr_svg(URL) == qr_svg(URL)


def test_a_quiet_zone_is_included():
    """Without margin, a code printed against dark furniture will not scan."""
    style = QRStyle(quiet_zone=3)
    svg = qr_svg(URL, style)
    span = int(re.search(r'viewBox="0 0 (\d+)', svg).group(1))
    assert span == module_count(URL) + 6


def test_horizontal_runs_are_merged_into_fewer_nodes():
    svg = qr_svg(URL)
    modules = module_count(URL)
    assert svg.count("<rect") < modules * modules / 3


def test_a_literal_colour_is_used_not_a_css_variable():
    """`fill="var(--ink)"` is unreliable in older Safari, and a QR with no fill
    is a blank square that silently does not scan."""
    svg = qr_svg(URL)
    assert "var(" not in svg
    assert re.search(r'fill="#[0-9A-Fa-f]{6}"', svg)


def test_a_transparent_background_is_the_default():
    assert "<rect width=" not in qr_svg(URL).split("<g")[0]
    assert "<rect width=" in qr_svg(URL, QRStyle(light="#FFFFFF")).split("<g")[0]


def test_a_longer_url_needs_a_bigger_code():
    assert module_count(URL + "/" + "x" * 120) > module_count(URL)


def test_the_code_carries_an_accessible_label():
    svg = qr_svg(URL, title="Foldok Capture")
    assert 'role="img"' in svg and "Foldok Capture" in svg


# --- the widget ----------------------------------------------------------
def test_it_renders_a_button_and_a_popover():
    html = widget(URL)
    assert 'class="gc-btn"' in html and 'class="gc-pop"' in html
    assert 'aria-haspopup="dialog"' in html and 'aria-expanded="false"' in html


def test_a_phone_is_never_shown_a_qr_code():
    """You are already holding the device the code points at."""
    html = widget(URL)
    assert "Android" in html and "iPhone" in html
    assert '.gc-desktop").hidden = true' in html


def test_android_gets_a_direct_install_and_ios_gets_the_truth():
    html = widget(URL, android_url="https://foldok.com/capture.apk")
    assert "capture.apk" in html
    assert "iOS coming" in html or "iOS kommer" in html


def test_both_languages_are_present_like_the_rest_of_the_site():
    html = widget(URL)
    assert 'data-i18n-no="Kamera-app"' in html
    assert 'data-i18n-en="Capture app"' in html


def test_copy_can_be_overridden():
    html = widget(URL, copy={"button": Copy("Kamera", "Camera")})
    assert 'data-i18n-en="Camera"' in html


def test_the_styles_are_scoped_so_it_cannot_leak_into_the_page():
    html = widget(URL, element_id="grabApp")
    css = html.split("<style>")[1].split("</style>")[0]
    # drop at-rule headers and keyframe stops; what is left must all be scoped
    selectors = [
        s.strip() for s in re.findall(r"([^{}]+)\{", css)
        if s.strip() and not s.strip().startswith("@")
        and s.strip() not in ("from", "to")
    ]
    unscoped = [s for s in selectors if "#grabApp" not in s]
    assert not unscoped, unscoped


def test_it_uses_the_sites_own_tokens_with_fallbacks():
    html = widget(URL)
    assert "var(--signal, #F2B705)" in html and "var(--line, #DAD7CC)" in html


def test_the_whole_block_makes_no_external_request():
    html = widget(URL)
    body = html.split("<style>")[0]
    assert "<script src" not in html
    assert 'href="https://foldok.com/capture"' in body        # the one intended link
    assert "cdn" not in html.lower()


def test_it_can_be_removed_as_one_block():
    html = widget(URL)
    assert html.startswith("<!-- Foldok :: get the Capture app")
    assert html.rstrip().endswith("<!-- /Foldok :: get the Capture app -->")


def test_it_closes_on_escape_and_on_a_click_outside():
    html = widget(URL)
    assert 'e.key === "Escape"' in html
    assert "!root.contains(e.target)" in html


def test_two_widgets_on_one_page_do_not_collide():
    a, b = widget(URL, element_id="one"), widget(URL, element_id="two")
    assert "#one" in a and "#one" not in b


# --- the CLI -------------------------------------------------------------
def test_the_cli_writes_a_snippet(tmp_path, capsys):
    out = tmp_path / "snippet.html"
    assert main(["--url", URL, "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("<!-- Foldok")
    assert "QR" in capsys.readouterr().out


def test_a_url_too_long_to_scan_comfortably_warns(tmp_path, capsys):
    main(["--url", "https://foldok.com/" + "x" * 200, "--out", str(tmp_path / "s.html")])
    assert "awkward to scan" in capsys.readouterr().err


def test_the_landing_note_says_why_the_qr_points_at_a_page():
    note = landing_note(URL)
    assert "distribution" in note and "keeps working" in note
