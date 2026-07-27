"""Foldok private calls — the model works on masked text; the machine holds the truth.

    client = PrivateClient(transport, vault, policy)
    envelope = client.prepare("generate_section_prose", text, facts=facts)
    print(envelope.preview())          # what leaves this machine, before it leaves
    result = client.send(envelope, approved=True)
    result.text                        # real values restored locally

Everything else in Foldok — indexing, gaps, layout, diagrams, tables, export —
runs with the network off. Only four purposes ever reach a model.
"""

from .atrest import (
    Cipher,
    ExportRefused,
    FernetCipher,
    NullCipher,
    assert_exportable,
    filter_exportable,
    is_local_only,
    repair,
)
from .client import (
    CallRefused,
    CallResult,
    EchoTransport,
    PrivateClient,
    Transport,
    enterprise,
)
from .policy import (
    DEFAULT,
    OFFLINE,
    OPEN,
    PRESETS,
    STRICT,
    Decision,
    Flag,
    Policy,
    Reason,
    content_flags,
    preset,
)
from .detect import Candidate, detect, from_facts, populate, review
from .envelope import PURPOSES, AuditLog, Envelope, ImageRef, Record
from .vault import (
    Entity,
    EntityKind,
    EntityVault,
    LeakRefused,
    MaskResult,
    UnmaskResult,
)

__all__ = [
    "AuditLog", "CallRefused", "CallResult", "Candidate", "Cipher", "DEFAULT",
    "Decision", "EchoTransport", "Entity", "EntityKind", "EntityVault", "Envelope",
    "ExportRefused", "FernetCipher", "Flag", "ImageRef", "LeakRefused", "MaskResult",
    "NullCipher", "OFFLINE", "OPEN", "PRESETS", "PURPOSES", "Policy", "PrivateClient",
    "Reason", "Record", "STRICT", "Transport", "UnmaskResult", "assert_exportable",
    "content_flags", "detect", "enterprise", "filter_exportable", "from_facts",
    "is_local_only", "populate", "preset", "repair", "review",
]

__version__ = "0.76.0"
