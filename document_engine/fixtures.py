"""Demo datasheet fixture — synthetic product (no real customer brands)."""

DATASHEET_FIXTURE = {
    "name": "product_datasheet",
    "title": "{{product_name}}",
    "type": "datasheet",
    "document_species": "datasheet",
    "brand": {
        "name": "DemoTek",
        "primary_color": "#16181D",
        "font": "Arial, Helvetica, sans-serif",
    },
    "pages": [
        {
            "type": "cover",
            "layout": "hero_split",
            "title": "{{product_name}}",
            "tagline": "{{tagline}}",
            "date": "{{doc_date}}",
            "bullet_points": [
                "{{bullet_1}}",
                "{{bullet_2}}",
                "{{bullet_3}}",
            ],
        },
        {
            "type": "overview",
            "layout": "component_grid",
            "title": "SYSTEM OVERVIEW",
            "components": [
                {
                    "name": "{{comp_1_name}}",
                    "description": "{{comp_1_desc}}",
                },
                {
                    "name": "{{comp_2_name}}",
                    "description": "{{comp_2_desc}}",
                },
                {
                    "name": "{{comp_3_name}}",
                    "description": "{{comp_3_desc}}",
                },
                {
                    "name": "{{comp_4_name}}",
                    "description": "{{comp_4_desc}}",
                },
            ],
        },
        {
            "type": "specifications",
            "layout": "comparison_table",
            "title": "SPECIFICATIONS",
            "table": {
                "headers": ["System", "S-32", "S-63", "S-90", "Comments"],
                "rows": [
                    ["Pipe size", "32 mm", "63 mm", "90 mm", "{{pipe_note}}"],
                    ["Max feed rate", "{{rate_32}}", "{{rate_63}}", "{{rate_90}}",
                     "Depends on transport distance"],
                    ["Max lines", "{{lines_32}}", "{{lines_63}}", "{{lines_90}}", ""],
                ],
                "footnotes": [
                    "* Demo values — replace from project facts.",
                ],
            },
        },
    ],
}

# Filled demo facts for self-test (not invented at runtime — fixture data)
DEMO_FACTS = {
    "product_name": "Demo CCS Feed System",
    "tagline": "Reliable feed transport for aquaculture demos",
    "doc_date": "2026-07-22",
    "bullet_1": "Handles multiple feed lines in parallel",
    "bullet_2": "Central interface for tank groups",
    "bullet_3": "Gentle handling for pellet integrity",
    "comp_1_name": "FEED BLOWERS",
    "comp_1_desc": "Air supply for transport distances in the demo layout.",
    "comp_2_name": "FEED DOSERS",
    "comp_2_desc": "Dosing modules with metered output.",
    "comp_3_name": "AIR COOLER",
    "comp_3_desc": "Lowers air temperature on long runs.",
    "comp_4_name": "SELECTOR VALVES",
    "comp_4_desc": "Line switching between destinations.",
    "pipe_note": "Imperial sizes available on request",
    "rate_32": "—",
    "rate_63": "—",
    "rate_90": "—",
    "lines_32": "8",
    "lines_63": "16",
    "lines_90": "24",
}
