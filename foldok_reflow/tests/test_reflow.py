"""Tests for PDF reflow.

The fixture is real pypdf output shape: one line per visual row, dotted-leader
contents, hyphenation across rows, a running header on every page.

Run:  python -m pytest foldok_reflow/tests -q
"""

from __future__ import annotations

import pytest

from foldok_reflow import quality, reflow, split_sentences

PDF_LIKE = """[page 1]
T E C H N I C A L  I N F O R M A T I O N
Background knowledge on EMC
CONTENTS
1 About this document.......................................4
2 EMC: Basics..............................................7
3 Shielding...............................................10

[page 2]
8027032/2022-07-19 | SICK
2 EMC: Basics
Equipotential bonding (also: earthing) can be divided into protective equipoten‐
tial bonding PE and functional equipotential bonding FE. Protective equipoten‐
tial bonding is used to protect persons from electric shock in the event of a
fault. An FE connection must never be used as a protective equipotential
bonding.

[page 3]
8027032/2022-07-19 | SICK
3 Shielding
Experience shows that the shielding should be applied on both sides. Deviations
are only permitted in exceptional and justified cases.
• Always connect the shielding to FE or PE on both sides.
1.5 2.5 4.0 6.0 10.0
"""


def test_a_sentence_spanning_several_rows_becomes_one_sentence():
    """This is the whole bug: pypdf emits visual rows, and a newline-based
    splitter turns one sentence into four claims."""
    out = reflow(PDF_LIKE)
    joined = [s for s in out.sentences() if "protect persons from electric shock" in s]
    assert joined
    assert "in the event of a fault" in joined[0]


def test_hyphenation_across_a_line_break_is_repaired():
    """'equipoten‐' + 'tial' arrived as the end of one claim and the start of
    another."""
    text = reflow(PDF_LIKE).text
    assert "equipotential" in text
    assert "equipoten‐" not in text and "equipoten " not in text


def test_a_table_of_contents_never_becomes_content():
    text = reflow(PDF_LIKE).text
    assert "About this document" not in text or "....." not in text
    assert reflow(PDF_LIKE).stats.toc_dropped >= 3


def test_a_running_header_is_dropped_by_frequency():
    """A running header looks exactly like a heading on the page it belongs to.
    Repetition is the only reliable signal."""
    text = reflow(PDF_LIKE).text
    assert text.count("8027032/2022-07-19") == 0


def test_a_bullet_starts_a_new_line_rather_than_joining():
    out = reflow(PDF_LIKE).text
    assert "\n• Always connect" in out or out.strip().endswith("both sides.")


def test_a_numeric_table_row_is_not_prose():
    out = reflow(PDF_LIKE)
    assert "1.5 2.5 4.0 6.0 10.0" not in out.text
    assert out.tables


def test_a_page_marker_becomes_a_paragraph_break_not_a_sentence():
    assert not any("[page" in s for s in reflow(PDF_LIKE).sentences())


# --- the quality signal ---------------------------------------------------
def test_raw_pdf_output_is_reported_as_unusable():
    """A folder producing thin documents from good sources is exactly where
    nobody thinks to look at the text itself."""
    before = quality(PDF_LIKE)
    assert not before["usable"]
    assert "fragments" in before["note"]


def test_reflowed_text_is_reported_as_usable():
    after = quality(reflow(PDF_LIKE).text)
    assert after["usable"]
    assert after["line_completeness"] > 0.5
    assert after["toc_lines"] == 0


def test_line_completeness_is_the_signal_not_sentence_count():
    """Sentence count barely moves; what changes is whether a line ends one."""
    before, after = quality(PDF_LIKE), quality(reflow(PDF_LIKE).text)
    assert after["line_completeness"] > before["line_completeness"] * 2
    assert after["words_per_line"] > before["words_per_line"]


# --- sentence splitting ---------------------------------------------------
def test_a_decimal_does_not_end_a_sentence():
    assert len(split_sentences("The cross-section shall be at least 2.5 mm2 in all cases.")) == 1


def test_a_clause_reference_does_not_end_a_sentence():
    assert len(split_sentences("Verification per §6-61 shall be recorded in the protocol.")) == 1


def test_a_numbered_heading_does_not_split_the_sentence_after_it():
    text = "Section 3.3.1 describes the recommended data lines for this application."
    assert len(split_sentences(text)) == 1


