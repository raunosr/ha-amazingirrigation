"""Runtime bridge from Home Assistant state to the pure decision engine.

Reads the live states a zone references, builds :class:`DecisionInputs`, and
returns an explained :class:`Decision`. This module performs no actuation; it
only evaluates what a Run Request would decide right now.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .engine import Decision, DecisionInputs, decide
from .zone import ZoneConfig, aggregate_zone_moisture, is_in_season

_INVALID_STATES = ("unknown", "unavailable", "", None)


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


def build_inputs(
    hass: HomeAssistant, zone: ZoneConfig, *, force: bool = False, zone_locked: bool = False
) -> DecisionInputs:
    """Gather a zone's live inputs for the decision engine."""
    readings = [read_number(hass, entity_id) for entity_id in zone.moisture_sensors]
    moisture = aggregate_zone_moisture(readings)

    now = dt_util.now()
    in_season = is_in_season(zone.season_start, zone.season_end, now.month, now.day)

    return DecisionInputs(
        moisture=moisture,
        target_moisture=zone.target_moisture,
        max_liters=zone.max_liters,
        gain_per_liter=zone.gain_per_liter,
        observed_rain_mm=read_number(hass, zone.observed_rain_amount),
        forecast_rain_mm=read_number(hass, zone.forecast_rain_amount),
        forecast_rain_probability=read_number(hass, zone.forecast_rain_probability),
        rain_skip_mm=zone.rain_skip_mm,
        rain_skip_probability=zone.rain_skip_probability,
        safety_blocked=_safety_blocked(hass, zone.safety_blockers),
        in_season=in_season,
        zone_locked=zone_locked,
        force=force,
    )


def evaluate_zone(
    hass: HomeAssistant, zone: ZoneConfig, *, force: bool = False, zone_locked: bool = False
) -> Decision:
    """Evaluate a Run Request for a zone and return the Irrigation Decision."""
    return decide(build_inputs(hass, zone, force=force, zone_locked=zone_locked))
