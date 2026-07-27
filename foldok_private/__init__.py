"""Foldok private calls — the model works on masked text; the machine holds the truth.

    client = PrivateClient(transport, vault, policy)
    envelope = client.prepare("generate_section_prose", text, facts=facts)
    print(envelope.preview())          # what leaves this machine, before it leaves
    result = client.send(envelope, approved=True)
    result.text                        # real values restored locally

Everything else in Foldok — indexing, gaps, layout, diagrams, tables, export —
runs with the network off. Only four purposes ever reach a model.
"""

from .client import (
    OFFLINE,
    CallRefused,
    CallResult,
    EchoTransport,
    Policy,
    PrivateClient,
    Transport,
    enterprise,
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
    "AuditLog", "CallRefused", "CallResult", "Candidate", "EchoTransport", "Entity",
    "EntityKind", "EntityVault", "Envelope", "ImageRef", "LeakRefused", "MaskResult",
    "OFFLINE", "PURPOSES", "Policy", "PrivateClient", "Record", "Transport",
    "UnmaskResult", "detect", "enterprise", "from_facts", "populate", "review",
]

__version__ = "0.75.0"
