"""Pure decision logic for guided Field Capacity Discovery.

Field Capacity (FC) is the *Drained Upper Limit* (FAO-56, Allen et al. 1998):
the moisture a soil holds once free gravity drainage has become negligible. The
recognised in-situ method saturates the profile, covers the soil so only gravity
drainage occurs (no evaporation), and reads FC when drainage slows to a trickle.

This module owns the *when to record FC* decision only — the part automation can
do well. The human does what automation can't: deeply saturate the sensor and
cover the soil. Given the sampled post-saturation drainage curve, this module
decides whether to keep waiting, record FC, or abort.

The decision is **rate-based**, not clock-based: FC is declared when the drainage
rate ``dθ/dt`` falls below a threshold that is *relative* to the initial
post-saturation rate (so it adapts to texture — sand drains in ~a day, clay in
several) with a small absolute floor, bounded by a minimum wait (skip the early
transient) and a maximum wait (graceful fallback). Everything is in the same
sensor moisture-% space the rest of the controller learns in, so no volumetric
conversion is needed and the result is internally consistent for scheduling.

Deliberately free of Home Assistant imports so it can be unit-tested in isolation;
the Home Assistant orchestration lives in :mod:`discovery_controller`.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime

from .const import (
    DISCOVERY_AWAITING_SATURATION,
    DISCOVERY_CANCELLED,
    DISCOVERY_COMPLETED,
    DISCOVERY_FAILED,
    DISCOVERY_IDLE,
    DISCOVERY_MAX_WAIT_HOURS,
    DISCOVERY_MIN_WAIT_HOURS,
    DISCOVERY_MONITORING,
    DISCOVERY_RATE_ABS_FLOOR,
    DISCOVERY_RATE_RELATIVE_STOP,
    DISCOVERY_RISE_ABORT_DELTA,
    DISCOVERY_STABILITY_WINDOW_HOURS,
)
from .waterbalance import (
    FIELD_CAPACITY_MAX,
    FIELD_CAPACITY_MIN,
    MOISTURE_MAX,
    MOISTURE_MIN,
)

# Decision outcomes returned by :func:`evaluate_discovery`.
OUTCOME_CONTINUE = "continue"
OUTCOME_RECORD = "record"
OUTCOME_ABORT = "abort"


@dataclass(frozen=True)
class DiscoverySample:
    """One moisture observation taken while monitoring drainage."""

    at: datetime
    moisture: float


@dataclass(frozen=True)
class DiscoveryConfig:
    """Tunable thresholds for the FC decision (all in sensor moisture-%)."""

    min_wait_hours: float = DISCOVERY_MIN_WAIT_HOURS
    max_wait_hours: float = DISCOVERY_MAX_WAIT_HOURS
    stability_window_hours: float = DISCOVERY_STABILITY_WINDOW_HOURS
    rate_relative_stop: float = DISCOVERY_RATE_RELATIVE_STOP
    rate_abs_floor: float = DISCOVERY_RATE_ABS_FLOOR
    rise_abort_delta: float = DISCOVERY_RISE_ABORT_DELTA


@dataclass(frozen=True)
class DiscoveryDecision:
    """The outcome of evaluating a drainage curve at one moment."""

    outcome: str
    reason: str
    elapsed_hours: float
    drainage_rate: float | None = None
    provisional_fc: float | None = None
    field_capacity: float | None = None


def _finite(value: object) -> float | None:
    """Return ``value`` as a finite float, or ``None``."""
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _valid_samples(samples: list[DiscoverySample]) -> list[DiscoverySample]:
    """Drop rail (0/100) and non-finite readings, keep chronological order."""
    clean: list[DiscoverySample] = []
    for sample in samples:
        moisture = _finite(sample.moisture)
        if moisture is None or moisture <= MOISTURE_MIN or moisture >= MOISTURE_MAX:
            continue
        clean.append(DiscoverySample(at=sample.at, moisture=moisture))
    clean.sort(key=lambda item: item.at)
    return clean


def _hours(later: datetime, earlier: datetime) -> float:
    """Signed hours between two timestamps."""
    return (later - earlier).total_seconds() / 3600.0


def _window_drainage_rate(
    samples: list[DiscoverySample], now: datetime, window_hours: float
) -> tuple[float | None, float | None]:
    """Mean drainage rate (%/h drop) and mean moisture over a trailing window.

    Returns ``(rate, mean_moisture)``. ``rate`` is positive while the soil is
    drying and ``None`` when the window holds fewer than two samples or spans no
    time.
    """
    recent = [s for s in samples if _hours(now, s.at) <= window_hours]
    if len(recent) < 2:
        return (None, recent[-1].moisture if recent else None)
    span = _hours(recent[-1].at, recent[0].at)
    mean_moisture = sum(s.moisture for s in recent) / len(recent)
    if span <= 0:
        return (None, mean_moisture)
    rate = (recent[0].moisture - recent[-1].moisture) / span
    return (rate, mean_moisture)


def _initial_drainage_rate(
    samples: list[DiscoverySample], window_hours: float
) -> float | None:
    """Drainage rate over the first ``window_hours`` of monitoring (>= 0)."""
    if len(samples) < 2:
        return None
    start = samples[0].at
    early = [s for s in samples if _hours(s.at, start) <= window_hours]
    if len(early) < 2:
        return None
    span = _hours(early[-1].at, early[0].at)
    if span <= 0:
        return None
    return max(0.0, (early[0].moisture - early[-1].moisture) / span)


def _clamp_fc(value: float) -> float:
    """Clamp a candidate Field Capacity to its physical sensor-% bounds."""
    return max(FIELD_CAPACITY_MIN, min(FIELD_CAPACITY_MAX, value))


def evaluate_discovery(
    samples: list[DiscoverySample],
    config: DiscoveryConfig,
    *,
    now: datetime,
) -> DiscoveryDecision:
    """Decide whether to keep monitoring, record FC, or abort.

    ``samples`` is the moisture curve captured since monitoring began (covered,
    saturated soil draining under gravity). The decision:

    * **abort** if the soil re-wets mid-test (moisture climbs back up by more than
      ``rise_abort_delta`` above its running minimum) — rain, a leak or a failed
      cover — because that violates the pure-drainage assumption.
    * **record** FC once at least ``min_wait_hours`` have elapsed *and* the trailing
      drainage rate has fallen below ``max(rate_abs_floor, rate_relative_stop *
      initial_rate)`` — the Drained Upper Limit knee. FC is the smoothed moisture
      over the trailing stability window.
    * **record** FC as a fallback once ``max_wait_hours`` is reached, using the
      current smoothed moisture (noting the max-wait fallback).
    * **continue** otherwise.
    """
    clean = _valid_samples(samples)
    if not clean:
        return DiscoveryDecision(
            outcome=OUTCOME_CONTINUE,
            reason="Waiting for a valid moisture reading",
            elapsed_hours=0.0,
        )

    elapsed = max(0.0, _hours(now, clean[0].at))
    rate, window_mean = _window_drainage_rate(
        clean, now, config.stability_window_hours
    )
    provisional_fc = _clamp_fc(window_mean) if window_mean is not None else None

    # Re-wetting guard: during pure drainage moisture only falls; a climb back up
    # signals rain / leak / cover failure.
    running_min = clean[0].moisture
    for sample in clean:
        running_min = min(running_min, sample.moisture)
    if clean[-1].moisture - running_min > config.rise_abort_delta:
        return DiscoveryDecision(
            outcome=OUTCOME_ABORT,
            reason="Moisture rose during monitoring (rain, leak or cover failed)",
            elapsed_hours=elapsed,
            drainage_rate=rate,
            provisional_fc=provisional_fc,
        )

    if elapsed >= config.max_wait_hours:
        fc = provisional_fc if provisional_fc is not None else _clamp_fc(clean[-1].moisture)
        return DiscoveryDecision(
            outcome=OUTCOME_RECORD,
            reason="Maximum wait reached; recording current moisture as Field Capacity",
            elapsed_hours=elapsed,
            drainage_rate=rate,
            provisional_fc=fc,
            field_capacity=fc,
        )

    if elapsed < config.min_wait_hours or rate is None:
        return DiscoveryDecision(
            outcome=OUTCOME_CONTINUE,
            reason="Monitoring drainage",
            elapsed_hours=elapsed,
            drainage_rate=rate,
            provisional_fc=provisional_fc,
        )

    initial_rate = _initial_drainage_rate(clean, config.stability_window_hours)
    threshold = config.rate_abs_floor
    if initial_rate is not None:
        threshold = max(threshold, config.rate_relative_stop * initial_rate)

    if rate <= threshold:
        fc = provisional_fc if provisional_fc is not None else _clamp_fc(clean[-1].moisture)
        return DiscoveryDecision(
            outcome=OUTCOME_RECORD,
            reason="Drainage settled; recording Field Capacity",
            elapsed_hours=elapsed,
            drainage_rate=rate,
            provisional_fc=fc,
            field_capacity=fc,
        )

    return DiscoveryDecision(
        outcome=OUTCOME_CONTINUE,
        reason="Monitoring drainage",
        elapsed_hours=elapsed,
        drainage_rate=rate,
        provisional_fc=provisional_fc,
    )


@dataclass
class DiscoveryState:
    """Persisted, human-facing state of a zone's discovery workflow.

    Stored as a plain dict inside :class:`state.ZoneState` (mirroring
    ``learning_state``); the controller converts to and from this dataclass.
    """

    phase: str = DISCOVERY_IDLE
    started_at: str | None = None
    monitor_started_at: str | None = None
    updated_at: str | None = None
    peak_moisture: float | None = None
    last_moisture: float | None = None
    drainage_rate: float | None = None
    provisional_fc: float | None = None
    result_fc: float | None = None
    reason: str | None = None

    def to_dict(self) -> dict:
        """Serialise for the ZoneState store."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> DiscoveryState:
        """Rebuild from a persisted record, ignoring unknown keys."""
        if not data:
            return cls()
        known = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in data.items() if key in known})


_INSTRUCTIONS: dict[str, str] = {
    DISCOVERY_IDLE: "Idle. Press Start Field Capacity Discovery to begin.",
    DISCOVERY_AWAITING_SATURATION: (
        "Water this zone until the moisture sensor stops rising (fully saturated), "
        "then cover the soil so it cannot dry by evaporation. When done, press "
        "'Saturated & Covered — Begin Monitoring'."
    ),
    DISCOVERY_MONITORING: (
        "Monitoring drainage. Keep the soil covered and do not water. Field "
        "Capacity will be recorded automatically once drainage settles."
    ),
    DISCOVERY_COMPLETED: (
        "Field Capacity recorded. You can uncover the soil and resume normal "
        "watering."
    ),
    DISCOVERY_FAILED: "Discovery could not complete. See the reason and try again.",
    DISCOVERY_CANCELLED: "Discovery cancelled.",
}


def instruction_for_phase(phase: str) -> str:
    """Return the human-readable instruction for a discovery phase."""
    return _INSTRUCTIONS.get(phase, _INSTRUCTIONS[DISCOVERY_IDLE])
