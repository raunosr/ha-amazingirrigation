"""Bootstrap water-balance learning from recorder history.

The top half of this module is deliberately pure: timestamped series are turned
into :class:`EstimatorObservation` objects and fitted without importing Home
Assistant.  The bottom half is thin Home Assistant glue that fetches recorder
states, delegates to the pure core, and persists successful results.
"""

from __future__ import annotations

import bisect
import logging
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .estimator import EstimatorObservation, JointEstimator
from .state import ZoneStateStore, apply_model_to_state, params_from_state
from .waterbalance import Climate, WaterBalanceParams, default_params
from .zone import ZoneConfig, aggregate_zone_moisture

_LOGGER = logging.getLogger(__name__)

DEFAULT_HISTORY_DAYS = 30
DEFAULT_MIN_INTERVAL_HOURS = 0.25
DEFAULT_MAX_INTERVAL_HOURS = 24.0
DEFAULT_MIN_BOOTSTRAP_INTERVALS = 12
DEFAULT_INFERRED_IRRIGATION_RISE = 3.0
_RAIN_EXPLAINS_RISE_MM = 0.5


@dataclass(frozen=True, order=True)
class SeriesPoint:
    """One finite numeric sample at a timezone-aware or naive timestamp."""

    timestamp: datetime
    value: float


@dataclass(frozen=True)
class IrrigationEvent:
    """Water applied at a point in time.

    ``liters`` is ``None`` for inferred moisture-step events.  Unknown inferred
    volume is intentionally not fabricated; assembly treats it as zero liters so
    it does not teach ``eta_irr`` from guessed data.
    """

    timestamp: datetime
    liters: float | None = None
    inferred: bool = False


@dataclass(frozen=True)
class TimeSeries:
    """Ordered finite numeric samples with as-of lookup."""

    points: tuple[SeriesPoint, ...]

    def __init__(self, points: Iterable[SeriesPoint | tuple[datetime, float]]) -> None:
        """Build a sorted, de-duplicated series from arbitrary points."""
        parsed: dict[datetime, float] = {}
        for point in points:
            if isinstance(point, SeriesPoint):
                timestamp = point.timestamp
                value = point.value
            else:
                timestamp, value = point
            finite = _finite_float(value)
            if finite is not None:
                parsed[timestamp] = finite
        ordered = tuple(SeriesPoint(timestamp, parsed[timestamp]) for timestamp in sorted(parsed))
        object.__setattr__(self, "points", ordered)

    @property
    def timestamps(self) -> tuple[datetime, ...]:
        """Return sample timestamps in ascending order."""
        return tuple(point.timestamp for point in self.points)

    def __bool__(self) -> bool:
        """Whether the series has at least one sample."""
        return bool(self.points)

    def as_of(self, timestamp: datetime) -> float | None:
        """Return the last value at or before ``timestamp``."""
        index = bisect.bisect_right(self.timestamps, timestamp) - 1
        if index < 0:
            return None
        return self.points[index].value

    def delta(self, start: datetime, end: datetime) -> float:
        """Return non-negative cumulative-counter increase over an interval."""
        start_value = self.as_of(start)
        end_value = self.as_of(end)
        if start_value is None or end_value is None:
            return 0.0
        return max(0.0, end_value - start_value)


@dataclass(frozen=True)
class BootstrapResult:
    """Outcome of fitting history into a water-balance model."""

    params: WaterBalanceParams
    confidence: dict[str, float]
    covariance: list[list[float]]
    intervals_used: int
    days_span: float
    summary: str
    success: bool = True
    reason: str | None = None


def assemble_observations(
    moisture_series: TimeSeries,
    *,
    rain_series: TimeSeries | None = None,
    temp_series: TimeSeries | None = None,
    humidity_series: TimeSeries | None = None,
    wind_series: TimeSeries | None = None,
    solar_series: TimeSeries | None = None,
    irrigation_events: Sequence[IrrigationEvent] | None = None,
    protected_rain: bool = False,
    max_interval_hours: float = DEFAULT_MAX_INTERVAL_HOURS,
    min_interval_hours: float = DEFAULT_MIN_INTERVAL_HOURS,
) -> list[EstimatorObservation]:
    """Turn consecutive moisture samples into estimator observations."""
    points = moisture_series.points
    if len(points) < 2:
        return []

    max_hours = max(0.0, float(max_interval_hours))
    min_hours = max(0.0, float(min_interval_hours))
    events = sorted(irrigation_events or (), key=lambda event: event.timestamp)
    observations: list[EstimatorObservation] = []
    start = points[0]

    for end in points[1:]:
        hours = _hours_between(start.timestamp, end.timestamp)
        if hours <= 0.0:
            start = end
            continue
        if max_hours and hours > max_hours:
            start = end
            continue
        if min_hours and hours < min_hours:
            continue

        liters = sum(
            event.liters
            for event in events
            if event.liters is not None
            and start.timestamp < event.timestamp <= end.timestamp
        )
        rain_mm = rain_series.delta(start.timestamp, end.timestamp) if rain_series else 0.0
        observations.append(
            EstimatorObservation(
                theta_start=start.value,
                theta_end=end.value,
                dt=hours,
                liters=max(0.0, liters),
                rain_mm=rain_mm,
                climate=_climate_as_of(
                    start.timestamp,
                    temp_series=temp_series,
                    humidity_series=humidity_series,
                    wind_series=wind_series,
                    solar_series=solar_series,
                ),
                protected_rain=protected_rain,
            )
        )
        start = end

    return observations


