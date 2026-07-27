"""WORKORDER_0.24 — Connection spec + deterministic block-diagram SVG.

Lane 2 (DIAGRAM_SPEC) minimally: AI/code proposes the CONNECTION GRAPH;
user confirms; CODE renders SVG. Never circuit schematics.
"""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy

BLOCK_TYPE = "connection_spec"

PROV_EXTRACTED = "extracted"
PROV_USER = "verified_by_user"
PROV_REFERENCE = "reference"

DEMO_EUR = 0.02

STANDARD_COMPONENTS = {
    "raspberry_pi_5": {
        "match": re.compile(r"raspberry\s*pi\s*5|pi\s*5|rpi\s*5", re.I),
        "id": "pi5",
        "label": "Raspberry Pi 5",
        "role": "logic",
        "pins": ["GPIO2/SDA", "GPIO3/SCL", "5V", "GND", "PWM0"],
    },
    "pca9685": {
        "match": re.compile(r"pca9685|pwm\s*driver|servo\s*driver", re.I),
        "id": "pca9685",
        "label": "PCA9685",
        "role": "peripheral",
        "pins": ["SDA", "SCL", "VCC", "GND", "PWM0", "PWM1"],
    },
    "buck_5v": {
        "match": re.compile(r"d24v50f5|buck|5\s*v\s*converter|pololu", re.I),
        "id": "buck5v",
        "label": "5V buck converter",
        "role": "converter",
        "pins": ["VIN", "VOUT", "GND"],
    },
    "battery": {
        "match": re.compile(r"battery|batteri|lipo|li-?ion|power\s*bank", re.I),
        "id": "batt",
        "label": "Battery / supply",
        "role": "power",
        "pins": ["V+", "GND"],
    },
    "servo": {
        "match": re.compile(r"servo|actuator|huina|motor", re.I),
        "id": "servo",
        "label": "Servo / actuator",
        "role": "actuator",
        "pins": ["PWM", "V+", "GND"],
    },
    "imu": {
        "match": re.compile(r"imu|mpu6050|bno055|gyro", re.I),
        "id": "imu",
        "label": "IMU",
        "role": "peripheral",
        "pins": ["SDA", "SCL", "VCC", "GND"],
    },
    "camera": {
        "match": re.compile(r"camera|kamera|csi", re.I),
        "id": "cam",
        "label": "Camera",
        "role": "peripheral",
        "pins": ["CSI", "GND"],
    },
}

STANDARD_EDGES = [
    ("batt", "V+", "buck5v", "VIN", "VIN"),
    ("batt", "GND", "buck5v", "GND", "GND"),
    ("buck5v", "VOUT", "pi5", "5V", "5V"),
    ("buck5v", "GND", "pi5", "GND", "GND"),
    ("pi5", "GPIO2/SDA", "pca9685", "SDA", "I2C"),
    ("pi5", "GPIO3/SCL", "pca9685", "SCL", "I2C"),
    ("pi5", "5V", "pca9685", "VCC", "5V"),
    ("pi5", "GND", "pca9685", "GND", "GND"),
    ("pca9685", "PWM0", "servo", "PWM", "PWM"),
    ("buck5v", "VOUT", "servo", "V+", "5V"),
    ("buck5v", "GND", "servo", "GND", "GND"),
    ("pi5", "GPIO2/SDA", "imu", "SDA", "I2C"),
    ("pi5", "GPIO3/SCL", "imu", "SCL", "I2C"),
    ("pi5", "5V", "imu", "VCC", "5V"),
    ("pi5", "GND", "imu", "GND", "GND"),
]

ROLE_ORDER = ("power", "converter", "logic", "peripheral", "actuator", "other")

CIRCUIT_ASK = re.compile(
    r"\b(circuit\s+schematic|kretsskjema|schematic\s+symbols?|"
    r"netlist|spice)\b",
    re.I,
)

BLOCK_ASK = re.compile(
    r"\b(schematic|blokkskjema|block\s*diagram|tilkobling|"
    r"funksjonsdiagram|prosess(?:flyt|diagram)|flow\s*diagram|"
    r"how\s+these\s+components\s+should\s+be\s+connected|"
    r"how\s+(?:the\s+)?components?\s+(?:are|should\s+be)\s+connected|"
    r"connection\s+(?:spec|diagram|drawing)|wiring\s+diagram|"
    r"lag\s+(?:et\s+)?(?:tilkobling|funksjonsdiagram|blokkskjema))\b",
    re.I,
)

