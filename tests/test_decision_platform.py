"""Tests for the Irrigation Decision sensor and evaluate_zone service."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    CONF_MAX_LITERS,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_SAFETY_BLOCKERS,
    CONF_TARGET_MOISTURE,
    CONF_ZONES,
    DOMAIN,
    EVENT_DECISION,
    SERVICE_EVALUATE_ZONE,
)


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


async def test_decision_sensor_reports_water_below_target(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set("sensor.a", "20.0")
    await _setup(
        hass,
        {
            CONF_NAME: "Herb Bed",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_TARGET_MOISTURE: 40,
            CONF_MAX_LITERS: 30,
        },
    )

    state = hass.states.get("sensor.herb_bed_irrigation_decision")
    assert state is not None
    assert state.state == "water"
    assert state.attributes["reason"] == "below_target"


async def test_decision_sensor_skips_above_target(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.a", "55.0")
    await _setup(
        hass,
        {
            CONF_NAME: "Herb Bed",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_TARGET_MOISTURE: 40,
        },
    )

    state = hass.states.get("sensor.herb_bed_irrigation_decision")
    assert state.state == "skip"
    assert state.attributes["reason"] == "above_target"


async def test_decision_sensor_fails_closed_on_safety_blocker(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("binary_sensor.lock", "on")
    await _setup(
        hass,
        {
            CONF_NAME: "Herb Bed",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_TARGET_MOISTURE: 40,
            CONF_SAFETY_BLOCKERS: ["binary_sensor.lock"],
        },
    )

    state = hass.states.get("sensor.herb_bed_irrigation_decision")
    assert state.state == "skip"
    assert state.attributes["reason"] == "safety_blocker"


async def test_decision_sensor_tracks_input_changes(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.a", "55.0")
    await _setup(
        hass,
        {
            CONF_NAME: "Herb Bed",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_TARGET_MOISTURE: 40,
        },
    )
    assert hass.states.get("sensor.herb_bed_irrigation_decision").state == "skip"

    hass.states.async_set("sensor.a", "15.0")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.herb_bed_irrigation_decision").state == "water"


async def test_evaluate_zone_service_returns_decision_and_fires_event(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set("sensor.a", "20.0")
    await _setup(
        hass,
        {
            CONF_NAME: "Herb Bed",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_TARGET_MOISTURE: 40,
            CONF_MAX_LITERS: 30,
        },
    )

    events = []
    hass.bus.async_listen(EVENT_DECISION, lambda e: events.append(e))

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_EVALUATE_ZONE,
        {"entity_id": "sensor.herb_bed_irrigation_decision"},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    assert response["results"][0]["action"] == "water"
    assert response["results"][0]["zone_id"] == "abc123"
    assert len(events) == 1
    assert events[0].data["reason"] == "below_target"


async def test_evaluate_zone_service_force_waters_above_target(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set("sensor.a", "80.0")
    await _setup(
        hass,
        {
            CONF_NAME: "Herb Bed",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_TARGET_MOISTURE: 40,
            CONF_MAX_LITERS: 30,
        },
    )

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_EVALUATE_ZONE,
        {"entity_id": "sensor.herb_bed_irrigation_decision", "force": True},
        blocking=True,
        return_response=True,
    )
    assert response["results"][0]["action"] == "water"
    assert response["results"][0]["reason"] == "forced"
    # The live sensor must keep showing the non-forced decision, not a sticky force.
    assert hass.states.get("sensor.herb_bed_irrigation_decision").state == "skip"


async def test_run_button_present_stop_absent_without_actuator(
    hass: HomeAssistant,
) -> None:
    """A Run button exists; no Stop button without a configured stop path."""
    hass.states.async_set("sensor.a", "20.0")
    await _setup(
        hass,
        {CONF_NAME: "Herb Bed", CONF_MOISTURE_SENSORS: ["sensor.a"]},
    )

    switches = [e for e in hass.states.async_entity_ids() if e.startswith("switch.")]
    buttons = [e for e in hass.states.async_entity_ids() if e.startswith("button.")]
    assert switches == []
    assert "button.herb_bed_run" in buttons
    assert "button.herb_bed_stop" not in buttons
