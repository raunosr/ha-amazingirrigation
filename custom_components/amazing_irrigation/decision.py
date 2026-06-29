"""Runtime bridge from Home Assistant state to the pure decision engine.

Reads the live states a zone references, builds :class:`DecisionInputs`, and
returns an explained :class:`Decision`. This module performs no actuation; it
only evaluates what a Run Request would decide right now.

A zone's live tunables and learned values (when present) come from its
:class:`ZoneState`: the persisted store is the live source of truth, while the
``ZoneConfig`` only provides the initial setup values. When no state is supplied
the config values are used unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DATA_WEATHER_FORECAST, DOMAIN
from .controller import ForecastInterval, TargetBand, band_from_target
from .demand import target_band_for_profile
from .engine import Decision, DecisionInputs, decide
from .state import ZoneState, params_from_state
from .waterbalance import Climate
from .weather_forecast import ForecastPoint, horizon_from_forecast, near_term_rain
from .zone import ZoneConfig, aggregate_zone_moisture, is_in_season

_INVALID_STATES = ("unknown", "unavailable", "", None)
_DEFAULT_HORIZON_HOURS = 24.0
_MAX_HORIZON_STEP_HOURS = 1.0
_ET_SOURCE_AUTO = "auto"
_ET_SOURCE_WEATHER = "weather"
_ET_SOURCE_GREENHOUSE = "greenhouse"


def read_number(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Return a numeric state value, or None when missing/non-numeric."""
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None or state.state in _INVALID_STATES:
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


def _safety_blocked(hass: HomeAssistant, blockers: list[str]) -> bool:
    """Whether any Safety Blocker is active; unavailable blockers block."""
    for entity_id in blockers:
        state = hass.states.get(entity_id)
        if state is None or state.state in ("unavailable", "unknown", None, ""):
            return True
        if state.state == "on":
            return True
    return False


def _gain_per_liter(zone: ZoneConfig, state: ZoneState | None) -> float | None:
    """The moisture gain per liter to use for a decision.

    A manually configured value always wins; otherwise the learned value is used
    only when the zone has Learning enabled. This keeps learned recommendations
    bounded and explainable, and lets a user override the model at any time.
    """
    if zone.gain_per_liter is not None:
        return zone.gain_per_liter
    if state is not None and state.learning_enabled:
        return state.learned_gain_per_liter
    return zone.gain_per_liter


def _climate_preference(zone: ZoneConfig) -> str:
    """Return the ET climate source preference resolved for this zone."""
    if zone.et_source == _ET_SOURCE_GREENHOUSE:
        return _ET_SOURCE_GREENHOUSE
    if zone.et_source == _ET_SOURCE_WEATHER:
        return _ET_SOURCE_WEATHER
    return _ET_SOURCE_GREENHOUSE if zone.greenhouse else _ET_SOURCE_WEATHER


def _temperature_candidates(zone: ZoneConfig) -> tuple[str | None, ...]:
    """Preferred temperature entities for the zone's configured ET source."""
    if _climate_preference(zone) == _ET_SOURCE_GREENHOUSE:
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
    """Preferred humidity entities for the zone's configured ET source."""
    if _climate_preference(zone) == _ET_SOURCE_GREENHOUSE:
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


def _first_number(hass: HomeAssistant, entity_ids: tuple[str | None, ...]) -> float | None:
    """Return the first numeric value among preferred entity ids."""
    for entity_id in entity_ids:
        value = read_number(hass, entity_id)
        if value is not None:
            return value
    return None


def _climate_from_entities(hass: HomeAssistant, zone: ZoneConfig) -> Climate | None:
    """Build a scalar forecast climate, falling back to observed sensors.

    Home Assistant exposes scalar forecast entities here rather than a full time
    series, so the same climate is held constant across every horizon step.
    """
    temp = _first_number(hass, _temperature_candidates(zone))
    humidity = _first_number(hass, _humidity_candidates(zone))

    wind = read_number(hass, zone.wind_speed)
    solar = read_number(hass, zone.solar_radiation)
    if temp is None and humidity is None and wind is None and solar is None:
        return None
    return Climate(
        air_temp_c=temp,
        air_humidity_pct=humidity,
        wind_ms=wind,
        solar=solar,
    )


