"""HybridKnowledgeEngine — project-local findings + location/maps registry.

Lives entirely inside the user's project folder. No data is copied outside.

- `project_findings.xlsx` — editable single source of truth (incl. location)
- `.foldok_index/` — optional LanceDB for semantic search (deletable / rebuildable)
- `assets/maps/` — generated location maps (PNG/PDF/SVG)

Maps are always *proposed* as ImageBlock for user confirmation — never auto-inserted.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REGISTRY_COLUMNS = [
    "finding_id",
    "source_file",
    "source_type",
    "component",
    "property",
    "value",
    "unit",
    "tolerance",
    "page_or_view",
    "citation",
    "last_updated",
    "confidence",
    "notes",
    # Location / map (project site + related geo)
    "location_type",
    "address",
    "municipality",
    "postal_code",
    "latitude",
    "longitude",
    "map_image_path",
    "map_style",
]

LOCATION_FINDING_ID = "LOC-PRIMARY"
EMBED_DIM = 384
EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _has_pandas():
    try:
        import pandas  # noqa: F401
        return True
    except ImportError:
        return False


def _has_lancedb():
    try:
        import lancedb  # noqa: F401
        return True
    except ImportError:
        return False


def _embedding_text(row: Dict[str, Any]) -> str:
    parts = [
        str(row.get("component") or ""),
        str(row.get("property") or ""),
        str(row.get("value") or ""),
        str(row.get("unit") or ""),
        str(row.get("citation") or ""),
        str(row.get("notes") or ""),
        str(row.get("source_file") or ""),
        str(row.get("address") or ""),
        str(row.get("municipality") or ""),
        str(row.get("location_type") or ""),
    ]
    return " ".join(p for p in parts if p and p != "nan").strip()


def _f(val) -> Optional[float]:
    if val is None or val == "" or str(val).lower() in ("nan", "none"):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


class HybridKnowledgeEngine:
    """Excel registry + optional LanceDB + project-local location maps."""

    def __init__(self, project_path: str, *, enable_vectors: bool = True):
        if not _has_pandas():
            raise ImportError(
                "HybridKnowledgeEngine requires pandas + openpyxl — "
                "pip install pandas openpyxl"
            )
        self.project_path = str(Path(project_path).resolve())
        self.registry_path = os.path.join(self.project_path, "project_findings.xlsx")
        from foldok_paths import index_dir as _foldok_index_dir
        self.index_path = str(_foldok_index_dir(self.project_path))
        self.maps_dir = os.path.join(self.project_path, "assets", "maps")
        self.enable_vectors = bool(enable_vectors) and _has_lancedb()
        self.db = None
        self.table = None
        self._embed_model = None
        self._ensure_registry_exists()
        if self.enable_vectors:
            self._init_vector_db()

    # ---------- Registry (Excel) ----------
    def _ensure_registry_exists(self) -> None:
        import pandas as pd

        Path(self.project_path).mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.registry_path):
            df = pd.DataFrame(columns=REGISTRY_COLUMNS)
            df.to_excel(self.registry_path, index=False)
            return
        # Migrate: add any new columns to existing workbook
        df = pd.read_excel(self.registry_path, dtype=str)
        changed = False
        for col in REGISTRY_COLUMNS:
            if col not in df.columns:
                df[col] = None
                changed = True
        if changed:
            df[REGISTRY_COLUMNS].to_excel(self.registry_path, index=False)

    def _load_registry(self):
        import pandas as pd

        self._ensure_registry_exists()
        df = pd.read_excel(self.registry_path, dtype=str)
        for col in REGISTRY_COLUMNS:
            if col not in df.columns:
                df[col] = None
        df = df[REGISTRY_COLUMNS]
        df = df.replace({"": None, "nan": None, "None": None})
        return df

    def _save_registry(self, df) -> None:
        out = df.copy()
        for col in REGISTRY_COLUMNS:
            if col not in out.columns:
                out[col] = None
        out = out[REGISTRY_COLUMNS].astype(object)
        for col in out.columns:
            out[col] = out[col].map(
                lambda v: None if v is None or (isinstance(v, float) and str(v) == "nan")
                else str(v) if v is not None else None
            )
        out.to_excel(self.registry_path, index=False)

    # ---------- Vector DB (LanceDB, optional) ----------
    def _init_vector_db(self) -> None:
        import lancedb

        os.makedirs(self.index_path, exist_ok=True)
        self.db = lancedb.connect(self.index_path)
        names = set(self.db.table_names()) if hasattr(self.db, "table_names") else set()
        if "findings" in names:
            self.table = self.db.open_table("findings")
        else:
            self.table = None

    def _get_embed_model(self):
        if self._embed_model is not None:
            return self._embed_model
        try:
            from lancedb.embeddings import get_registry

            self._embed_model = get_registry().get("sentence-transformers").create(
                name=EMBED_MODEL_NAME
            )
            return self._embed_model
        except Exception:
            return None

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        model = self._get_embed_model()
        if model is not None:
            try:
                vectors = model.compute_source_embeddings(texts)
                return [list(v) for v in vectors]
            except Exception:
                pass
        out = []
        for t in texts:
            digest = hashlib.sha256((t or "").encode("utf-8")).digest()
            buf = digest
            while len(buf) < EMBED_DIM:
                buf += hashlib.sha256(buf).digest()
            vec = [(b / 127.5) - 1.0 for b in buf[:EMBED_DIM]]
            out.append(vec)
        return out

    def _rebuild_vector_index(self) -> int:
        if not self.enable_vectors or self.db is None:
            return 0
        import pandas as pd

        df = self._load_registry()
        if df.empty:
            try:
                self.table = self.db.create_table(
                    "findings",
                    data=pd.DataFrame([{
                        "finding_id": "_empty",
                        "source_file": "",
                        "source_type": "",
                        "component": "",
                        "property": "",
                        "value": "",
                        "unit": "",
                        "tolerance": None,
                        "page_or_view": None,
                        "citation": "",
                        "last_updated": _iso_now(),
                        "confidence": 0.0,
                        "notes": None,
                        "vector": [0.0] * EMBED_DIM,
                        "embed_text": "",
                    }]),
                    mode="overwrite",
                )
            except Exception:
                self.table = None
            return 0

        texts = [_embedding_text(row.to_dict()) for _, row in df.iterrows()]
        embeddings = self._embed_texts(texts)
        records = []
        for i, (_, row) in enumerate(df.iterrows()):
            d = row.to_dict()

            def _s(key, default=""):
                v = d.get(key, default)
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    return default if default != "" else None
                return str(v)

            conf = d.get("confidence", 0.9)
            try:
                conf_f = float(conf) if conf is not None and not (
                    isinstance(conf, float) and pd.isna(conf)) else 0.9
            except (TypeError, ValueError):
                conf_f = 0.9

            records.append({
                "finding_id": _s("finding_id", "") or "",
                "source_file": _s("source_file", "") or "",
                "source_type": _s("source_type", "") or "",
                "component": _s("component", "") or "",
                "property": _s("property", "") or "",
                "value": _s("value", "") or "",
                "unit": _s("unit", "") or "",
                "tolerance": _s("tolerance"),
                "page_or_view": _s("page_or_view"),
                "citation": _s("citation", "") or "",
                "last_updated": _s("last_updated", _iso_now()) or _iso_now(),
                "confidence": conf_f,
                "notes": _s("notes"),
                "vector": embeddings[i],
                "embed_text": texts[i],
            })
        self.table = self.db.create_table("findings", data=records, mode="overwrite")
        return len(records)

    # ---------- Findings API ----------
    def index_project(self, force_rebuild: bool = False) -> Dict[str, Any]:
        self._ensure_registry_exists()
        n = 0
        if self.enable_vectors and (force_rebuild or self.table is None):
            n = self._rebuild_vector_index()
        df = self._load_registry()
        return {
            "registry_path": self.registry_path,
            "index_path": self.index_path if self.enable_vectors else None,
            "maps_dir": self.maps_dir,
            "rows": int(len(df)),
            "vectors_rebuilt": n,
            "vectors_enabled": self.enable_vectors,
        }

    def get_findings(
        self,
        component: Optional[str] = None,
        property_name: Optional[str] = None,
        source_file: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        import pandas as pd

        df = self._load_registry()
        if component:
            df = df[df["component"].astype(str).str.contains(component, case=False, na=False)]
        if property_name:
            df = df[df["property"].astype(str).str.contains(property_name, case=False, na=False)]
        if source_file:
            df = df[df["source_file"].astype(str).str.contains(source_file, case=False, na=False)]
        return df.where(pd.notnull(df), None).to_dict(orient="records")

    def update_finding(self, finding: Dict[str, Any], *, rebuild_vectors: bool = True) -> str:
        import pandas as pd

        df = self._load_registry()
        finding = dict(finding or {})
        finding_id = finding.get("finding_id") or (
            f"FIND-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        )
        finding["finding_id"] = finding_id
        finding["last_updated"] = _iso_now()
        if finding.get("confidence") is None:
            finding["confidence"] = 0.9

        row = {c: finding.get(c) for c in REGISTRY_COLUMNS}
        for k, v in list(row.items()):
            if v is None:
                continue
            row[k] = str(v)

        ids = df["finding_id"].astype(str) if not df.empty else pd.Series(dtype=str)
        if not df.empty and finding_id in ids.values:
            idx = df.index[ids == finding_id][0]
            for k, v in row.items():
                if k in df.columns and v is not None:
                    df.at[idx, k] = v
        else:
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

        self._save_registry(df)
        if rebuild_vectors and self.enable_vectors:
            self._rebuild_vector_index()
        return finding_id

    def upsert_findings(self, findings: List[Dict[str, Any]]) -> List[str]:
        ids = []
        for f in findings or []:
            ids.append(self.update_finding(f, rebuild_vectors=False))
        if self.enable_vectors and ids:
            self._rebuild_vector_index()
        return ids

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        import pandas as pd

        q = (query or "").strip()
        if not q:
            return []

        if self.enable_vectors and self.table is not None:
            try:
                qvec = self._embed_texts([q])[0]
                results = self.table.search(qvec).limit(limit).to_pandas()
                if "vector" in results.columns:
                    results = results.drop(columns=["vector"])
                return results.where(pd.notnull(results), None).to_dict(orient="records")
            except Exception:
                try:
                    results = self.table.search(q).limit(limit).to_pandas()
                    if "vector" in results.columns:
                        results = results.drop(columns=["vector"])
                    return results.where(pd.notnull(results), None).to_dict(orient="records")
                except Exception:
                    pass

        df = self._load_registry()
        if df.empty:
            return []
        tokens = [t for t in re.split(r"\W+", q.lower()) if len(t) > 2]
        scored = []
        for _, row in df.iterrows():
            blob = _embedding_text(row.to_dict()).lower()
            score = sum(1 for t in tokens if t in blob)
            if score:
                d = row.to_dict()
                d["_score"] = score
                scored.append(d)
        scored.sort(key=lambda x: -x.get("_score", 0))
        out = []
        for d in scored[:limit]:
            d.pop("_score", None)
            for k, v in list(d.items()):
                if isinstance(v, float) and pd.isna(v):
                    d[k] = None
            out.append(d)
        return out

    def rebuild_index(self) -> Dict[str, Any]:
        n = self._rebuild_vector_index() if self.enable_vectors else 0
        return {
            "ok": True,
            "rows_indexed": n,
            "registry_path": self.registry_path,
            "vectors_enabled": self.enable_vectors,
        }

    def import_from_index_facts(self, index_entries: List[Dict[str, Any]]) -> List[str]:
        rows = []
        for e in index_entries or []:
            src = e.get("file") or e.get("source_file") or ""
            kind = e.get("kind") or "doc"
            for f in e.get("facts") or []:
                key = f.get("key") or ""
                rows.append({
                    "source_file": src,
                    "source_type": kind,
                    "component": f.get("component") or "",
                    "property": key or f.get("fact_type") or "fact",
                    "value": str(f.get("value") if f.get("value") is not None else ""),
                    "unit": f.get("unit") or "",
                    "page_or_view": f.get("source_location") or "",
                    "citation": f.get("source_excerpt") or f.get("id") or src,
                    "confidence": float(f.get("confidence") or 0.85),
                    "notes": f.get("fact_type") or None,
                    "finding_id": f.get("id"),
                })
        return self.upsert_findings(rows)

    # ---------- Location / maps ----------
    def get_location(self) -> Optional[Dict[str, Any]]:
        """Return the primary project location from the registry."""
        import pandas as pd

        df = self._load_registry()
        if df.empty:
            return None
        # Prefer LOC-PRIMARY, else first row with address or coordinates
        hit = None
        if LOCATION_FINDING_ID in df["finding_id"].astype(str).values:
            hit = df[df["finding_id"].astype(str) == LOCATION_FINDING_ID].iloc[0]
        else:
            for _, row in df.iterrows():
                if row.get("address") or row.get("latitude") or row.get("longitude"):
                    hit = row
                    break
        if hit is None:
            return None
        d = hit.to_dict() if hasattr(hit, "to_dict") else dict(hit)
        for k, v in list(d.items()):
            if isinstance(v, float) and pd.isna(v):
                d[k] = None
        d["latitude"] = _f(d.get("latitude"))
        d["longitude"] = _f(d.get("longitude"))
        return d

    def set_location(
        self,
        address: str,
        municipality: Optional[str] = None,
        postal_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_type: str = "project_site",
        *,
        citation: Optional[str] = None,
        geocode_if_needed: bool = True,
        map_style: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store or update primary location in project_findings.xlsx."""
        lat, lon = _f(latitude), _f(longitude)
        cite = citation or "user / project registry"
        if geocode_if_needed and (lat is None or lon is None) and address:
            try:
                from tools.osm_vector_tiles import geocode_address
                geo = geocode_address(
                    address, municipality=municipality, postal_code=postal_code
                )
            except Exception:
                geo = None
            if geo:
                lat = lat if lat is not None else geo.get("latitude")
                lon = lon if lon is not None else geo.get("longitude")
                municipality = municipality or geo.get("municipality")
                postal_code = postal_code or geo.get("postal_code")
                cite = geo.get("citation") or cite

        existing = self.get_location() or {}
        finding = {
            "finding_id": LOCATION_FINDING_ID,
            "source_file": existing.get("source_file") or "project_findings.xlsx",
            "source_type": "location",
            "component": "project",
            "property": "site_location",
            "value": address or existing.get("value") or "",
            "unit": "",
            "citation": cite,
            "confidence": 1.0,
            "notes": "Primary project site location",
            "location_type": location_type or "project_site",
            "address": address,
            "municipality": municipality,
            "postal_code": postal_code,
            "latitude": lat,
            "longitude": lon,
            "map_image_path": existing.get("map_image_path"),
            "map_style": map_style or existing.get("map_style") or "default",
        }
        self.update_finding(finding)
        return self.get_location() or finding

    def generate_location_map(
        self,
        style: str = "default",
        width: int = 1200,
        height: int = 800,
        zoom: int = 16,
        color_overrides: Optional[Dict] = None,
        output_format: str = "png",
    ) -> str:
        """
        Call the OSM vector tile / stitch generator.
        Save into assets/maps/ inside the project.
        Return the *relative* path (from project root) to the generated image.
        """
        loc = self.get_location()
        if not loc:
            raise ValueError("No location in registry — call set_location first")
        lat, lon = _f(loc.get("latitude")), _f(loc.get("longitude"))
        if lat is None or lon is None:
            # Try geocode from stored address
            if loc.get("address"):
                self.set_location(
                    loc["address"],
                    municipality=loc.get("municipality"),
                    postal_code=loc.get("postal_code"),
                    location_type=loc.get("location_type") or "project_site",
                    citation=loc.get("citation"),
                    geocode_if_needed=True,
                    map_style=style,
                )
                loc = self.get_location() or loc
                lat, lon = _f(loc.get("latitude")), _f(loc.get("longitude"))
        if lat is None or lon is None:
            raise ValueError("Location has no coordinates — provide latitude/longitude or a geocodable address")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fmt = (output_format or "png").lower().lstrip(".")
        rel = f"assets/maps/location_map_{ts}.{fmt}"
        abs_path = os.path.join(self.project_path, rel.replace("/", os.sep))
        Path(abs_path).parent.mkdir(parents=True, exist_ok=True)

        from tools.osm_vector_tiles import render_location_map

        written = render_location_map(
            lat, lon, abs_path,
            width=width, height=height, zoom=zoom, style=style,
            color_overrides=color_overrides or {},
            output_format=fmt,
        )
        # Normalize relative path if backend changed extension
        written_path = Path(written)
        try:
            rel = written_path.resolve().relative_to(Path(self.project_path).resolve()).as_posix()
        except ValueError:
            rel = f"assets/maps/{written_path.name}"

        self.update_finding({
            "finding_id": LOCATION_FINDING_ID,
            "source_file": loc.get("source_file") or "project_findings.xlsx",
            "source_type": "location",
            "component": "project",
            "property": "site_location",
            "value": loc.get("address") or loc.get("value") or "",
            "citation": loc.get("citation") or "OSM map",
            "location_type": loc.get("location_type") or "project_site",
            "address": loc.get("address"),
            "municipality": loc.get("municipality"),
            "postal_code": loc.get("postal_code"),
            "latitude": lat,
            "longitude": lon,
            "map_image_path": rel,
            "map_style": style,
        })
        return rel

    def propose_location_map(
        self,
        style: str = "default",
        width: int = 1200,
        height: int = 800,
        zoom: int = 16,
        color_overrides: Optional[Dict] = None,
        output_format: str = "png",
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate the map and return an ImageBlock *proposal* for user confirmation.
        Never inserts into the Document AST — agent must wait for confirm.
        """
        rel = self.generate_location_map(
            style=style, width=width, height=height, zoom=zoom,
            color_overrides=color_overrides, output_format=output_format,
        )
        loc = self.get_location() or {}
        addr = loc.get("address") or ""
        muni = loc.get("municipality") or ""
        cap = caption or (" · ".join(p for p in [addr, muni] if p) or "Project site map")
        proposal = {
            "needs_confirm": True,
            "block_type": "ImageBlock",
            "proposal_id": f"map-{uuid.uuid4().hex[:8]}",
            "image": {
                "path": rel,
                "caption": cap,
                "role": "site_map",
                "alt": cap,
            },
            "location": {
                "address": loc.get("address"),
                "municipality": loc.get("municipality"),
                "postal_code": loc.get("postal_code"),
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "citation": loc.get("citation"),
                "map_style": style,
            },
            "message": (
                "Kart foreslått — bekreft for å sette inn som ImageBlock, "
                "eller erstatt filen i assets/maps/ med ditt eget bilde."
            ),
        }
        return proposal


def open_project_knowledge(project_path: str, **kw) -> HybridKnowledgeEngine:
    return HybridKnowledgeEngine(project_path, **kw)
