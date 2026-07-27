"""OO facade — DiagramEngine over connection_spec + deterministic SVG.

Consumes shared ArtifactEngine for theme colors, fonts, and HTML/PDF export.
Provenance edge colors stay fixed (extracted / user / reference contract).

    eng = DiagramEngine(theme="engineering")
    eng.load_spec(spec)                 # or load_from_artifact / load_fixture
    eng.set_intent("process")           # optional; auto-classified otherwise
    eng.add_node("pump", "Pump", type="actuator")
    eng.add_connection("tank.ut", "pump.inn", label="flow")
    svg = eng.render("svg")
    html = eng.render_html()
"""
from __future__ import annotations

import html as html_lib
import json
import re
from copy import deepcopy
from pathlib import Path

from artifact_engine.core import get_engine
from artifact_engine.render.pdf import PDFRenderer

from . import intent as intent_mod
from .electrical import (
    SLD_FIXTURE,
    WATER_HEATER_240V_FIXTURE,
    WIRING_FIXTURE,
    normalize_electrical_graph,
    render_electrical_diagram,
)
from .graph import normalize_graph
from .mechanical import (
    HYBRID_FIXTURE,
    MECHANICAL_FIXTURE,
    render_hybrid_diagram,
    render_mechanical_diagram,
)
from .piping import PID_FIXTURE, PIPING_FIXTURE, render_piping_diagram
from .render_svg import (
    EXCAVATORBRAIN_FIXTURE,
    RENSEANLEGG_FIXTURE,
    render_block_diagram,
    svg_fingerprint,
)
from .symbols import get_symbol


