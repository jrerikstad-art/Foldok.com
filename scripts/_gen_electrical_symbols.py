"""One-shot generator: IEC-style electrical symbol pack for DiagramEngine."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "diagram_engine" / "symbols" / "electrical"

# Foldok originals — IEC-oriented line symbols for deterministic SVG assembly.
# Inspired by public-domain conventions (not copies of proprietary CAD libraries).
SYMBOLS: dict[str, dict] = {
    "breaker": {
        "label": "Circuit breaker",
        "ports": [("line", "Line", "top"), ("load", "Load", "bottom")],
        "body": """
  <line x1="32" y1="4" x2="32" y2="16" stroke="#16181D" stroke-width="1.5"/>
  <rect x="24" y="16" width="16" height="16" fill="#fff" stroke="#16181D" stroke-width="1.5"/>
  <line x1="28" y1="20" x2="36" y2="28" stroke="#16181D" stroke-width="1.5"/>
  <line x1="32" y1="32" x2="32" y2="44" stroke="#16181D" stroke-width="1.5"/>
  <text x="32" y="47" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="6">Q</text>
""",
    },
    "mcb": {
        "label": "Miniature circuit breaker",
        "ports": [("line", "Line", "top"), ("load", "Load", "bottom")],
        "body": """
  <line x1="32" y1="4" x2="32" y2="14" stroke="#16181D" stroke-width="1.5"/>
  <rect x="22" y="14" width="20" height="20" rx="2" fill="#fff" stroke="#16181D" stroke-width="1.5"/>
  <path d="M28 28 L32 18 L36 28" fill="none" stroke="#16181D" stroke-width="1.5"/>
  <line x1="32" y1="34" x2="32" y2="44" stroke="#16181D" stroke-width="1.5"/>
  <text x="32" y="47" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="6">MCB</text>
""",
    },
    "rcd": {
        "label": "RCD / RCCB",
        "ports": [("line", "Line", "top"), ("load", "Load", "bottom")],
        "body": """
  <line x1="32" y1="4" x2="32" y2="12" stroke="#16181D" stroke-width="1.5"/>
  <rect x="18" y="12" width="28" height="22" fill="#fff" stroke="#16181D" stroke-width="1.5"/>
  <circle cx="32" cy="23" r="6" fill="none" stroke="#16181D" stroke-width="1.5"/>
  <text x="32" y="26" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="5">IΔn</text>
  <line x1="32" y1="34" x2="32" y2="44" stroke="#16181D" stroke-width="1.5"/>
  <text x="32" y="47" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="6">RCD</text>
""",
    },
    "fuse": {
        "label": "Fuse",
        "ports": [("line", "Line", "top"), ("load", "Load", "bottom")],
        "body": """
  <line x1="32" y1="4" x2="32" y2="14" stroke="#16181D" stroke-width="1.5"/>
  <rect x="26" y="14" width="12" height="20" fill="#fff" stroke="#16181D" stroke-width="1.5"/>
  <line x1="32" y1="16" x2="32" y2="32" stroke="#16181D" stroke-width="1.2"/>
  <line x1="32" y1="34" x2="32" y2="44" stroke="#16181D" stroke-width="1.5"/>
  <text x="32" y="47" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="6">F</text>
""",
    },
    "contactor": {
        "label": "Contactor",
        "ports": [
            ("line", "Line", "top"),
            ("load", "Load", "bottom"),
            ("coil_a", "A1", "left"),
            ("coil_b", "A2", "right"),
        ],
        "body": """
  <line x1="32" y1="4" x2="32" y2="16" stroke="#16181D" stroke-width="1.5"/>
  <circle cx="32" cy="24" r="10" fill="#fff" stroke="#16181D" stroke-width="1.5"/>
  <line x1="26" y1="20" x2="38" y2="28" stroke="#16181D" stroke-width="1.5"/>
  <line x1="32" y1="34" x2="32" y2="44" stroke="#16181D" stroke-width="1.5"/>
  <line x1="8" y1="24" x2="22" y2="24" stroke="#16181D" stroke-width="1.2"/>
  <line x1="42" y1="24" x2="56" y2="24" stroke="#16181D" stroke-width="1.2"/>
  <text x="32" y="47" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="6">KM</text>