def _hours_until_next_schedule(now: datetime, schedule_times: list[str]) -> float:
    """Hours from ``now`` to the next active HH:MM slot, or a 24h default."""
    if not schedule_times:
        return _DEFAULT_HORIZON_HOURS
    candidates: list[datetime] = []
    for value in schedule_times:
        try:
            hour, minute = (int(part) for part in value.split(":", 1))
        except (AttributeError, ValueError):
            continue
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        candidates.append(candidate)
    if not candidates:
        return _DEFAULT_HORIZON_HOURS
    hours = (min(candidates) - now).total_seconds() / 3600.0
    return max(0.0, hours)


def _effective_forecast_rain(hass: HomeAssistant, zone: ZoneConfig) -> float:
    """Forecast rain that should be included in a predictive horizon."""
    if zone.protected_rain:
        return 0.0
    rain = read_number(hass, zone.forecast_rain_amount) or 0.0
    probability = read_number(hass, zone.forecast_rain_probability)
    if probability is not None and probability < zone.rain_skip_probability:
        return 0.0
    return max(0.0, rain)


def _weather_points(hass: HomeAssistant, zone: ZoneConfig) -> list[ForecastPoint] | None:
    """Return cached points for the zone's preferred weather entity."""
    if not zone.weather_forecast_entity:
        return None
    cache = hass.data.get(DOMAIN, {}).get(DATA_WEATHER_FORECAST, {})
    points = cache.get(zone.weather_forecast_entity)
    return points if points else None


def _forecast_horizon(
    hass: HomeAssistant,
    zone: ZoneConfig,
    state: ZoneState,
    now: datetime,
) -> list[ForecastInterval]:
    """Build hourly forecast intervals until the next active schedule slot."""
    total_hours = _hours_until_next_schedule(now, state.active_schedule_times())
    if total_hours <= 0:
        total_hours = _DEFAULT_HORIZON_HOURS
    points = _weather_points(hass, zone)
    if points:
        weather_intervals = horizon_from_forecast(
            points,
            start=now,
            total_hours=total_hours,
            step_hours=_MAX_HORIZON_STEP_HOURS,
            protected_rain=zone.protected_rain,
            rain_skip_probability=zone.rain_skip_probability,
            solar=read_number(hass, zone.solar_radiation),
        )
        if weather_intervals:
            return weather_intervals
    climate = _climate_from_entities(hass, zone)
    forecast_rain = _effective_forecast_rain(hass, zone)
    intervals: list[ForecastInterval] = []
    remaining = total_hours
    while remaining > 1.0e-6:
        dt = min(_MAX_HORIZON_STEP_HOURS, remaining)
        rain_mm = 0.0
        if total_hours > 0 and forecast_rain > 0:
            rain_mm = forecast_rain * (dt / total_hours)
        intervals.append(
            ForecastInterval(
                dt=dt,
                rain_mm=rain_mm,
                climate=climate,
                protected_rain=zone.protected_rain,
            )
        )
        remaining -= dt
    return intervals


def _predictive_kwargs(
    hass: HomeAssistant,
    zone: ZoneConfig,
    state: ZoneState | None,
    target_moisture: float | None,
    now: datetime,
) -> dict:
    """Return predictive DecisionInputs kwargs, or an empty safe fallback."""
    if (
        state is None
        or not state.learning_enabled
        or not isinstance(state.model_params, Mapping)
        or not state.model_params
        or target_moisture is None
    ):
        return {}
    params = params_from_state(state, soil_type=zone.soil_type)
    if params is None:
        return {}
    horizon = _forecast_horizon(hass, zone, state, now)
    if not horizon:
        return {}
    return {
        "predictive": True,
        "params": params,
        "horizon": horizon,
        "target_band": _target_band(
            hass, zone, target_moisture, params.field_capacity, params.wilting_point
        ),
    }


