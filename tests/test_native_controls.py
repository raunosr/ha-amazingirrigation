"""Integration tests for editable native tunable & schedule entities."""

from __future__ import annotations

from datetime import time as dt_time

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    CONF_MAX_LITERS,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_SCHEDULE_TIMES,
    CONF_TARGET_MOISTURE,
    CONF_ZONES,
    DATA_ZONE_STATE,
    DOMAIN,
)

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


def _state(hass: HomeAssistant, entry: MockConfigEntry):
    return hass.data[DOMAIN][entry.entry_id][DATA_ZONE_STATE].get("abc123")


async def test_tunable_entities_seeded_from_options(hass: HomeAssistant) -> None:
    """Number/switch/time entities reflect the seeded ZoneState values."""
    hass.states.async_set("sensor.a", "20.0")
    await _setup(hass, _ZONE)

    assert float(hass.states.get("number.herb_bed_target_moisture").state) == 40.0
    assert float(hass.states.get("number.herb_bed_max_liters_per_run").state) == 30.0
    assert hass.states.get("switch.herb_bed_zone_enabled").state == "on"
    assert hass.states.get("switch.herb_bed_learning_enabled").state == "off"
    assert hass.states.get("switch.herb_bed_schedule_1_active").state == "on"
    assert hass.states.get("switch.herb_bed_schedule_2_active").state == "off"
    assert hass.states.get("time.herb_bed_schedule_1_time").state == "06:00:00"


async def test_setting_number_persists_to_zone_state(hass: HomeAssistant) -> None:
    """Editing Target Moisture writes through to the persisted ZoneState."""
    hass.states.async_set("sensor.a", "20.0")
    entry = await _setup(hass, _ZONE)

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.herb_bed_target_moisture", "value": 55},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert _state(hass, entry).target_moisture == 55.0
    assert float(hass.states.get("number.herb_bed_target_moisture").state) == 55.0


async def test_toggling_switch_persists_to_zone_state(hass: HomeAssistant) -> None:
    """Toggling Learning Enabled writes through to the persisted ZoneState."""
    hass.states.async_set("sensor.a", "20.0")
    entry = await _setup(hass, _ZONE)

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.herb_bed_learning_enabled"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert _state(hass, entry).learning_enabled is True


async def test_new_knob_numbers_present_and_persist(hass: HomeAssistant) -> None:
    """Sensor depth, rain fraction and min application write through to state."""
    hass.states.async_set("sensor.a", "20.0")
    entry = await _setup(hass, _ZONE)

    assert float(hass.states.get("number.herb_bed_rain_fraction").state) == 100.0
    assert (
        float(hass.states.get("number.herb_bed_minimum_application").state) == 0.1
    )

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.herb_bed_rain_fraction", "value": 40},
        blocking=True,
    )
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.herb_bed_sensor_depth", "value": 150},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert _state(hass, entry).rain_fraction == 40.0
    assert _state(hass, entry).sensor_depth_mm == 150.0


async def test_soil_and_profile_selects_present_and_persist(
    hass: HomeAssistant,
) -> None:
    """Soil Type and Plant Profile selects write through to the ZoneState."""
    hass.states.async_set("sensor.a", "20.0")
    entry = await _setup(hass, _ZONE)

    assert hass.states.get("select.herb_bed_soil_type").state == "good_garden"

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.herb_bed_soil_type", "option": "sandy"},
        blocking=True,
    )
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.herb_bed_plant_profile", "option": "high"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert _state(hass, entry).soil_type == "sandy"
    assert _state(hass, entry).demand_profile == "high"


async def test_auto_target_switch_persists_mode(hass: HomeAssistant) -> None:
    """The Automatic Target switch toggles ZoneState target mode auto/manual."""
    hass.states.async_set("sensor.a", "20.0")
    entry = await _setup(hass, _ZONE)

    assert hass.states.get("switch.herb_bed_target_automatic").state == "off"

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.herb_bed_target_automatic"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert _state(hass, entry).target_mode == "auto"

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.herb_bed_target_automatic"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert _state(hass, entry).target_mode == "manual"


async def test_setting_schedule_time_persists_and_normalises(
    hass: HomeAssistant,
) -> None:
    """Editing a schedule time persists HH:MM and updates active times."""
    hass.states.async_set("sensor.a", "20.0")
    entry = await _setup(hass, _ZONE)

    await hass.services.async_call(
        "time",
        "set_value",
        {"entity_id": "time.herb_bed_schedule_1_time", "time": dt_time(7, 30)},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = _state(hass, entry)
    assert state.schedule_1_time == "07:30"
    assert state.active_schedule_times() == ["07:30"]
    assert hass.states.get("time.herb_bed_schedule_1_time").state == "07:30:00"
