"""Bounded, integration-owned Irrigation History for explainability.

The integration keeps a compact, bounded recent history per Irrigation Zone so
a user can see *why* a zone did or did not water: the Run Requests it received,
the Irrigation Decisions that resulted, the Rain Events observed, and the
Watering Events that actually ran. Long-term numeric charts are left to Home
Assistant's recorder/statistics; this store is only the recent explanation log.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum

from homeassistant.util import dt as dt_util

from .const import HISTORY_LIMIT


class ObservationKind(StrEnum):
    """The kind of evidence captured in Irrigation History."""

    RUN_REQUEST = "run_request"
    DECISION = "decision"
    RAIN_EVENT = "rain_event"
    WATERING_EVENT = "watering_event"


@dataclass(frozen=True)
class Observation:
    """A single timestamped entry in a zone's Irrigation History."""

    kind: ObservationKind
    data: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: dt_util.utcnow().isoformat())

    def as_dict(self) -> dict:
        """Serialise for sensor attributes."""
        return {"kind": self.kind.value, "timestamp": self.timestamp, **self.data}


class IrrigationHistory:
    """A bounded ring buffer of a single zone's recent Observations."""

    def __init__(self, zone_id: str, limit: int = HISTORY_LIMIT) -> None:
        """Initialise an empty bounded history for one zone."""
        self.zone_id = zone_id
        self._entries: deque[Observation] = deque(maxlen=max(1, limit))
        self._listeners: list = []

    def record(self, kind: ObservationKind, data: dict | None = None) -> Observation:
        """Append an Observation, evicting the oldest when full."""
        observation = Observation(kind=kind, data=dict(data or {}))
        self._entries.append(observation)
        for listener in list(self._listeners):
            listener()
        return observation

    def add_listener(self, listener) -> callable:
        """Register an update callback; returns an unsubscribe handle."""
        self._listeners.append(listener)

        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    @property
    def count(self) -> int:
        """Number of entries currently held."""
        return len(self._entries)

    @property
    def last(self) -> Observation | None:
        """The most recent Observation, or ``None`` when empty."""
        return self._entries[-1] if self._entries else None

    def recent(self, limit: int | None = None) -> list[dict]:
        """Most-recent-first list of serialised entries (optionally capped)."""
        entries = list(reversed(self._entries))
        if limit is not None:
            entries = entries[:limit]
        return [entry.as_dict() for entry in entries]


def build_histories(zones: dict[str, dict]) -> dict[str, IrrigationHistory]:
    """Create an IrrigationHistory for each configured zone."""
    return {zone_id: IrrigationHistory(zone_id) for zone_id in zones}
