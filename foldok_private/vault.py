"""The entity vault — real values in, tokens out, and back again.

The design premise, which only works because of how Foldok is already built:

    The model does not need "Equinor · Johan Sverdrup · P-4102 · Aker Solutions".
    It needs the *shape* of the sentence.

So the four call sites send ``CLIENT_A · PROJECT_B · TAG_1 · VENDOR_C`` and the
local fact base puts the real values back afterwards.  ChatGPT and Claude cannot
do this, because for them the text *is* the working memory.  Foldok holds ground
truth in code, on the machine — "AI proposes, code decides" turns out to have a
privacy consequence nobody designed for.

Three properties this file has to guarantee, in order of how badly each one
fails if it is wrong:

1.  **No leak.**  ``assert_no_leak`` re-scans the masked text for every real
    value the vault knows, including case and spelling variants.  If anything
    survives, the call is refused rather than sent.  A near-miss here is the
    whole product's credibility.
2.  **Exact restoration.**  "CLIENT_A's cable" must come back as "Equinor's
    cable".  Tokens are plain ``UPPER_SNAKE`` because models preserve those and
    mangle unusual glyphs.
3.  **Honest reporting.**  If the model returns a token the vault never issued,
    that is an invented entity, and it is surfaced rather than silently passed
    through — the same stance the rest of the product takes on unsourced facts.

The vault never leaves the machine.  It is the one file in Foldok that must not
be uploaded, synced, or included in a support bundle.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

EntityKind = Literal[
    "client", "project", "person", "vendor", "site", "tag", "serial",
    "document_no", "email", "phone", "org_no", "coordinate", "url", "path", "other",
]

# Token prefixes.  Short, readable, and safe through a language model.
PREFIX: dict[str, str] = {
    "client": "CLIENT", "project": "PROJECT", "person": "PERSON", "vendor": "VENDOR",
    "site": "SITE", "tag": "TAG", "serial": "SERIAL", "document_no": "DOC",
    "email": "EMAIL", "phone": "PHONE", "org_no": "ORGNO", "coordinate": "COORD",
    "url": "URL", "path": "PATH", "other": "ENTITY",
}

TOKEN_RE = re.compile(r"\b([A-Z]{3,8})_([A-Z0-9]{1,4})\b")
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _fold(text: str) -> str:
    """Case- and accent-insensitive form, for variant matching."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.lower()).strip()


