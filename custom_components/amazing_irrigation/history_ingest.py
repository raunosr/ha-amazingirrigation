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
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any

from .estimator import EstimatorObservation, JointEstimator
from .state import ZoneStateStore, apply_model_to_state, params_from_state
from .waterbalance import (
    MOISTURE_MAX,
    MOISTURE_MIN,
    Climate,
    WaterBalanceParams,
    default_params,
)
from .zone import ZoneConfig, aggregate_zone_moisture

_LOGGER = logging.getLogger(__name__)

DEFAULT_HISTORY_DAYS = 30
DEFAULT_MIN_INTERVAL_HOURS = 0.25
DEFAULT_MAX_INTERVAL_HOURS = 24.0
DEFAULT_MIN_BOOTSTRAP_INTERVALS = 12
DEFAULT_INFERRED_IRRIGATION_RISE = 3.0
_RAIN_EXPLAINS_RISE_MM = 0.5

# Raw recorder states are memory-heavy, so they are fetched only for the most
# recent window (default recorder purge horizon) and the older history is filled
# by hourly long-term statistics.  The raw window is fetched in day-sized chunks
# so peak heap stays bounded to roughly one day of states per zone.
DEFAULT_RAW_HISTORY_DAYS = 14
RAW_FETCH_CHUNK_DAYS = 1

# Compressed recorder-state dict keys (homeassistant.const.COMPRESSED_STATE_*).
# Hard-coded to avoid importing Home Assistant from the pure core of this module.
_COMPRESSED_STATE_STATE = "s"
_COMPRESSED_STATE_LAST_CHANGED = "lc"
_COMPRESSED_STATE_LAST_UPDATED = "lu"


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
        # Cache the timestamp tuple once: ``as_of`` is called many times per
        # bootstrap and recomputing this on every call was O(N^2) churn.
        object.__setattr__(self, "_timestamps", tuple(point.timestamp for point in ordered))

    @property
    def timestamps(self) -> tuple[datetime, ...]:
        """Return sample timestamps in ascending order."""
        return self._timestamps

    def __bool__(self) -> bool:
        """Whether the series has at least one sample."""
        return bool(self.points)

    def as_of(self, timestamp: datetime) -> float | None:
        """Return the last value at or before ``timestamp``."""
        index = bisect.bisect_right(self._timestamps, timestamp) - 1
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
    requested_days: int = 0
    source: str = ""


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
    estimator = JointEstimator(
        prior_params=bounded_prior,
        prior_cov=[16.0, 16.0, 2.0, 0.20],
        measurement_noise=0.25,
        overrides=overrides,
    )
    # Field Capacity / Wilting Point are moisture-envelope quantities: derive them
    # from the fetched moisture window regardless of how many irrigation intervals
    # exist, so a re-learn never inherits a stale (possibly polluted) learned FC.
    estimator.seed_envelope(
        moisture
        for obs in intervals
        for moisture in (obs.theta_start, obs.theta_end)
    )
    if len(intervals) < min_intervals:
        summary = (
            f"Insufficient history: {len(intervals)} intervals over "
            f"{days_span:.1f} days"
        )
        return BootstrapResult(
            params=estimator.params,
            confidence={},
            covariance=[],
            intervals_used=len(intervals),
            days_span=days_span,
            summary=summary,
            success=False,
            reason="insufficient_history",
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
    days: int | None = None,
) -> BootstrapResult | None:
    """Fetch recorder history for one zone, fit a model, and persist it."""
    state = store.get(zone.zone_id)
    if state is None or not zone.moisture_sensors:
        return None

    effective_days = days if days is not None else zone.history_days
    end_time = _utcnow()
    start_time = end_time - timedelta(days=max(1, int(effective_days)))
    entity_ids = _history_entity_ids(zone)
    try:
        history, source = await _async_fetch_zone_history(
            hass, entity_ids, start_time, end_time
        )
    except Exception as err:  # noqa: BLE001 - recorder absence must never break setup
        _LOGGER.info(
            "Unable to bootstrap %s from recorder history: %s", zone.zone_id, err
        )
        return None

    # The expensive recorder fetch above has now run. Record the attempt so the
    # automatic setup-time bootstrap does not repeat it on every reload (e.g.
    # when the user edits a zone's configuration), regardless of whether the fit
    # below succeeds. The manual Bootstrap button/service call this function
    # directly and so always force a fresh attempt.
    state.bootstrap_attempted = end_time.isoformat()

    moisture = _aggregate_moisture_history(zone.moisture_sensors, history)
    if len(moisture.points) < 2:
        await store.async_save()
        return None

    rain = _series_for(history, zone.observed_rain_amount)
    protected = zone.protected_rain or zone.greenhouse
    temp_series = _first_series(history, *_temperature_candidates(zone))
    humidity_series = _first_series(history, *_humidity_candidates(zone))
    wind_series = _series_for(history, zone.wind_speed)
    solar_series = _series_for(history, zone.solar_radiation)
    irrigation_events = detect_irrigation_events(moisture, rain_series=rain)
    # The per-entity history dict is the largest live structure; release it now
    # that the needed series are bound so unused candidate series can be freed
    # before the (allocation-heavy) observation assembly runs.
    history = {}
    observations = assemble_observations(
        moisture,
        rain_series=rain,
        temp_series=temp_series,
        humidity_series=humidity_series,
        wind_series=wind_series,
        solar_series=solar_series,
        irrigation_events=irrigation_events,
        protected_rain=protected,
    )
    prior = params_from_state(
        state,
        soil_type=zone.soil_type,
        area_m2=zone.area_m2,
        root_depth_mm=zone.root_depth_mm,
        demand_profile=zone.demand_profile,
    ) or default_params(
        zone.soil_type,
        area_m2=zone.area_m2,
        root_depth_mm=zone.root_depth_mm,
        demand_profile=zone.demand_profile,
    )
    result = replace(
        bootstrap_from_series(prior, observations, overrides=_zone_overrides(zone)),
        requested_days=int(effective_days),
        source=source,
    )
    result = replace(result, summary=_enriched_summary(result))
    if not result.success:
        await store.async_save()
        return result

    apply_model_to_state(
        state,
        result.params,
        result.confidence,
        covariance=result.covariance,
        updated=end_time.isoformat(),
    )
    state.bootstrapped_days = result.days_span
    state.bootstrap_intervals = result.intervals_used
    state.bootstrap_requested_days = result.requested_days or None
    state.bootstrap_source = result.source or None
    await store.async_save()
    return result


