from .datasheet import DATASHEET
from .engineering import ENGINEERING
from .manual import MANUAL

# Customer brand names are never shipped as themes.
# "akva" is accepted only as an alias → manual (neutral tokens).
THEMES = {
    "engineering": ENGINEERING,
    "datasheet": DATASHEET,
    "manual": MANUAL,
    "akva": MANUAL,
}

__all__ = ["ENGINEERING", "DATASHEET", "MANUAL", "THEMES"]