PROCESS_ASK = re.compile(
    r"\b(funksjonsdiagram|prosess(?:flyt|diagram)|renseanlegg|"
    r"process\s+flow|flow\s*diagram)\b",
    re.I,
)


def is_circuit_schematic_ask(msg: str) -> bool:
    return bool(CIRCUIT_ASK.search(msg or ""))


def is_connection_diagram_ask(msg: str) -> bool:
    return bool(BLOCK_ASK.search(msg or "") or CIRCUIT_ASK.search(msg or ""))


def circuit_boundary_reply(lang: str = "no") -> str:
    if lang == "en":
        return (
            "I produce block diagrams with connections and pins — not circuit "
            "schematics (no IEC symbols, nets, or component values). "
            "Want the block diagram?"
        )
    return (
        "Jeg lager blokkskjema med tilkoblinger og pinner — ikke kretsskjema. "
        "Vil du ha blokkskjemaet?"
    )


def _slug(label: str, used: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "", (label or "comp").lower())[:12] or "comp"
    cand = base
    n = 2
    while cand in used:
        cand = f"{base}{n}"
        n += 1
    used.add(cand)
    return cand


def match_standard(name: str) -> dict | None:
    for key, spec in STANDARD_COMPONENTS.items():
        if spec["match"].search(name or ""):
            return {**spec, "std_key": key}
    return None


def collect_components(artifact: dict | None, bom_components: list | None,
                       index: list | None = None) -> list:
    used_ids: set = set()
    comps: list = []
    seen_labels: set = set()

    def add(label, *, image=None, fact_id=None, pins=None, role=None, cid=None):
        lab = (label or "").strip()
        if not lab:
            return
        key = lab.lower()
        if key in seen_labels:
            return
        seen_labels.add(key)
        std = match_standard(lab)
        if std:
            cid = cid or std["id"]
            if cid in used_ids:
                cid = _slug(lab, used_ids)
            else:
                used_ids.add(cid)
            pins = list(std["pins"])
            role = std["role"]
            lab = lab if lab else std["label"]
            # Prefer canonical label for known parts
            if std["match"].search(lab):
                lab = std["label"]
        else:
            cid = cid or _slug(lab, used_ids)
            pins = list(pins or [])
            role = role or "other"
        comps.append({
            "id": cid,
            "label": lab,
            "fact_id": fact_id,
            "image": image,
            "pins": pins,
            "role": role,
        })

    art = artifact or {}
    for c in art.get("main_components") or []:
        if isinstance(c, dict):
            add(c.get("name") or c.get("label"), fact_id=c.get("fact_id"))
        else:
            add(str(c))

    for row in bom_components or []:
        add(row.get("part_no") or row.get("caption") or row.get("file"),
            image=row.get("file"), fact_id=row.get("fact_id"))

    for e in index or []:
        for f in e.get("facts") or []:
            key = (f.get("key") or "").lower()
            if key in ("hardware", "part_no", "model", "component"):
                add(str(f.get("value") or ""), image=e.get("file"),
                    fact_id=f.get("id"))

    return comps


def _pin_allowed(comp: dict, pin: str) -> bool:
    pins = comp.get("pins") or []
    if not pins:
        return pin.upper() in ("5V", "GND", "VCC", "VIN", "VOUT", "V+")
    return pin in pins


