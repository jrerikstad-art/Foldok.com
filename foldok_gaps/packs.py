"""Requirement packs — the breadth proof.

Four segments, four packs, zero engine changes between them.  That is the whole
argument: electrical installation, EU machinery technical file, aquaculture
site, and a prototype build log are all the same shape of problem, so they are
all data.  If a fifth segment needed a code change, the model would be wrong.

Note what varies and what does not:

*  Sections vary.  The prototype pack defines its own five, and nothing in the
   engine cares.
*  ``per`` varies: per circuit, per machine, per cage, per document.  This is
   what produces "30 mangler" out of six requirements.
*  Severity and ``allow_not_applicable`` vary a lot.  The prototype pack has no
   blocking requirement at all, which is exactly why it works for someone who
   is not chasing a certificate.
*  The evidential/expository split does not vary.  A measured value is evidence
   in every segment.
"""

from __future__ import annotations

from .requirements import (
    FOLDOK_SPINE,
    FormField,
    Requirement,
    RequirementPack,
    Section,
)

# ----------------------------------------------------------------------
# 1. Electrical installation, Norway
# ----------------------------------------------------------------------
_INSTRUMENT = FormField("instrument", "Instrument and serial no.", kind="text")
_DATE = FormField("date", "Date", kind="date")
_BY = FormField("measured_by", "Measured by", kind="text")

NO_ELECTRICAL = RequirementPack(
    id="no_electrical_installation",
    title="Electrical installation — Norway",
    segment="electrical",
    version="1",
    jurisdiction="NO_IT_230",
    standards=("NEK 400", "FEL"),
    description="Installation documentation and verification for a fixed electrical installation.",
    requirements=(
        Requirement(
            key="el.identification",
            section="identification",
            title="Installation identified",
            kind="text",
            severity="blocking",
            allow_not_applicable=False,
            authority="FEL §12",
            description="Address, installation number, revision and date.",
        ),
        Requirement(
            key="el.parties",
            section="parties",
            title="Responsible undertaking and installer named",
            kind="text",
            severity="blocking",
            allow_not_applicable=False,
        ),
        Requirement(
            key="el.scope",
            section="scope",
            title="Scope of work described",
            kind="text",
            severity="required",
        ),
        Requirement(
            key="el.standards",
            section="standards",
            title="Standards applied",
            kind="table",
            severity="required",
            fields=(FormField("standard", "Standard"), FormField("edition", "Edition")),
        ),
        Requirement(
            key="el.board_schematic",
            section="drawings",
            title="Distribution board schematic",
            kind="diagram",
            evidence="evidential",
            per="board",
            severity="blocking",
            allow_not_applicable=False,
            authority="NEK 400:2022 §8-1",
            description="As-built single line for the board, including protective devices.",
        ),
        Requirement(
            key="el.circuit_schematic",
            section="drawings",
            title="Circuit schematic",
            kind="diagram",
            evidence="evidential",
            per="circuit",
            severity="required",
            authority="NEK 400:2022 §8-1",
        ),
        Requirement(
            key="el.parts_list",
            section="components",
            title="Parts list",
            kind="table",
            evidence="evidential",
            severity="required",
            fields=(
                FormField("item", "Item"),
                FormField("type", "Type"),
                FormField("quantity", "Qty", kind="number"),
            ),
        ),
        Requirement(
            key="el.board_photo",
            section="installation",
            title="Photograph of the finished board",
            kind="photo",
            evidence="evidential",
            per="board",
            severity="required",
            capture_prompt="Photograph the board with the cover off, labels legible.",
        ),
        Requirement(
            key="el.continuity",
            section="verification",
            title="Continuity of protective conductor",
            kind="measurement",
            evidence="evidential",
            per="circuit",
            severity="blocking",
            allow_not_applicable=False,
            authority="NEK 400:2022 §6-61",
            fields=(
                FormField("resistance_ohm", "Resistance", unit="Ω", kind="number"),
                _INSTRUMENT,
                _DATE,
                _BY,
            ),
        ),
        Requirement(
            key="el.insulation",
            section="verification",
            title="Insulation resistance",
            kind="measurement",
            evidence="evidential",
            per="circuit",
            severity="blocking",
            allow_not_applicable=False,
            authority="NEK 400:2022 §6-61",
            fields=(
                FormField("resistance_mohm", "Insulation resistance", unit="MΩ", kind="number"),
                FormField("test_voltage_v", "Test voltage", unit="V", kind="number"),
                _INSTRUMENT,
                _DATE,
                _BY,
            ),
        ),
        Requirement(
            key="el.loop_impedance",
            section="verification",
            title="Earth fault loop impedance",
            kind="measurement",
            evidence="evidential",
            per="circuit",
            severity="required",
            fields=(
                FormField("impedance_ohm", "Z", unit="Ω", kind="number"),
                _INSTRUMENT,
                _DATE,
            ),
        ),
        Requirement(
            key="el.rcd_trip",
            section="verification",
            title="RCD trip time",
            kind="measurement",
            evidence="evidential",
            per="circuit",
            severity="required",
            applies_when={"has_rcd": True},
            fields=(
                FormField("trip_time_ms", "Trip time", unit="ms", kind="number"),
                FormField("test_current_ma", "Test current", unit="mA", kind="number"),
                _INSTRUMENT,
                _DATE,
            ),
        ),
        Requirement(
            key="el.deviations",
            section="deviations",
            title="Deviations recorded",
            kind="text",
            severity="required",
            description="Any departure from the standard, and the reasoning.",
        ),
        Requirement(
            key="el.user_instructions",
            section="operation",
            title="Instructions for the user",
            kind="text",
            severity="recommended",
        ),
        Requirement(
            key="el.declaration",
            section="handover",
            title="Declaration of conformity signed",
            kind="signature",
            evidence="evidential",
            severity="blocking",
            allow_not_applicable=False,
            authority="FEL §12",
        ),
    ),
)


