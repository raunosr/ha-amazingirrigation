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

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .engine import Decision, DecisionInputs, decide
from .state import ZoneState
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
