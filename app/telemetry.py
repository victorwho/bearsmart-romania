"""Typed event catalog and in-memory sink for BearSmart KPIs.

The dossier KPIs (28-day return, alert CTR, checklist completion by town) all
derive from this event stream. This module keeps an in-process ring buffer
that downstream workers in Horizon 4 will drain into a real store.

References: IMPLEMENTATION_PLAN.md §0.3.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Literal

logger = logging.getLogger("bearsmart.telemetry")

EventName = Literal[
    "alert_published",
    "alert_opened",
    "report_submitted",
    "report_status_changed",
    "checklist_item_completed",
    "trip_subscription_created",
    "town_page_viewed",
    "cert_evidence_uploaded",
    # Platform events introduced alongside H0/H1.
    "session_started",
    "emergency_gate_shown",
    "emergency_gate_dismissed",
    "moderation_decision_made",
]

KNOWN_EVENTS: frozenset[str] = frozenset(
    [
        "alert_published",
        "alert_opened",
        "report_submitted",
        "report_status_changed",
        "checklist_item_completed",
        "trip_subscription_created",
        "town_page_viewed",
        "cert_evidence_uploaded",
        "session_started",
        "emergency_gate_shown",
        "emergency_gate_dismissed",
        "moderation_decision_made",
    ]
)

_MAX_EVENTS = 1024


@dataclass(frozen=True)
class Event:
    name: str
    props: dict[str, Any]
    timestamp: str


@dataclass
class _Sink:
    buffer: deque[Event] = field(default_factory=lambda: deque(maxlen=_MAX_EVENTS))
    lock: Lock = field(default_factory=Lock)

    def record(self, event: Event) -> None:
        with self.lock:
            self.buffer.append(event)

    def snapshot(self) -> list[Event]:
        with self.lock:
            return list(self.buffer)

    def clear(self) -> None:
        with self.lock:
            self.buffer.clear()


_sink = _Sink()


def track(name: str, **props: Any) -> Event:
    """Record a typed event. Unknown names are logged and dropped in prod."""
    if name not in KNOWN_EVENTS:
        logger.warning("telemetry: unknown event name %r", name)
        # Still record it in dev so tests catch regressions.
    event = Event(
        name=name,
        props=dict(props),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    _sink.record(event)
    return event


def recent_events(limit: int = 100) -> list[Event]:
    events = _sink.snapshot()
    return events[-limit:]


def reset_for_tests() -> None:
    _sink.clear()
