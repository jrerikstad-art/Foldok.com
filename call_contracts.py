"""Call contracts — every model call has shape, validator, fallback.

WORKORDER 0.49 Part A / ENGINE_CONTRACT amendment:
  (1) ONE output shape
  (2) a code validator for that shape
  (3) a deterministic fallback when validation fails twice

Prefer COMPUTATION over VALIDATION: if code can produce the artifact,
do not call the model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class CallContract:
    """Binding for one model call purpose."""

    purpose: str
    shape: str  # human-readable shape description
    validate: Callable[[Any], bool]
    fallback: Callable[[], Any]
    model: str = ""
    max_tokens: int = 800
    max_attempts: int = 2
    parse: str = "text"  # "text" | "json"
    notes: str = ""


@dataclass
class ContractResult:
    value: Any
    used_fallback: bool = False
    attempts: int = 0
    purpose: str = ""


# Registry of shipped contracts (documentation + runtime lookup)
CONTRACTS: dict[str, CallContract] = {}


def register(contract: CallContract) -> CallContract:
    CONTRACTS[contract.purpose] = contract
    return contract


def run_contracted(
    contract: CallContract,
    ask_fn: Callable[..., str],
    messages: list,
    *,
    system: Optional[str] = None,
    parse_json_fn: Optional[Callable[[str], Any]] = None,
) -> ContractResult:
    """Run ask_fn up to max_attempts; on failure return contract.fallback()."""
    last_err: Optional[Exception] = None
    for attempt in range(1, contract.max_attempts + 1):
        try:
            raw = ask_fn(
                contract.purpose,
                contract.model,
                messages,
                system=system,
                max_tokens=contract.max_tokens,
            )
            if contract.parse == "json":
                if not parse_json_fn:
                    raise RuntimeError("parse_json_fn required for JSON contracts")
                value = parse_json_fn(raw)
            else:
                value = raw
            if contract.validate(value):
                return ContractResult(
                    value=value,
                    used_fallback=False,
                    attempts=attempt,
                    purpose=contract.purpose,
                )
        except Exception as e:
            last_err = e
            continue
    _ = last_err  # reserved for ledger diagnostics
    return ContractResult(
        value=contract.fallback(),
        used_fallback=True,
        attempts=contract.max_attempts,
        purpose=contract.purpose,
    )


def require_contract(purpose: str) -> CallContract:
    c = CONTRACTS.get(purpose)
    if not c:
        raise KeyError(
            f"No CallContract registered for purpose={purpose!r}. "
            "Every model call must declare shape + validator + fallback."
        )
    return c


# Lightweight ledger of purposes that intentionally have no model call
# (computation-only steps of the section pipeline).
COMPUTATION_STEPS = frozenset({
    "select_facts",
    "build_table",
    "place_figures",
    "compose_paginate",
    "editorial_furniture",
    "number_figures",
    "illustration_appendix",
    "glossary_compile",
    "cross_ref_resolve",
})
