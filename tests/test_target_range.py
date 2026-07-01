"""Tests for target transparency: Target Range sensor, plain-language summary,
inactive manual Target Moisture in Auto mode, and diagnostic learned sensors."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    CONF_MAX_LITERS,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_SCHEDULE_TIMES,
    CONF_TARGET_MOISTURE,
    CONF_ZONES,
    DOMAIN,
)
from custom_components.amazing_irrigation.engine import (
    Decision,
    DecisionAction,
    DecisionReason,
)
from custom_components.amazing_irrigation.sensor import _decision_summary

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


def _decision(action: DecisionAction, reason: DecisionReason, liters: float = 0.0):
    return Decision(action, reason, liters, False, {})


def test_summary_above_target_names_band() -> None:
    """An on-target skip states the moisture and the active band."""
    summary = _decision_summary(
        _decision(DecisionAction.SKIP, DecisionReason.ABOVE_TARGET),
        moisture=50.0,
        band_low=33.0,
        band_high=58.0,
    )
    assert summary == "Skip \u2014 moisture 50% is within target 33\u201358%"


def test_summary_below_target_states_amount_and_band() -> None:
    """A watering decision states litres, moisture and the band."""
    summary = _decision_summary(
        _decision(DecisionAction.WATER, DecisionReason.BELOW_TARGET, 4.2),
        moisture=25.0,
        band_low=33.0,
        band_high=58.0,
    )
    assert summary == "Water 4.2 L \u2014 moisture 25% is below target 33\u201358%"


def test_summary_below_min_is_explained() -> None:
    """The minimum-application skip is stated in plain language."""
    summary = _decision_summary(
        _decision(DecisionAction.SKIP, DecisionReason.BELOW_MIN),
        moisture=32.0,
        band_low=33.0,
        band_high=58.0,
    )
    assert "minimum application" in summary


def test_summary_disabled_without_band() -> None:
    """Early-exit reasons summarise even when no band was computed."""
    summary = _decision_summary(
        _decision(DecisionAction.SKIP, DecisionReason.DISABLED),
        moisture=None,
        band_low=None,
        band_high=None,
    )
    assert summary == "Skip \u2014 zone is disabled"


async def test_target_range_sensor_reports_manual_band(hass: HomeAssistant) -> None:
    """The Target Range sensor exposes the active band and its source."""
    hass.states.async_set("sensor.a", "20.0")
    await _setup(hass, _ZONE)

    state = hass.states.get("sensor.herb_bed_target_range")
    assert state is not None
    assert state.state.endswith("%")
    assert state.attributes["start_watering_below"] == 40
    assert state.attributes["mode"] == "manual"
    assert state.attributes["source"] == "manual target"


async def test_target_range_sensor_switches_to_auto_profile(
    hass: HomeAssistant,
) -> None:
    """Turning on Automatic Target makes the band come from the plant profile."""
    hass.states.async_set("sensor.a", "20.0")
    await _setup(hass, _ZONE)

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.herb_bed_target_automatic"},
        blocking=True,
    )
    await hass.async_block_till_done()
    # Nudge the decision engine so the pushed band refreshes.
    hass.states.async_set("sensor.a", "21.0")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.herb_bed_target_range")
    assert state.attributes["mode"] == "automatic"
    assert "profile" in state.attributes["source"]


async def test_manual_target_moisture_inactive_in_auto(hass: HomeAssistant) -> None:
    """The manual Target Moisture number is unavailable while Auto is on."""
    hass.states.async_set("sensor.a", "20.0")
    await _setup(hass, _ZONE)
    assert await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()

    assert hass.states.get("number.herb_bed_target_moisture").state != "unavailable"

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.herb_bed_target_automatic"},
        blocking=True,
    )
    await hass.async_block_till_done()
    await hass.services.async_call(
        "homeassistant",
        "update_entity",
        {"entity_id": "number.herb_bed_target_moisture"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get("number.herb_bed_target_moisture").state == "unavailable"


async def test_learned_sensors_are_diagnostic(hass: HomeAssistant) -> None:
    """Learned parameter sensors are categorised as diagnostic to declutter."""
    hass.states.async_set("sensor.a", "20.0")
    await _setup(hass, _ZONE)

    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    entry = registry.async_get("sensor.herb_bed_learned_field_capacity")
    assert entry is not None
    assert entry.entity_category == EntityCategory.DIAGNOSTIC
