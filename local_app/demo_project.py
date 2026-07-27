"""WORKORDER_0.23 C — Synthetic demo projects (marked, non-exportable as paid)."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIFTING_DEMO = ROOT / "examples" / "demo-lifting-tool"

DEMO_BANNER = (
    "SYNTETISK DEMOMATERIALE — fiktive parter, ingen juridisk virkning"
)
DEMO_FOOTER = (
    "\n\n---\n"
    f"{DEMO_BANNER}\n"
)


def _wrap(body: str) -> str:
    body = (body or "").strip()
    if DEMO_BANNER in body:
        return body if body.endswith("\n") else body + "\n"
    return f"{DEMO_BANNER}\n\n{body}{DEMO_FOOTER}"


def _demo_name(kind: str) -> str:
    if kind == "technical":
        return "DEMO_Løfteverktøy"
    return "DEMO_Kontraktsak"


CONTRACT_A = """\
AVTALE — ENTREPRISE (SYNTETISK)
Saknr.: DEMO-2026-0042
Parter: Fiktiv Entreprenør AS (leverandør) og Demo Byggherre AS (oppdragsgiver)

§1 Omfang
Leverandør skal levere prosjektering og montasje av midlertidig stillas i henhold
til vedlagte tegninger. Leveransen omfatter ikke permanent fundament.

§2 Frister
Oppstart: 2026-03-01.
Ferdigstillelse: 2026-06-15 (§2).
I §7 (sanksjoner) står imidlertid: «ved forsinkelse etter 2026-05-30 påløper dagmulkt.»
(PLANTED FINDING: conflicting deadlines — §2 vs §7.)

§3 Betaling
Betaling 30 dager etter godkjent milepæl.

§4 Ansvar
Partene er ansvarlige for skade forårsaket av egen uaktsomhet.
(PLANTED FINDING: missing liability cap — no maximum amount stated.)

§5 Definisjoner
«Vesentlig forsinkelse» brukes i §7 uten definisjon i denne avtalen.
(PLANTED FINDING: undefined term «vesentlig forsinkelse».)

§6 Lovvalg
Norsk rett.
"""

CONTRACT_B = """\
RAMMEAVTALE — UNDERENTREPRISE (SYNTETISK)
Saknr.: DEMO-2026-0042-B
Parter: Fiktiv Entreprenør AS og Demo Underentreprenør AS

§1 Leveranse
Montering av stillasdeler etter anvisning fra hovedentreprenør.

§2 Frist
Underentreprenør skal være ferdig senest 2026-05-20 — dette avviker fra
hovedavtalens ferdigstillelse 2026-06-15 (PLANTED: cross-document deadline tension).

§3 Erstatning
Ingen tak på erstatningsansvar er angitt (PLANTED: missing liability cap echo).

§4 Terminologi
«Vesentlig forsinkelse» henvises til hovedavtalen uten egen definisjon.
"""


def write_contract_demo_files(folder: Path) -> list:
    out = []
    pairs = [
        ("DEMO_avtale_entreprise.txt", CONTRACT_A),
        ("DEMO_rammeavtale_underentreprise.txt", CONTRACT_B),
    ]
    dest_dir = folder / "Notater"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for name, body in pairs:
        path = dest_dir / name
        path.write_text(_wrap(body), encoding="utf-8")
        out.append(str(path.relative_to(folder)).replace("\\", "/"))
    readme = folder / "DEMO_README.txt"
    readme.write_text(_wrap(
        "Dette er en merket demosak for kontraktsgjennomgang.\n"
        "Fiktive parter: Fiktiv Entreprenør AS / Demo Byggherre AS.\n"
        "Plantede funn: manglende ansvarstak, konfliktende frister, udefinert term.\n"
        "Eksporteres ikke som betalt dokument — kun forhåndsvisning med DEMO-vannmerke.\n"
    ), encoding="utf-8")
    out.append("DEMO_README.txt")
    return out


def write_technical_demo_files(folder: Path) -> list:
    out = []
    src = LIFTING_DEMO
    if not src.is_dir():
        # Minimal fallback
        p = folder / "Notater" / "DEMO_heis_spec.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_wrap("DEMO-HEIS-0042 — 500 kg SWL, Verkstedveien 1, 4000 Demo."),
                     encoding="utf-8")
        return ["Notater/DEMO_heis_spec.txt"]
    for f in src.iterdir():
        if not f.is_file():
            continue
        if f.suffix.lower() not in {".txt", ".md"}:
            continue
        if f.name.lower() == "readme.md":
            continue
        name = f.name if f.name.upper().startswith("DEMO_") else f"DEMO_{f.name}"
        # Prefer Notater for docs
        dest = folder / "Notater" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = f.read_text(encoding="utf-8", errors="replace")
        dest.write_text(_wrap(text), encoding="utf-8")
        out.append(str(dest.relative_to(folder)).replace("\\", "/"))
    readme = folder / "DEMO_README.txt"
    readme.write_text(_wrap(
        "Teknisk demosak basert på examples/demo-lifting-tool.\n"
        "Alle filer er syntetiske. Ikke eksporterbar som betalt dokument.\n"
    ), encoding="utf-8")
    out.append("DEMO_README.txt")
    return out


def stamp_demo_watermark(content: str) -> str:
    """C2 — generated demo docs carry a DEMO watermark banner."""
    mark = f"\n\n<!-- DEMO WATERMARK -->\n**{DEMO_BANNER}**\n\n"
    if DEMO_BANNER in (content or ""):
        return content
    return mark + (content or "")


def create_demo_files(folder: Path, kind: str) -> list:
    kind = (kind or "contract").lower().strip()
    if kind in ("technical", "tech", "lifting"):
        return write_technical_demo_files(folder)
    return write_contract_demo_files(folder)
