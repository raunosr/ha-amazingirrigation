"""Tests for the read-only Zone Moisture sensor."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_ZONES,
    DOMAIN,
)


async def _setup_zone(hass: HomeAssistant, sensors: list[str]) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_ZONES: {
                "abc123": {CONF_NAME: "Herb Bed", CONF_MOISTURE_SENSORS: sensors}
            }
        },
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_zone_moisture_is_minimum_valid(hass: HomeAssistant) -> None:
    """Zone Moisture reflects the driest valid sensor."""
    hass.states.async_set("sensor.a", "45.0")
    hass.states.async_set("sensor.b", "30.0")
    await _setup_zone(hass, ["sensor.a", "sensor.b"])

    state = hass.states.get("sensor.herb_bed_zone_moisture")
    assert state is not None
    assert float(state.state) == 30.0
    assert state.attributes["degraded"] is False
    assert state.attributes["sensors_used"] == 2


async def test_zone_moisture_degraded_when_one_unavailable(
    hass: HomeAssistant,
) -> None:
    """A missing sensor degrades but does not break Zone Moisture."""
    hass.states.async_set("sensor.a", "unavailable")
    hass.states.async_set("sensor.b", "33.0")
    await _setup_zone(hass, ["sensor.a", "sensor.b"])

    state = hass.states.get("sensor.herb_bed_zone_moisture")
    assert float(state.state) == 33.0
    assert state.attributes["degraded"] is True
    assert state.attributes["sensors_used"] == 1


async def test_zone_moisture_unavailable_when_all_invalid(
    hass: HomeAssistant,
) -> None:
    """Fail closed: no valid reading means the sensor is unavailable."""
    hass.states.async_set("sensor.a", "unknown")
    await _setup_zone(hass, ["sensor.a"])

    state = hass.states.get("sensor.herb_bed_zone_moisture")
    assert state.state == "unavailable"


async def test_zone_moisture_tracks_source_updates(hass: HomeAssistant) -> None:
    """Zone Moisture updates when a source sensor changes."""
    hass.states.async_set("sensor.a", "50.0")
    await _setup_zone(hass, ["sensor.a"])

    assert float(hass.states.get("sensor.herb_bed_zone_moisture").state) == 50.0

    hass.states.async_set("sensor.a", "20.0")
    await hass.async_block_till_done()

    assert float(hass.states.get("sensor.herb_bed_zone_moisture").state) == 20.0


async def test_run_button_created_without_stop_when_no_actuator(
    hass: HomeAssistant,
) -> None:
    """A Run button exists; Stop only when a stop path is configured."""
    hass.states.async_set("sensor.a", "40.0")
    await _setup_zone(hass, ["sensor.a"])

    switches = [e for e in hass.states.async_entity_ids() if e.startswith("switch.")]
    buttons = [e for e in hass.states.async_entity_ids() if e.startswith("button.")]
    # Per-zone control switches exist; no actuator switch entity is created.
    assert "switch.herb_bed_zone_enabled" in switches
    assert "button.herb_bed_run" in buttons
    assert "button.herb_bed_stop" not in buttons
