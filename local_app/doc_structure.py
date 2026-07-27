"""WORKORDER_0.27 C — per-document layout overlay (move/add/toggle/layout)."""
from __future__ import annotations

import re
import unicodedata
from copy import deepcopy

import doc_state as ds


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


def overlay(state: dict) -> dict:
    doc = state.setdefault("doc", {"sections": {}})
    ov = doc.setdefault("structure_overlay", {})
    ov.setdefault("positions", {})
    ov.setdefault("disabled", [])
    ov.setdefault("layouts", {})
    ov.setdefault("renames", {})
    ov.setdefault("extra_sections", [])
    ov.setdefault("structural_edits", 0)
    ov.setdefault("save_template_offered", False)
    return ov


def effective_sections(state: dict, template: dict) -> list:
    """Template sections merged with per-document overlay."""
    base = sorted(template.get("sections") or [], key=lambda x: x.get("position", 99))
    ov = overlay(state)
    disabled = set(ov.get("disabled") or [])
    layouts = ov.get("layouts") or {}
    renames = ov.get("renames") or {}
    pos_map = dict(ov.get("positions") or {})
    extras = {s["section_key"]: s for s in ov.get("extra_sections") or [] if s.get("section_key")}

    merged = []
    for s in base:
        sk = s["section_key"]
        if sk in disabled:
            continue
        sec = deepcopy(s)
        if sk in extras:
            sec.update({k: v for k, v in extras[sk].items() if v is not None})
        if sk in renames:
            sec["title_no"] = renames[sk]
            sec["title"] = renames[sk]
        if sk in layouts:
            wr = dict(sec.get("writing_rules") or {})
            wr["structure"] = layouts[sk]
            sec["writing_rules"] = wr
        if sk in pos_map:
            sec["position"] = pos_map[sk]
        merged.append(sec)

    merged.sort(key=lambda x: (pos_map.get(x["section_key"], x.get("position", 99)),
                               x.get("section_key", "")))
    return merged


def section_order(state: dict, template: dict) -> list[str]:
    return [s["section_key"] for s in effective_sections(state, template)]


def find_section_key(text: str, template: dict, state: dict) -> str | None:
    q = _fold(text)
    candidates = effective_sections(state, template)
    best, best_score = None, 0
    for s in candidates:
        sk = s["section_key"]
        for label in (_fold(s.get("title_no") or ""),
                      _fold(s.get("title") or ""),
                      sk.replace("_", " ")):
            if not label:
                continue
            if label in q:
                score = len(label) + 2
            elif any(tok in q for tok in label.split() if len(tok) > 4):
                score = 5
            else:
                continue
            if score > best_score:
                best_score, best = score, sk
    if re.search(r"materialliste|bill of materials|\bbom\b", q):
        for s in candidates:
            if s["section_key"] in ("bom", "materials", "bill_of_materials"):
                return s["section_key"]
    return best


def parse_layout_intent(message: str, template: dict, state: dict) -> dict | None:
    if not template or not state.get("doc"):
        return None
    q = _fold(message)

    if re.search(r"\b(fjern|remove|skjul|hide)\b", q) and re.search(
            r"kilderegister|source register", q):
        return {"tool": "toggle_section", "key": "source_register", "enabled": False}

    if re.search(r"\b(legg til|add)\b", q) and re.search(r"\bseksjon|section\b", q):
        title = "HMS"
        m = re.search(r"\b(hms|safety|sikkerhet)\b", q, re.I)
        if m:
            title = m.group(0).upper() if m.group(0).lower() == "hms" else m.group(0).title()
        after = find_section_key(message, template, state)
        if not after and re.search(r"systemoversikt|system overview", q):
            after = "system_overview"
        return {"tool": "add_section", "title": title, "after": after or "system_overview"}

    if re.search(r"\b(tabell|table)\b", q) and re.search(r"\b(i stedet|instead|som)\b", q):
        key = find_section_key(message, template, state)
        if key:
            return {"tool": "set_block_layout", "key": key, "layout": "table"}

    if re.search(r"\b(flytt|move)\b", q):
        key = find_section_key(message, template, state)
        if not key:
            return None
        if re.search(r"\b(øverst|top|first|først|topp)\b", q):
            return {"tool": "move_section", "key": key, "position": 1}
        m_before = re.search(
            r"\b(før|before|foran)\s+(.+)$", message, re.I)
        if m_before:
            target = find_section_key(m_before.group(2), template, state)
            if target:
                return {"tool": "move_section", "key": key, "before": target}
        m_after = re.search(r"\b(etter|after|bak)\s+(.+)$", message, re.I)
        if m_after:
            target = find_section_key(m_after.group(2), template, state)
            if target:
                return {"tool": "move_section", "key": key, "after": target}
        return {"tool": "move_section", "key": key, "position": 1}
    return None


