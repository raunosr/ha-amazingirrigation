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
    CONF_ENABLED,
    CONF_ET_SOURCE,
    CONF_FIELD_CAPACITY,
    CONF_FORECAST_AIR_HUMIDITY,
    CONF_FORECAST_AIR_TEMPERATURE,
    CONF_FORECAST_RAIN_AMOUNT,
    CONF_FORECAST_RAIN_PROBABILITY,
    CONF_GAIN_PER_LITER,
    CONF_GREENHOUSE,
    CONF_HISTORY_DAYS,
    CONF_HUMIDITY_SENSOR,
    CONF_LEARNING_ENABLED,
    CONF_MAX_LITERS,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_OBSERVED_AIR_HUMIDITY,
    CONF_OBSERVED_AIR_TEMPERATURE,
    CONF_OBSERVED_RAIN_AMOUNT,
    CONF_PROTECTED_RAIN,
    CONF_RAIN_SKIP_MM,
    CONF_RAIN_SKIP_PROBABILITY,
    CONF_SAFETY_BLOCKERS,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_WEEKDAYS,
    CONF_SEASON_END,
    CONF_SEASON_START,
    CONF_SOIL_TYPE,
    CONF_SOLAR_RADIATION,
    CONF_TARGET_MOISTURE,
    CONF_TARGET_MOISTURE_HIGH,
    CONF_TARGET_MOISTURE_LOW,
    CONF_TEMPERATURE_SENSOR,
    CONF_WEATHER_FORECAST_ENTITY,
    CONF_WILTING_POINT,
    CONF_WIND_SPEED,
    DEFAULT_MAX_LITERS,
    DEFAULT_RAIN_SKIP_MM,
    DEFAULT_RAIN_SKIP_PROBABILITY,
    DEFAULT_TARGET_MOISTURE,
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
    weather_forecast_entity: str | None = None
    observed_rain_amount: str | None = None
    safety_blockers: list[str] = field(default_factory=list)
    target_moisture: float | None = DEFAULT_TARGET_MOISTURE
    target_moisture_low: float | None = None
    target_moisture_high: float | None = None
    max_liters: float = DEFAULT_MAX_LITERS
    gain_per_liter: float | None = None
    rain_skip_mm: float = DEFAULT_RAIN_SKIP_MM
    rain_skip_probability: float = DEFAULT_RAIN_SKIP_PROBABILITY
    season_start: str | None = None
    season_end: str | None = None
    enabled: bool = True
    schedule_weekdays: list[str] = field(default_factory=list)
    schedule_times: list[str] = field(default_factory=list)
    field_capacity: float | None = None
    wilting_point: float | None = None
    learning_enabled: bool = False
    history_days: int = 60
    et_source: str = "auto"
    soil_type: str = "loam"
    greenhouse: bool = False
    protected_rain: bool = False
    temperature_sensor: str | None = None
    humidity_sensor: str | None = None
    observed_air_temperature: str | None = None
    observed_air_humidity: str | None = None
    forecast_air_temperature: str | None = None
    forecast_air_humidity: str | None = None
    wind_speed: str | None = None
    solar_radiation: str | None = None

    @classmethod
    def from_record(cls, zone_id: str, record: dict) -> ZoneConfig:
        """Build a ZoneConfig from a stored options record."""
        return cls(
            zone_id=zone_id,
            name=record.get(CONF_NAME, zone_id),
            moisture_sensors=list(record.get(CONF_MOISTURE_SENSORS, []) or []),
            forecast_rain_amount=record.get(CONF_FORECAST_RAIN_AMOUNT) or None,
            forecast_rain_probability=record.get(CONF_FORECAST_RAIN_PROBABILITY) or None,
            weather_forecast_entity=record.get(CONF_WEATHER_FORECAST_ENTITY) or None,
            observed_rain_amount=record.get(CONF_OBSERVED_RAIN_AMOUNT) or None,
            safety_blockers=list(record.get(CONF_SAFETY_BLOCKERS, []) or []),
            target_moisture=_as_float(record.get(CONF_TARGET_MOISTURE), DEFAULT_TARGET_MOISTURE),
            target_moisture_low=_as_float(record.get(CONF_TARGET_MOISTURE_LOW), None),
            target_moisture_high=_as_float(record.get(CONF_TARGET_MOISTURE_HIGH), None),
            max_liters=_as_float(record.get(CONF_MAX_LITERS), DEFAULT_MAX_LITERS),
            gain_per_liter=_as_float(record.get(CONF_GAIN_PER_LITER), None),
            rain_skip_mm=_as_float(record.get(CONF_RAIN_SKIP_MM), DEFAULT_RAIN_SKIP_MM),
            rain_skip_probability=_as_float(
                record.get(CONF_RAIN_SKIP_PROBABILITY), DEFAULT_RAIN_SKIP_PROBABILITY
            ),
            season_start=record.get(CONF_SEASON_START) or None,
            season_end=record.get(CONF_SEASON_END) or None,
            enabled=bool(record.get(CONF_ENABLED, True)),
            schedule_weekdays=list(record.get(CONF_SCHEDULE_WEEKDAYS, []) or []),
            schedule_times=list(record.get(CONF_SCHEDULE_TIMES, []) or []),
            field_capacity=_as_float(record.get(CONF_FIELD_CAPACITY), None),
            wilting_point=_as_float(record.get(CONF_WILTING_POINT), None),
            learning_enabled=bool(record.get(CONF_LEARNING_ENABLED, False)),
            history_days=_as_history_days(record.get(CONF_HISTORY_DAYS)),
            et_source=_select(record.get(CONF_ET_SOURCE), {"auto", "weather", "greenhouse"}, "auto"),
            soil_type=_select(record.get(CONF_SOIL_TYPE), {"loam", "sand", "clay"}, "loam"),
            greenhouse=bool(record.get(CONF_GREENHOUSE, False)),
            protected_rain=bool(record.get(CONF_PROTECTED_RAIN, False)),
            temperature_sensor=record.get(CONF_TEMPERATURE_SENSOR) or None,
            humidity_sensor=record.get(CONF_HUMIDITY_SENSOR) or None,
            observed_air_temperature=(
                record.get(CONF_OBSERVED_AIR_TEMPERATURE) or None
            ),
            observed_air_humidity=record.get(CONF_OBSERVED_AIR_HUMIDITY) or None,
            forecast_air_temperature=(
                record.get(CONF_FORECAST_AIR_TEMPERATURE) or None
            ),
            forecast_air_humidity=record.get(CONF_FORECAST_AIR_HUMIDITY) or None,
            wind_speed=record.get(CONF_WIND_SPEED) or None,
            solar_radiation=record.get(CONF_SOLAR_RADIATION) or None,
        )