def _target_band(
    hass: HomeAssistant,
    zone: ZoneConfig,
    target_moisture: float | None,
    field_capacity: float | None,
    wilting_point: float | None,
) -> TargetBand:
    """Return the active target range for the zone.

    In Automatic mode the band is derived from learned WP/FC plus the zone's
    plant demand profile (lifted on hot days); explicit user bounds still win.
    In Manual mode the configured Target Moisture drives the band as before.
    """
    if zone.target_mode == "auto":
        air_temp = _first_number(hass, _temperature_candidates(zone))
        auto = target_band_for_profile(
            wilting_point,
            field_capacity,
            zone.demand_profile,
            air_temp_c=air_temp,
        )
        if auto is not None:
            return _apply_explicit_bounds(zone, auto)
    band = band_from_target(target_moisture, field_capacity=field_capacity)
    return _apply_explicit_bounds(zone, band)


def _apply_explicit_bounds(zone: ZoneConfig, band: TargetBand) -> TargetBand:
    """Override a band with any explicit user-set low/high safety bounds."""
    low = zone.target_moisture_low
    high = zone.target_moisture_high
    if low is None and high is None:
        return band
    explicit = TargetBand(
        low=band.low if low is None else max(0.0, min(100.0, float(low))),
        high=band.high if high is None else max(0.0, min(100.0, float(high))),
    )
    if explicit.high < explicit.low:
        return TargetBand(explicit.low, explicit.low)
    return explicit


def _forecast_rain_inputs(
    hass: HomeAssistant,
    zone: ZoneConfig,
    state: ZoneState | None,
    now: datetime,
) -> tuple[float | None, float | None]:
    """Return forecast rain inputs for the rule-based decision path."""
    points = _weather_points(hass, zone)
    if points:
        schedule_times = state.active_schedule_times() if state else zone.schedule_times
        hours = _hours_until_next_schedule(now, schedule_times)
        if hours <= 0:
            hours = _DEFAULT_HORIZON_HOURS
        return near_term_rain(
            points,
            start=now,
            hours=hours,
            protected_rain=zone.protected_rain,
            rain_skip_probability=zone.rain_skip_probability,
        )
    return (
        read_number(hass, zone.forecast_rain_amount),
        read_number(hass, zone.forecast_rain_probability),
    )


def build_inputs(
    hass: HomeAssistant,
    zone: ZoneConfig,
    *,
    force: bool = False,
    zone_locked: bool = False,
    state: ZoneState | None = None,
) -> DecisionInputs:
    """Gather a zone's live inputs for the decision engine."""
    readings = [read_number(hass, entity_id) for entity_id in zone.moisture_sensors]
    moisture = aggregate_zone_moisture(readings)

    now = dt_util.now()
    in_season = is_in_season(zone.season_start, zone.season_end, now.month, now.day)

    target_moisture = zone.target_moisture
    max_liters = zone.max_liters
    enabled = zone.enabled
    if state is not None:
        target_moisture = state.target_moisture
        max_liters = state.max_liters
        enabled = state.enabled
    if zone.target_moisture_low is not None:
        target_moisture = zone.target_moisture_low
    predictive = _predictive_kwargs(hass, zone, state, target_moisture, now)
    forecast_rain_mm, forecast_rain_probability = _forecast_rain_inputs(
        hass, zone, state, now
    )

    return DecisionInputs(
        moisture=moisture,
        target_moisture=target_moisture,
        max_liters=max_liters,
        gain_per_liter=_gain_per_liter(zone, state),
        observed_rain_mm=read_number(hass, zone.observed_rain_amount),
        forecast_rain_mm=forecast_rain_mm,
        forecast_rain_probability=forecast_rain_probability,
        rain_skip_mm=zone.rain_skip_mm,
        rain_skip_probability=zone.rain_skip_probability,
        safety_blocked=_safety_blocked(hass, zone.safety_blockers),
        enabled=enabled,
        in_season=in_season,
        zone_locked=zone_locked,
        force=force,
        protected_rain=zone.protected_rain,
        **predictive,
    )


def evaluate_zone(
    hass: HomeAssistant,
    zone: ZoneConfig,
    *,
    force: bool = False,
    zone_locked: bool = False,
    state: ZoneState | None = None,
) -> Decision:
    """Evaluate a Run Request for a zone and return the Irrigation Decision."""
    return decide(
        build_inputs(
            hass, zone, force=force, zone_locked=zone_locked, state=state
        )
    )
