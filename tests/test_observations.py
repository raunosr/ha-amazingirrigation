"""Integration tests for Irrigation History capture and Rain Events."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, ServiceCall
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    ACTUATOR_SWITCH,
    CONF_ACTUATOR_SWITCH,
    CONF_ACTUATOR_TYPE,
    CONF_FIELD_CAPACITY,
    CONF_MAX_LITERS,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_OBSERVED_RAIN_AMOUNT,
    CONF_TARGET_MOISTURE,
    CONF_WILTING_POINT,
    CONF_ZONES,
    DATA_CONTROLLERS,
    DATA_HISTORY,
    DOMAIN,
)
from custom_components.amazing_irrigation.history import ObservationKind


def _register_switch(hass: HomeAssistant) -> None:
    async def _noop(call: ServiceCall) -> None:
        return None

    hass.services.async_register("switch", "turn_on", _noop)
    hass.services.async_register("switch", "turn_off", _noop)


_ZONE = {
    CONF_NAME: "Herb Bed",
    CONF_MOISTURE_SENSORS: ["sensor.a"],
    CONF_TARGET_MOISTURE: 40,
    CONF_MAX_LITERS: 30,
    CONF_ACTUATOR_TYPE: ACTUATOR_SWITCH,
    CONF_ACTUATOR_SWITCH: "switch.valve",
    CONF_OBSERVED_RAIN_AMOUNT: "sensor.rain",
    CONF_FIELD_CAPACITY: 45,
    CONF_WILTING_POINT: 20,
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


async def test_run_records_request_and_decision_and_event(
    hass: HomeAssistant,
) -> None:
    """A watering run records a Run Request, Decision, and Watering Event."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.rain", "0.0")
    _register_switch(hass)
    entry = await _setup(hass, _ZONE)

    controller = hass.data[DOMAIN][entry.entry_id][DATA_CONTROLLERS]["abc123"]
    await controller.async_run()
    await hass.async_block_till_done()

    history = hass.data[DOMAIN][entry.entry_id][DATA_HISTORY]["abc123"]
    kinds = [entry["kind"] for entry in history.recent()]
    assert ObservationKind.RUN_REQUEST.value in kinds
    assert ObservationKind.DECISION.value in kinds
    assert ObservationKind.WATERING_EVENT.value in kinds


async def test_skip_records_decision_but_no_watering_event(
    hass: HomeAssistant,
) -> None:
    """A skipped Run Request records the Decision but no Watering Event."""
    hass.states.async_set("sensor.a", "55.0")  # above target -> skip
    hass.states.async_set("sensor.rain", "0.0")
    _register_switch(hass)
    entry = await _setup(hass, _ZONE)

    controller = hass.data[DOMAIN][entry.entry_id][DATA_CONTROLLERS]["abc123"]
    await controller.async_run()
    await hass.async_block_till_done()

    history = hass.data[DOMAIN][entry.entry_id][DATA_HISTORY]["abc123"]
    kinds = [entry["kind"] for entry in history.recent()]
    assert ObservationKind.DECISION.value in kinds
    assert ObservationKind.WATERING_EVENT.value not in kinds


async def test_observed_rain_increase_records_rain_event(
    hass: HomeAssistant,
) -> None:
    """An increase in Observed Rain Amount records a Rain Event."""
    hass.states.async_set("sensor.a", "30.0")
    hass.states.async_set("sensor.rain", "0.0")
    _register_switch(hass)
    entry = await _setup(hass, _ZONE)

    hass.states.async_set("sensor.rain", "3.5")
    await hass.async_block_till_done()

    history = hass.data[DOMAIN][entry.entry_id][DATA_HISTORY]["abc123"]
    rain_entries = [
        entry
        for entry in history.recent()
        if entry["kind"] == ObservationKind.RAIN_EVENT.value
    ]
    assert len(rain_entries) == 1
    assert rain_entries[0]["delta_mm"] == 3.5


async def test_rain_reset_does_not_record_event(hass: HomeAssistant) -> None:
    """A drop in the observed counter rebases without recording a Rain Event."""
    hass.states.async_set("sensor.a", "30.0")
    hass.states.async_set("sensor.rain", "5.0")
    _register_switch(hass)
    entry = await _setup(hass, _ZONE)

    hass.states.async_set("sensor.rain", "0.0")  # daily counter rollover
    await hass.async_block_till_done()

    history = hass.data[DOMAIN][entry.entry_id][DATA_HISTORY]["abc123"]
    rain_entries = [
        entry
        for entry in history.recent()
        if entry["kind"] == ObservationKind.RAIN_EVENT.value
    ]
    assert rain_entries == []


async def test_decision_sensor_exposes_calibration(hass: HomeAssistant) -> None:
    """The decision sensor exposes available-water and calibration attributes."""
    hass.states.async_set("sensor.a", "32.5")  # midpoint of 20..45 -> 0.5
    hass.states.async_set("sensor.rain", "0.0")
    _register_switch(hass)
    await _setup(hass, _ZONE)

    state = hass.states.get("sensor.herb_bed_irrigation_decision")
    assert state is not None
    assert state.attributes["field_capacity"] == 45
    assert state.attributes["wilting_point"] == 20
    assert state.attributes["available_water"] == 0.5
    assert state.attributes["learning_enabled"] is False


async def test_history_sensor_reports_readable_summary(hass: HomeAssistant) -> None:
    """The history sensor reports a readable summary and most recent kind."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.rain", "0.0")
    _register_switch(hass)
    entry = await _setup(hass, _ZONE)

    controller = hass.data[DOMAIN][entry.entry_id][DATA_CONTROLLERS]["abc123"]
    await controller.async_run()
    await hass.async_block_till_done()

    state = hass.states.get("sensor.herb_bed_irrigation_history")
    assert state is not None
    assert isinstance(state.state, str) and state.state != ""
    assert state.attributes["observation_count"] >= 3
    assert state.attributes["last_kind"] == ObservationKind.WATERING_EVENT.value
    assert len(state.attributes["entries"]) >= 3
    assert "summary" in state.attributes["entries"][0]