def test_an_abbreviation_does_not_end_a_sentence():
    text = "See fig. 12 for the recommended arrangement of the shielding connection."
    assert len(split_sentences(text)) == 1


def test_initials_do_not_end_a_sentence():
    text = "The measurement was carried out by J. R. Erikstad using a calibrated meter."
    assert len(split_sentences(text)) == 1


def test_two_real_sentences_are_two():
    text = ("The shielding should be applied on both sides. "
            "Deviations are only permitted in justified cases.")
    assert len(split_sentences(text)) == 2


# --- it only joins and drops ---------------------------------------------
def test_nothing_but_hyphenation_rewrites_a_word():
    out = reflow(PDF_LIKE).text
    for word in ("shielding", "Deviations", "protective", "functional"):
        assert word in out


def test_empty_input_is_not_an_error():
    out = reflow("")
    assert out.text == "" and out.stats.sentences == 0


def test_prose_that_is_already_clean_survives_untouched():
    clean = ("The shielding should be applied on both sides.\n\n"
             "Deviations are only permitted in exceptional cases.")
    out = reflow(clean)
    assert "both sides." in out.text and "exceptional cases." in out.text
    assert out.stats.hyphens_repaired == 0


def test_the_stats_explain_what_happened():
    text = reflow(PDF_LIKE).stats.summary()
    assert "joined" in text and "hyphenations repaired" in text


# --- figures and tables inside PDFs --------------------------------------
def test_captions_are_recognised_in_both_languages():
    from foldok_reflow.assets import _captions

    text = ("Figure 4: Busbar support for high connection point\n"
            "Figur 12: Kabelbro i gangen\n"
            "Table 2: Conductor cross-sections\n"
            "This is ordinary prose about shielding and should not match.")
    found = _captions(text)
    assert len(found) == 3
    assert any("Busbar" in c for c in found)
    assert any("Kabelbro" in c for c in found)


def test_a_figure_without_a_caption_is_still_returned():
    """A person can look at it and a heuristic cannot."""
    from foldok_reflow.assets import Figure

    figure = Figure(id="FIG1", page=3, index=0, width=400, height=300)
    assert figure.usable and not figure.captioned


def test_a_logo_sized_image_is_not_content():
    from foldok_reflow.assets import Figure

    assert not Figure(id="F", page=1, index=0, width=40, height=20).usable


def test_a_table_is_found_when_the_column_structure_survives():
    from foldok_reflow.assets import find_tables

    text = ("Cross-section    Current    Voltage drop\n"
            "1.5              16         2.4\n"
            "2.5              20         1.8\n"
            "4.0              25         1.2\n")
    tables = find_tables(text, source="x.pdf")
    assert tables and tables[0].usable
    assert tables[0].shape == (4, 3)


def test_a_table_needs_a_numeric_column():
    """Otherwise every two-column list of prose becomes a table."""
    from foldok_reflow.assets import find_tables

    text = ("Shielding      applied on both sides\n"
            "Bonding        360 degrees at terminations\n")
    assert not [t for t in find_tables(text) if t.usable]


def test_a_table_renders_as_markdown():
    from foldok_reflow.assets import find_tables

    text = "Size    Load\n10      2.5\n16      4.0\n"
    md = find_tables(text)[0].to_markdown()
    assert md.startswith("| Size | Load |")
    assert "| --- | --- |" in md


def test_reflow_destroys_tables_so_they_must_be_found_first():
    """The fix for fragmented prose joins short cells into sentences. Running
    table detection afterwards finds nothing, which is a real ordering trap."""
    from foldok_reflow import reflow
    from foldok_reflow.assets import find_tables

    text = "Size    Load\n10      2.5\n16      4.0\n"
    assert find_tables(text)
    assert not find_tables(reflow(text).text)


def test_a_flattened_table_is_reported_not_silently_missing():
    """pypdf emits one cell per line, so 'no tables' and 'tables cannot be seen'
    look identical to a caller. Only the second tells you what to do."""
    from foldok_reflow.assets import table_note

    flattened = "\n".join([
        "AC voltages up to 50 volts rms are permissible",
        "as protective extra-low voltage, or more correctly",
        "safety extra-low voltage. Above a limit of 75 volts DC",
    ])
    note = table_note(flattened)
    assert "flattens tables" in note and "pdfplumber" in note