def _bump_structural(state: dict, summary: str, section: str | None = None) -> int:
    ov = overlay(state)
    ov["structural_edits"] = int(ov.get("structural_edits") or 0) + 1
    ds.add_version(state, "user", "structure", summary, section=section)
    return ov["structural_edits"]


def move_section(state: dict, template: dict, key: str, *,
                 position: int | None = None, after: str | None = None,
                 before: str | None = None) -> dict:
    ov = overlay(state)
    positions = ov["positions"]
    keys = section_order(state, template)
    if key not in keys:
        raise ValueError(f"Ukjent seksjon: {key}")
    keys = [k for k in keys if k != key]
    if before and before in keys:
        idx = keys.index(before)
    elif after and after in keys:
        idx = keys.index(after) + 1
    elif position is not None:
        idx = max(0, min(int(position) - 1, len(keys)))
    else:
        idx = 0
    keys.insert(idx, key)
    for i, sk in enumerate(keys, 1):
        positions[sk] = i
    n = _bump_structural(state, f"Flyttet seksjon {key}", section=key)
    return {"key": key, "order": keys, "structural_edits": n}


def toggle_section(state: dict, template: dict, key: str, *, enabled: bool = True) -> dict:
    ov = overlay(state)
    disabled = set(ov.get("disabled") or [])
    if enabled:
        disabled.discard(key)
    else:
        disabled.add(key)
    ov["disabled"] = sorted(disabled)
    n = _bump_structural(
        state,
        f"{'Aktiverte' if enabled else 'Deaktiverte'} seksjon {key}",
        section=key,
    )
    warning = "traceability_reduced" if not enabled and key == "source_register" else None
    return {"key": key, "enabled": enabled, "warning": warning, "structural_edits": n}


def set_block_layout(state: dict, template: dict, key: str, layout: str) -> dict:
    ov = overlay(state)
    ov.setdefault("layouts", {})[key] = layout
    n = _bump_structural(state, f"Layout {layout} på {key}", section=key)
    return {"key": key, "layout": layout, "structural_edits": n}


def add_section(state: dict, template: dict, title: str, after: str | None = None,
                rules: dict | None = None) -> dict:
    ov = overlay(state)
    base_key = re.sub(r"[^a-z0-9]+", "_", _fold(title)).strip("_") or "extra"
    key = base_key
    existing = {s["section_key"] for s in effective_sections(state, template)}
    n = 2
    while key in existing:
        key = f"{base_key}_{n}"
        n += 1
    sec_def = {
        "section_key": key,
        "title": title,
        "title_no": title,
        "position": 99,
        "required": False,
        "gap_severity": "warning",
        "required_facts": [],
        "required_media": {},
        "writing_rules": rules or {"structure": "prose", "fact_citation": "required"},
    }
    ov.setdefault("extra_sections", []).append(sec_def)
    state.setdefault("doc", {}).setdefault("sections", {})[key] = {"md": "", "files": []}
    if after:
        move_section(state, template, key, after=after)
    else:
        _bump_structural(state, f"La til seksjon {title}", section=key)
    return {"key": key, "title": title}


def maybe_save_template_offer(state: dict) -> bool:
    ov = overlay(state)
    if int(ov.get("structural_edits") or 0) >= 3 and not ov.get("save_template_offered"):
        ov["save_template_offered"] = True
        return True
    return False


def export_user_template(state: dict, template: dict, *, story: str = "") -> dict:
    """C3 — save overlay as owned template."""
    t = deepcopy(template)
    t["origin"] = "user_modified"
    t["badge"] = "Egen mal"
    t["ai_drafted"] = False
    t.pop("file", None)
    secs = effective_sections(state, template)
    for i, s in enumerate(secs, 1):
        s["position"] = i
    t["sections"] = secs
    if story:
        t.setdefault("description", story[:240])
    return t


def format_move_reply(key: str, template: dict, state: dict, lang: str = "no") -> str:
    titles = {s["section_key"]: s.get("title_no") or s.get("title") or s["section_key"]
              for s in effective_sections(state, template)}
    name = titles.get(key, key)
    if lang == "en":
        return f"Moved **{name}** — new order saved in version log. No regeneration run."
    return f"Flyttet **{name}** — ny rekkefølge logget i versjonsloggen. Ingen regenerering."


def save_template_offer_reply(lang: str = "no") -> str:
    if lang == "en":
        return "Want to save this layout as your own template for next time?"
    return "Vil du lagre dette som din egen mal for neste gang?"


def toggle_warning_reply(lang: str = "no") -> str:
    if lang == "en":
        return " Source register hidden — export traceability is reduced."
    return " Kilderegister skjult — sporbarhet i eksport er redusert."