def _as_float(value: object, default: float | None) -> float | None:
    """Coerce a stored value to float, falling back to a default."""
    if value in (None, ""):
        return default
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _select(value: object, allowed: set[str], default: str) -> str:
    """Return a stored select value when allowed, otherwise the default."""
    if not isinstance(value, str):
        return default
    normalized = value.strip().lower()
    return normalized if normalized in allowed else default


def _as_history_days(value: object, default: int = 60) -> int:
    """Coerce a stored history-window value to a bounded positive day count."""
    try:
        days = int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return min(365, max(1, days))


def _parse_md(value: str | None) -> tuple[int, int] | None:
    """Parse an ``MM-DD`` season boundary into a (month, day) tuple."""
    if not value:
        return None
    try:
        month, day = (int(part) for part in value.split("-", 1))
    except (ValueError, AttributeError):
        return None
    if 1 <= month <= 12 and 1 <= day <= 31:
        return (month, day)
    return None


def is_in_season(
    season_start: str | None, season_end: str | None, month: int, day: int
) -> bool:
    """Whether (month, day) falls within the inclusive season window.

    Both boundaries are ``MM-DD`` strings. A window that wraps the year end
    (start later than end, e.g. ``11-01``..``02-28``) is supported. If either
    boundary is missing or invalid, the zone is considered always in season.
    """
    start = _parse_md(season_start)
    end = _parse_md(season_end)
    if start is None or end is None:
        return True
    today = (month, day)
    if start <= end:
        return start <= today <= end
    # Wrap-around window: in season if at/after start OR at/before end.
    return today >= start or today <= end
