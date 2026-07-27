"""Geocode addresses via Nominatim (OSM) — results stored only in the project registry."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

USER_AGENT = "FoldokEngine/0.52 (local documentation; contact: local)"


def geocode_address(
    address: str,
    *,
    municipality: Optional[str] = None,
    postal_code: Optional[str] = None,
    country: str = "Norway",
) -> Optional[Dict[str, Any]]:
    """Return {latitude, longitude, display_name, municipality?, postal_code?} or None."""
    parts = [p for p in [address, postal_code, municipality, country] if p]
    q = ", ".join(parts)
    if not q.strip():
        return None
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
        "q": q,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    })
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    if not data:
        return None
    hit = data[0]
    addr = hit.get("address") or {}
    return {
        "latitude": float(hit["lat"]),
        "longitude": float(hit["lon"]),
        "display_name": hit.get("display_name") or q,
        "municipality": addr.get("municipality") or addr.get("city") or addr.get("town")
                        or municipality,
        "postal_code": addr.get("postcode") or postal_code,
        "citation": f"Nominatim OSM: {hit.get('display_name') or q}",
    }