def _enriched_summary(result: BootstrapResult) -> str:
    """Human-readable summary including window, intervals, and data source."""
    if not result.success:
        return result.summary
    source = f" via {result.source}" if result.source else ""
    requested = f" of {result.requested_days} requested" if result.requested_days else ""
    return (
        f"Learned from {result.intervals_used} intervals over "
        f"{result.days_span:.1f}{requested} days{source}"
    )


async def _async_fetch_zone_history(
    hass: Any,
    entity_ids: Sequence[str],
    start_time: datetime,
    end_time: datetime,
) -> tuple[dict[str, TimeSeries], str]:
    """Fetch numeric history for entity ids.

    Long-term **statistics** (hourly means, retained for ~1 year) supply the
    long window beyond the recorder's short raw-state retention, while raw
    recorder states supply fine recent detail.  The two are merged per entity,
    with raw winning on any overlapping window.  Returns the merged history and
    a human-readable description of which backends supplied data.
    """
    if not entity_ids:
        return {}, "none"

    unique = list(dict.fromkeys(entity_ids))
    statistics = await _async_fetch_statistics(hass, unique, start_time, end_time)
    # Raw states dominate memory, so only the recent window is pulled in detail;
    # statistics supply everything older and the merge prefers raw on overlap.
    raw_start = max(start_time, end_time - timedelta(days=DEFAULT_RAW_HISTORY_DAYS))
    raw = await _async_fetch_recorder_states(hass, unique, raw_start, end_time)

    merged: dict[str, TimeSeries] = {}
    for entity_id in unique:
        series = _merge_series_prefer_raw(
            statistics.get(entity_id), raw.get(entity_id)
        )
        if series:
            merged[entity_id] = series
    source = _history_source(bool(statistics), bool(raw))
    return merged, source


