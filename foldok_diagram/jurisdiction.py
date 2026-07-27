"""Jurisdiction rulesets.

Why this module exists: the first generated wiring diagram was internally
consistent and confidently wrong for its market — AWG conductors and a
"30 A 2-pole" breaker on a Norwegian water heater.  A plausible-but-wrong
diagram is worse output than an ugly correct one, so jurisdiction is a required
graph field and is checked, not assumed.

Note the trap: in a Norwegian IT installation 230 V is taken between two line
conductors, so L1 + L2 + PE with no neutral is CORRECT there and would be wrong
in a TN system, where the same load is L1 + N + PE.  The system, not the
conductor count, is the thing to get right.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Jurisdiction:
    id: str
    title: str
    system: str                      # IT / TN-S / TN-C-S / NEC split-phase
    phase_names: tuple[str, ...]
    neutral_name: str | None
    pe_name: str
    conductor_unit: str              # "mm2" | "AWG"
    size_pattern: str                # human hint for the size field
    nominal_voltages: tuple[int, ...]
    breaker_style: str               # "curve" (B/C/D) | "trip" (15/20/30 A)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def is_phase(self, designation: str | None) -> bool:
        return bool(designation) and designation in self.phase_names


JURISDICTIONS: dict[str, Jurisdiction] = {
    "NO_IT_230": Jurisdiction(
        id="NO_IT_230",
        title="Norway — IT system, 230 V line-to-line",
        system="IT",
        phase_names=("L1", "L2", "L3"),
        neutral_name=None,
        pe_name="PE",
        conductor_unit="mm2",
        size_pattern="e.g. 2.5 mm2",
        nominal_voltages=(230, 400),
        breaker_style="curve",
        notes=(
            "230 V is taken between two line conductors; there is no neutral.",
            "Size per NEK 400; breakers stated as curve + rating, e.g. C16.",
        ),
    ),
    "NO_TN_230_400": Jurisdiction(
        id="NO_TN_230_400",
        title="Norway — TN-S, 230/400 V",
        system="TN-S",
        phase_names=("L1", "L2", "L3"),
        neutral_name="N",
        pe_name="PE",
        conductor_unit="mm2",
        size_pattern="e.g. 2.5 mm2",
        nominal_voltages=(230, 400),
        breaker_style="curve",
        notes=("Single-phase loads are L + N + PE.",),
    ),
    "EU_TN_230_400": Jurisdiction(
        id="EU_TN_230_400",
        title="EU / IEC — TN, 230/400 V",
        system="TN-C-S",
        phase_names=("L1", "L2", "L3"),
        neutral_name="N",
        pe_name="PE",
        conductor_unit="mm2",
        size_pattern="e.g. 2.5 mm2",
        nominal_voltages=(230, 400),
        breaker_style="curve",
    ),
    "US_NEC_120_240": Jurisdiction(
        id="US_NEC_120_240",
        title="US — NEC split-phase 120/240 V",
        system="NEC split-phase",
        phase_names=("L1", "L2"),
        neutral_name="N",
        pe_name="EGC",
        conductor_unit="AWG",
        size_pattern="e.g. AWG 10",
        nominal_voltages=(120, 240),
        breaker_style="trip",
        notes=("Protective conductor is the EGC, not PE.",),
    ),
}

DEFAULT_JURISDICTION = "NO_IT_230"


def get(jid: str) -> Jurisdiction:
    try:
        return JURISDICTIONS[jid]
    except KeyError as exc:
        raise ValueError(
            f"unknown jurisdiction '{jid}'; known: {sorted(JURISDICTIONS)}"
        ) from exc


def size_unit_matches(size: str, juris: Jurisdiction) -> bool:
    s = size.lower().replace(" ", "")
    if juris.conductor_unit == "mm2":
        return ("mm2" in s) or ("mm²" in s) or s.startswith("dn") or s.startswith("g")
    return "awg" in s or s.endswith("kcmil")
