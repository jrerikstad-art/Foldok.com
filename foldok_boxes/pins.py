"""Layout pins — how the user takes control without breaking the flow.

Identical idea to the diagram engine's pin store, deliberately: one concept for
the whole product.  The flow engine computes where every block goes; a hand edit
records what the user *wanted*; the user's layer wins.

    user  >  template  >  engine (computed)

What this buys, and each one is a thing users complain about in editors that
store geometry directly:

*  Reflow never destroys a hand edit.  Add a paragraph above and the pinned
   two-column figure stays two columns.
*  Pin the width, leave the height automatic.  Pinning is per-property.
*  ``release()`` puts a block back under the engine's control — a real "reset",
   not an approximation.
*  Pins are scoped to the page geometry, so a layout tuned for A4 does not
   corrupt the same document at Letter or in a 6-column theme.
*  ``lock`` freezes a signed-off page against template changes.
*  Pins serialise sorted, so "what did the user change" is one readable diff,
   and promoting them into a template is a copy rather than an inference.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

Layer = Literal["engine", "template", "user"]
LAYER_RANK: dict[str, int] = {"engine": 0, "template": 1, "user": 2}
GLOBAL_SCOPE = "*"

PROPS = {
    "col",             # int — start column
    "span",            # int — width in columns
    "rows",            # int | None — explicit height in baseline units
    "align",           # left | center | right | justify
    "order",           # int — position in document order
    "break_before",    # bool
    "keep_with_next",  # bool
    "hidden",          # bool
}


def target(block_id: str) -> str:
    return f"block:{block_id}"


@dataclass
class Pin:
    target: str
    prop: str
    value: Any
    layer: Layer = "user"
    scope: str = GLOBAL_SCOPE
    locked: bool = False
    note: str | None = None
    created_at: float = 0.0

    def key(self) -> tuple[str, str, str]:
        return (self.scope, self.target, self.prop)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "scope": self.scope,
            "target": self.target,
            "prop": self.prop,
            "value": self.value,
            "layer": self.layer,
        }
        if self.locked:
            d["locked"] = True
        if self.note:
            d["note"] = self.note
        if self.created_at:
            d["created_at"] = round(self.created_at, 3)
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Pin":
        return Pin(
            target=d["target"], prop=d["prop"], value=d["value"],
            layer=d.get("layer", "user"), scope=d.get("scope", GLOBAL_SCOPE),
            locked=bool(d.get("locked", False)), note=d.get("note"),
            created_at=float(d.get("created_at", 0.0)),
        )


class PinStore:
    def __init__(self, pins: Iterable[Pin] | None = None, clock=time.time) -> None:
        self._pins: dict[tuple[str, str, str], Pin] = {}
        self._clock = clock
        for p in pins or ():
            self._pins[p.key()] = p

    # -- write ----------------------------------------------------------
    def pin(
        self,
        block_id: str,
        prop: str,
        value: Any,
        *,
        layer: Layer = "user",
        scope: str = GLOBAL_SCOPE,
        note: str | None = None,
        locked: bool | None = None,
    ) -> Pin:
        if prop not in PROPS:
            raise ValueError(f"'{prop}' is not a pinnable layout property; pinnable: {sorted(PROPS)}")
        t = target(block_id)
        existing = self._pins.get((scope, t, prop))
        if existing is not None and existing.locked and layer != "user":
            return existing
        keep = existing.locked if (existing and locked is None) else bool(locked)
        p = Pin(t, prop, value, layer, scope, keep, note, self._clock())
        self._pins[p.key()] = p
        return p

    def release(self, block_id: str, prop: str, *, scope: str = GLOBAL_SCOPE, force: bool = False) -> bool:
        key = (scope, target(block_id), prop)
        p = self._pins.get(key)
        if p is None or (p.locked and not force):
            return False
        del self._pins[key]
        return True

    def release_block(self, block_id: str, *, scope: str | None = None, force: bool = False) -> int:
        t = target(block_id)
        n = 0
        for key in list(self._pins):
            s, tt, _ = key
            if tt != t or (scope is not None and s != scope):
                continue
            if self._pins[key].locked and not force:
                continue
            del self._pins[key]
            n += 1
        return n

    def set_lock(self, block_id: str, prop: str, locked: bool, *, scope: str = GLOBAL_SCOPE) -> bool:
        p = self._pins.get((scope, target(block_id), prop))
        if p is None:
            return False
        p.locked = locked
        return True

    # -- read -----------------------------------------------------------
    def resolve(self, block_id: str, prop: str, scope: str) -> Pin | None:
        t = target(block_id)
        candidates = [
            p for key, p in self._pins.items()
            if key[1] == t and key[2] == prop and key[0] in (scope, GLOBAL_SCOPE)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda p: (LAYER_RANK[p.layer], 1 if p.scope == scope else 0, p.created_at))
        return candidates[-1]

    def value(self, block_id: str, prop: str, scope: str, default: Any = None) -> Any:
        p = self.resolve(block_id, prop, scope)
        return default if p is None else p.value

    def pinned_props(self, block_id: str, scope: str) -> tuple[str, ...]:
        return tuple(sorted(p for p in PROPS if self.resolve(block_id, p, scope) is not None))

    def is_locked(self, block_id: str, prop: str, scope: str) -> bool:
        p = self.resolve(block_id, prop, scope)
        return bool(p and p.locked)

    def all(self) -> list[Pin]:
        return [self._pins[k] for k in sorted(self._pins)]

    def user_pins(self) -> list[Pin]:
        return [p for p in self.all() if p.layer == "user"]

    def for_scope(self, scope: str) -> list[Pin]:
        return [p for p in self.all() if p.scope in (scope, GLOBAL_SCOPE)]

    def blocks(self) -> list[str]:
        return sorted({p.target.split(":", 1)[1] for p in self.all()})

    def __len__(self) -> int:
        return len(self._pins)

    # -- integrity -------------------------------------------------------
    def orphans(self, known_block_ids: Iterable[str]) -> list[Pin]:
        known = set(known_block_ids)
        return [p for p in self.all() if p.target.split(":", 1)[1] not in known]

    # -- serialisation ---------------------------------------------------
    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(p.to_dict(), ensure_ascii=False) for p in self.all())

    @staticmethod
    def from_jsonl(text: str) -> "PinStore":
        return PinStore([Pin.from_dict(json.loads(l)) for l in text.splitlines() if l.strip()])