def propose_connection_spec(components: list | None = None, *,
                            artifact=None, bom_components=None, index=None,
                            ask_fn=None, lang: str = "no") -> dict:
    comps = list(components or collect_components(artifact, bom_components, index))
    by_id = {c["id"]: c for c in comps}
    id_set = set(by_id)

    edges = []
    for fr_id, fr_pin, to_id, to_pin, label in STANDARD_EDGES:
        if fr_id not in id_set or to_id not in id_set:
            continue
        if not _pin_allowed(by_id[fr_id], fr_pin):
            continue
        if not _pin_allowed(by_id[to_id], to_pin):
            continue
        note = ("AI-foreslått — verifiser mot datablad" if lang == "no"
                else "AI-suggested — verify against datasheet")
        cite = None
        for cid in (fr_id, to_id):
            if by_id[cid].get("fact_id"):
                cite = by_id[cid]["fact_id"]
                break
        edge = {
            "from": f"{fr_id}.{fr_pin}",
            "to": f"{to_id}.{to_pin}",
            "label": label,
            "note": note,
            "provenance": PROV_REFERENCE,
        }
        if cite:
            edge["fact_id"] = cite
            if label in ("5V", "GND", "VIN"):
                edge["note"] = (
                    f"Component cited {{{{fact:{cite}}}}} — wiring is reference"
                    if lang == "en" else
                    f"Komponent sitert {{{{fact:{cite}}}}} — tilkobling er referanse"
                )
        edges.append(edge)

    spec = {
        "block_type": BLOCK_TYPE,
        "components": comps,
        "connections": edges,
        "status": "proposed",
        "lang": lang,
    }

    if ask_fn and comps:
        try:
            prompt = (
                "Propose ONLY additional standard wiring edges as JSON array "
                "[{from,to,label}] using existing component ids and pins. "
                "Do NOT invent pins not listed. Components:\n"
                + json.dumps(comps, ensure_ascii=False)
            )
            raw = ask_fn(
                "diagram_interpret",
                None,
                [{"role": "user", "content": prompt}],
                max_tokens=400,
            )
            m = re.search(r"\[.*\]", raw or "", re.S)
            if m:
                extra = json.loads(m.group(0))
                existing = {(e["from"], e["to"]) for e in edges}
                for e in extra:
                    fr, to = e.get("from"), e.get("to")
                    if not fr or not to or (fr, to) in existing:
                        continue
                    fr_c, _, fr_p = fr.partition(".")
                    to_c, _, to_p = to.partition(".")
                    if fr_c not in by_id or to_c not in by_id:
                        continue
                    if not _pin_allowed(by_id[fr_c], fr_p) or not _pin_allowed(by_id[to_c], to_p):
                        continue
                    edges.append({
                        "from": fr, "to": to,
                        "label": e.get("label") or "signal",
                        "note": "AI-foreslått — verifiser mot datablad",
                        "provenance": PROV_REFERENCE,
                    })
                spec["connections"] = edges
                spec["model_enriched"] = True
        except Exception:
            pass

    return spec


def format_confirm_table(spec: dict, lang: str = "no") -> str:
    """Confirm rows in plain text — never markdown tables (0.26 §A1/D1)."""
    edges = spec.get("connections") or []
    if lang == "en":
        lines = [
            "Proposed connection specification — confirm each row "
            "(accept / edit / drop). Then I render the block diagram into the document.",
            "",
        ]
    else:
        lines = [
            "Foreslått tilkoblingsspesifikasjon — bekreft hver rad "
            "(godta / rediger / dropp). Deretter legges blokkskjemaet inn i dokumentet.",
            "",
        ]
    for i, e in enumerate(edges, 1):
        prov = e.get("provenance") or PROV_REFERENCE
        mark = "~" if prov == PROV_REFERENCE else ("*" if prov == PROV_USER else "+")
        lines.append(
            f"{i}. {e.get('from')} → {e.get('to')}  ·  "
            f"{e.get('label') or '—'}  ·  provenance={prov} {mark}"
        )
    if not edges:
        lines.append("(no edges yet)")
    n_ref = sum(1 for e in edges if e.get("provenance") == PROV_REFERENCE)
    if lang == "en":
        lines += [
            "",
            f"{len(edges)} edges ({n_ref} reference-class, amber). "
            f"Say **confirm all** to accept, or list row numbers to drop.",
            (f"Proposal call ~€{DEMO_EUR:.2f}." if spec.get("model_enriched")
             else "Proposed from known-standard wiring (0 tokens)."),
        ]
    else:
        lines += [
            "",
            f"{len(edges)} kanter ({n_ref} referanseklasse, amber). "
            f"Si **bekreft alle** for å godta, eller list radnumre å droppe.",
            (f"Forslagskall ~€{DEMO_EUR:.2f}." if spec.get("model_enriched")
             else "Foreslått fra kjent standard-wiring (0 tokens)."),
        ]
    return "\n".join(lines)


def apply_edge_decisions(spec: dict, *, accept_all: bool = False,
                         drop_rows: list | None = None,
                         keep_rows: list | None = None) -> dict:
    out = deepcopy(spec)
    edges = list(out.get("connections") or [])
    drop = set(drop_rows or [])
    keep = set(keep_rows or []) if keep_rows is not None else None
    new = []
    for i, e in enumerate(edges, 1):
        if i in drop:
            continue
        if keep is not None and i not in keep and not accept_all:
            continue
        if accept_all or (keep is not None and i in keep):
            if e.get("provenance") == PROV_REFERENCE:
                e = {
                    **e,
                    "provenance": PROV_USER,
                    "note": ("Confirmed by user" if out.get("lang") == "en"
                             else "Bekreftet av bruker"),
                }
        new.append(e)
    out["connections"] = new
    out["status"] = "confirmed"
    return out