def _label(index: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA.  Stable and readable."""
    out = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        out = LETTERS[rem] + out
    return out


@dataclass
class Entity:
    token: str                       # "CLIENT_A"
    kind: EntityKind
    value: str                       # the real value — never leaves this machine
    aliases: tuple[str, ...] = ()    # "Equinor ASA", "EQNR", surname alone
    source: str = ""                 # where it was learned: fact id, file, user
    locked: bool = False             # user pinned this mapping

    def variants(self) -> list[str]:
        seen: dict[str, str] = {}
        for v in (self.value, *self.aliases):
            if v and _fold(v) not in seen:
                seen[_fold(v)] = v
        return sorted(seen.values(), key=len, reverse=True)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"token": self.token, "kind": self.kind, "value": self.value}
        if self.aliases:
            d["aliases"] = list(self.aliases)
        if self.source:
            d["source"] = self.source
        if self.locked:
            d["locked"] = True
        return d


@dataclass
class MaskResult:
    text: str
    entities: tuple[Entity, ...] = ()
    replacements: int = 0
    leaked: tuple[str, ...] = ()     # real values still present — must be empty

    @property
    def clean(self) -> bool:
        return not self.leaked

    def to_dict(self) -> dict[str, Any]:
        return {
            "chars": len(self.text),
            "entities": len(self.entities),
            "replacements": self.replacements,
            "tokens": sorted({e.token for e in self.entities}),
            "clean": self.clean,
        }


@dataclass
class UnmaskResult:
    text: str
    restored: int = 0
    unknown_tokens: tuple[str, ...] = ()   # the model invented an entity
    missing_tokens: tuple[str, ...] = ()   # a token we sent never came back

    @property
    def ok(self) -> bool:
        return not self.unknown_tokens


class LeakRefused(Exception):
    """A real value survived masking.  The call must not be sent."""


class EntityVault:
    """Local, per-project, never uploaded."""

    def __init__(self, entities: Iterable[Entity] | None = None) -> None:
        self._by_token: dict[str, Entity] = {}
        self._by_fold: dict[str, Entity] = {}
        self._counters: dict[str, int] = {}
        for e in entities or ():
            self._install(e)

    # -- building --------------------------------------------------------
    def _install(self, entity: Entity) -> Entity:
        self._by_token[entity.token] = entity
        for v in entity.variants():
            self._by_fold[_fold(v)] = entity
        prefix, _, label = entity.token.rpartition("_")
        self._counters[prefix] = max(self._counters.get(prefix, 0), _index_of(label) + 1)
        return entity

    def add(
        self,
        value: str,
        kind: EntityKind = "other",
        *,
        aliases: Iterable[str] = (),
        source: str = "",
        locked: bool = False,
    ) -> Entity:
        """Register a real value.  Returns the existing entity if already known,
        so the same client always gets the same token across a whole project."""
        value = (value or "").strip()
        if not value:
            raise ValueError("cannot vault an empty value")
        existing = self._by_fold.get(_fold(value))
        if existing is not None:
            merged = tuple(dict.fromkeys((*existing.aliases, *(a for a in aliases if a))))
            if merged != existing.aliases:
                existing.aliases = merged
                self._install(existing)
            return existing
        prefix = PREFIX.get(kind, "ENTITY")
        token = f"{prefix}_{_label(self._counters.get(prefix, 0))}"
        return self._install(
            Entity(token=token, kind=kind, value=value,
                   aliases=tuple(a for a in aliases if a), source=source, locked=locked)
        )

    def learn(self, pairs: Iterable[tuple[str, str]], *, source: str = "") -> list[Entity]:
        """Bulk-register from the fact base: [(value, kind), ...].

        This is why no NER model is needed — Foldok already knows the client, the
        project, the tags and the people, because they are facts with citations.
        Detection is mostly lookup.
        """
        return [self.add(v, k, source=source) for v, k in pairs if v]  # type: ignore[arg-type]

    # -- reading ---------------------------------------------------------
    def entity(self, token: str) -> Entity | None:
        return self._by_token.get(token)

    def of_value(self, value: str) -> Entity | None:
        return self._by_fold.get(_fold(value))

    def entities(self) -> list[Entity]:
        return [self._by_token[t] for t in sorted(self._by_token)]

    def __len__(self) -> int:
        return len(self._by_token)

    # -- masking ---------------------------------------------------------
    def mask(self, text: str, *, strict: bool = True) -> MaskResult:
        if not text:
            return MaskResult(text="", entities=(), replacements=0)
        out = text
        used: list[Entity] = []
        count = 0
        # Longest variants first: "Aker Solutions AS" before "Aker".
        pairs: list[tuple[str, Entity]] = []
        for entity in self.entities():
            for variant in entity.variants():
                pairs.append((variant, entity))
        pairs.sort(key=lambda p: len(p[0]), reverse=True)

        for variant, entity in pairs:
            pattern = re.compile(_boundary(variant), re.IGNORECASE)
            out, n = pattern.subn(entity.token, out)
            if n:
                count += n
                if entity not in used:
                    used.append(entity)

        leaked = self._scan(out)
        if leaked and strict:
            raise LeakRefused(
                f"{len(leaked)} real value(s) survived masking and the call was not sent: "
                + ", ".join(sorted(leaked)[:5])
                + ". This usually means a spelling variant is missing from the vault — "
                "add it as an alias, or send this passage by hand."
            )
        return MaskResult(text=out, entities=tuple(used), replacements=count, leaked=tuple(leaked))

    def _scan(self, masked: str) -> list[str]:
        """Re-scan for anything the vault knows.  Belt and braces on purpose:
        a near-miss here is the product's credibility."""
        folded = _fold(masked)
        hits: list[str] = []
        for entity in self.entities():
            for variant in entity.variants():
                v = _fold(variant)
                if len(v) < 3:
                    continue
                if re.search(rf"(?<![a-z0-9]){re.escape(v)}(?![a-z0-9])", folded):
                    hits.append(variant)
        return sorted(set(hits))

    def assert_no_leak(self, masked: str) -> None:
        leaked = self._scan(masked)
        if leaked:
            raise LeakRefused(f"real value(s) present in outbound text: {', '.join(leaked[:5])}")

    # -- unmasking -------------------------------------------------------
    def unmask(self, text: str, *, sent: Iterable[str] = ()) -> UnmaskResult:
        """Put the real values back, and report anything the model invented."""
        restored = 0
        unknown: list[str] = []
        sent_tokens = set(sent)

        def repl(match: re.Match[str]) -> str:
            nonlocal restored
            token = match.group(0)
            entity = self._by_token.get(token)
            if entity is None:
                unknown.append(token)
                return token
            restored += 1
            return entity.value

        out = TOKEN_RE.sub(repl, text or "")
        missing = sorted(t for t in sent_tokens if t not in text)
        return UnmaskResult(
            text=out,
            restored=restored,
            unknown_tokens=tuple(sorted(set(unknown))),
            missing_tokens=tuple(missing),
        )

    # -- persistence -----------------------------------------------------
    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(e.to_dict(), ensure_ascii=False) for e in self.entities())

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.write_text(self.to_jsonl(), encoding="utf-8")
        return p

    @staticmethod
    def from_jsonl(text: str) -> "EntityVault":
        vault = EntityVault()
        for line in text.splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            vault._install(
                Entity(
                    token=d["token"], kind=d.get("kind", "other"), value=d["value"],
                    aliases=tuple(d.get("aliases", ())), source=d.get("source", ""),
                    locked=bool(d.get("locked", False)),
                )
            )
        return vault

    @staticmethod
    def load(path: str | Path) -> "EntityVault":
        p = Path(path)
        return EntityVault.from_jsonl(p.read_text(encoding="utf-8")) if p.exists() else EntityVault()


def _boundary(variant: str) -> str:
    """Match a variant as a whole word, tolerating possessives and hyphens."""
    escaped = re.escape(variant).replace(r"\ ", r"[\s\-]+")
    return rf"(?<![\w]){escaped}(?:'s|’s|s)?(?![\w])"


def _index_of(label: str) -> int:
    total = 0
    for ch in label:
        if ch not in LETTERS:
            return 0
        total = total * 26 + (LETTERS.index(ch) + 1)
    return total - 1
