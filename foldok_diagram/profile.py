"""Profiles — one graph, several views.

This was the largest hole in the earlier spec: ``profile`` appeared in every
code path and was never defined.  A profile answers four questions:

1.  Which components and connections are visible?
2.  How does a component render here?  A pump is a symbol in the piping view
    and a load block in a single-line diagram — same component, different
    symbol variant.
3.  What is the y axis?  ``layered`` = topology.  ``elevation`` = real height,
    which drainage risers need.
4.  What is printed on the run?  Wiring wants designation + cross-section;
    piping wants size + medium.

A component excluded from a view is not deleted and its pins are not touched.
Connections whose endpoints fall outside the view are dropped, and if a dropped
component sat mid-run the run is reported as broken rather than bridged — a
silent bridge would invent a circuit that does not exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Profile:
    id: str
    title: str
    include_domains: tuple[str, ...] = ("electrical", "piping", "mechanical", "signal", "hybrid")
    include_media: tuple[str, ...] = ("wire", "pipe", "shaft", "duct", "signal")
    include_roles: tuple[str, ...] = ("equipment", "fitting", "terminal", "reference")
    axis: str = "layered"                      # "layered" | "elevation"
    symbol_variants: dict[str, str] = field(default_factory=dict)
    show_port_labels: bool = True
    show_designation: bool = True
    show_size: bool = False
    show_flow_arrows: bool = False
    show_elevation_axis: bool = False

    def wants_component(self, component) -> bool:
        return component.domain in self.include_domains and component.role in self.include_roles

    def wants_connection(self, connection) -> bool:
        return connection.medium in self.include_media

    def symbol_for(self, component) -> str:
        return self.symbol_variants.get(component.type, component.type)


WIRING = Profile(
    id="wiring",
    title="Terminal interconnection",
    include_media=("wire", "signal"),
    show_port_labels=True,
    show_designation=True,
    show_size=True,
)

SINGLE_LINE = Profile(
    id="single_line",
    title="Single-line diagram",
    include_media=("wire",),
    show_port_labels=False,
    show_designation=True,
    show_size=True,
    symbol_variants={
        "centrifugal_pump": "load_block",
        "motor_ac": "load_block",
        "heating_element": "load_block",
    },
)

PIPING = Profile(
    id="piping",
    title="Piping schematic",
    include_media=("pipe", "duct"),
    include_domains=("piping", "mechanical", "hybrid"),
    show_port_labels=False,
    show_designation=True,
    show_size=True,
    show_flow_arrows=True,
)

DRAINAGE_RISER = Profile(
    id="drainage_riser",
    title="Drainage riser",
    include_media=("pipe",),
    include_domains=("piping", "hybrid"),
    axis="elevation",
    show_port_labels=False,
    show_size=True,
    show_flow_arrows=True,
    show_elevation_axis=True,
)

MECHANICAL = Profile(
    id="mechanical",
    title="Mechanical arrangement",
    include_media=("shaft",),
    include_domains=("mechanical", "hybrid"),
    show_port_labels=True,
    show_designation=False,
)

PROFILES: dict[str, Profile] = {
    p.id: p for p in (WIRING, SINGLE_LINE, PIPING, DRAINAGE_RISER, MECHANICAL)
}


def get(profile_id: str) -> Profile:
    try:
        return PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"unknown profile '{profile_id}'; known: {sorted(PROFILES)}") from exc