def _escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _layout_columns(components: list) -> list:
    buckets = {r: [] for r in ROLE_ORDER}
    for c in sorted(components or [], key=lambda x: x.get("id") or ""):
        role = c.get("role") if c.get("role") in buckets else "other"
        buckets[role].append(c)
    cols = [buckets[r] for r in ROLE_ORDER if buckets[r]]
    return cols or [[]]


def render_block_diagram(spec: dict, title: str | None = None) -> str:
    """0.26 §D2 — diagram_engine is the ONLY renderer."""
    import diagram_engine as deng
    kind = (spec or {}).get("layout_kind") or (spec or {}).get("kind")
    return deng.render_block_diagram(spec, title=title, kind=kind)


def svg_fingerprint(svg: str) -> str:
    import diagram_engine as deng
    return deng.svg_fingerprint(svg)


def is_process_diagram_ask(msg: str) -> bool:
    return bool(PROCESS_ASK.search(msg or ""))


def process_fixture_spec(lang: str = "no") -> dict:
    """Renseanlegg / funksjonsdiagram fixture as proposed connection_spec."""
    import diagram_engine as deng
    from copy import deepcopy
    fix = deepcopy(deng.RENSEANLEGG_FIXTURE)
    return {
        "block_type": BLOCK_TYPE,
        "components": fix["components"],
        "connections": fix["connections"],
        "status": "proposed",
        "lang": lang,
        "kind": "process_flow",
    }


def diagram_created_reply(spec: dict, *, section: str = "connection_diagram",
                          lang: str = "no", assumption: str | None = None) -> str:
    """0.26 §C — three-line reference to the document artifact, never the SVG."""
    n_c = len(spec.get("components") or [])
    n_e = len(spec.get("connections") or [])
    n_ref = sum(
        1 for e in (spec.get("connections") or [])
        if (e.get("provenance") or "") == PROV_REFERENCE
    )
    n_cited = n_e - n_ref
    sec = section or "connection_diagram"
    if lang == "en":
        assume = assumption or (
            "Chamber layout was not in the sources, so the plant is drawn as one module."
            if spec.get("kind") == "process_flow" else
            "Reference-class edges still need datasheet verification."
        )
        return (
            f"Added block diagram in **{sec}** — {n_c} blocks, {n_e} connections"
            f"{f', {n_cited} cited' if n_cited else ''}. "
            f"{assume} [Open in document]"
        )
    assume = assumption or (
        "Kammerinndeling er ikke oppgitt i kildene, så anlegget er tegnet "
        "som én integrert modul."
        if spec.get("kind") == "process_flow" else
        "Referansekanter må fortsatt verifiseres mot datablad."
    )
    return (
        f"Lagt inn funksjonsdiagram i **{sec}** — {n_c} blokker, "
        f"{n_e} forbindelser"
        f"{f', {n_cited} sitert' if n_cited else ''}. "
        f"{assume} [Vis i dokumentet]"
    )


def embed_svg_markdown(svg: str, lang: str = "no") -> str:
    """Document body only — never paste this into chat (0.26 §A)."""
    if lang == "en":
        head = (
            "### Block diagram — connections\n\n"
            "*Block diagram (not a circuit schematic). "
            "Amber = reference — verify against datasheet.*\n\n"
        )
    else:
        head = (
            "### Blokkskjema — tilkoblinger\n\n"
            "*Blokkskjema (ikke kretsskjema). "
            "Amber = referanse — verifiser mot datablad.*\n\n"
        )
    return head + svg + "\n"


def parse_confirm_message(msg: str) -> dict:
    q = (msg or "").strip().lower()
    if re.search(
        r"\b(confirm\s+all|bekreft\s+alle|godta\s+alle|accept\s+all)\b", q
    ):
        return {"accept_all": True}
    drop = [int(x) for x in re.findall(r"(?:drop|fjern)\s*#?\s*(\d+)", q)]
    keep = [int(x) for x in re.findall(r"(?:keep|behold)\s*#?\s*(\d+)", q)]
    nums = [int(x) for x in re.findall(r"\b(\d+)\b", q)]
    if re.search(r"\b(drop|fjern|reject)\b", q) and nums:
        return {"drop_rows": nums}
    if keep:
        return {"keep_rows": keep}
    if drop:
        return {"drop_rows": drop}
    if re.search(r"\b(ja|yes|ok|confirm|bekreft)\b", q):
        return {"accept_all": True}
    return {}
