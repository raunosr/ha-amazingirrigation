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

from .controller import ForecastInterval, band_from_target
from .engine import Decision, DecisionInputs, decide
from .state import ZoneState, params_from_state
from .waterbalance import Climate
from .zone import ZoneConfig, aggregate_zone_moisture, is_in_season

_INVALID_STATES = ("unknown", "unavailable", "", None)
_DEFAULT_HORIZON_HOURS = 24.0
_MAX_HORIZON_STEP_HOURS = 1.0


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


def _climate_from_entities(hass: HomeAssistant, zone: ZoneConfig) -> Climate | None:
    """Build a scalar forecast climate, falling back to observed sensors.

    Home Assistant exposes scalar forecast entities here rather than a full time
    series, so the same climate is held constant across every horizon step.
    """
    temp = read_number(hass, zone.forecast_air_temperature)
    if temp is None:
        temp = read_number(hass, zone.observed_air_temperature)
    if temp is None:
        temp = read_number(hass, zone.temperature_sensor)

    humidity = read_number(hass, zone.forecast_air_humidity)
    if humidity is None:
        humidity = read_number(hass, zone.observed_air_humidity)
    if humidity is None:
        humidity = read_number(hass, zone.humidity_sensor)

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
    params = params_from_state(state)
    if params is None:
        return {}
    horizon = _forecast_horizon(hass, zone, state, now)
    if not horizon:
        return {}
    return {
        "predictive": True,
        "params": params,
        "horizon": horizon,
        "target_band": band_from_target(
            target_moisture,
            field_capacity=params.field_capacity,
        ),
    }


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
    predictive = _predictive_kwargs(hass, zone, state, target_moisture, now)

    return DecisionInputs(
        moisture=moisture,
        target_moisture=target_moisture,
        max_liters=max_liters,
        gain_per_liter=_gain_per_liter(zone, state),
        observed_rain_mm=read_number(hass, zone.observed_rain_amount),
        forecast_rain_mm=read_number(hass, zone.forecast_rain_amount),
        forecast_rain_probability=read_number(hass, zone.forecast_rain_probability),
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
