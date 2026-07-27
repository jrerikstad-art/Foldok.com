"""Foldok asset library — one index over the registries that already exist.

    lib = AssetLibrary.load(".")
    lib.find(kind="symbol", domain="piping")
    lib.resolve("template.installation_manual")
    lib.seal(lib.pack("marine_starter", ids))     # refuses anything unshippable

Assets are indexed where they live. Nothing is moved.
"""

from .discover import ADAPTERS, discover
from .library import AssetLibrary, PackRefused, Resolution
from .model import (
    KINDS,
    SHIPPABLE,
    Asset,
    AssetKind,
    Pack,
    PackRef,
    Source,
    asset_id,
    checksum_of,
)

__all__ = [
    "ADAPTERS", "Asset", "AssetKind", "AssetLibrary", "KINDS", "Pack", "PackRef",
    "PackRefused", "Resolution", "SHIPPABLE", "Source", "asset_id", "checksum_of",
    "discover",
]

__version__ = "0.74.0"