# ----------------------------------------------------------------------
# 2. EU machinery technical file
# ----------------------------------------------------------------------
EU_MACHINERY = RequirementPack(
    id="eu_machinery_technical_file",
    title="Machinery technical file — 2006/42/EC",
    segment="machinery",
    version="1",
    standards=("2006/42/EC", "EN ISO 12100"),
    description="Technical file for machinery placed on the EU market.",
    requirements=(
        Requirement(
            key="mach.identification",
            section="identification",
            title="Machine identified",
            kind="text",
            per="machine",
            severity="blocking",
            allow_not_applicable=False,
            authority="2006/42/EC Annex VII A(1)(a)",
        ),
        Requirement(
            key="mach.arrangement",
            section="drawings",
            title="General arrangement drawing",
            kind="diagram",
            evidence="evidential",
            per="machine",
            severity="blocking",
            allow_not_applicable=False,
            authority="Annex VII A(1)(a)",
        ),
        Requirement(
            key="mach.control_circuit",
            section="drawings",
            title="Control circuit diagram",
            kind="diagram",
            evidence="evidential",
            per="machine",
            severity="required",
            authority="Annex VII A(1)(a)",
        ),
        Requirement(
            key="mach.risk_assessment",
            section="basis",
            title="Risk assessment",
            kind="text",
            per="machine",
            severity="blocking",
            allow_not_applicable=False,
            authority="Annex I(1)",
            description="Hazards identified, risk estimated, measures applied, residual risk stated.",
        ),
        Requirement(
            key="mach.standards",
            section="standards",
            title="Harmonised standards applied",
            kind="table",
            severity="required",
            fields=(FormField("standard", "Standard"), FormField("clause", "Clause")),
        ),
        Requirement(
            key="mach.safety_validation",
            section="verification",
            title="Safety function validation",
            kind="measurement",
            evidence="evidential",
            per="machine",
            severity="blocking",
            allow_not_applicable=False,
            authority="EN ISO 13849-2",
            fields=(
                FormField("function", "Safety function"),
                FormField("stop_time_ms", "Stop time", unit="ms", kind="number"),
                FormField("result", "Result", kind="choice", choices=("pass", "fail")),
                _DATE,
                _BY,
            ),
        ),
        Requirement(
            key="mach.ce_photo",
            section="installation",
            title="CE marking photographed on the machine",
            kind="photo",
            evidence="evidential",
            per="machine",
            severity="required",
            capture_prompt="Photograph the rating plate so the CE mark and serial number are legible.",
        ),
        Requirement(
            key="mach.instructions",
            section="operation",
            title="Instructions for use",
            kind="text",
            per="machine",
            severity="blocking",
            allow_not_applicable=False,
            authority="Annex I(1.7.4)",
        ),
        Requirement(
            key="mach.declaration",
            section="handover",
            title="EC declaration of conformity",
            kind="signature",
            evidence="evidential",
            per="machine",
            severity="blocking",
            allow_not_applicable=False,
            authority="Annex II(1)(A)",
        ),
    ),
)


