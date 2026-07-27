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


def _sym(sid: str, w: float, h: float, *elements, fill_body: bool = True) -> Symbol:
    return Symbol(sid, w, h, tuple(elements), fill_body)


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

EARTH = _sym(
    "earth", 26, 20,
    ("line", 0, -10, 0, 0, "equipment"),
    ("line", -12, 0, 12, 0, "equipment"),
    ("line", -8, 4, 8, 4, "equipment"),
    ("line", -4, 8, 4, 8, "equipment"),
    fill_body=False,
)

TERMINAL = _sym(
    "terminal", 12, 12,
    ("circle", 0, 0, 4, "equipment"),
    fill_body=False,
)

JUNCTION = _sym(
    "junction", 10, 10,
    ("circle", 0, 0, 3, "heavy"),
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

STOPCOCK = _sym(
    "stopcock", 26, 22,
    ("poly", [(-13, -8), (-13, 8), (0, 0)], "equipment", True),
    ("poly", [(13, -8), (13, 8), (0, 0)], "equipment", True),
    ("line", 0, -8, 0, -14, "equipment"),
    ("line", -7, -14, 7, -14, "equipment"),
    fill_body=False,
)

TEE_EQUAL = _sym(
    "tee_equal", 18, 18,
    ("line", -9, 0, 9, 0, "heavy"),
    ("line", 0, 0, 0, 9, "heavy"),
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

FALLBACK = _sym("fallback", 34, 26, _box(34, 26), ("glyph", 0, 3, "?", 11))

SYMBOLS: dict[str, Symbol] = {
    s.id: s
    for s in (
        DISTRIBUTION_BOARD, BREAKER_1P, BREAKER_2P, THERMOSTAT, HEATING_ELEMENT,
        LOAD_BLOCK, MOTOR_AC, EARTH, TERMINAL, JUNCTION,
        CENTRIFUGAL_PUMP, VALVE_BALL, VALVE_CHECK, STOPCOCK, TEE_EQUAL,
        ELBOW_90, REDUCER, MANIFOLD, WATER_HEATER, FIXTURE, TRAP, FLOOR_DRAIN,
        GEARBOX, COUPLING, FALLBACK,
    )
}

# Fittings must be Components, so the engine needs to know which types are
# fittings when it tells the user "insert a fitting here".
FITTING_TYPES = ("tee_equal", "elbow_90", "reducer", "manifold", "junction")


def get(symbol_id: str) -> Symbol:
    return SYMBOLS.get(symbol_id, FALLBACK)


def known(symbol_id: str) -> bool:
    return symbol_id in SYMBOLS


def describe() -> list[dict[str, Any]]:
    return [
        {"id": s.id, "w": s.w, "h": s.h, "fitting": s.id in FITTING_TYPES}
        for s in sorted(SYMBOLS.values(), key=lambda s: s.id)
    ]
