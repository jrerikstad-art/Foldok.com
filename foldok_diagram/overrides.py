"""Pin store — how a user takes manual control of the drawing.

The problem:  the engine computes geometry, so any hand adjustment gets wiped on
the next relayout.  The fix is NOT to store hand-edited geometry as the truth.
It is to store the *user's intent* as a pin, in its own layer, and let the
engine compute everything that is not pinned.

    layer priority:   user  >  ai  >  engine (computed)

Properties of this design:

*  A relayout never destroys a hand edit.
*  A user can pin x and leave y automatic, or pin one waypoint of a run and let
   the rest route itself.  Pinning is per-property, not per-object.
*  ``release()`` hands a property back to the engine.  This is the undo for
   "I fiddled with it and now it looks worse than auto".
*  ``lock`` stops the AI layer and bulk relayout from proposing anything on
   that property.  A signed-off figure can be frozen.
*  Pins are scoped to a profile, so moving a pump in the piping view does not
   move it in the wiring view.
*  Pins serialise to sorted JSONL: a hand adjustment is one readable line in a
   git diff, and a re-issued document shows exactly what a human changed.
*  If the graph changes under a pin (component deleted, port renamed) the pin
   becomes an orphan and is REPORTED, never silently dropped.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

Layer = Literal["engine", "ai", "user"]
LAYER_RANK: dict[str, int] = {"engine": 0, "ai": 1, "user": 2}

GLOBAL_SCOPE = "*"

# Pinnable properties.  Anything not in here is not user-adjustable geometry and
# belongs in the graph itself.
PROPS = {
    "position",       # {"x": float|None, "y": float|None} — partial allowed
    "rotation",       # int, 0/90/180/270
    "column",         # int — force a component into a layout column
    "waypoints",      # [{"x": float, "y": float}, ...] explicit route anchors
    "label_offset",   # {"dx": float, "dy": float}
    "label_side",     # "above"|"below"|"left"|"right"
    "hidden",         # bool — drop from this profile without deleting
    "style",          # {token: value} — per-element style escape hatch
    "size_label",     # str — force the printed size on a run
}


def target_component(component_id: str) -> str:
    return f"component:{component_id}"


def target_connection(connection_id: str) -> str:
    return f"connection:{connection_id}"


def target_port_label(component_id: str, port_id: str) -> str:
    return f"portlabel:{component_id}:{port_id}"


@dataclass
class Pin:
    target: str
    prop: str
    value: Any
    layer: Layer = "user"
    scope: str = GLOBAL_SCOPE      # profile id, or "*" for every profile
    locked: bool = False
    note: str | None = None
    created_at: float = field(default_factory=lambda: 0.0)

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
            target=d["target"],
            prop=d["prop"],
            value=d["value"],
            layer=d.get("layer", "user"),
            scope=d.get("scope", GLOBAL_SCOPE),
            locked=bool(d.get("locked", False)),
            note=d.get("note"),
            created_at=float(d.get("created_at", 0.0)),
        )


@dataclass
class Orphan:
    pin: Pin
    reason: str


class PinStore:
    """Ordered, de-duplicated set of pins.  One store per document."""

    def __init__(self, pins: Iterable[Pin] | None = None, clock=time.time) -> None:
        self._pins: dict[tuple[str, str, str], Pin] = {}
        self._clock = clock
        for p in pins or ():
            self._pins[p.key()] = p

    # -- write ----------------------------------------------------------
    def pin(
        self,
        target: str,
        prop: str,
        value: Any,
        *,
        layer: Layer = "user",
        scope: str = GLOBAL_SCOPE,
        note: str | None = None,
        locked: bool | None = None,
    ) -> Pin:
        if prop not in PROPS:
            raise ValueError(f"'{prop}' is not a pinnable property; pinnable: {sorted(PROPS)}")
        existing = self._pins.get((scope, target, prop))
        if existing is not None and existing.locked and layer != "user":
            # A locked pin can only be changed by an explicit user action.
            return existing
        keep_locked = existing.locked if (existing and locked is None) else bool(locked)
        p = Pin(
            target=target,
            prop=prop,
            value=value,
            layer=layer,
            scope=scope,
            locked=keep_locked,
            note=note,
            created_at=self._clock(),
        )
        self._pins[p.key()] = p
        return p

    def release(self, target: str, prop: str, *, scope: str = GLOBAL_SCOPE, force: bool = False) -> bool:
        """Hand a property back to the engine.  Returns True if a pin was removed."""
        p = self._pins.get((scope, target, prop))
        if p is None:
            return False
        if p.locked and not force:
            return False
        del self._pins[(scope, target, prop)]
        return True

    def release_target(self, target: str, *, scope: str | None = None, force: bool = False) -> int:
        n = 0
        for key in list(self._pins):
            s, t, _ = key
            if t != target:
                continue
            if scope is not None and s != scope:
                continue
            if self._pins[key].locked and not force:
                continue
            del self._pins[key]
            n += 1
        return n

    def set_lock(self, target: str, prop: str, locked: bool, *, scope: str = GLOBAL_SCOPE) -> bool:
        p = self._pins.get((scope, target, prop))
        if p is None:
            return False
        p.locked = locked
        return True

    # -- read -----------------------------------------------------------
    def resolve(self, target: str, prop: str, profile_id: str) -> Pin | None:
        """Highest-ranked pin for this property, profile scope beating global."""
        candidates = [
            p
            for key, p in self._pins.items()
            if key[1] == target and key[2] == prop and key[0] in (profile_id, GLOBAL_SCOPE)
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda p: (LAYER_RANK[p.layer], 1 if p.scope == profile_id else 0, p.created_at)
        )
        return candidates[-1]

    def value(self, target: str, prop: str, profile_id: str, default: Any = None) -> Any:
        p = self.resolve(target, prop, profile_id)
        return default if p is None else p.value

    def is_locked(self, target: str, prop: str, profile_id: str) -> bool:
        p = self.resolve(target, prop, profile_id)
        return bool(p and p.locked)

    def all(self) -> list[Pin]:
        return [self._pins[k] for k in sorted(self._pins)]

    def for_profile(self, profile_id: str) -> list[Pin]:
        return [p for p in self.all() if p.scope in (profile_id, GLOBAL_SCOPE)]

    def user_pins(self) -> list[Pin]:
        return [p for p in self.all() if p.layer == "user"]

    def __len__(self) -> int:
        return len(self._pins)

    # -- integrity ------------------------------------------------------
    def orphans(self, graph) -> list[Orphan]:
        """Pins whose target no longer exists.  Report these; never auto-drop."""
        out: list[Orphan] = []
        for p in self.all():
            kind, _, rest = p.target.partition(":")
            if kind == "component":
                if graph.component(rest) is None:
                    out.append(Orphan(p, f"component '{rest}' is not in the graph"))
            elif kind == "connection":
                if graph.connection(rest) is None:
                    out.append(Orphan(p, f"connection '{rest}' is not in the graph"))
            elif kind == "portlabel":
                cid, _, pid = rest.partition(":")
                comp = graph.component(cid)
                if comp is None:
                    out.append(Orphan(p, f"component '{cid}' is not in the graph"))
                elif comp.port(pid) is None:
                    out.append(Orphan(p, f"port '{pid}' is not on component '{cid}'"))
        return out

    # -- serialisation --------------------------------------------------
    def to_jsonl(self) -> str:
        """One pin per line, ordered scope/target/prop.

        Key order is fixed rather than alphabetical so that sorting the file by
        line and sorting it by pin identity give the same answer — that is what
        keeps a hand adjustment to one readable line in a git diff.
        """
        return "\n".join(json.dumps(p.to_dict(), ensure_ascii=False) for p in self.all())

    @staticmethod
    def from_jsonl(text: str) -> "PinStore":
        pins = [Pin.from_dict(json.loads(line)) for line in text.splitlines() if line.strip()]
        return PinStore(pins)
