"""Synthetic product-sheet / user-manual ASTs — no real customer brands."""
from artifact_engine.model.blocks import (
    CalloutBox,
    EngineeringTable,
    FeatureCard,
    FeatureGrid,
    HeroBlock,
    ParagraphBlock,
    ParameterGrid,
    ParameterItem,
    Procedure,
    ProcedureStep,
    RevisionEntry,
    RevisionHistory,
    SpecRow,
    SpecificationTable,
    TableOfContentsBlock,
    WarningBox,
)
from artifact_engine.model.document import Document
from artifact_engine.model.section import Section


def demo_ccs_document() -> Document:
    return Document(
        title="Demo CCS Feed System",
        document_type="product_sheet",
        language="en",
        theme="datasheet",
        hero=HeroBlock(
            headline="Demo CCS Feed System",
            summary="Reliable feed transport for aquaculture demos",
            bullets=[
                "Handles multiple feed lines in parallel",
                "Central interface for tank groups",
                "Gentle handling for pellet integrity",
            ],
        ),
        sections=[
            Section(
                title="System Overview",
                blocks=[
                    FeatureGrid(
                        columns=2,
                        items=[
                            FeatureCard(
                                "Feed Blowers",
                                "Air supply for transport distances in the demo layout.",
                            ),
                            FeatureCard(
                                "Feed Dosers",
                                "Dosing modules with metered output.",
                            ),
                            FeatureCard(
                                "Air Cooler",
                                "Lowers air temperature on long runs.",
                            ),
                            FeatureCard(
                                "Selector Valves",
                                "Line switching between destinations.",
                            ),
                        ],
                    ),
                ],
            ),
            Section(
                title="Specifications",
                page_break_before=True,
                blocks=[
                    SpecificationTable(
                        headers=["System", "S-32", "S-63", "S-90", "Comments"],
                        rows=[
                            SpecRow(
                                "Pipe size",
                                ["32 mm", "63 mm", "90 mm"],
                                note="Imperial sizes on request",
                            ),
                            SpecRow(
                                "Max lines",
                                ["8", "16", "24"],
                                note="",
                            ),
                            SpecRow(
                                "Max feed rate*",
                                ["—", "—", "—"],
                                note="Depends on transport distance",
                            ),
                        ],
                        footnotes=[
                            "* Demo placeholders — replace from project facts.",
                        ],
                    ),
                ],
            ),
        ],
        metadata={"origin": "fixture", "brand": "DemoTek"},
    )


def demo_rotor_spreader_manual() -> Document:
    """
    User-manual shaped AST (cover → legal → symbols → summary → glossary →
    TOC → product → specs → assembly → revision).

    Synthetic DemoTek product — not a customer brand.
    theme \"manual\" (\"akva\" aliases to the same DesignSystem).
    """
    return Document(
        title="Rotor Spreader Hex MKII — User Manual",
        document_type="user_manual",
        language="en",
        theme="manual",
        hero=HeroBlock(
            headline="Rotor Spreader Hex MKII",
            summary="User manual for the DemoTek floating feed spreader.",
            bullets=[
                "HDPE body with stainless fasteners",
                "90 mm PE pipe connection",
                "Approx. 35 kg assembled weight",
            ],
        ),
        sections=[
            Section(
                title="Legal",
                blocks=[
                    ParagraphBlock(
                        text="This manual is for DemoTek training use only. "
                        "Follow local regulations and site HSE rules.",
                    ),
                    CalloutBox(
                        variant="important",
                        title="Liability",
                        text="Incorrect installation or operation may void warranty.",
                    ),
                ],
            ),
            Section(
                title="Symbols",
                blocks=[
                    CalloutBox(
                        variant="warning",
                        title="Warning",
                        text="Risk of injury if ignored.",
                    ),
                    CalloutBox(
                        variant="requirement",
                        title="Requirement",
                        text="Mandatory action for safe operation.",
                    ),
                    CalloutBox(
                        variant="note",
                        title="Note",
                        text="Useful information for the operator.",
                    ),
                ],
            ),
            Section(
                title="Summary",
                blocks=[
                    ParagraphBlock(
                        text="The Rotor Spreader Hex MKII distributes pellets "
                        "evenly across the cage surface using a rotating head.",
                    ),
                    EngineeringTable(
                        headers=["No", "Part"],
                        rows=[
                            ["1", "Spreader head"],
                            ["2", "Drive unit"],
                            ["3", "Float body"],
                            ["4", "PE pipe adapter 90 mm"],
                        ],
                        caption="Illustration 1: Main components",
                    ),
                ],
            ),
            Section(
                title="Abbreviations and Glossary",
                blocks=[
                    ParameterGrid(
                        title="Terms",
                        columns=2,
                        items=[
                            ParameterItem("HDPE", "High-density polyethylene"),
                            ParameterItem("POM", "Polyoxymethylene"),
                            ParameterItem("HSE", "Health, safety and environment"),
                            ParameterItem("PE", "Polyethylene"),
                        ],
                    ),
                ],
            ),
            Section(
                title="Table of Contents",
                blocks=[TableOfContentsBlock()],
            ),
            Section(
                title="1 Product Description",
                page_break_before=True,
                blocks=[
                    ParagraphBlock(
                        text="The unit floats at the cage and spins under air/feed flow. "
                        "Main parts are listed in Table 1.",
                    ),
                    EngineeringTable(
                        headers=["No", "Part name"],
                        rows=[
                            ["1", "Spreader head"],
                            ["2", "Drive unit"],
                            ["3", "Float body"],
                        ],
                        caption="Table 1: Part names",
                    ),
                ],
            ),
            Section(
                title="2.1 Technical Specifications",
                blocks=[
                    EngineeringTable(
                        headers=["Parameter", "Specification"],
                        rows=[
                            ["Materials", "HDPE / Stainless steel / Aluminum / POM / PU-foam"],
                            ["Weight", "Approximately 35 kg"],
                            ["PE Pipe dimension", "90 mm"],
                            ["Max pellet size*", "Up to 12 mm"],
                        ],
                        footnotes=["* Depending on feed system and pellet size"],
                    ),
                ],
            ),
            Section(
                title="3 Assembly",
                page_break_before=True,
                blocks=[
                    Procedure(
                        title="Assemble the Rotor Spreader Hex",
                        steps=[
                            ProcedureStep(
                                1, "Unpack",
                                "Check that all parts in Table 1 are present.",
                            ),
                            ProcedureStep(
                                2, "Fit adapter",
                                "Mount the 90 mm PE pipe adapter to the float body.",
                            ),
                            ProcedureStep(
                                3, "Mount head",
                                "Attach the spreader head to the drive unit.",
                                warning="Do not operate without the float body secured.",
                            ),
                        ],
                    ),
                    WarningBox(
                        title="Warning",
                        text="Never stand under a suspended spreader during lifting.",
                    ),
                ],
            ),
            Section(
                title="9 Revision History",
                blocks=[
                    RevisionHistory(entries=[
                        RevisionEntry("A", "2025-09-01", "First issue", "DemoTek"),
                        RevisionEntry("B", "2026-03-15", "Specs updated", "DemoTek"),
                    ]),
                ],
            ),
        ],
        metadata={"origin": "fixture", "brand": "DemoTek", "species": "user_manual"},
    )