def detect_irrigation_events(
    moisture_series: TimeSeries,
    *,
    recorded_events: Sequence[IrrigationEvent] | None = None,
    rain_series: TimeSeries | None = None,
    min_rise: float = DEFAULT_INFERRED_IRRIGATION_RISE,
) -> list[IrrigationEvent]:
    """Return explicit watering events, or infer step-rises unexplained by rain."""
    if recorded_events:
        return sorted(recorded_events, key=lambda event: event.timestamp)

    threshold = max(0.0, float(min_rise))
    inferred: list[IrrigationEvent] = []
    points = moisture_series.points
    for start, end in zip(points, points[1:], strict=False):
        rise = end.value - start.value
        if rise < threshold:
            continue
        rain_delta = rain_series.delta(start.timestamp, end.timestamp) if rain_series else 0.0
        if rain_delta >= _RAIN_EXPLAINS_RISE_MM:
            continue
        inferred.append(IrrigationEvent(end.timestamp, liters=None, inferred=True))
    return inferred


def bootstrap_from_series(
    prior_params: WaterBalanceParams,
    observations: Sequence[EstimatorObservation],
    *,
    overrides: Mapping[str, float] | None = None,
    min_intervals: int = DEFAULT_MIN_BOOTSTRAP_INTERVALS,
) -> BootstrapResult:
    """Fit :class:`JointEstimator` from observations, or report insufficiency."""
    bounded_prior = prior_params.clamped()
    intervals = list(observations)
    days_span = sum(max(0.0, _finite_float(obs.dt) or 0.0) for obs in intervals) / 24.0
    if len(intervals) < min_intervals:
        summary = (
            f"Insufficient history: {len(intervals)} intervals over "
            f"{days_span:.1f} days"
        )
        return BootstrapResult(
            params=bounded_prior,
            confidence={},
            covariance=[],
            intervals_used=len(intervals),
            days_span=days_span,
            summary=summary,
            success=False,
            reason="insufficient_history",
        )

    estimator = JointEstimator(
        prior_params=bounded_prior,
        prior_cov=[16.0, 16.0, 2.0, 0.20],
        measurement_noise=0.25,
        overrides=overrides,
    )
    params = estimator.fit(intervals)
    covariance = estimator.covariance.tolist()
    summary = f"Learned from {len(intervals)} intervals over {days_span:.1f} days"
    return BootstrapResult(
        params=params,
        confidence=estimator.confidence,
        covariance=covariance,
        intervals_used=len(intervals),
        days_span=days_span,
        summary=summary,
    )


def _climate_as_of(
    timestamp: datetime,
    *,
    temp_series: TimeSeries | None,
    humidity_series: TimeSeries | None,
    wind_series: TimeSeries | None,
    solar_series: TimeSeries | None,
) -> Climate | None:
    temp = temp_series.as_of(timestamp) if temp_series else None
    humidity = humidity_series.as_of(timestamp) if humidity_series else None
    wind = wind_series.as_of(timestamp) if wind_series else None
    solar = solar_series.as_of(timestamp) if solar_series else None
    if temp is None and humidity is None and wind is None and solar is None:
        return None
    return Climate(temp, humidity, wind_ms=wind, solar=solar)


def _hours_between(start: datetime, end: datetime) -> float:
    hours = (end - start).total_seconds() / 3600.0
    return hours if math.isfinite(hours) else 0.0


def _finite_float(value: object) -> float | None:
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


# --- Home Assistant glue -------------------------------------------------


