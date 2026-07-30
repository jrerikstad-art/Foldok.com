"""Foldok authoring — intent decides how to write, facts decide what may be said.

    engine = AuthoringEngine(lang="no")
    result = engine.author("declare_conformity", facts)
    result.publishable      # grounded, and it used the facts it had to

Six intents generate from facts. Four do not, by name and with a reason:
procedures, hazards, troubleshooting and process explanations are authored,
because inventing them fluently is worse than tabulating them badly.
"""

from .compose import compose
from .defaults import (
    SECTION_INTENT,
    facts_from_foldok,
    inject_fact_citations,
    is_authored_not_generated,
    resolve_intent,
)
from .engine import AuthoringEngine
from .intents import INTENTS, WHY_NOT, available, get
from .model import (
    AUTHORED_NOT_GENERATED,
    Claim,
    Fact,
    IntentRefused,
    Plan,
    Result,
)
from .procedure import Procedure, Step
from .verify import verify

# Compatibility aliases for earlier Foldok wiring
AuthoringResult = Result
NarrativePlan = Plan
get_intent = get

__all__ = [
    "AUTHORED_NOT_GENERATED",
    "AuthoringEngine",
    "AuthoringResult",
    "Claim",
    "Fact",
    "INTENTS",
    "IntentRefused",
    "NarrativePlan",
    "Plan",
    "Procedure",
    "Result",
    "SECTION_INTENT",
    "Step",
    "WHY_NOT",
    "available",
    "compose",
    "facts_from_foldok",
    "get",
    "get_intent",
    "inject_fact_citations",
    "is_authored_not_generated",
    "resolve_intent",
    "verify",
]

__version__ = "0.86.0"
