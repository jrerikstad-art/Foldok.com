"""Templates that learn.

"The template must be dynamic so the user feels in control" is really two
requirements, and the second one is the interesting half:

1.  A template supplies defaults, not a cage.  Anything it sets can be overridden
    by a pin, per block, at any time.
2.  A repeated override should stop being an override.  If the user drags every
    photograph to half width, the next document should place photographs at half
    width — the template should have *learned the rule*, not accumulated twelve
    exceptions.

``promote()`` does exactly that.  It looks at the user's pins, finds properties
where every block of a role agrees, and writes those into the role default;
everything else becomes a block-level default.  The result is a new template
version — never a mutation, so a promotion is reviewable and revertable like any
other change.

The honest limit: promotion generalises over *role*, which is a real signal, and
nothing else.  It will not invent a rule from two blocks that merely happen to
look alike.  ``min_examples`` guards that, and a wrong guess here is expensive
because it silently reshapes every future document.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any, Sequence

from .flow import BlockInput
from .model import Box, PageGrid
from .pins import PinStore

PROMOTABLE = ("col", "span", "rows", "align", "break_before", "keep_with_next")


@dataclass
class LayoutTemplate:
    id: str
    title: str = ""
    version: int = 1
    columns: int = 12
    page_size: str = "A4"
    role_defaults: dict[str, dict[str, Any]] = field(default_factory=dict)
    block_defaults: dict[str, dict[str, Any]] = field(default_factory=dict)
    locked_blocks: tuple[str, ...] = ()
    parent_version: int | None = None
    note: str = ""

    # -- reading ---------------------------------------------------------
    def scope(self) -> str:
        return f"{self.page_size}/{self.columns}"

    def defaults_for(self, blocks: Sequence[BlockInput], grid: PageGrid) -> dict[str, Box]:
        out: dict[str, Box] = {}
        for block in blocks:
            spec: dict[str, Any] = {
                "col": 0,
                "span": grid.columns,
                "align": "left",
                "role": block.role,
            }
            spec.update(_defaults_for_role(self, block.role))
            spec.update(self.block_defaults.get(block.id, {}))
            box = Box(
                block_id=block.id,
                col=int(spec.get("col", 0)),
                span=int(spec.get("span", grid.columns)),
                rows=None if spec.get("rows") is None else int(spec["rows"]),
                align=spec.get("align", "left"),
                min_span=int(spec.get("min_span", 1)),
                max_span=int(spec.get("max_span", grid.columns)),
                aspect=spec.get("aspect", block.aspect),
                keep_with_next=bool(spec.get("keep_with_next", False)),
                break_before=bool(spec.get("break_before", False)),
                role=block.role,
            )
            out[block.id] = box.clamped(grid)
        return out

    def is_locked(self, block_id: str) -> bool:
        return block_id in self.locked_blocks

    # -- learning --------------------------------------------------------
    def promote(
        self,
        pins: PinStore,
        blocks: Sequence[BlockInput],
        grid: PageGrid,
        *,
        min_examples: int = 2,
        note: str = "",
    ) -> tuple["LayoutTemplate", dict[str, Any]]:
        """Fold the user's pins into a new template version."""
        scope = grid.scoped()
        roles: dict[str, list[BlockInput]] = {}
        for b in blocks:
            roles.setdefault(b.role, []).append(b)

        new_roles = {k: dict(v) for k, v in self.role_defaults.items()}
        new_blocks = {k: dict(v) for k, v in self.block_defaults.items()}
        learned_rules: list[str] = []
        learned_blocks: list[str] = []

        consumed: set[tuple[str, str]] = set()

        for role, members in sorted(roles.items()):
            if len(members) < min_examples:
                continue
            for prop in PROMOTABLE:
                values = [pins.value(b.id, prop, scope, _MISSING) for b in members]
                if any(v is _MISSING for v in values):
                    continue
                first = values[0]
                if any(v != first for v in values):
                    continue
                new_roles.setdefault(role, {})[prop] = first
                learned_rules.append(f"{role}.{prop} = {first!r} (from {len(members)} blocks)")
                for b in members:
                    consumed.add((b.id, prop))

        for block in blocks:
            for prop in PROMOTABLE:
                if (block.id, prop) in consumed:
                    continue
                pin = pins.resolve(block.id, prop, scope)
                if pin is None or pin.layer != "user":
                    continue
                new_blocks.setdefault(block.id, {})[prop] = pin.value
                learned_blocks.append(f"{block.id}.{prop} = {pin.value!r}")

        promoted = replace(
            self,
            version=self.version + 1,
            parent_version=self.version,
            role_defaults=new_roles,
            block_defaults=new_blocks,
            note=note or f"promoted {len(learned_rules)} rule(s), {len(learned_blocks)} block default(s)",
        )
        report = {
            "version": promoted.version,
            "rules": learned_rules,
            "block_defaults": learned_blocks,
            "rule_count": len(learned_rules),
            "block_count": len(learned_blocks),
        }
        return promoted, report

    def diff(self, other: "LayoutTemplate") -> list[str]:
        out: list[str] = []
        for role in sorted(set(self.role_defaults) | set(other.role_defaults)):
            a = self.role_defaults.get(role, {})
            b = other.role_defaults.get(role, {})
            for prop in sorted(set(a) | set(b)):
                if a.get(prop) != b.get(prop):
                    out.append(f"{role}.{prop}: {a.get(prop)!r} -> {b.get(prop)!r}")
        for bid in sorted(set(self.block_defaults) | set(other.block_defaults)):
            a = self.block_defaults.get(bid, {})
            b = other.block_defaults.get(bid, {})
            for prop in sorted(set(a) | set(b)):
                if a.get(prop) != b.get(prop):
                    out.append(f"{bid}.{prop}: {a.get(prop)!r} -> {b.get(prop)!r}")
        return out

    # -- serialisation ---------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "version": self.version,
            "parent_version": self.parent_version,
            "columns": self.columns,
            "page_size": self.page_size,
            "role_defaults": {k: dict(sorted(v.items())) for k, v in sorted(self.role_defaults.items())},
            "block_defaults": {k: dict(sorted(v.items())) for k, v in sorted(self.block_defaults.items())},
            "locked_blocks": list(self.locked_blocks),
            "note": self.note,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "LayoutTemplate":
        return LayoutTemplate(
            id=d["id"],
            title=d.get("title", ""),
            version=int(d.get("version", 1)),
            columns=int(d.get("columns", 12)),
            page_size=d.get("page_size", "A4"),
            role_defaults={k: dict(v) for k, v in (d.get("role_defaults") or {}).items()},
            block_defaults={k: dict(v) for k, v in (d.get("block_defaults") or {}).items()},
            locked_blocks=tuple(d.get("locked_blocks", ())),
            parent_version=d.get("parent_version"),
            note=d.get("note", ""),
        )


class _Missing:
    def __repr__(self) -> str:  # pragma: no cover
        return "<missing>"


_MISSING = _Missing()


def _defaults_for_role(template: LayoutTemplate, role: str) -> dict[str, Any]:
    return dict(template.role_defaults.get(role, {}))


# ----------------------------------------------------------------------
def compliance_a4(columns: int = 12) -> LayoutTemplate:
    """A sane starting template: full-width prose, half-width figures, tables
    kept with the heading above them."""
    return LayoutTemplate(
        id="foldok.compliance.a4",
        title="Compliance document — A4",
        columns=columns,
        page_size="A4",
        role_defaults={
            "heading": {"col": 0, "span": columns, "keep_with_next": True},
            "text": {"col": 0, "span": columns},
            "callout": {"col": 0, "span": columns},
            "table": {"col": 0, "span": columns},
            "image": {"col": 0, "span": columns // 2},
            "diagram": {"col": 0, "span": columns // 2},
            "spacer": {"col": 0, "span": columns, "rows": 1},
        },
    )