def _history_source(has_statistics: bool, has_raw: bool) -> str:
    """Describe which recorder backends supplied data, for the UI summary."""
    if has_statistics and has_raw:
        return "statistics + recorder"
    if has_statistics:
        return "statistics"
    if has_raw:
        return "recorder"
    return "none"


async def _async_fetch_recorder_states(
    hass: Any,
    entity_ids: Sequence[str],
    start_time: datetime,
    end_time: datetime,
) -> dict[str, TimeSeries]:
    """Fetch raw recorder state history for entity ids (recent fine detail).

    The window is pulled in day-sized chunks using the recorder's memory-frugal
    options (``minimal_response`` + ``compressed_state_format`` + ``no_attributes``
    + ``significant_changes_only``) so peak heap stays bounded to roughly one
    chunk of compressed state dicts rather than the whole window of ``LazyState``
    objects.  ``include_start_time_state`` seeds only the first chunk; subsequent
    chunks contribute their own changes and any boundary duplicates collapse in
    :class:`TimeSeries`.
    """
    if not entity_ids:
        return {}

    try:
        from homeassistant.components.recorder import get_instance, history

        recorder = get_instance(hass)
    except Exception as err:  # noqa: BLE001 - recorder absence must never break setup
        _LOGGER.debug("Recorder unavailable: %s", err)
        return {}

    unique = list(dict.fromkeys(entity_ids))
    accumulated: dict[str, list[SeriesPoint]] = {}
    chunk = timedelta(days=max(1, RAW_FETCH_CHUNK_DAYS))
    chunk_start = start_time
    first_chunk = True
    while chunk_start < end_time:
        chunk_end = min(chunk_start + chunk, end_time)
        try:
            raw = await recorder.async_add_executor_job(
                history.get_significant_states,
                hass,
                chunk_start,
                chunk_end,
                unique,
                None,  # filters
                first_chunk,  # include_start_time_state (seed only first chunk)
                True,  # significant_changes_only (drop duplicate states)
                True,  # minimal_response
                True,  # no_attributes
                True,  # compressed_state_format
            )
        except Exception as err:  # noqa: BLE001 - recorder absence must never break setup
            _LOGGER.debug("Recorder state history unavailable: %s", err)
            return {}
        for entity_id, states in (raw or {}).items():
            if not states:
                continue
            bucket = accumulated.setdefault(entity_id, [])
            for state in states:
                value = _state_value(state)
                timestamp = _state_timestamp(state)
                if value is not None and timestamp is not None:
                    bucket.append(SeriesPoint(timestamp, value))
        del raw
        chunk_start = chunk_end
        first_chunk = False

    return {
        entity_id: TimeSeries(points)
        for entity_id, points in accumulated.items()
        if points
    }


async def _async_fetch_statistics(
    hass: Any,
    entity_ids: Sequence[str],
    start_time: datetime,
    end_time: datetime,
) -> dict[str, TimeSeries]:
    """Fetch hourly long-term statistics for entity ids (long history window)."""
    if not entity_ids:
        return {}

    try:
        from homeassistant.components.recorder import get_instance
        from homeassistant.components.recorder.statistics import (
            statistics_during_period,
        )

        recorder = get_instance(hass)
        rows = await recorder.async_add_executor_job(
            statistics_during_period,
            hass,
            start_time,
            end_time,
            set(entity_ids),
            "hour",
            None,
            {"mean", "state", "sum"},
        )
    except Exception as err:  # noqa: BLE001 - statistics absence must never break setup
        _LOGGER.debug("Long-term statistics unavailable: %s", err)
        return {}

    series: dict[str, TimeSeries] = {}
    for entity_id, entity_rows in (rows or {}).items():
        converted = _statistics_to_series(entity_rows)
        if converted:
            series[entity_id] = converted
    return series


def _statistics_to_series(rows: Iterable[Any]) -> TimeSeries:
    """Convert recorder statistic rows into a numeric series.

    Each row carries a period ``start`` and one or more aggregate values.  For
    measurement sensors (moisture, temperature, humidity, wind, solar) the
    ``mean`` is used; for cumulative meters (rain) the ``state``/``sum`` reading
    is used so :meth:`TimeSeries.delta` can recover per-interval amounts.
    """
    points: list[SeriesPoint] = []
    for row in rows or ():
        timestamp = _statistics_timestamp(row)
        value = _statistics_value(row)
        if timestamp is not None and value is not None:
            points.append(SeriesPoint(timestamp, value))
    return TimeSeries(points)


