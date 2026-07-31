"""Tests for the diagram route.

Run:  python -m pytest foldok_route/tests -q
"""

from __future__ import annotations

import pytest

from foldok_route import handle, is_diagram_request

SPEC = {
    "title": "Control electronics",
    "components": [
        {"id": "A", "label": "Buck", "ports": [{"id": "o", "name": "5V", "side": "right"}]},
        {"id": "B", "label": "Pi", "ports": [{"id": "i", "name": "5V", "side": "left"}]},
    ],
    "connections": [{"from": "A.o", "to": "B.i", "designation": "V+", "size": "20 AWG"}],
}


@pytest.mark.parametrize("question", [
    "there should be a wiring diagram in the manual, how do i connect the components",
    "kan du lage et koblingsskjema for tavla?",
    "hvordan kobler jeg sammen komponentene?",
    "legg inn enlinjeskjema i kapittel 4",
    "can you draw a schematic",
])
def test_a_drawing_request_is_routed(question):
    assert is_diagram_request(question)


@pytest.mark.parametrize("question", [
    "kan du lese DWG-filen min?",
    "lag en 3d model av huset",
    "hva koster en eksport?",
    "importer tegning fra SolidWorks",
])
def test_a_question_about_files_or_cad_is_not(question):
    assert not is_diagram_request(question)


def test_with_a_spec_it_draws():
    result = handle("lag et koblingsskjema", spec=SPEC, lang="no")
    assert result.handled and result.svg.startswith("<svg")
    assert "koblingsskjema" in result.reply.lower()


def test_without_a_spec_it_asks_and_says_what_it_already_has():
    """'I need more information' with no list is the same dead end as
    'I have no tool'."""
    result = handle("hvordan kobler jeg sammen komponentene?",
                    components=[{"label": "Raspberry Pi 5"}, {"label": "PCA9685 PWM"}],
                    lang="no")
    assert result.spec_needed
    assert "Raspberry Pi 5" in result.reply and "PCA9685 PWM" in result.reply


def test_a_bad_spec_returns_the_engine_message_not_a_stack_trace():
    bad = dict(SPEC, connections=[{"from": "A", "to": "B.i"}])
    result = handle("koblingsskjema", spec=bad)
    assert result.handled and "COMPONENT.PORT" in result.reply


def test_an_unrelated_question_is_left_alone():
    assert handle("hva koster en eksport?").handled is False
