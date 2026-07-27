"""python -m diagram_engine — self-test + write fixtures/*.svg."""
from pathlib import Path

from .electrical import SLD_FIXTURE, WIRING_FIXTURE, render_electrical_diagram
from .mechanical import HYBRID_FIXTURE, MECHANICAL_FIXTURE, render_hybrid_diagram, render_mechanical_diagram
from .piping import PIPING_FIXTURE, render_piping_diagram
from .render_svg import (
    EXCAVATORBRAIN_FIXTURE,
    RENSEANLEGG_FIXTURE,
    render_block_diagram,
)
from .symbols import list_symbols

if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    fixtures = root / "fixtures"
    fixtures.mkdir(exist_ok=True)
    for name, fix, title, kind in (
        ("excavatorbrain_wiring.svg", EXCAVATORBRAIN_FIXTURE,
         "ExcavatorBrain — koblingsskjema (blokk)", "wiring"),
        ("renseanlegg_flow.svg", RENSEANLEGG_FIXTURE,
         "Renseanlegg — funksjonsdiagram", "process"),
    ):
        a = render_block_diagram(fix, title, kind=kind)
        b = render_block_diagram(fix, title, kind=kind)
        assert a == b, f"determinism broken: {name}"
        assert "Kanter:" in a and "stroke-dasharray" in a
        assert f'data-layout="{kind}"' in a
        (fixtures / name).write_text(a, encoding="utf-8")
        print(f"OK {name}: {len(fix['connections'])} edges kind={kind}")
    multi = render_block_diagram({
        "components": [{"id": "a", "label": "Linje1\\nLinje2", "pins": ["p"]}],
        "connections": [],
    })
    assert "Linje1" in multi and "Linje2" in multi

    by_dom = {}
    for r in list_symbols():
        by_dom.setdefault(r["domain"], 0)
        by_dom[r["domain"]] += 1
    assert by_dom.get("electrical", 0) >= 15
    assert by_dom.get("piping", 0) >= 10
    assert by_dom.get("mechanical", 0) >= 7

    for name, fix, mode, renderer in (
        ("electrical_sld.svg", SLD_FIXTURE, "single_line", render_electrical_diagram),
        ("electrical_wiring.svg", WIRING_FIXTURE, "wiring", render_electrical_diagram),
        ("piping_schematic.svg", PIPING_FIXTURE, "piping", render_piping_diagram),
        ("mechanical_arrangement.svg", MECHANICAL_FIXTURE, "mechanical", render_mechanical_diagram),
    ):
        a = renderer(fix, mode=mode)
        b = renderer(fix, mode=mode)
        assert a == b, f"determinism broken: {name}"
        assert f'data-layout="{mode}"' in a
        (fixtures / name).write_text(a, encoding="utf-8")
        print(f"OK {name}: mode={mode}")

    h = render_hybrid_diagram(HYBRID_FIXTURE)
    assert h == render_hybrid_diagram(HYBRID_FIXTURE)
    assert 'data-layout="hybrid"' in h
    (fixtures / "hybrid_skid.svg").write_text(h, encoding="utf-8")
    print("OK hybrid_skid.svg")

    print("diagram_engine selftest OK")