""",
    },
    "motor": {
        "label": "AC motor",
        "ports": [
            ("u", "U", "top"),
            ("v", "V", "left"),
            ("w", "W", "right"),
            ("pe", "PE", "bottom"),
        ],
        "body": """
  <circle cx="32" cy="24" r="14" fill="#fff" stroke="#16181D" stroke-width="1.5"/>
  <text x="32" y="28" text-anchor="middle" font-family="IBM Plex Sans,sans-serif" font-size="14" font-weight="600">M</text>
  <line x1="32" y1="4" x2="32" y2="10" stroke="#16181D" stroke-width="1.2"/>
  <line x1="8" y1="24" x2="18" y2="24" stroke="#16181D" stroke-width="1.2"/>
  <line x1="46" y1="24" x2="56" y2="24" stroke="#16181D" stroke-width="1.2"/>
  <line x1="32" y1="38" x2="32" y2="44" stroke="#16181D" stroke-width="1.2"/>
""",
    },
    "transformer": {
        "label": "Transformer",
        "ports": [
            ("pri_a", "H1", "top"),
            ("pri_b", "H2", "top"),
            ("sec_a", "X1", "bottom"),
            ("sec_b", "X2", "bottom"),
        ],
        "body": """
  <circle cx="24" cy="24" r="10" fill="none" stroke="#16181D" stroke-width="1.5"/>
  <circle cx="40" cy="24" r="10" fill="none" stroke="#16181D" stroke-width="1.5"/>
  <line x1="24" y1="4" x2="24" y2="14" stroke="#16181D" stroke-width="1.2"/>
  <line x1="40" y1="4" x2="40" y2="14" stroke="#16181D" stroke-width="1.2"/>
  <line x1="24" y1="34" x2="24" y2="44" stroke="#16181D" stroke-width="1.2"/>
  <line x1="40" y1="34" x2="40" y2="44" stroke="#16181D" stroke-width="1.2"/>
  <text x="32" y="47" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="6">T</text>
""",
    },
    "terminal": {
        "label": "Terminal",
        "ports": [("a", "A", "left"), ("b", "B", "right")],
        "body": """
  <circle cx="32" cy="24" r="6" fill="#fff" stroke="#16181D" stroke-width="1.5"/>
  <line x1="8" y1="24" x2="26" y2="24" stroke="#16181D" stroke-width="1.5"/>
  <line x1="38" y1="24" x2="56" y2="24" stroke="#16181D" stroke-width="1.5"/>
""",
    },
    "terminal_strip": {
        "label": "Terminal strip",
        "ports": [
            ("t1", "1", "left"),
            ("t2", "2", "left"),
            ("t3", "3", "left"),
            ("t4", "4", "right"),
            ("t5", "5", "right"),
            ("t6", "6", "right"),
        ],
        "body": """
  <rect x="16" y="6" width="32" height="36" fill="#fff" stroke="#16181D" stroke-width="1.5"/>
  <line x1="16" y1="18" x2="48" y2="18" stroke="#16181D" stroke-width="1"/>
  <line x1="16" y1="30" x2="48" y2="30" stroke="#16181D" stroke-width="1"/>
  <circle cx="24" cy="12" r="2.5" fill="#16181D"/>
  <circle cx="40" cy="12" r="2.5" fill="#16181D"/>
  <circle cx="24" cy="24" r="2.5" fill="#16181D"/>
  <circle cx="40" cy="24" r="2.5" fill="#16181D"/>
  <circle cx="24" cy="36" r="2.5" fill="#16181D"/>
  <circle cx="40" cy="36" r="2.5" fill="#16181D"/>
""",
    },
    "busbar": {
        "label": "Busbar",
        "ports": [("in", "In", "left"), ("out", "Out", "right"), ("tap", "Tap", "bottom")],
        "body": """
  <rect x="6" y="18" width="52" height="12" fill="#16181D" stroke="#16181D"/>
  <line x1="32" y1="30" x2="32" y2="42" stroke="#16181D" stroke-width="1.5"/>
""",
    },
    "socket": {
        "label": "Socket outlet",
        "ports": [("l", "L", "top"), ("n", "N", "top"), ("pe", "PE", "bottom")],
        "body": """
  <circle cx="32" cy="24" r="14" fill="#fff" stroke="#16181D" stroke-width="1.5"/>
  <circle cx="26" cy="22" r="2.5" fill="#16181D"/>
  <circle cx="38" cy="22" r="2.5" fill="#16181D"/>
  <path d="M24 30 Q32 36 40 30" fill="none" stroke="#16181D" stroke-width="1.5"/>
  <line x1="26" y1="8" x2="26" y2="12" stroke="#16181D" stroke-width="1.2"/>
  <line x1="38" y1="8" x2="38" y2="12" stroke="#16181D" stroke-width="1.2"/>
  <line x1="32" y1="38" x2="32" y2="44" stroke="#16181D" stroke-width="1.2"/>
