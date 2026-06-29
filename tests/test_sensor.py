"""Tests for the read-only Zone Moisture sensor."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_ZONES,
    DATA_LEARNERS,
    DATA_ZONE_STATE,
    DOMAIN,
)
from custom_components.amazing_irrigation.state import apply_model_to_state
from custom_components.amazing_irrigation.waterbalance import WaterBalanceParams


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


async def test_model_insight_sensor_exposes_explainability(
    hass: HomeAssistant,
) -> None:
    """Model Insight carries parameters, confidence and latest explanation."""
    hass.states.async_set("sensor.a", "40.0")
    entry = await _setup_zone(hass, ["sensor.a"])
    store = hass.data[DOMAIN][entry.entry_id][DATA_ZONE_STATE]
    zone_state = store.get("abc123")
    zone_state.learning_enabled = True
    zone_state.bootstrapped_days = 7.5
    zone_state.total_liters = 123.456
    zone_state.decision_explanation = {
        "terms": {"irrigation": 2.0, "rain": 0.5, "et": -0.2, "drainage": -0.1},
        "predicted_trajectory": [38.0, 39.5],
        "horizon_hours": 2.0,
        "chosen_liters": 1.0,
        "predicted_critical_theta_with_water": 38.0,
        "predicted_peak_theta": 39.5,
    }
    apply_model_to_state(
        zone_state,
        WaterBalanceParams(1.5, 0.9, 0.65, 0.14, 50.0, 18.0),
        {"eta_irr": 0.8, "eta_rain": 0.6, "k_et": 0.7, "drain_rate": 0.5},
        updated="2026-06-28T12:00:00+00:00",
    )
    learner = hass.data[DOMAIN][entry.entry_id][DATA_LEARNERS]["abc123"]
    for listener in list(learner._listeners):  # noqa: SLF001
        listener()
    await hass.async_block_till_done()

    state = hass.states.get("sensor.herb_bed_model_insight")
    assert state is not None
    assert state.state == "65% confidence"
    attrs = state.attributes
    assert attrs["parameters"]["eta_irr"]["name"] == "Irrigation Efficiency"
    assert attrs["parameters"]["eta_irr"]["value"] == 1.5
    assert attrs["parameters"]["eta_irr"]["confidence"] == 0.8
    assert attrs["overall_confidence"] == 0.65
    assert attrs["bootstrapped_days"] == 7.5
    assert attrs["bootstrap_summary"] == "Bootstrapped from 7.5 days"
    assert attrs["decision_explanation"]["chosen_liters"] == 1.0
    assert attrs["water_balance_terms"]["irrigation"] == 2.0
    assert attrs["predicted_trajectory"] == [38.0, 39.5]
    assert attrs["horizon_hours"] == 2.0
    assert attrs["predicted_critical_theta"] == 38.0
    assert attrs["predicted_peak_theta"] == 39.5
    assert attrs["model_updated"] == "2026-06-28T12:00:00+00:00"
    assert attrs["total_liters"] == 123.456


async def test_model_insight_sensor_handles_missing_model(
    hass: HomeAssistant,
) -> None:
    """Model Insight has a sensible empty state before learning has a model."""
    hass.states.async_set("sensor.a", "40.0")
    await _setup_zone(hass, ["sensor.a"])

    state = hass.states.get("sensor.herb_bed_model_insight")
    assert state is not None
    assert state.state == "no model"
    assert state.attributes["parameters"]["eta_irr"]["value"] is None
    assert state.attributes["overall_confidence"] is None
    assert state.attributes["decision_explanation"] is None


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
    assert "button.herb_bed_watering_run" in buttons
    assert "button.herb_bed_watering_stop" not in buttons
