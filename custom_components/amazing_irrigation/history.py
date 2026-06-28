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


# Human-readable phrasing for each machine-readable Decision reason.
_DECISION_REASON_LABELS: dict[str, str] = {
    "safety_blocker": "blocked by safety",
    "forced": "manual run",
    "disabled": "zone disabled",
    "out_of_season": "out of season",
    "moisture_unavailable": "moisture unavailable",
    "zone_locked": "actuator busy",
    "no_target": "no target set",
    "above_target": "above target",
    "rain_sufficient": "rain sufficient",
    "rain_reduce": "rain expected",
    "below_target": "below target",
}


def _format_liters(value) -> str:
    """Format a liter amount compactly (e.g. ``8 L`` or ``4.5 L``)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0 L"
    if number == int(number):
        return f"{int(number)} L"
    return f"{number:.1f} L"


def summarize_observation(observation: Observation) -> str:
    """Return a short human-readable summary of a single Observation.

    The phrasing is intended to be the *state* of the Irrigation History
    sensor, so it must be concise and meaningful to a non-technical user.
    """
    data = observation.data
    if observation.kind is ObservationKind.RUN_REQUEST:
        if data.get("zone_locked"):
            return "Run requested (actuator busy)"
        return "Run requested (manual)" if data.get("force") else "Run requested"

    if observation.kind is ObservationKind.DECISION:
        action = data.get("action")
        reason = _DECISION_REASON_LABELS.get(
            data.get("reason"), str(data.get("reason") or "")
        )
        liters = _format_liters(data.get("recommended_liters", 0))
        if action == "water":
            return f"Watering {liters}"
        if action == "reduce":
            return f"Reduced to {liters} ({reason})" if reason else f"Reduced to {liters}"
        if action == "skip":
            return f"Skipped: {reason}" if reason else "Skipped"
        return "Decision recorded"

    if observation.kind is ObservationKind.RAIN_EVENT:
        delta = data.get("delta_mm")
        try:
            delta_value = float(delta)
        except (TypeError, ValueError):
            delta_value = 0.0
        sign = "+" if delta_value >= 0 else ""
        return f"Rain {sign}{delta_value:g} mm"

    if observation.kind is ObservationKind.WATERING_EVENT:
        status = data.get("status")
        measured = data.get("measured_liters")
        requested = data.get("requested_liters")
        amount = _format_liters(measured if measured is not None else requested)
        if data.get("confirmed") or status == "confirmed":
            return f"Watered {amount}"
        if status == "skipped":
            return "Watering skipped"
        if status == "no_actuator":
            return "No actuator configured"
        if status == "failed":
            return "Watering failed"
        if status == "stopped":
            return "Watering stopped"
        if status == "commanded":
            return f"Watering started ({amount})"
        return "Watering event"

    return "Observation"


@dataclass(frozen=True)
class Observation:
    """A single timestamped entry in a zone's Irrigation History."""

    kind: ObservationKind
    data: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: dt_util.utcnow().isoformat())

    def as_dict(self) -> dict:
        """Serialise for sensor attributes."""
        return {
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "summary": self.summary,
            **self.data,
        }

    @property
    def summary(self) -> str:
        """A short human-readable description of this Observation."""
        return summarize_observation(self)


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