def _statistics_value(row: Any) -> float | None:
    if not isinstance(row, Mapping):
        return None
    for key in ("mean", "state", "sum"):
        if key in row:
            value = _finite_float(row.get(key))
            if value is not None:
                return value
    return None


def _statistics_timestamp(row: Any) -> datetime | None:
    if not isinstance(row, Mapping):
        return None
    start = row.get("start")
    if isinstance(start, datetime):
        return start
    if isinstance(start, (int, float)):
        from datetime import UTC

        return datetime.fromtimestamp(float(start), tz=UTC)
    return None


def _merge_series_prefer_raw(
    statistics: TimeSeries | None, raw: TimeSeries | None
) -> TimeSeries:
    """Merge statistics with raw states; raw wins on any overlapping window.

    Statistics points older than the earliest raw sample extend the history
    backwards, while raw samples provide the recent, fine-grained detail.
    """
    stats_points = statistics.points if statistics else ()
    raw_points = raw.points if raw else ()
    if not raw_points:
        return TimeSeries(stats_points)
    if not stats_points:
        return TimeSeries(raw_points)
    cutoff = raw_points[0].timestamp
    kept = [point for point in stats_points if point.timestamp < cutoff]
    return TimeSeries((*kept, *raw_points))


def _state_value(state: Any) -> float | None:
    if isinstance(state, Mapping):
        if "state" in state:
            return _finite_float(state.get("state"))
        return _finite_float(state.get(_COMPRESSED_STATE_STATE))
    return _finite_float(getattr(state, "state", None))


def _state_timestamp(state: Any) -> datetime | None:
    if isinstance(state, Mapping):
        value = (
            state.get("last_changed")
            or state.get("last_updated")
            or state.get(_COMPRESSED_STATE_LAST_CHANGED)
            or state.get(_COMPRESSED_STATE_LAST_UPDATED)
        )
    else:
        value = getattr(state, "last_changed", None) or getattr(
            state, "last_updated", None
        )
    return _coerce_timestamp(value)


def _coerce_timestamp(value: Any) -> datetime | None:
    """Normalise a recorder timestamp to an aware ``datetime``.

    Handles every shape the recorder emits across its fetch options: ``datetime``
    (``LazyState``), ISO strings (non-compressed ``minimal_response``), and float
    epoch seconds (``compressed_state_format``).
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        from homeassistant.util import dt as dt_util

        return dt_util.parse_datetime(value)
    if isinstance(value, (int, float)):
        from datetime import UTC

        try:
            return datetime.fromtimestamp(float(value), tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    return None


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
        if moisture is not None and MOISTURE_MIN < moisture < MOISTURE_MAX:
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


def _prefer_greenhouse_climate(zone: ZoneConfig) -> bool:
    """Whether climate history should prefer greenhouse-local sensors."""
    return zone.et_source == "greenhouse" or (
        zone.et_source == "auto" and zone.greenhouse
    )


def _temperature_candidates(zone: ZoneConfig) -> tuple[str | None, ...]:
    """Temperature history candidates ordered by the zone's ET source preference."""
    if _prefer_greenhouse_climate(zone):
        return (
            zone.temperature_sensor,
            zone.observed_air_temperature,
            zone.forecast_air_temperature,
        )
    return (
        zone.forecast_air_temperature,
        zone.observed_air_temperature,
        zone.temperature_sensor,
    )


def _humidity_candidates(zone: ZoneConfig) -> tuple[str | None, ...]:
    """Humidity history candidates ordered by the zone's ET source preference."""
    if _prefer_greenhouse_climate(zone):
        return (
            zone.humidity_sensor,
            zone.observed_air_humidity,
            zone.forecast_air_humidity,
        )
    return (
        zone.forecast_air_humidity,
        zone.observed_air_humidity,
        zone.humidity_sensor,
    )


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
