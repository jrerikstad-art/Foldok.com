"""Foldok capabilities — derived from the engines, reconciled with the manifest.

    rec = reconcile(".")
    print(rec.report())                       # what the manifest is missing
    write_manifest("capabilities.json", merge_into(load_manifest("."), rec.capabilities))

Exists because a build shipping 45 diagram symbols told a user it had no drawing
tools — correctly, because the manifest never mentioned them.
"""

from .discover import DISCOVERERS, discover
from .model import (
    SCHEMA_VERSION,
    Capability,
    Denial,
    Drift,
    Limit,
    Reconciliation,
)
from .reconcile import MANIFEST, evidence_summary, load_manifest, reconcile
from .render import manifest_block, merge_into, prompt_lines, write_manifest

__all__ = [
    "Capability", "DISCOVERERS", "Denial", "Drift", "Limit", "MANIFEST",
    "Reconciliation", "SCHEMA_VERSION", "discover", "evidence_summary",
    "load_manifest", "manifest_block", "merge_into", "prompt_lines",
    "reconcile", "write_manifest",
]

__version__ = "0.83.0"