""",
    },
    "switch": {
        "label": "Switch",
        "ports": [("line", "Line", "top"), ("load", "Load", "bottom")],
        "body": """
  <line x1="32" y1="4" x2="32" y2="18" stroke="#16181D" stroke-width="1.5"/>
  <circle cx="32" cy="20" r="2.5" fill="#16181D"/>
  <line x1="32" y1="22" x2="44" y2="32" stroke="#16181D" stroke-width="1.5"/>
  <circle cx="32" cy="34" r="2.5" fill="#16181D"/>
  <line x1="32" y1="36" x2="32" y2="44" stroke="#16181D" stroke-width="1.5"/>
""",
    },
    "lamp": {
        "label": "Lamp / luminaire",
        "ports": [("l", "L", "top"), ("n", "N", "top")],
        "body": """
  <circle cx="32" cy="24" r="12" fill="#fff" stroke="#16181D" stroke-width="1.5"/>
  <line x1="24" y1="16" x2="40" y2="32" stroke="#16181D" stroke-width="1.2"/>
  <line x1="40" y1="16" x2="24" y2="32" stroke="#16181D" stroke-width="1.2"/>
  <line x1="26" y1="6" x2="26" y2="12" stroke="#16181D" stroke-width="1.2"/>
  <line x1="38" y1="6" x2="38" y2="12" stroke="#16181D" stroke-width="1.2"/>
""",
    },
    "earth": {
        "label": "Protective earth",
        "ports": [("pe", "PE", "top")],
        "body": """
  <line x1="32" y1="8" x2="32" y2="24" stroke="#16181D" stroke-width="1.5"/>
  <line x1="18" y1="24" x2="46" y2="24" stroke="#16181D" stroke-width="1.5"/>
  <line x1="22" y1="30" x2="42" y2="30" stroke="#16181D" stroke-width="1.5"/>
  <line x1="26" y1="36" x2="38" y2="36" stroke="#16181D" stroke-width="1.5"/>
""",
    },
    "meter": {
        "label": "Energy meter",
        "ports": [("in", "In", "top"), ("out", "Out", "bottom")],
        "body": """
  <rect x="16" y="10" width="32" height="28" fill="#fff" stroke="#16181D" stroke-width="1.5"/>
  <text x="32" y="28" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="10">kWh</text>
  <line x1="32" y1="4" x2="32" y2="10" stroke="#16181D" stroke-width="1.2"/>
  <line x1="32" y1="38" x2="32" y2="44" stroke="#16181D" stroke-width="1.2"/>
""",
    },
    "distribution_board": {
        "label": "Distribution board",
        "ports": [
            ("in", "Supply", "top"),
            ("c1", "C1", "bottom"),
            ("c2", "C2", "bottom"),
            ("c3", "C3", "bottom"),
        ],
        "body": """
  <rect x="10" y="8" width="44" height="32" fill="#fff" stroke="#16181D" stroke-width="1.5"/>
  <line x1="18" y1="16" x2="46" y2="16" stroke="#16181D" stroke-width="1"/>
  <line x1="18" y1="24" x2="46" y2="24" stroke="#16181D" stroke-width="1"/>
  <line x1="18" y1="32" x2="46" y2="32" stroke="#16181D" stroke-width="1"/>
  <line x1="32" y1="4" x2="32" y2="8" stroke="#16181D" stroke-width="1.2"/>
  <line x1="20" y1="40" x2="20" y2="44" stroke="#16181D" stroke-width="1.2"/>
  <line x1="32" y1="40" x2="32" y2="44" stroke="#16181D" stroke-width="1.2"/>
  <line x1="44" y1="40" x2="44" y2="44" stroke="#16181D" stroke-width="1.2"/>
  <text x="32" y="47" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="5">DB</text>
""",
    },
    "disconnect": {
        "label": "Disconnector / isolator",
        "ports": [("line", "Line", "top"), ("load", "Load", "bottom")],
        "body": """
  <line x1="32" y1="4" x2="32" y2="16" stroke="#16181D" stroke-width="1.5"/>
  <circle cx="32" cy="18" r="2.5" fill="#16181D"/>
  <line x1="32" y1="20" x2="42" y2="30" stroke="#16181D" stroke-width="1.5"/>
  <line x1="28" y1="32" x2="36" y2="32" stroke="#16181D" stroke-width="1.5"/>
  <line x1="32" y1="32" x2="32" y2="44" stroke="#16181D" stroke-width="1.5"/>
