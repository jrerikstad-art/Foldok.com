"""Audit first-20 piping+mechanical symbols against the canonical port table."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from diagram_engine.symbols import get_symbol, load_symbols  # noqa: E402

load_symbols.cache_clear()

# Spec table: symbol_id -> [(port_id, side), ...]
EXPECTED = {
    "pipe_straight": [("in", "left"), ("out", "right")],
    "pipe_elbow": [("in", "left"), ("out", "bottom")],
    "pipe_tee": [("run_in", "left"), ("run_out", "right"), ("branch", "bottom")],
    "pipe_reducer": [("in", "left"), ("out", "right")],
    "valve_ball": [("in", "left"), ("out", "right")],
    "valve_gate": [("in", "left"), ("out", "right")],
    "valve_check": [("in", "left"), ("out", "right")],
    "valve_control": [("in", "left"), ("out", "right"), ("signal", "top")],
    "centrifugal_pump": [("suction", "left"), ("discharge", "right"), ("drive", "bottom")],
    "tank_vertical": [("outlet", "bottom"), ("inlet", "top"), ("vent", "top")],
    "strainer": [("in", "left"), ("out", "right")],
    "instrument_pt": [("process", "bottom")],
    "motor_ac": [("electrical", "left"), ("shaft", "right")],
    "gearbox": [("input_shaft", "left"), ("output_shaft", "right")],
    "coupling": [("in", "left"), ("out", "right")],
    "fan": [("drive", "left"), ("air_out", "right")],
    "cylinder_pneumatic": [("port_a", "left"), ("port_b", "right"), ("rod", "right")],
    # Through-shaft: left + right (spec: shaft left/right through)
    "bearing_block": [("shaft_l", "left"), ("shaft_r", "right")],
    "skid_frame": [],
    "pump_motor_set": [("suction", "left"), ("discharge", "right"), ("electrical", "left")],
}

DOMAIN = {
    **{k: "piping" for k in list(EXPECTED)[:12]},
    **{k: "mechanical" for k in list(EXPECTED)[12:19]},
    "pump_motor_set": "hybrid",
}


def main() -> int:
    errors = []
    for sid, ports in EXPECTED.items():
        sym = get_symbol(sid)
        if not sym:
            errors.append(f"MISSING symbol {sid}")
            continue
        want_dom = DOMAIN[sid]
        got_dom = sym.get("domain") or sym.get("_domain_dir")
        if got_dom != want_dom:
            errors.append(f"{sid}: domain {got_dom!r} != {want_dom!r}")
        got = [(p.get("id"), p.get("side")) for p in (sym.get("ports") or [])]
        if got != ports:
            errors.append(f"{sid}: ports {got} != {ports}")
        svg = Path(sym.get("_svg_path") or "")
        if not svg.exists():
            errors.append(f"{sid}: missing SVG {svg}")
    if errors:
        print("FAIL")
        for e in errors:
            print(" ", e)
        return 1
    print(f"OK first-20 symbols ({len(EXPECTED)}) match port table")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