def _slug(name: str, used: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", (name or "node").lower()).strip("_") or "node"
    cand = base[:32]
    i = 2
    while cand in used:
        cand = f"{base[:28]}_{i}"
        i += 1
    used.add(cand)
    return cand


class DiagramEngine:
    def __init__(
        self,
        theme: str = "engineering",
        orientation: str | None = None,
        diagram_style: str | None = None,
    ):
        self.title = "System Diagram"
        self.kind: str | None = None  # set explicitly or via classify
        self._spec: dict = {"components": [], "connections": [], "status": "draft"}
        self._ask: str = ""
        self._artifact: dict | None = None
        self.theme_name = theme or "engineering"
        self.artifact = get_engine(self.theme_name)
        self.theme = self.artifact.theme
        # None → auto from intent (process=TB, else LR)
        self.orientation = orientation
        self._layout_cache = None
        from artifact_engine.diagram_style import (
            THEME_DIAGRAM_STYLE,
            get_diagram_style,
        )
        self.diagram_style_id = diagram_style or THEME_DIAGRAM_STYLE.get(
            self.theme_name, "engineering_default",
        )
        self._diagram_style = get_diagram_style(self.diagram_style_id)

    def set_diagram_style(self, style_id: str) -> "DiagramEngine":
        from artifact_engine.diagram_style import get_diagram_style
        self.diagram_style_id = style_id or "engineering_default"
        self._diagram_style = get_diagram_style(self.diagram_style_id)
        self._layout_cache = None
        return self

    # ── loaders ──────────────────────────────────────────────────────
    def load_spec(self, spec: dict, *, title: str | None = None) -> "DiagramEngine":
        if not isinstance(spec, dict):
            raise TypeError("spec must be a connection_spec dict")
        self._spec = deepcopy(spec)
        self._spec.setdefault("components", [])
        self._spec.setdefault("connections", [])
        self._layout_cache = None
        if title:
            self.title = title
        elif spec.get("title"):
            self.title = spec["title"]
        return self

    def load_fixture(self, name: str = "excavator") -> "DiagramEngine":
        if name in ("rense", "renseanlegg", "process"):
            self.title = "Renseanlegg — funksjonsdiagram"
            return self.load_spec(RENSEANLEGG_FIXTURE)
        if name in ("electrical_sld", "sld", "single_line"):
            self.title = SLD_FIXTURE.get("title") or "Single-line diagram"
            self.kind = "power"
            return self.load_spec(normalize_electrical_graph(SLD_FIXTURE))
        if name in ("electrical_wiring", "wiring_electrical", "interconnection"):
            self.title = WIRING_FIXTURE.get("title") or "Wiring diagram"
            self.kind = "wiring"
            return self.load_spec(normalize_electrical_graph(WIRING_FIXTURE))
        if name in (
            "water_heater",
            "water_heater_240v",
            "electrical_water_heater",
            "wh_240v",
        ):
            self.title = WATER_HEATER_240V_FIXTURE.get("title") or "Water heater wiring"
            self.kind = "wiring"
            return self.load_spec(normalize_electrical_graph(WATER_HEATER_240V_FIXTURE))
        if name in ("piping", "piping_schematic"):
            self.title = PIPING_FIXTURE.get("title") or "Piping schematic"
            return self.load_spec(normalize_graph(
                PIPING_FIXTURE, default_type="piping", default_domain="piping",
            ))
        if name in ("pid", "p_and_id"):
            self.title = PID_FIXTURE.get("title") or "P&ID-style sketch"
            return self.load_spec(normalize_graph(
                PID_FIXTURE, default_type="pid", default_domain="piping",
            ))
        if name in ("mechanical", "mech", "drive_train"):
            self.title = MECHANICAL_FIXTURE.get("title") or "Mechanical arrangement"
            return self.load_spec(normalize_graph(
                MECHANICAL_FIXTURE, default_type="mechanical", default_domain="mechanical",
            ))
        if name in ("hybrid", "skid", "hybrid_skid"):
            self.title = HYBRID_FIXTURE.get("title") or "Hybrid skid overview"
            return self.load_spec(normalize_graph(
                HYBRID_FIXTURE, default_type="hybrid", default_domain="hybrid",
            ))
        self.title = "ExcavatorBrain — koblingsskjema (blokk)"
        return self.load_spec(EXCAVATORBRAIN_FIXTURE)

    def load_from_artifact(self, artifact: dict, *, bom: list | None = None,
                           ask: str = "") -> "DiagramEngine":
        """Build proposed graph from artifact — does not invent beyond propose_."""
        self._artifact = artifact or {}
        self._ask = ask or ""
        self.title = (
            (artifact or {}).get("title")
            or (artifact or {}).get("name")
            or "System Overview"
        )
        try:
            import connection_diagram as cdiag
            comps = cdiag.collect_components(artifact, bom, None)
            spec = cdiag.propose_connection_spec(
                comps, artifact=artifact)
            self.load_spec(spec)
        except Exception:
            # Fallback: components list on artifact only (no invented edges)
            comps = []
            used: set = set()
            for c in (artifact or {}).get("components") or []:
                if isinstance(c, str):
                    cid = _slug(c, used)
                    comps.append({"id": cid, "label": c, "pins": []})
                elif isinstance(c, dict) and (c.get("id") or c.get("name") or c.get("label")):
                    cid = c.get("id") or _slug(c.get("name") or c.get("label"), used)
                    used.add(cid)
                    comps.append({
                        "id": cid,
                        "label": c.get("label") or c.get("name") or cid,
                        "pins": list(c.get("pins") or []),
                        "role": c.get("type") or c.get("role"),
                    })
            edges = []
            for e in (artifact or {}).get("connections") or []:
                if not isinstance(e, dict):
                    continue
                fr, to = e.get("from"), e.get("to")
                if fr and to:
                    edges.append({
                        "from": fr, "to": to,
                        "label": e.get("label") or "",
                        "provenance": e.get("provenance") or "user",
                    })
            self.load_spec({"components": comps, "connections": edges, "status": "draft"})
        return self

    def set_intent(self, kind: str) -> "DiagramEngine":
        if kind not in intent_mod.KINDS:
            raise ValueError(f"kind must be one of {intent_mod.KINDS}")
        self.kind = kind
        self._layout_cache = None
        return self

    def set_title(self, title: str) -> "DiagramEngine":
        self.title = title or self.title
        return self

    def set_orientation(self, orientation: str) -> "DiagramEngine":
        o = (orientation or "").upper()
        if o not in ("TB", "LR"):
            raise ValueError("orientation must be TB or LR")
        self.orientation = o
        self._layout_cache = None
        return self

    def set_theme(self, theme: str) -> "DiagramEngine":
        self.theme_name = theme or "engineering"
        self.artifact = get_engine(self.theme_name)
        self.theme = self.artifact.theme
        self._layout_cache = None
        return self

    # ── mutate graph (user/code — not silent AI invent) ─────────────
    def add_node(self, name: str, label: str | None = None,
                 type: str = "component", pins: list | None = None) -> "DiagramEngine":
        used = {c["id"] for c in self._spec["components"]}
        cid = name if name and name not in used else _slug(name or label or "node", used)
        if cid not in used:
            used.add(cid)
        self._spec["components"].append({
            "id": cid,
            "label": label or name or cid,
            "type": type,
            "role": type,
            "pins": list(pins or []),
        })
        self._layout_cache = None
        return self

    def add_connection(self, from_node: str, to_node: str, label: str = "",
                       *, provenance: str = "user") -> "DiagramEngine":
        self._spec["connections"].append({
            "from": from_node,
            "to": to_node,
            "label": label or "",
            "provenance": provenance,
        })
        self._layout_cache = None
        return self

    @property
    def nodes(self) -> list:
        return self._spec.get("components") or []

    @property
    def connections(self) -> list:
        return self._spec.get("connections") or []

    @property
    def spec(self) -> dict:
        return self._spec

    def classify(self) -> dict:
        return intent_mod.classify_intent(
            ask=self._ask, title=self.title,
            artifact=self._artifact, spec=self._spec,
        )

    def resolve_kind(self) -> str:
        if self.kind:
            return self.kind
        return self.classify()["kind"]

    def render_svg(self) -> str:
        style = self._diagram_style
        # Canvas editor sets layout_mode=manual (user positions; engine routes edges)
        if (self._spec.get("layout_mode") or "").lower() == "manual":
            from .manual_layout import render_manual_diagram
            profile = self.resolve_render_profile()
            if profile == "block":
                profile = self._spec.get("type") or "piping"
            return render_manual_diagram(
                self._spec, profile=profile, title=self.title, style=style,
            )
        profile = self.resolve_render_profile()
        if profile in ("single_line", "wiring"):
            return render_electrical_diagram(
                self._spec, mode=profile, title=self.title, style=style,
            )
        if profile in ("piping", "pid"):
            return render_piping_diagram(
                self._spec, mode=profile, title=self.title, style=style,
            )
        if profile == "mechanical":
            return render_mechanical_diagram(
                self._spec, mode=profile, title=self.title, style=style,
            )
        if profile == "hybrid":
            return render_hybrid_diagram(self._spec, title=self.title, style=style)
        kind = self.resolve_kind()
        return render_block_diagram(
            self._spec,
            title=self.title,
            kind=kind,
            theme=self.theme,
            orientation=self.orientation,
        )

    def resolve_render_profile(self) -> str:
        """Map spec domain/type → render profile (one engine, many profiles)."""
        t = (self._spec.get("type") or "").lower().replace("-", "_")
        if t in ("sld",):
            t = "single_line"
        if t in ("p_and_id", "pnid"):
            t = "pid"
        if t in ("single_line", "wiring", "piping", "pid", "mechanical", "hybrid"):
            if t == "wiring" and not self._looks_electrical():
                return "block"
            return t
        domain = (self._spec.get("domain") or "").lower()
        if domain == "electrical" or self._looks_electrical():
            return "wiring" if self.resolve_kind() == "wiring" else "single_line"
        if domain == "piping":
            return "piping"
        if domain == "mechanical":
            return "mechanical"
        if domain == "hybrid":
            return "hybrid"
        return "block"

    def render_electrical(self, mode: str = "single_line") -> str:
        """Force electrical SLD or wiring SVG (symbol pack + wire colors)."""
        return render_electrical_diagram(
            self._spec, mode=mode, title=self.title, style=self._diagram_style,
        )

    def render_piping(self, mode: str = "piping") -> str:
        return render_piping_diagram(
            self._spec, mode=mode, title=self.title, style=self._diagram_style,
        )

    def render_mechanical(self, mode: str = "mechanical") -> str:
        return render_mechanical_diagram(
            self._spec, mode=mode, title=self.title, style=self._diagram_style,
        )

    def render_hybrid(self) -> str:
        return render_hybrid_diagram(
            self._spec, title=self.title, style=self._diagram_style,
        )

    def _looks_electrical(self) -> bool:
        if (self._spec.get("domain") or "").lower() == "electrical":
            return True
        comps = [c for c in (self._spec.get("components") or []) if isinstance(c, dict)]
        if not comps:
            return False
        if all((c.get("domain") or "").lower() == "electrical" for c in comps):
            return True
        return any(
            (c.get("domain") or "").lower() == "electrical"
            or (get_symbol(c.get("symbol") or c.get("type") or "") or {}).get("domain")
            == "electrical"
            for c in comps
        )

    def render_html(self) -> str:
        """Wrap SVG in a themed HTML page (shared ArtifactEngine colors)."""
        t = self.theme
        svg = self.render_svg()
        title = html_lib.escape(self.title)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
body {{
  margin: 0;
  font-family: {t.font_sans};
  background: {t.page_chrome};
  color: {t.text_color};
}}
.diagram-page {{
  max-width: 960px;
  margin: 24px auto;
  padding: 16px;
  background: {t.background};
}}
.diagram-page svg {{ width: 100%; height: auto; display: block; }}
</style>
</head>
<body>
<div class="diagram-page" data-foldok="diagram" data-theme="{html_lib.escape(t.name)}">
{svg}
</div>
</body>
</html>"""

    def render_pdf(self, path: str) -> str:
        """Export via shared PDF pipeline (WeasyPrint → Playwright)."""
        html = self.render_html()
        out = PDFRenderer(theme_name=self.theme_name).render_html_string(html, path)
        return str(out)

    def render(self, format: str = "svg") -> str:
        kind = self.resolve_kind()
        if format == "json":
            return json.dumps({
                "title": self.title,
                "kind": kind,
                "theme": self.theme_name,
                "components": self.nodes,
                "connections": self.connections,
            }, indent=2, ensure_ascii=False)
        if format == "markdown":
            return self._to_markdown(kind)
        if format == "html":
            return self.render_html()
        # svg default — real renderer, provenance colors, connections drawn
        return self.render_svg()

    def fingerprint(self) -> str:
        return svg_fingerprint(self.render("svg"))

    def _to_markdown(self, kind: str) -> str:
        lines = [f"## {self.title}", "", f"_layout: {kind}_", ""]
        for n in self.nodes:
            lines.append(f"- **{n.get('label') or n.get('id')}** (`{n.get('id')}`)")
        if self.connections:
            lines.append("")
            lines.append("### Connections")
            for e in self.connections:
                lines.append(
                    f"- `{e.get('from')}` → `{e.get('to')}` "
                    f"{e.get('label') or ''} [{e.get('provenance') or '—'}]"
                )
        return "\n".join(lines)
