"""Regression: question-driven ask — prose understanding, not claim tables."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "local_app"))

from foldok_ask import ask, compose_topic_brief, retrieve, synthesize_scope  # noqa: E402


def _emc_index(n_files: int = 54):
    base = [
        {
            "file": "Documents/Chalfant 78411.pdf",
            "caption": "Chalfant EMI/RFI shielded cable tray. Premium Ultra RF. MIL STD 285 attenuation.",
            "content_tags": ["emc", "cable_tray", "shielding"],
            "facts": [
                {"id": "a1", "key": "h_field_attenuation_premium", "value": "70 to 83", "unit": "dB"},
                {"id": "a2", "key": "test_standard", "value": "MIL STD 285"},
            ],
        },
        {
            "file": "Documents/Amucor-faraday-cage-leaflet.pdf",
            "caption": "Amucor Faraday cage leaflet EMI foil TEMPEST rooms 110 dB attenuation.",
            "content_tags": ["emc", "faraday", "shielding"],
            "facts": [
                {"id": "b1", "key": "attenuation_e_field", "value": "110", "unit": "dB"},
                {"id": "b2", "key": "first_order_filter_attenuation_rate",
                 "value": "6 dB/octave or 20 dB/decade"},
            ],
        },
        {
            "file": "Documents/BEAMA-cable-tray-guide.pdf",
            "caption": "BEAMA best practice cable ladder tray. Cable classes 1-6 segregation rules.",
            "content_tags": ["cable_tray", "cable_class", "separation"],
            "facts": [
                {"id": "c1", "key": "cable_class", "value": "Class 4 power circuits"},
                {"id": "c2", "key": "cable_class_signal", "value": "Class 2 signal cables"},
                {"id": "c3", "key": "separation_between_classes", "value": "segregate power and signal classes"},
            ],
        },
        {
            "file": "Documents/Wibe Cable Trays For Demanding Application.pdf",
            "caption": "Wibe cable trays installation guide for demanding applications.",
            "content_tags": ["cable_tray", "installation"],
            "facts": [
                {"id": "w1", "key": "installation_distance_tray_ceiling", "value": "300", "unit": "mm"},
                {"id": "w2", "key": "installation_distance_wall", "value": "50", "unit": "mm"},
            ],
        },
    ]
    # Pad to n_files for omfang test
    out = list(base)
    i = 0
    while len(out) < n_files:
        i += 1
        out.append({
            "file": f"Documents/extra_{i:02d}.pdf",
            "caption": f"Technical note {i} on electromagnetic compatibility and cable management.",
            "content_tags": ["emc", "cable_management"],
            "facts": [],
        })
    return out


def test_kabelklasser_does_not_lead_with_ceiling_distance():
    idx = _emc_index(10)
    hits = retrieve("Kabelklasser og avstandskrav", idx, k=8)
    assert hits, "expected some hits for cable classes"
    top = hits[0].text.lower() + " " + hits[0].file_id.lower()
    assert "ceiling" not in top and "tray ceiling" not in top
    assert "installation_distance_tray_ceiling" not in top
    # Should prefer class/segregation language or BEAMA
    blob = " ".join(h.text.lower() + h.file_id.lower() for h in hits[:3])
    assert "class" in blob or "beama" in blob or "segregat" in blob

    ans = ask(idx, "Kabelklasser og avstandskrav", lang="no")
    md = ans.markdown(lang="no").lower()
    assert "248" not in md
    # Must not lead with ceiling clearance table row
    first = (ans.prose or "").lower()[:200]
    assert "ceiling" not in first
    assert "300 mm" not in first or "class" in first
    assert not (ans.prose or "").lower().startswith("tabellen under")


def test_omfang_two_sentences_when_files_exist():
    idx = _emc_index(54)
    ans = synthesize_scope(idx, artifact={"name": "EMC"}, lang="no")
    assert ans.grounded
    assert "MANGLER" not in ans.prose
    assert "54" in ans.prose
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", ans.prose.strip()) if s.strip()]
    assert 2 <= len(sentences) <= 3

    # ask() route for omfang question
    ans2 = ask(idx, "Hva handler dette korpuset om?", lang="no", artifact={"name": "EMC"})
    assert ans2.grounded
    assert "MANGLER" not in ans2.prose
    assert "54" in ans2.prose


def test_topic_brief_overview_never_mangler_with_index():
    parts = compose_topic_brief(_emc_index(54), artifact={"name": "EMC"}, lang="no")
    assert "MANGLER" not in parts["overview"]
    assert "54" in parts["overview"]


def test_ask_empty_hits_is_gap_not_essay():
    ans = ask(_emc_index(5), "sveisemetode WPS for aluminium trykktanker", lang="no")
    assert not ans.grounded
    assert ans.gaps
    assert len(ans.prose) < 80


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
    print("ALL PASS")
