"""Irrigation Zone model and pure Zone Moisture aggregation.

An Irrigation Zone is an independently watered section of plants. A zone can
reference one or more soil moisture sensors, but the integration always reduces
them to a single canonical *Zone Moisture* value used for decisions.

This slice is observe-only: zones expose read-only state and never actuate
water. The aggregation function here is intentionally pure (no Home Assistant
dependency) so the decision-engine slice can build on it and test it cheaply.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .const import (
    CONF_FORECAST_RAIN_AMOUNT,
    CONF_FORECAST_RAIN_PROBABILITY,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_OBSERVED_RAIN_AMOUNT,
    CONF_SAFETY_BLOCKERS,
)


@dataclass(frozen=True)
class ZoneMoisture:
    """Result of aggregating a zone's moisture sensor readings.

    ``value`` is ``None`` only when no valid reading exists (fail closed).
    ``degraded`` is ``True`` when at least one configured sensor is missing a
    valid reading but a Zone Moisture could still be computed from the rest.
    """

    value: float | None
    used: int
    configured: int

    @property
    def degraded(self) -> bool:
        """Whether some configured sensors were unavailable."""
        return self.used < self.configured

    @property
    def available(self) -> bool:
        """Whether a usable Zone Moisture value exists."""
        return self.value is not None


def aggregate_zone_moisture(readings: list[float | None]) -> ZoneMoisture:
    """Reduce raw moisture readings to a single Zone Moisture value.

    The default aggregation strategy is the *minimum valid reading*: the
    driest sensor governs the zone so watering decisions stay conservative.
    Invalid readings (``None``) are dropped; if every reading is invalid the
    result is unavailable so callers can fail closed.
    """
    valid = [value for value in readings if value is not None]
    if not valid:
        return ZoneMoisture(value=None, used=0, configured=len(readings))
    return ZoneMoisture(value=min(valid), used=len(valid), configured=len(readings))


@dataclass(frozen=True)
class ZoneConfig:
    """A single Irrigation Zone's stored configuration.

    Stored inside the integration entry's options under ``zones`` keyed by
    ``zone_id``. Only inputs needed for observe-only state live here; actuator
    and decision settings arrive in later slices.
    """

    zone_id: str
    name: str
    moisture_sensors: list[str] = field(default_factory=list)
    forecast_rain_amount: str | None = None
    forecast_rain_probability: str | None = None
    observed_rain_amount: str | None = None
    safety_blockers: list[str] = field(default_factory=list)

    @classmethod
    def from_record(cls, zone_id: str, record: dict) -> ZoneConfig:
        """Build a ZoneConfig from a stored options record."""
        return cls(
            zone_id=zone_id,
            name=record.get(CONF_NAME, zone_id),
            moisture_sensors=list(record.get(CONF_MOISTURE_SENSORS, []) or []),
            forecast_rain_amount=record.get(CONF_FORECAST_RAIN_AMOUNT) or None,
            forecast_rain_probability=record.get(CONF_FORECAST_RAIN_PROBABILITY) or None,
            observed_rain_amount=record.get(CONF_OBSERVED_RAIN_AMOUNT) or None,
            safety_blockers=list(record.get(CONF_SAFETY_BLOCKERS, []) or []),
        )