# ----------------------------------------------------------------------
# 3. Aquaculture site — shows a third subject kind with no code changes
# ----------------------------------------------------------------------
AQUACULTURE_SITE = RequirementPack(
    id="aquaculture_site",
    title="Aquaculture site documentation",
    segment="aquaculture",
    version="1",
    jurisdiction="NO",
    standards=("NS 9415",),
    requirements=(
        Requirement(
            key="aqua.site_survey",
            section="basis",
            title="Site survey on file",
            kind="file",
            evidence="evidential",
            severity="blocking",
            allow_not_applicable=False,
            authority="NS 9415",
        ),
        Requirement(
            key="aqua.mooring_layout",
            section="drawings",
            title="Mooring layout",
            kind="diagram",
            evidence="evidential",
            severity="blocking",
            allow_not_applicable=False,
        ),
        Requirement(
            key="aqua.component_certificates",
            section="components",
            title="Component certificates",
            kind="file",
            evidence="evidential",
            per="cage",
            severity="required",
        ),
        Requirement(
            key="aqua.net_inspection",
            section="verification",
            title="Net inspection record",
            kind="measurement",
            evidence="evidential",
            per="cage",
            severity="required",
            fields=(
                FormField("mesh_condition", "Mesh condition", kind="choice",
                          choices=("ok", "repair needed", "replace")),
                FormField("depth_m", "Inspection depth", unit="m", kind="number"),
                _DATE,
                _BY,
            ),
        ),
        Requirement(
            key="aqua.mooring_tension",
            section="verification",
            title="Mooring line tension check",
            kind="measurement",
            evidence="evidential",
            per="cage",
            severity="required",
            fields=(
                FormField("tension_kn", "Tension", unit="kN", kind="number"),
                _INSTRUMENT,
                _DATE,
            ),
        ),
        Requirement(
            key="aqua.photo",
            section="installation",
            title="Cage photographed in place",
            kind="photo",
            evidence="evidential",
            per="cage",
            severity="recommended",
            capture_prompt="Photograph the cage collar and mooring attachment from the workboat.",
        ),
    ),
)


# ----------------------------------------------------------------------
# 4. Prototype build log — the non-compliance user
# ----------------------------------------------------------------------
PROTOTYPE_SECTIONS = (
    Section("what", "What it is", 10),
    Section("how", "How it works", 20),
    Section("parts", "What it is made of", 30),
    Section("evidence", "Pictures and measurements", 40),
    Section("next", "What to change next", 50),
)

PROTOTYPE_BUILD_LOG = RequirementPack(
    id="prototype_build_log",
    title="Prototype build log",
    segment="prototype",
    version="1",
    sections=PROTOTYPE_SECTIONS,
    description=(
        "For documenting something you built, with no standard behind it. "
        "Nothing here blocks anything; it is a checklist of things worth writing down "
        "while you still remember them."
    ),
    requirements=(
        Requirement(
            key="proto.summary",
            section="what",
            title="What you built, in a paragraph",
            kind="text",
            severity="recommended",
        ),
        Requirement(
            key="proto.principle",
            section="how",
            title="How it works",
            kind="text",
            severity="recommended",
        ),
        Requirement(
            key="proto.sketch",
            section="how",
            title="Sketch or schematic",
            kind="diagram",
            severity="optional",
        ),
        Requirement(
            key="proto.parts",
            section="parts",
            title="Parts used",
            kind="table",
            severity="recommended",
            fields=(
                FormField("item", "Part"),
                FormField("source", "Where from", required=False),
                FormField("cost", "Cost", required=False),
            ),
        ),
        Requirement(
            key="proto.photo",
            section="evidence",
            title="Photo of the build",
            kind="photo",
            evidence="evidential",
            severity="recommended",
            capture_prompt="Photograph it as built, before you take it apart again.",
        ),
        Requirement(
            key="proto.measurements",
            section="evidence",
            title="Anything you measured",
            kind="measurement",
            evidence="evidential",
            severity="optional",
            fields=(
                FormField("what", "What you measured"),
                FormField("value", "Value", kind="number"),
                FormField("unit", "Unit", required=False),
            ),
        ),
        Requirement(
            key="proto.next",
            section="next",
            title="What you would change",
            kind="text",
            severity="optional",
        ),
    ),
)


PACKS: dict[str, RequirementPack] = {
    p.id: p for p in (NO_ELECTRICAL, EU_MACHINERY, AQUACULTURE_SITE, PROTOTYPE_BUILD_LOG)
}


def get(pack_id: str) -> RequirementPack:
    try:
        return PACKS[pack_id]
    except KeyError as exc:
        raise ValueError(f"unknown pack '{pack_id}'; known: {sorted(PACKS)}") from exc


def for_segment(segment: str) -> list[RequirementPack]:
    return [p for p in PACKS.values() if p.segment == segment]
