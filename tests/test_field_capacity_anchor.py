"""Tests for the trusted manual Field Capacity / Wilting Point anchor.

The anchor is a user-settable FC/WP override that wins over the learned model
everywhere (target band + physics), survives learning, and can be cleared back
to auto by setting it to 0.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    CONF_FIELD_CAPACITY,
    CONF_MAX_LITERS,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_SCHEDULE_TIMES,
    CONF_TARGET_MODE,
    CONF_TARGET_MOISTURE,
    CONF_ZONES,
    DATA_LEARNERS,
    DATA_ZONE_STATE,
    DOMAIN,
)
from custom_components.amazing_irrigation.state import ZoneState, params_from_state

_ZONE = {
    CONF_NAME: "Herb Bed",
    CONF_MOISTURE_SENSORS: ["sensor.a"],
    CONF_TARGET_MOISTURE: 40,
    CONF_MAX_LITERS: 30,
    CONF_SCHEDULE_TIMES: ["06:00"],
}


async def _setup(hass: HomeAssistant, record: dict) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={CONF_ZONES: {"abc123": record}},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _state(hass: HomeAssistant, entry: MockConfigEntry) -> ZoneState:
    return hass.data[DOMAIN][entry.entry_id][DATA_ZONE_STATE].get("abc123")


# --- Unit: resolution priority in params_from_state ---------------------------


def test_override_wins_over_learned_model_params() -> None:
    """A manual FC/WP anchor beats a confidently learned model."""
    state = ZoneState(zone_id="z1", field_capacity_override=45.0)
    state.model_params = {
        "eta_irr": 1.7,
        "eta_rain": 1.2,
        "k_et": 0.7,
        "drain_rate": 0.09,
        "field_capacity": 72.0,
        "wilting_point": 2.0,
    }

    params = params_from_state(state)

    assert params.field_capacity == 45.0


def test_override_wins_over_learned_mirror() -> None:
    """Both FC and WP anchors beat the legacy learned mirrors."""
    state = ZoneState(
        zone_id="z1",
        field_capacity_override=50.0,
        wilting_point_override=18.0,
        learned_field_capacity=72.0,
        learned_wilting_point=2.0,
    )

    params = params_from_state(state)

    assert params.field_capacity == 50.0
    assert params.wilting_point == 18.0


def test_zero_override_falls_back_to_learned() -> None:
    """A 0 (cleared) anchor means auto - fall back to the learned value."""
    state = ZoneState(
        zone_id="z1",
        field_capacity_override=0.0,
        wilting_point_override=0.0,
        learned_field_capacity=52.0,
        learned_wilting_point=20.0,
    )

    params = params_from_state(state)

    assert params.field_capacity == 52.0
    assert params.wilting_point == 20.0


def test_override_pair_is_reconciled_when_fc_below_wp() -> None:
    """A mismatched anchor pair is clamped so FC stays above WP."""
    state = ZoneState(
        zone_id="z1",
        field_capacity_override=20.0,
        wilting_point_override=40.0,
    )

    params = params_from_state(state)

    assert params.field_capacity > params.wilting_point


# --- Integration: number entity, attributes, discovery ------------------------


async def test_field_capacity_number_pins_then_clears(hass: HomeAssistant) -> None:
    """Setting the Field Capacity number pins the anchor; 0 clears it to auto."""
    hass.states.async_set("sensor.a", "20.0")
    assert await async_setup_component(hass, "homeassistant", {})
    entry = await _setup(hass, _ZONE)

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.herb_bed_field_capacity", "value": 45},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert _state(hass, entry).field_capacity_override == 45.0

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.herb_bed_field_capacity", "value": 0},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert _state(hass, entry).field_capacity_override is None


async def test_decision_attributes_expose_anchor(hass: HomeAssistant) -> None:
    """The decision sensor advertises the active FC anchor for the card."""
    record = {**_ZONE, CONF_TARGET_MODE: "auto", CONF_FIELD_CAPACITY: 48}
    hass.states.async_set("sensor.a", "20.0")
    entry = await _setup(hass, record)
    # Nudge the engine so attributes refresh.
    hass.states.async_set("sensor.a", "21.0")
    await hass.async_block_till_done()

    attrs = hass.states.get("sensor.herb_bed_irrigation_decision").attributes
    assert attrs["field_capacity_anchored"] is True
    assert attrs["field_capacity_override"] == 48
    assert attrs["field_capacity"] == 48
    assert _state(hass, entry).field_capacity_override == 48


async def test_target_range_source_notes_manual_field_capacity(
    hass: HomeAssistant,
) -> None:
    """The Target Range source names the manual anchor when one is active."""
    record = {**_ZONE, CONF_TARGET_MODE: "auto", CONF_FIELD_CAPACITY: 48}
    hass.states.async_set("sensor.a", "20.0")
    await _setup(hass, record)
    hass.states.async_set("sensor.a", "21.0")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.herb_bed_target_range")
    assert "manual field capacity" in state.attributes["source"]


async def test_discovery_writes_field_capacity_anchor(hass: HomeAssistant) -> None:
    """A discovered Field Capacity is stored as the trusted manual anchor."""
    hass.states.async_set("sensor.a", "20.0")
    entry = await _setup(hass, _ZONE)
    learner = hass.data[DOMAIN][entry.entry_id][DATA_LEARNERS]["abc123"]

    learner.apply_discovered_field_capacity(41.5)

    assert _state(hass, entry).field_capacity_override == 41.5
