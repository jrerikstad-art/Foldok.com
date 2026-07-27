"""The private client — the only thing in Foldok that talks to a model.

    client = PrivateClient(transport, vault, policy)
    reply = client.call("generate_section_prose", text, facts=facts)

What happens inside, in order, and every step is refusable:

    1  learn entities from the fact base (confirmed, cited values)
    2  mask the text; re-scan for leaks; refuse rather than send if any survive
    3  build the envelope and show it — the "what leaves this machine" panel
    4  policy check: purpose allowed, size budget, images approved
    5  send via the transport
    6  unmask locally; report any entity the model invented
    7  log, content-free

**The transport is the enterprise tier.**  A company that insists on its own
Anthropic or Azure deployment swaps one object; nothing else in Foldok changes.
That is a licence conversation, not a fork — which is the right shape, because a
junior engineer should be able to open the tab and work on day one, and the
enterprise version should be something a procurement department buys later
rather than something a user has to configure first.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Protocol, Sequence, runtime_checkable

from .detect import populate
from .envelope import PURPOSES, AuditLog, Envelope, ImageRef
from .policy import DEFAULT, OFFLINE, OPEN, STRICT, Decision, Policy, preset
from .vault import EntityVault, LeakRefused, UnmaskResult


class CallRefused(Exception):
    """The call was not sent, with the reason the user should see."""


@runtime_checkable
class Transport(Protocol):
    """Where the masked payload goes.  Swap this for BYO endpoint."""

    id: str

    def send(self, envelope: Envelope) -> str: ...


@dataclass
class EchoTransport:
    """Offline transport for tests and for the 'nothing left this machine' demo."""

    id: str = "echo"
    reply: str = ""

    def send(self, envelope: Envelope) -> str:
        return self.reply or envelope.text


@dataclass
class CallResult:
    text: str                                # unmasked, ready to use
    envelope: Envelope
    unmask: UnmaskResult
    raw: str = ""                            # masked reply, for the panel

    @property
    def invented_entities(self) -> tuple[str, ...]:
        return self.unmask.unknown_tokens

    @property
    def ok(self) -> bool:
        return self.unmask.ok

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope": self.envelope.to_dict(),
            "restored": self.unmask.restored,
            "invented_entities": list(self.invented_entities),
            "missing_tokens": list(self.unmask.missing_tokens),
        }


class PrivateClient:
    def __init__(
        self,
        transport: Transport,
        vault: EntityVault | None = None,
        policy: Policy | str | None = None,
        audit: AuditLog | None = None,
        model: str = "",
        clock=time.time,
    ) -> None:
        self.transport = transport
        self.vault = vault or EntityVault()
        self.policy = preset(policy) if isinstance(policy, str) else (policy or DEFAULT)
        self.audit = audit or AuditLog(clock=clock)
        self.model = model
        self._clock = clock
        self.pending: Envelope | None = None
        self.last_decision: Decision | None = None

    # -- preparing --------------------------------------------------------
    def prepare(
        self,
        purpose: str,
        text: str,
        *,
        facts: Iterable[dict] = (),
        images: Sequence[ImageRef] = (),
        meta: dict[str, Any] | None = None,
        structured: bool = False,
    ) -> Envelope:
        """Everything up to the point of sending.  Call this to render the panel.

        ``structured=True`` declares that the payload is a descriptor the engine
        built (a gap record), not free project text. Some purposes accept
        nothing else — ``gap_fill_code`` in particular, whose name reads like
        arbitrary code and must never carry project source.
        """
        meta = dict(meta or {})
        if structured:
            meta["structured"] = True
        if purpose not in PURPOSES:
            raise CallRefused(
                f"'{purpose}' is not one of the four purposes the engine calls a model for "
                f"({', '.join(PURPOSES)}). Everything else runs locally."
            )
        populate(
            self.vault, text=text, facts=facts,
            include_uncertain=self.policy.redact_uncertain,
        )
        try:
            masked = self.vault.mask(text, strict=self.policy.strict_masking)
        except LeakRefused as exc:
            envelope = Envelope(purpose=purpose, text="", model=self.model, created_at=self._clock())
            self.audit.add(envelope, "refused", str(exc))
            raise CallRefused(str(exc)) from exc

        envelope = Envelope.build(
            purpose, masked, model=self.model, images=images, meta=meta, clock=self._clock
        )
        self.pending = envelope
        return envelope

    def decide(self, envelope: Envelope) -> Decision:
        """Policy as data, so the UI can render it.

        A verdict of ``needs_approval`` is not a failure — it is the product
        asking a person to look at what is about to leave. That is the whole
        point of the panel, and it cannot be drawn from a stack trace.
        """
        policy = self.policy
        if not policy.allowed_purposes:
            policy = replace(policy, allowed_purposes=PURPOSES)
        return policy.decide(envelope)

    # -- sending -----------------------------------------------------------
    def send(self, envelope: Envelope, *, approved: bool = False) -> CallResult:
        decision = self.decide(envelope)
        self.last_decision = decision
        if decision.blocked:
            self.audit.add(envelope, "refused", decision.summary())
            raise CallRefused(decision.summary())
        if decision.needs_approval and not approved:
            self.audit.add(envelope, "refused", decision.summary())
            raise CallRefused(
                decision.summary()
                + " — show the preview and pass approved=True once a person has read it"
            )
        try:
            raw = self.transport.send(envelope)
        except Exception as exc:  # noqa: BLE001
            self.audit.add(envelope, "failed", f"{type(exc).__name__}: {exc}")
            raise
        result = self.vault.unmask(raw, sent=envelope.tokens_used)
        self.audit.add(envelope, "sent", decision.summary() if decision.reasons else "")
        self.pending = None
        return CallResult(text=result.text, envelope=envelope, unmask=result, raw=raw)

    def call(
        self,
        purpose: str,
        text: str,
        *,
        facts: Iterable[dict] = (),
        images: Sequence[ImageRef] = (),
        meta: dict[str, Any] | None = None,
        structured: bool = False,
        approved: bool = False,
    ) -> CallResult:
        return self.send(
            self.prepare(purpose, text, facts=facts, images=images, meta=meta,
                         structured=structured),
            approved=approved,
        )

    # -- reporting ----------------------------------------------------------
    def summary(self) -> dict[str, Any]:
        totals = self.audit.totals()
        totals.update(
            {
                "transport": self.transport.id,
                "model": self.model,
                "vault_entities": len(self.vault),
                "policy": self.policy.describe(),
            }
        )
        return totals

    def receipt(self) -> str:
        """The line that goes on the demo, and eventually in the document.

        "This package was compiled on your machine. Here is everything that
        left." — for most jobs the honest number is small, and for some it is
        zero.
        """
        t = self.audit.totals()
        if t["sent"] == 0:
            return "Nothing left this machine. The whole document was built locally."
        return (
            f"{t['sent']} call(s) left this machine, {t['bytes_sent']} bytes total, "
            f"with {len(self.vault)} identifier(s) replaced by tokens before sending."
        )


# ----------------------------------------------------------------------
def enterprise(transport: Transport, **kw: Any) -> PrivateClient:
    """A customer's own endpoint.

    The only difference from the default build is which transport is passed in.
    Same engine, same masking, same audit log — their deployment, their tokens,
    their retention terms, and Foldok is not in the data path at all.
    """
    return PrivateClient(transport=transport, **kw)
