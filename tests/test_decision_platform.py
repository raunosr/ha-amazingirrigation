"""Tests for the Irrigation Decision sensor and evaluate_zone service."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    CONF_FORECAST_AIR_HUMIDITY,
    CONF_FORECAST_AIR_TEMPERATURE,
    CONF_GREENHOUSE,
    CONF_HUMIDITY_SENSOR,
    CONF_MAX_LITERS,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_OBSERVED_AIR_HUMIDITY,
    CONF_OBSERVED_AIR_TEMPERATURE,
    CONF_OBSERVED_RAIN_AMOUNT,
    CONF_PROTECTED_RAIN,
    CONF_RAIN_SKIP_MM,
    CONF_SAFETY_BLOCKERS,
    CONF_SOLAR_RADIATION,
    CONF_TARGET_MOISTURE,
    CONF_TEMPERATURE_SENSOR,
    CONF_WIND_SPEED,
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


async def test_greenhouse_zone_exposes_context_and_ignores_rain(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.rain", "20.0")  # heavy rain
    hass.states.async_set("sensor.temp", "27.4")
    hass.states.async_set("sensor.hum", "65")
    await _setup(
        hass,
        {
            CONF_NAME: "Greenhouse",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_TARGET_MOISTURE: 40,
            CONF_MAX_LITERS: 30,
            CONF_OBSERVED_RAIN_AMOUNT: "sensor.rain",
            CONF_RAIN_SKIP_MM: 3,
            CONF_GREENHOUSE: True,
            CONF_PROTECTED_RAIN: True,
            CONF_TEMPERATURE_SENSOR: "sensor.temp",
            CONF_HUMIDITY_SENSOR: "sensor.hum",
        },
    )

    state = hass.states.get("sensor.greenhouse_irrigation_decision")
    assert state is not None
    # Protected from rain, so heavy rain does not skip watering.
    assert state.state == "water"
    assert state.attributes["greenhouse"] is True
    assert state.attributes["protected_rain"] is True
    assert state.attributes["temperature"] == 27.4
    assert state.attributes["humidity"] == 65.0


async def test_decision_sensor_references_climate_inputs(
    hass: HomeAssistant,
) -> None:
    """Configured ET climate inputs are surfaced for the card."""
    await _setup(
        hass,
        {
            CONF_NAME: "Climate Bed",
            CONF_MOISTURE_SENSORS: ["sensor.soil"],
            CONF_OBSERVED_AIR_TEMPERATURE: "sensor.air_temp",
            CONF_OBSERVED_AIR_HUMIDITY: "sensor.air_humidity",
            CONF_FORECAST_AIR_TEMPERATURE: "sensor.forecast_temp",
            CONF_FORECAST_AIR_HUMIDITY: "sensor.forecast_humidity",
            CONF_WIND_SPEED: "sensor.wind_speed",
            CONF_SOLAR_RADIATION: "sensor.solar_radiation",
        },
    )

    state = hass.states.get("sensor.climate_bed_irrigation_decision")
    assert state is not None
    assert state.attributes["references"] == {
        "moisture_sensors": ["sensor.soil"],
        "forecast_rain_amount": None,
        "forecast_rain_probability": None,
        "observed_rain_amount": None,
        "temperature_sensor": None,
        "humidity_sensor": None,
        "observed_air_temperature": "sensor.air_temp",
        "observed_air_humidity": "sensor.air_humidity",
        "forecast_air_temperature": "sensor.forecast_temp",
        "forecast_air_humidity": "sensor.forecast_humidity",
        "wind_speed": "sensor.wind_speed",
        "solar_radiation": "sensor.solar_radiation",
        "safety_blockers": [],
    }


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
    # The integration exposes per-zone control switches (zone/learning/schedule)
    # but never an actuator switch entity.
    assert "switch.herb_bed_zone_enabled" in switches
    assert "button.herb_bed_run" in buttons
    assert "button.herb_bed_stop" not in buttons
