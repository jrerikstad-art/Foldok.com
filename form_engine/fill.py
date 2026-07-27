"""Bind project facts into a FormPackage — never redesign the paper."""
from __future__ import annotations

from copy import deepcopy

from .model import apply_values_to_package, validate_package
from . import smart_defaults


def values_from_form_state(state: dict, template: dict) -> dict:
    """Collect {key: {value, source, unit}} from form_fill doc state."""
    values = {}
    doc = (state or {}).get("doc") or {}
    sections = doc.get("sections") or {}
    for sdef in template.get("sections") or []:
        sk = sdef.get("section_key")
        slots = (sections.get(sk) or {}).get("fields") or {}
        for fdef in sdef.get("fields") or []:
            key = fdef.get("key")
            if not key:
                continue
            slot = slots.get(key) or {}
            if slot.get("value") is not None and slot.get("value") != "":
                values[key] = {
                    "value": slot.get("value"),
                    "source": slot.get("source") or slot.get("source_fact_id"),
                    "unit": slot.get("unit") or fdef.get("unit"),
                }
    return values


def bind_package(pkg: dict, state: dict, template: dict | None = None,
                 *, artifact: dict | None = None,
                 index: list | None = None,
                 enable_smart_defaults: bool = True) -> dict:
    """
    Prefill via form_model when template given; stamp onto package.
    Ratings remain empty unless user/technician set them.
    """
    pkg = validate_package(pkg)
    template = template or {}
    values = values_from_form_state(state, template) if template else {}

    # If doc empty, try form_model.prefill into a temp state copy
    if not values and template and index is not None:
        try:
            import form_model as fm
            st = deepcopy(state or {})
            if not st.get("doc"):
                # minimal shell
                st["doc"] = {"sections": {
                    s["section_key"]: {"fields": {}}
                    for s in template.get("sections") or [] if s.get("section_key")
                }}
            pref = fm.prefill_form(st, template, index)
            values = values_from_form_state(st, template)
            pkg.setdefault("meta", {})["prefilled"] = pref.get("prefilled", 0)
        except Exception:
            pass

    if enable_smart_defaults:
        suggestions = smart_defaults.suggest(pkg, artifact=artifact, index=index)
        for k, slot in suggestions.items():
            if k not in values:
                values[k] = slot

    return apply_values_to_package(pkg, values)