async def async_bootstrap_zone(
    hass: Any,
    zone: ZoneConfig,
    store: ZoneStateStore,
    *,
    days: int = DEFAULT_HISTORY_DAYS,
) -> BootstrapResult | None:
    """Fetch recorder history for one zone, fit a model, and persist it."""
    state = store.get(zone.zone_id)
    if state is None or not zone.moisture_sensors:
        return None

    end_time = _utcnow()
    start_time = end_time - timedelta(days=max(1, int(days)))
    entity_ids = _history_entity_ids(zone)
    try:
        history = await _async_fetch_zone_history(hass, entity_ids, start_time, end_time)
    except Exception as err:  # noqa: BLE001 - recorder absence must never break setup
        _LOGGER.info(
            "Unable to bootstrap %s from recorder history: %s", zone.zone_id, err
        )
        return None

    moisture = _aggregate_moisture_history(zone.moisture_sensors, history)
    if len(moisture.points) < 2:
        return None

    rain = _series_for(history, zone.observed_rain_amount)
    protected = zone.protected_rain or zone.greenhouse
    observations = assemble_observations(
        moisture,
        rain_series=rain,
        temp_series=_first_series(
            history,
            zone.observed_air_temperature,
            zone.temperature_sensor,
            zone.forecast_air_temperature,
        ),
        humidity_series=_first_series(
            history,
            zone.observed_air_humidity,
            zone.humidity_sensor,
            zone.forecast_air_humidity,
        ),
        wind_series=_series_for(history, zone.wind_speed),
        solar_series=_series_for(history, zone.solar_radiation),
        irrigation_events=detect_irrigation_events(moisture, rain_series=rain),
        protected_rain=protected,
    )
    prior = params_from_state(state) or default_params("loam")
    result = bootstrap_from_series(
        prior,
        observations,
        overrides=_zone_overrides(zone),
    )
    if not result.success:
        return result

    apply_model_to_state(
        state,
        result.params,
        result.confidence,
        covariance=result.covariance,
        updated=end_time.isoformat(),
    )
    state.bootstrapped_days = result.days_span
    await store.async_save()
    return result


async def _async_fetch_zone_history(
    hass: Any,
    entity_ids: Sequence[str],
    start_time: datetime,
    end_time: datetime,
) -> dict[str, TimeSeries]:
    """Fetch numeric recorder state history for entity ids."""
    if not entity_ids:
        return {}

    from homeassistant.components.recorder import get_instance, history

    recorder = get_instance(hass)
    raw = await recorder.async_add_executor_job(
        history.get_significant_states,
        hass,
        start_time,
        end_time,
        list(dict.fromkeys(entity_ids)),
        None,
        True,
        False,
        False,
        True,
    )
    return {
        entity_id: _states_to_series(states)
        for entity_id, states in raw.items()
        if states
    }


def _states_to_series(states: Iterable[Any]) -> TimeSeries:
    points: list[SeriesPoint] = []
    for state in states:
        value = _state_value(state)
        timestamp = _state_timestamp(state)
        if value is not None and timestamp is not None:
            points.append(SeriesPoint(timestamp, value))
    return TimeSeries(points)


def _state_value(state: Any) -> float | None:
    if isinstance(state, Mapping):
        return _finite_float(state.get("state"))
    return _finite_float(getattr(state, "state", None))


def _state_timestamp(state: Any) -> datetime | None:
    if isinstance(state, Mapping):
        value = state.get("last_changed") or state.get("last_updated")
    else:
        value = getattr(state, "last_changed", None) or getattr(
            state, "last_updated", None
        )
    return value if isinstance(value, datetime) else None


def _history_entity_ids(zone: ZoneConfig) -> list[str]:
    ids = [
        *zone.moisture_sensors,
        zone.observed_rain_amount,
        zone.observed_air_temperature,
        zone.observed_air_humidity,
        zone.forecast_air_temperature,
        zone.forecast_air_humidity,
        zone.temperature_sensor,
        zone.humidity_sensor,
        zone.wind_speed,
        zone.solar_radiation,
    ]
    return [entity_id for entity_id in ids if entity_id]


def _aggregate_moisture_history(
    moisture_sensors: Sequence[str], history: Mapping[str, TimeSeries]
) -> TimeSeries:
    series = [history[entity_id] for entity_id in moisture_sensors if entity_id in history]
    if not series:
        return TimeSeries(())
    timestamps = sorted({point.timestamp for item in series for point in item.points})
    points: list[SeriesPoint] = []
    for timestamp in timestamps:
        readings = [item.as_of(timestamp) for item in series]
        moisture = aggregate_zone_moisture(readings).value
        if moisture is not None:
            points.append(SeriesPoint(timestamp, moisture))
    return TimeSeries(points)


def _series_for(
    history: Mapping[str, TimeSeries], entity_id: str | None
) -> TimeSeries | None:
    if entity_id is None:
        return None
    series = history.get(entity_id)
    return series if series else None


def _first_series(
    history: Mapping[str, TimeSeries], *entity_ids: str | None
) -> TimeSeries | None:
    for entity_id in entity_ids:
        series = _series_for(history, entity_id)
        if series:
            return series
    return None


def _zone_overrides(zone: ZoneConfig) -> dict[str, float]:
    overrides: dict[str, float] = {}
    if zone.gain_per_liter is not None:
        overrides["eta_irr"] = zone.gain_per_liter
    if zone.field_capacity is not None:
        overrides["field_capacity"] = zone.field_capacity
    if zone.wilting_point is not None:
        overrides["wilting_point"] = zone.wilting_point
    return overrides


def _utcnow() -> datetime:
    from homeassistant.util import dt as dt_util

    return dt_util.utcnow()
