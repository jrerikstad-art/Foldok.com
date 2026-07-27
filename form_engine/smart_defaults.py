"""Optional smart defaults / web lookup — never redesign; only fill blanks."""
from __future__ import annotations

# Ratings are NEVER suggested here (technician judgment).


def suggest(pkg: dict, *, artifact: dict | None = None,
            index: list | None = None) -> dict:
    """
    Return {key: {value, source}} for empty fields where a safe default exists.
    source must be labeled so chips show provenance.
    """
    out = {}
    artifact = artifact or {}
    # Example: project/artifact name → customer_name if blank
    name = artifact.get("name") or artifact.get("customer") or ""
    keys = {f.get("key") for f in (pkg.get("fields") or [])}
    if name and "customer_name" in keys:
        out["customer_name"] = {
            "value": name,
            "source": "smart:artifact_name",
        }
    # Address → building regulations: stub for future web lookup
    # (explicitly not inventing values)
    _ = index  # reserved for fact scan
    return out


def lookup_address_regulations(address: str) -> dict | None:
    """
    Pluggable hook — returns None until a real provider is wired.
    Must never fabricate legal requirements.
    """
    if not (address or "").strip():
        return None
    return None
