"""Foldok signals — analytics that obeys the same rules as everything else.

    s = Signals(log_path, consent)
    s.folder_opened(files=42)
    s.on_refusal(exc)                     # every refusal is feedback
    print(s.report())                     # where people stop, and where it said no

Content-free by construction: events carry numbers and codes from a fixed
vocabulary. There is no field that would accept a file name.
"""

from .journey import FUNNEL, FUNNEL_LABELS, Consent, EventLog, Funnel, failure_summary, funnel
from .model import (
    EVENTS,
    VOCAB,
    Event,
    Feedback,
    SignalRefused,
    new_install_id,
    scrub_context,
    vocabulary,
    vocabulary_json,
)
from .signals import REFUSAL_REASONS, LocalSink, Signals, Sink

__all__ = [
    "Consent", "EVENTS", "Event", "EventLog", "FUNNEL", "FUNNEL_LABELS", "Feedback",
    "Funnel", "LocalSink", "REFUSAL_REASONS", "SignalRefused", "Signals", "Sink",
    "VOCAB", "failure_summary", "funnel", "new_install_id", "scrub_context",
    "vocabulary", "vocabulary_json",
]

__version__ = "0.77.0"
