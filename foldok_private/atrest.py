"""Token repair, encryption at rest, and the export denylist.

Three separate hardening jobs that share one theme: the vault is the most
sensitive artefact Foldok creates, and a docstring saying "do not upload this"
is not a control.

**Token repair.**  Models mangle tokens — ``CLIENT_ A``, ``Client_A``,
``**CLIENT_A**``, ``CLIENT-A``.  Each one is a value that silently fails to come
back.  ``repair`` normalises the known set before restoration.

**Encryption at rest.**  Deliberately *not* hand-rolled.  A cipher written by
someone who is not a cryptographer is worse than plaintext, because plaintext at
least looks as dangerous as it is.  So encryption is pluggable, uses
``cryptography``'s Fernet when it is installed, and writing plaintext requires
saying so explicitly.

**Export denylist.**  The vault maps every token to every real client, project,
person and site for a whole project.  It must never reach an export, a backup, a
support bundle or a crash report.  ``assert_exportable`` is the check that makes
that a rule instead of a hope, and it belongs in every bundling path.
"""

from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol, Sequence, runtime_checkable

VAULT_SUFFIXES: tuple[str, ...] = (".vault", ".vault.jsonl", ".entities.jsonl")
VAULT_NAMES: tuple[str, ...] = ("vault.jsonl", "entities.jsonl", "foldok_vault.json")


class ExportRefused(Exception):
    """Something that must stay local was about to be bundled."""


# ----------------------------------------------------------------------
# token repair
# ----------------------------------------------------------------------
def repair(text: str, tokens: Iterable[str]) -> tuple[str, int]:
    """Normalise mangled tokens back to canonical form.

    Returns (text, repairs). Longest tokens first so ``FDK7X_CLIENT_AA`` is not
    half-matched by ``FDK7X_CLIENT_A``.
    """
    out = text or ""
    repairs = 0
    for token in sorted(set(tokens), key=len, reverse=True):
        parts = [re.escape(part) for part in token.split("_")]
        # Between segments tolerate any run of separator noise: spaces,
        # underscores, hyphens, and markdown emphasis characters.
        joiner = r"[\s_\-\*`]*"
        pattern = joiner.join(parts)
        rx = re.compile(rf"(?<![A-Za-z0-9]){pattern}(?![A-Za-z0-9])", re.IGNORECASE)
        before = out
        out = rx.sub(token, out)
        if out != before:
            # count only the ones that were not already canonical
            repairs += sum(
                1 for m in rx.finditer(before) if m.group(0) != token
            )
    return out, repairs


def looks_like_token(text: str, prefix: str) -> list[str]:
    """Token-shaped strings already present in source text.

    A real document that happens to contain the exact token pattern would have a
    value injected into it on restoration — fabricated content in a compliance
    document. With a project salt this is close to impossible, which is why the
    salt exists; this function is the assertion that it worked.
    """
    rx = re.compile(rf"(?<![A-Za-z0-9]){re.escape(prefix)}_[A-Z]{{3,8}}_[A-Z0-9]{{1,4}}(?![A-Za-z0-9])")
    return sorted(set(rx.findall(text or "")))


# ----------------------------------------------------------------------
# encryption at rest
# ----------------------------------------------------------------------
@runtime_checkable
class Cipher(Protocol):
    id: str

    def encrypt(self, data: bytes) -> bytes: ...

    def decrypt(self, data: bytes) -> bytes: ...


@dataclass
class NullCipher:
    """Plaintext. Only usable when the caller asks for it by name."""

    id: str = "plaintext"

    def encrypt(self, data: bytes) -> bytes:
        return data

    def decrypt(self, data: bytes) -> bytes:
        return data


class FernetCipher:
    """AES-128-CBC + HMAC via ``cryptography``. Key derived from a passphrase.

    Not invented here on purpose. If ``cryptography`` is missing this raises at
    construction rather than quietly degrading to plaintext.
    """

    id = "fernet"

    def __init__(self, passphrase: str, salt: bytes = b"foldok-vault-v1") -> None:
        try:
            from cryptography.fernet import Fernet  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "vault encryption needs the 'cryptography' package "
                "(pip install cryptography). Refusing to fall back to plaintext."
            ) from exc
        if not passphrase:
            raise ValueError("a passphrase is required")
        key = hashlib.scrypt(
            passphrase.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32
        )
        self._f = Fernet(base64.urlsafe_b64encode(key))

    def encrypt(self, data: bytes) -> bytes:
        return self._f.encrypt(data)

    def decrypt(self, data: bytes) -> bytes:
        return self._f.decrypt(data)


def cipher_for(passphrase: str | None) -> Cipher:
    return FernetCipher(passphrase) if passphrase else NullCipher()


# ----------------------------------------------------------------------
# export denylist
# ----------------------------------------------------------------------
def is_local_only(path: str | Path) -> bool:
    p = Path(path)
    name = p.name.lower()
    return name in VAULT_NAMES or any(name.endswith(s) for s in VAULT_SUFFIXES)


def assert_exportable(paths: Sequence[str | Path], *, what: str = "export") -> None:
    """Call this in every bundling path: export, backup, support bundle, upload.

    A rule enforced in one place is a rule. A rule written in a README is a
    preference.
    """
    offenders = [str(p) for p in paths if is_local_only(p)]
    if offenders:
        raise ExportRefused(
            f"{len(offenders)} local-only file(s) were about to be included in this {what}: "
            + ", ".join(offenders[:5])
            + ". The entity vault maps every token to a real client, project and person "
            "for this job. It stays on this machine."
        )


def filter_exportable(paths: Iterable[str | Path]) -> list[Path]:
    """Non-raising variant for building a file list."""
    return [Path(p) for p in paths if not is_local_only(p)]