""",
    },
    "overload_relay": {
        "label": "Thermal overload relay",
        "ports": [("in", "In", "top"), ("out", "Out", "bottom")],
        "body": """
  <line x1="32" y1="4" x2="32" y2="14" stroke="#16181D" stroke-width="1.5"/>
  <rect x="22" y="14" width="20" height="20" fill="#fff" stroke="#16181D" stroke-width="1.5"/>
  <path d="M28 28 Q32 18 36 28" fill="none" stroke="#16181D" stroke-width="1.5"/>
  <line x1="32" y1="34" x2="32" y2="44" stroke="#16181D" stroke-width="1.5"/>
  <text x="32" y="47" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="5">F1</text>
""",
    },
    "generator": {
        "label": "Generator",
        "ports": [
            ("l1", "L1", "top"),
            ("l2", "L2", "top"),
            ("l3", "L3", "top"),
            ("n", "N", "bottom"),
            ("pe", "PE", "bottom"),
        ],
        "body": """
  <circle cx="32" cy="24" r="14" fill="#fff" stroke="#16181D" stroke-width="1.5"/>
  <text x="32" y="28" text-anchor="middle" font-family="IBM Plex Sans,sans-serif" font-size="14" font-weight="600">G</text>
  <line x1="22" y1="6" x2="22" y2="12" stroke="#16181D" stroke-width="1.2"/>
  <line x1="32" y1="4" x2="32" y2="10" stroke="#16181D" stroke-width="1.2"/>
  <line x1="42" y1="6" x2="42" y2="12" stroke="#16181D" stroke-width="1.2"/>
  <line x1="26" y1="38" x2="26" y2="44" stroke="#16181D" stroke-width="1.2"/>
  <line x1="38" y1="38" x2="38" y2="44" stroke="#16181D" stroke-width="1.2"/>
""",
    },
    "battery": {
        "label": "Battery",
        "ports": [("pos", "+", "top"), ("neg", "−", "bottom")],
        "body": """
  <line x1="20" y1="18" x2="44" y2="18" stroke="#16181D" stroke-width="2.5"/>
  <line x1="24" y1="26" x2="40" y2="26" stroke="#16181D" stroke-width="1.5"/>
  <line x1="20" y1="34" x2="44" y2="34" stroke="#16181D" stroke-width="2.5"/>
  <line x1="32" y1="8" x2="32" y2="18" stroke="#16181D" stroke-width="1.2"/>
  <line x1="32" y1="34" x2="32" y2="44" stroke="#16181D" stroke-width="1.2"/>
  <text x="48" y="20" font-family="IBM Plex Mono,monospace" font-size="8">+</text>
""",
    },
    "junction": {
        "label": "Wire junction",
        "ports": [
            ("a", "A", "left"),
            ("b", "B", "right"),
            ("c", "C", "top"),
            ("d", "D", "bottom"),
        ],
        "body": """
  <circle cx="32" cy="24" r="3.5" fill="#16181D"/>
  <line x1="8" y1="24" x2="28" y2="24" stroke="#16181D" stroke-width="1.5"/>
  <line x1="36" y1="24" x2="56" y2="24" stroke="#16181D" stroke-width="1.5"/>
  <line x1="32" y1="8" x2="32" y2="20" stroke="#16181D" stroke-width="1.5"/>
  <line x1="32" y1="28" x2="32" y2="40" stroke="#16181D" stroke-width="1.5"/>
""",
    },
}


def _svg(body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 48" '
        'width="64" height="48">\n'
        f"{body.rstrip()}\n"
        "</svg>\n"
    )


def _yaml(sid: str, label: str, ports: list[tuple[str, str, str]]) -> str:
    orders = {"left": 0, "right": 0, "top": 0, "bottom": 0}
    lines = [
        f"id: {sid}",
        "domain: electrical",
        f"label: {label}",
        f"svg: {sid}.svg",
        "default_orientation: 0",
        "standard_hint: IEC-style",
        "ports:",
    ]
    for pid, name, side in ports:
        orders[side] += 1
        lines.extend(
            [
                f"- id: {pid}",
                f"  name: {name}",
                f"  side: {side}",
                "  kind: electrical",
                "  allowed_media:",
                "  - wire",
                f"  order: {orders[side]}",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for sid, meta in SYMBOLS.items():
        (ROOT / f"{sid}.svg").write_text(_svg(meta["body"]), encoding="utf-8")
        (ROOT / f"{sid}.yaml").write_text(
            _yaml(sid, meta["label"], meta["ports"]), encoding="utf-8"
        )
    print(f"Wrote {len(SYMBOLS)} electrical symbols -> {ROOT}")


if __name__ == "__main__":
    main()
