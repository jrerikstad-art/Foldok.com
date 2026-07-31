"""Symbol pack.

Symbols carry geometry only: a box size and a list of primitives drawn in local
coordinates centred on (0, 0).  Port ANCHORS are not baked into the symbol —
they are derived from the graph's ports, spread along the side the port declares
and ordered by ``Port.order``.  That way one symbol serves any port count and a
component can gain a port without a new symbol.

Primitives (kept deliberately small so the Flutter canvas can render the same
set natively if it ever needs to):

    ("line", x1, y1, x2, y2, weight)
    ("rect", x, y, w, h, weight)
    ("circle", cx, cy, r, weight)
    ("path", d, weight)
    ("poly", [(x, y), ...], weight, closed)
    ("glyph", x, y, text, size)

``weight`` is one of "equipment", "thin", "heavy".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Symbol:
    id: str
    w: float
    h: float
    elements: tuple[tuple, ...] = field(default_factory=tuple)
    fill_body: bool = True          # paint symbol_fill behind the marks
    labels_inside: bool = False
    """Print port labels inside the body instead of in the routing channel.

    Correct for modules and terminal blocks, which are drawn as rectangles wide
    enough to hold pin names — the way every breakout-board wiring diagram does
    it. Wrong for a valve or a breaker, where the body is a mark and the channel
    is empty. Getting this backwards suppresses labels: the engine refuses to
    overlap text, so a crowded channel simply loses them."""


def _sym(
    sid: str,
    w: float,
    h: float,
    *elements,
    fill_body: bool = True,
    labels_inside: bool = False,
) -> Symbol:
    return Symbol(sid, w, h, tuple(elements), fill_body, labels_inside)


def _box(w: float, h: float, weight: str = "equipment"):
    return ("rect", -w / 2, -h / 2, w, h, weight)


# --- electrical ---------------------------------------------------------
DISTRIBUTION_BOARD = _sym(
    "distribution_board", 44, 32,
    _box(44, 32),
    ("line", -16, -6, 16, -6, "thin"),
    ("line", -16, 0, 16, 0, "thin"),
    ("line", -16, 6, 16, 6, "thin"),
)

BREAKER_1P = _sym(
    "breaker_1p", 26, 30,
    _box(26, 30),
    ("line", 0, -15, 0, -6, "equipment"),
    ("line", 0, 6, 0, 15, "equipment"),
    ("line", -7, -6, 7, 6, "equipment"),
    ("line", -8, 6, 8, 6, "thin"),
)

BREAKER_2P = _sym(
    "breaker_2p", 34, 30,
    _box(34, 30),
    ("line", -7, -15, -7, -6, "equipment"),
    ("line", -7, 6, -7, 15, "equipment"),
    ("line", -13, -6, -1, 6, "equipment"),
    ("line", 7, -15, 7, -6, "equipment"),
    ("line", 7, 6, 7, 15, "equipment"),
    ("line", 1, -6, 13, 6, "equipment"),
    ("line", -10, 0, 10, 0, "thin"),
)

RCD = _sym(
    "rcd", 34, 30,
    _box(34, 30),
    ("line", -8, -15, -8, -6, "equipment"),
    ("line", -8, 6, -8, 15, "equipment"),
    ("line", -14, -6, -2, 6, "equipment"),
    ("line", 8, -15, 8, -6, "equipment"),
    ("line", 8, 6, 8, 15, "equipment"),
    ("line", 2, -6, 14, 6, "equipment"),
    ("circle", 0, 0, 3.5, "thin"),
    ("glyph", 0, 2.5, "Δ", 8),
)

FUSE = _sym(
    "fuse", 28, 18,
    _box(28, 18),
    ("rect", -10, -4, 20, 8, "thin"),
    ("line", -14, 0, -10, 0, "equipment"),
    ("line", 10, 0, 14, 0, "equipment"),
)

CONTACTOR = _sym(
    "contactor", 34, 28,
    _box(34, 28),
    ("line", -10, -8, -10, 8, "equipment"),
    ("line", 0, -8, 0, 8, "equipment"),
    ("line", 10, -8, 10, 8, "equipment"),
    ("line", -14, -4, -6, 4, "equipment"),
    ("line", -4, -4, 4, 4, "equipment"),
    ("line", 6, -4, 14, 4, "equipment"),
)

SWITCH = _sym(
    "switch", 28, 22,
    _box(28, 22),
    ("line", -10, 0, -2, 0, "equipment"),
    ("line", -2, 0, 8, -7, "equipment"),
    ("circle", 10, 0, 2, "equipment"),
)

THERMOSTAT = _sym(
    "thermostat", 32, 26,
    _box(32, 26),
    ("path", "M -10 4 L -4 4 L -4 -4 L 4 -4 L 4 4 L 10 4", "equipment"),
    ("line", -12, -8, 12, -8, "thin"),
)

HEATING_ELEMENT = _sym(
    "heating_element", 36, 24,
    _box(36, 24),
    ("path", "M -13 0 l 4 -7 l 4 14 l 4 -14 l 4 14 l 4 -14 l 4 7", "equipment"),
)

LOAD_BLOCK = _sym(
    "load_block", 34, 26,
    _box(34, 26),
    ("line", -17, -13, 17, 13, "thin"),
)

MOTOR_AC = _sym(
    "motor_ac", 30, 30,
    ("circle", 0, 0, 15, "equipment"),
    ("glyph", 0, 3.5, "M", 11),
)

LAMP = _sym(
    "lamp", 28, 28,
    ("circle", 0, 0, 12, "equipment"),
    ("line", -8, -8, 8, 8, "thin"),
    ("line", -8, 8, 8, -8, "thin"),
)

EARTH = _sym(
    "earth", 26, 20,
    ("line", 0, -10, 0, 0, "equipment"),
    ("line", -12, 0, 12, 0, "equipment"),
    ("line", -8, 4, 8, 4, "equipment"),
    ("line", -4, 8, 4, 8, "equipment"),
    fill_body=False,
)

# IEC 60417 protection-class marks (equipment nameplates / manuals).
# Class I — protective earth in a circle.
PROTECTION_CLASS_I = _sym(
    "protection_class_i", 24, 24,
    ("circle", 0, 0, 10, "equipment"),
    ("line", 0, -10, 0, 0, "equipment"),
    ("line", -7, 0, 7, 0, "equipment"),
    ("line", -5, 3, 5, 3, "equipment"),
    ("line", -3, 6, 3, 6, "equipment"),
    fill_body=False,
)

# Class II — double insulation (concentric squares).
PROTECTION_CLASS_II = _sym(
    "protection_class_ii", 24, 24,
    ("rect", -9, -9, 18, 18, "equipment"),
    ("rect", -5, -5, 10, 10, "equipment"),
    fill_body=False,
)

# Class III — SELV (diamond with three vertical bars).
PROTECTION_CLASS_III = _sym(
    "protection_class_iii", 24, 24,
    ("poly", [(0, -10), (10, 0), (0, 10), (-10, 0)], "equipment", True),
    ("line", -3.5, -4.5, -3.5, 4.5, "equipment"),
    ("line", 0, -4.5, 0, 4.5, "equipment"),
    ("line", 3.5, -4.5, 3.5, 4.5, "equipment"),
    fill_body=False,
)

# Equipotential bonding connectors (large area / large cross-section).
# Sized to sit with breaker/earth marks — not full-width nameplates.
BOND_STRAP = _sym(
    "bond_strap", 34, 12,
    ("rect", -15, -4, 30, 8, "equipment"),
    ("circle", -10, 0, 2.2, "equipment"),
    ("circle", 10, 0, 2.2, "equipment"),
    fill_body=False,
)

BOND_BRAID_LUG = _sym(
    "bond_braid_lug", 38, 14,
    ("rect", -17, -5, 7, 10, "equipment"),
    ("circle", -13.5, 0, 2, "equipment"),
    ("rect", -10, -3, 20, 6, "equipment"),
    ("line", -8, -2.5, -4, 2.5, "thin"),
    ("line", -4, -2.5, 0, 2.5, "thin"),
    ("line", 0, -2.5, 4, 2.5, "thin"),
    ("line", 4, -2.5, 8, 2.5, "thin"),
    ("line", -8, 2.5, -4, -2.5, "thin"),
    ("line", -4, 2.5, 0, -2.5, "thin"),
    ("line", 0, 2.5, 4, -2.5, "thin"),
    ("line", 4, 2.5, 8, -2.5, "thin"),
    ("rect", 10, -5, 7, 10, "equipment"),
    ("circle", 13.5, 0, 2, "equipment"),
    fill_body=False,
)

BOND_BRAID_RING = _sym(
    "bond_braid_ring", 38, 14,
    ("circle", -14, 0, 4.5, "equipment"),
    ("circle", -14, 0, 2, "thin"),
    ("rect", -9.5, -2, 3.5, 4, "equipment"),
    ("rect", -6, -3, 12, 6, "equipment"),
    ("line", -4, -2.5, 0, 2.5, "thin"),
    ("line", 0, -2.5, 4, 2.5, "thin"),
    ("line", -4, 2.5, 0, -2.5, "thin"),
    ("line", 0, 2.5, 4, -2.5, "thin"),
    ("rect", 6, -2, 3.5, 4, "equipment"),
    ("circle", 14, 0, 4.5, "equipment"),
    ("circle", 14, 0, 2, "thin"),
    fill_body=False,
)

TERMINAL = _sym(
    "terminal", 12, 12,
    ("circle", 0, 0, 4, "equipment"),
    fill_body=False,
)

TERMINAL_STRIP = _sym(
    "terminal_strip", 52, 24,
    _box(52, 24),
    ("line", -18, -12, -18, 12, "thin"),
    ("line", -6, -12, -6, 12, "thin"),
    ("line", 6, -12, 6, 12, "thin"),
    ("line", 18, -12, 18, 12, "thin"),
    labels_inside=True,
)

JUNCTION = _sym(
    "junction", 10, 10,
    ("circle", 0, 0, 3, "heavy"),
    fill_body=False,
)

# Isolating transformer — two coils side by side (IEC-style).
TRANSFORMER = _sym(
    "transformer", 40, 32,
    _box(40, 32),
    ("path", "M -14 -10 q -4 5 0 10 q 4 5 0 10", "equipment"),
    ("path", "M -8 -10 q -4 5 0 10 q 4 5 0 10", "equipment"),
    ("line", -2, -12, -2, 12, "thin"),
    ("path", "M 4 -10 q 4 5 0 10 q -4 5 0 10", "equipment"),
    ("path", "M 10 -10 q 4 5 0 10 q -4 5 0 10", "equipment"),
)

# Mains / EMI filter — box with LC π hint.
MAINS_FILTER = _sym(
    "mains_filter", 42, 30,
    _box(42, 30),
    ("path", "M -14 0 q -3 -8 0 -8 q 3 0 0 8 q -3 8 0 8 q 3 0 0 -8", "equipment"),
    ("line", -6, -8, -6, 8, "thin"),
    ("line", -10, -8, -2, -8, "thin"),
    ("line", -10, 8, -2, 8, "thin"),
    ("path", "M 6 0 q -3 -8 0 -8 q 3 0 0 8 q -3 8 0 8 q 3 0 0 -8", "equipment"),
    ("glyph", 14, 3, "Z", 9),
)

# Safety / PELV PSU — rectified DC out mark.
POWER_SUPPLY = _sym(
    "power_supply", 40, 30,
    _box(40, 30),
    ("path", "M -14 -2 q 4 -6 8 0 q 4 6 8 0", "equipment"),
    ("line", -2, -10, -2, 10, "thin"),
    ("line", 4, -6, 14, -6, "equipment"),
    ("line", 4, 0, 12, 0, "equipment"),
    ("line", 4, 6, 14, 6, "equipment"),
)

# Field / safety sensor — optic eye + body.
SENSOR = _sym(
    "sensor", 36, 28,
    _box(36, 28),
    ("circle", -6, 0, 7, "equipment"),
    ("circle", -6, 0, 2.5, "thin"),
    ("line", 2, -6, 12, 0, "equipment"),
    ("line", 2, 6, 12, 0, "equipment"),
)

# Shielded / screened cable segment (braid mark).
CABLE_SHIELDED = _sym(
    "cable_shielded", 48, 22,
    _box(48, 22),
    ("line", -20, 0, 20, 0, "heavy"),
    ("path", "M -12 -6 q 4 6 0 12", "thin"),
    ("path", "M -4 -6 q 4 6 0 12", "thin"),
    ("path", "M 4 -6 q 4 6 0 12", "thin"),
    ("path", "M 12 -6 q 4 6 0 12", "thin"),
)

FERRITE = _sym(
    "ferrite", 28, 22,
    _box(28, 22),
    ("rect", -8, -8, 16, 16, "thin"),
    ("line", -14, 0, -8, 0, "equipment"),
    ("line", 8, 0, 14, 0, "equipment"),
)

CAPACITOR = _sym(
    "capacitor", 24, 28,
    ("line", 0, -14, 0, -6, "equipment"),
    ("line", -10, -6, 10, -6, "equipment"),
    ("line", -10, 6, 10, 6, "equipment"),
    ("line", 0, 6, 0, 14, "equipment"),
    fill_body=False,
)

# --- piping ------------------------------------------------------------
CENTRIFUGAL_PUMP = _sym(
    "centrifugal_pump", 32, 32,
    ("circle", 0, 0, 16, "equipment"),
    ("poly", [(-4, -9), (12, 0), (-4, 9)], "equipment", True),
)

VALVE_BALL = _sym(
    "valve_ball", 28, 20,
    ("poly", [(-14, -9), (-14, 9), (0, 0)], "equipment", True),
    ("poly", [(14, -9), (14, 9), (0, 0)], "equipment", True),
    ("circle", 0, 0, 4, "equipment"),
    fill_body=False,
)

VALVE_CHECK = _sym(
    "valve_check", 28, 20,
    ("poly", [(-14, -9), (-14, 9), (6, 0)], "equipment", True),
    ("line", 8, -9, 8, 9, "equipment"),
    fill_body=False,
)

VALVE_GATE = _sym(
    "valve_gate", 28, 22,
    ("poly", [(-14, -9), (-14, 9), (0, 0)], "equipment", True),
    ("poly", [(14, -9), (14, 9), (0, 0)], "equipment", True),
    ("line", 0, -10, 0, 10, "equipment"),
    fill_body=False,
)

VALVE_MIXING = _sym(
    "valve_mixing", 30, 26,
    ("poly", [(-14, -6), (-14, 6), (0, 0)], "equipment", True),
    ("poly", [(14, -6), (14, 6), (0, 0)], "equipment", True),
    ("poly", [(-6, 12), (6, 12), (0, 0)], "equipment", True),
    ("circle", 0, 0, 3, "thin"),
    fill_body=False,
)

VALVE_PRV = _sym(
    "valve_prv", 30, 26,
    ("poly", [(-14, -9), (-14, 9), (0, 0)], "equipment", True),
    ("poly", [(14, -9), (14, 9), (0, 0)], "equipment", True),
    ("path", "M -4 -14 L 0 -8 L 4 -14", "equipment"),
    ("line", -6, -14, 6, -14, "thin"),
    fill_body=False,
)

STOPCOCK = _sym(
    "stopcock", 26, 22,
    ("poly", [(-13, -8), (-13, 8), (0, 0)], "equipment", True),
    ("poly", [(13, -8), (13, 8), (0, 0)], "equipment", True),
    ("line", 0, -8, 0, -14, "equipment"),
    ("line", -7, -14, 7, -14, "equipment"),
    fill_body=False,
)

STRAINER = _sym(
    "strainer", 30, 24,
    ("poly", [(-14, -9), (-14, 9), (0, 0)], "equipment", True),
    ("poly", [(14, -9), (14, 9), (0, 0)], "equipment", True),
    ("line", -4, 2, 4, 10, "thin"),
    ("line", 0, 2, 8, 10, "thin"),
    ("line", 4, 2, 10, 8, "thin"),
    fill_body=False,
)

WATER_METER = _sym(
    "water_meter", 30, 30,
    ("circle", 0, 0, 14, "equipment"),
    ("glyph", 0, 3.5, "M", 10),
)

EXPANSION_VESSEL = _sym(
    "expansion_vessel", 28, 36,
    ("circle", 0, -4, 12, "equipment"),
    ("line", -12, -4, 12, -4, "thin"),
    ("line", 0, 8, 0, 16, "equipment"),
    ("line", -6, 16, 6, 16, "equipment"),
)

AIR_VENT = _sym(
    "air_vent", 22, 28,
    ("line", 0, 12, 0, 0, "equipment"),
    ("circle", 0, -6, 8, "equipment"),
    ("line", -4, -10, 4, -2, "thin"),
    ("line", -4, -2, 4, -10, "thin"),
    fill_body=False,
)

RADIATOR = _sym(
    "radiator", 48, 28,
    _box(48, 28),
    ("line", -16, -14, -16, 14, "thin"),
    ("line", -5, -14, -5, 14, "thin"),
    ("line", 5, -14, 5, 14, "thin"),
    ("line", 16, -14, 16, 14, "thin"),
)

BOILER = _sym(
    "boiler", 40, 44,
    ("path", "M -18 -14 a 18 10 0 0 1 36 0 l 0 28 a 18 10 0 0 1 -36 0 Z", "equipment"),
    ("line", -18, -14, 18, -14, "thin"),
    ("path", "M -8 4 l 3 -5 l 3 10 l 3 -10 l 3 5", "thin"),
)

TEE_EQUAL = _sym(
    "tee_equal", 18, 18,
    ("line", -9, 0, 9, 0, "heavy"),
    ("line", 0, 0, 0, 9, "heavy"),
    ("circle", 0, 0, 2.5, "heavy"),
    fill_body=False,
)

CROSS_EQUAL = _sym(
    "cross_equal", 18, 18,
    ("line", -9, 0, 9, 0, "heavy"),
    ("line", 0, -9, 0, 9, "heavy"),
    ("circle", 0, 0, 2.5, "heavy"),
    fill_body=False,
)

ELBOW_90 = _sym(
    "elbow_90", 16, 16,
    ("path", "M -8 0 L 0 0 L 0 8", "heavy"),
    fill_body=False,
)

REDUCER = _sym(
    "reducer", 22, 18,
    ("poly", [(-11, -8), (11, -4), (11, 4), (-11, 8)], "equipment", True),
    fill_body=False,
)

MANIFOLD = _sym(
    "manifold", 56, 20,
    _box(56, 20),
    ("line", -20, -10, -20, 10, "thin"),
    ("line", -6, -10, -6, 10, "thin"),
    ("line", 8, -10, 8, 10, "thin"),
    ("line", 22, -10, 22, 10, "thin"),
)

WATER_HEATER = _sym(
    "water_heater", 40, 52,
    ("path", "M -20 -18 a 20 12 0 0 1 40 0 l 0 36 a 20 12 0 0 1 -40 0 Z", "equipment"),
    ("line", -20, -18, 20, -18, "thin"),
)

FIXTURE = _sym(
    "fixture", 32, 22,
    ("path", "M -16 -11 a 16 11 0 0 0 32 0", "equipment"),
    ("line", -16, -11, 16, -11, "equipment"),
    fill_body=False,
)

TRAP = _sym(
    "trap", 24, 22,
    ("path", "M -10 -11 L -10 4 a 10 8 0 0 0 20 0 L 10 -11", "equipment"),
    fill_body=False,
)

FLOOR_DRAIN = _sym(
    "floor_drain", 30, 18,
    ("line", -15, -9, 15, -9, "equipment"),
    ("path", "M -9 -9 L 0 6 L 9 -9", "equipment"),
    fill_body=False,
)

# Cable-tray cross-sections — compact marks (~breaker size), not full figures.

def _multicore(cx: float, cy: float, r: float = 3.2) -> tuple:
    """Seven-conductor cable cross-section."""
    dots = []
    for dx, dy in (
        (0, 0), (-1.3, -0.7), (1.3, -0.7), (-1.3, 0.7), (1.3, 0.7),
        (0, -1.4), (0, 1.4),
    ):
        dots.append(("circle", cx + dx, cy + dy, 0.55, "heavy"))
    return (("circle", cx, cy, r, "equipment"), *dots)


_CABLE_DEEP = (
    _multicore(-5, 4, 2.8) + _multicore(0, 4, 2.8) + _multicore(5, 4, 2.8)
    + _multicore(-2.5, -1, 2.8) + _multicore(2.5, -1, 2.8)
)
_CABLE_SHALLOW = (
    _multicore(-9, 1.5, 2.6) + _multicore(-3, 1.5, 2.6) + _multicore(3, 1.5, 2.6)
    + _multicore(9, 1.5, 2.6)
    + _multicore(-6, -3.5, 2.6) + _multicore(0, -3.5, 2.6) + _multicore(6, -3.5, 2.6)
)

CABLE_TRAY_DEEP = _sym(
    "cable_tray_deep", 28, 26,
    ("path", "M -10 -10 L -10 10 L 10 10 L 10 -10", "equipment"),
    ("path", "M -8 8 Q 0 -1 8 8", "thin"),
    ("path", "M -8 6.5 Q 0 0.5 8 6.5", "thin"),
    ("path", "M -8 5 Q 0 2 8 5", "thin"),
    fill_body=False,
)

CABLE_TRAY_SHALLOW = _sym(
    "cable_tray_shallow", 36, 18,
    ("path", "M -15 -5 L -15 6 L 15 6 L 15 -5", "equipment"),
    ("path", "M -13 5 Q 0 -2 13 5", "thin"),
    ("path", "M -13 3.5 Q 0 -0.5 13 3.5", "thin"),
    fill_body=False,
)

CABLE_TRAY_DEEP_OK = _sym(
    "cable_tray_deep_ok", 32, 30,
    ("path", "M -10 -11 L -10 10 L 10 10 L 10 -11", "equipment"),
    ("path", "M -8 8 Q 0 -2 8 8", "thin"),
    ("path", "M -8 6.5 Q 0 -0.5 8 6.5", "thin"),
    *_CABLE_DEEP,
    ("path", "M 12 6 L 14.5 9.5 L 19 2", "heavy"),
    fill_body=False,
)

CABLE_TRAY_SHALLOW_BAD = _sym(
    "cable_tray_shallow_bad", 40, 24,
    ("path", "M -15 -6 L -15 6 L 15 6 L 15 -6", "equipment"),
    ("path", "M -13 5 Q 0 -3 13 5", "thin"),
    *_CABLE_SHALLOW,
    ("line", 13, -8, 19, -1, "heavy"),
    ("line", 13, -1, 19, -8, "heavy"),
    fill_body=False,
)

CABLE_MULTICORE = _sym(
    "cable_multicore", 12, 12,
    *_multicore(0, 0, 5),
    fill_body=False,
)

# --- mechanical --------------------------------------------------------
GEARBOX = _sym(
    "gearbox", 34, 28,
    _box(34, 28),
    ("circle", -6, 0, 7, "thin"),
    ("circle", 8, 0, 5, "thin"),
)

COUPLING = _sym(
    "coupling", 18, 20,
    ("rect", -9, -10, 7, 20, "equipment"),
    ("rect", 2, -10, 7, 20, "equipment"),
    fill_body=False,
)

BEARING = _sym(
    "bearing", 26, 22,
    ("rect", -11, -9, 22, 18, "equipment"),
    ("circle", 0, 0, 5, "thin"),
)

SHAFT = _sym(
    "shaft", 40, 12,
    ("line", -18, 0, 18, 0, "heavy"),
    ("line", -18, -4, -18, 4, "equipment"),
    ("line", 18, -4, 18, 4, "equipment"),
    fill_body=False,
)

FALLBACK = _sym("fallback", 34, 26, _box(34, 26), ("glyph", 0, 3, "?", 11))

SYMBOLS: dict[str, Symbol] = {
    s.id: s
    for s in (
        # electrical
        DISTRIBUTION_BOARD, BREAKER_1P, BREAKER_2P, RCD, FUSE, CONTACTOR, SWITCH,
        THERMOSTAT, HEATING_ELEMENT, LOAD_BLOCK, MOTOR_AC, LAMP, EARTH,
        PROTECTION_CLASS_I, PROTECTION_CLASS_II, PROTECTION_CLASS_III,
        BOND_STRAP, BOND_BRAID_LUG, BOND_BRAID_RING,
        TERMINAL, TERMINAL_STRIP, JUNCTION, TRANSFORMER, MAINS_FILTER,
        POWER_SUPPLY, SENSOR, CABLE_SHIELDED, FERRITE, CAPACITOR,
        # piping
        CENTRIFUGAL_PUMP, VALVE_BALL, VALVE_CHECK, VALVE_GATE, VALVE_MIXING,
        VALVE_PRV, STOPCOCK, STRAINER, WATER_METER, EXPANSION_VESSEL, AIR_VENT,
        RADIATOR, BOILER, TEE_EQUAL, CROSS_EQUAL, ELBOW_90, REDUCER, MANIFOLD,
        WATER_HEATER, FIXTURE, TRAP, FLOOR_DRAIN,
        CABLE_TRAY_DEEP, CABLE_TRAY_SHALLOW, CABLE_TRAY_DEEP_OK,
        CABLE_TRAY_SHALLOW_BAD, CABLE_MULTICORE,
        # mechanical
        GEARBOX, COUPLING, BEARING, SHAFT, FALLBACK,
    )
}

# Fittings must be Components, so the engine needs to know which types are
# fittings when it tells the user "insert a fitting here".
FITTING_TYPES = (
    "tee_equal", "cross_equal", "elbow_90", "reducer", "manifold", "junction",
)


def get(symbol_id: str) -> Symbol:
    return SYMBOLS.get(symbol_id, FALLBACK)


def known(symbol_id: str) -> bool:
    return symbol_id in SYMBOLS


def describe() -> list[dict[str, Any]]:
    return [
        {"id": s.id, "w": s.w, "h": s.h, "fitting": s.id in FITTING_TYPES}
        for s in sorted(SYMBOLS.values(), key=lambda s: s.id)
    ]
