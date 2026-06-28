"""Tests for the Amazing Irrigation options flow (zone management)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_ZONES,
    DOMAIN,
)


async def _setup_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_add_zone_creates_record(hass: HomeAssistant) -> None:
    """A user can create one observe-only Irrigation Zone."""
    entry = await _setup_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_zone"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_zone"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Herb Bed",
            CONF_MOISTURE_SENSORS: ["sensor.gw2000a_soil_moisture_5"],
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    zones = entry.options[CONF_ZONES]
    assert len(zones) == 1
    record = next(iter(zones.values()))
    assert record[CONF_NAME] == "Herb Bed"
    assert record[CONF_MOISTURE_SENSORS] == ["sensor.gw2000a_soil_moisture_5"]


async def test_add_zone_requires_a_moisture_sensor(hass: HomeAssistant) -> None:
    """A zone cannot be created without at least one moisture sensor."""
    entry = await _setup_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_zone"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_NAME: "Empty", CONF_MOISTURE_SENSORS: []}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_MOISTURE_SENSORS: "no_moisture_sensors"}
    assert CONF_ZONES not in entry.options


async def test_edit_zone_updates_record(hass: HomeAssistant) -> None:
    """A user can edit an existing Irrigation Zone."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_ZONES: {
                "abc123": {
                    CONF_NAME: "Old Name",
                    CONF_MOISTURE_SENSORS: ["sensor.a"],
                }
            }
        },
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_zone"}
    )
    # Pick the zone to edit.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"zone": "abc123"}
    )
    assert result["step_id"] == "edit_zone"
    # Submit the edited values.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_NAME: "New Name", CONF_MOISTURE_SENSORS: ["sensor.a", "sensor.b"]},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    record = entry.options[CONF_ZONES]["abc123"]
    assert record[CONF_NAME] == "New Name"
    assert record[CONF_MOISTURE_SENSORS] == ["sensor.a", "sensor.b"]


async def test_remove_zone(hass: HomeAssistant) -> None:
    """A user can remove an Irrigation Zone."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_ZONES: {
                "abc123": {CONF_NAME: "Bed", CONF_MOISTURE_SENSORS: ["sensor.a"]}
            }
        },
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_zone"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"zone": "abc123"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_ZONES] == {}
