"""Integration tests for the live ZoneLearner wiring."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    ACTUATOR_SWITCH,
    CONF_ACTUATOR_SWITCH,
    CONF_ACTUATOR_TYPE,
    CONF_FIELD_CAPACITY,
    CONF_GAIN_PER_LITER,
    CONF_GREENHOUSE,
    CONF_HUMIDITY_SENSOR,
    CONF_LEARNING_ENABLED,
    CONF_MAX_LITERS,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_OBSERVED_RAIN_AMOUNT,
    CONF_SOIL_TYPE,
    CONF_SOLAR_RADIATION,
    CONF_TARGET_MOISTURE,
    CONF_TEMPERATURE_SENSOR,
    CONF_WILTING_POINT,
    CONF_WIND_SPEED,
    CONF_ZONES,
    DATA_LEARNERS,
    DATA_ZONE_STATE,
    DOMAIN,
    EVENT_WATERING,
)
from custom_components.amazing_irrigation.state import apply_model_to_state
from custom_components.amazing_irrigation.waterbalance import (
    WaterBalanceParams,
    default_params,
)

_ZONE = {
    CONF_NAME: "Herb Bed",
    CONF_MOISTURE_SENSORS: ["sensor.a"],
    CONF_TARGET_MOISTURE: 40,
    CONF_MAX_LITERS: 30,
    CONF_ACTUATOR_TYPE: ACTUATOR_SWITCH,
    CONF_ACTUATOR_SWITCH: "switch.valve",
    CONF_OBSERVED_RAIN_AMOUNT: "sensor.rain",
    CONF_LEARNING_ENABLED: True,
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


async def test_learner_learns_gain_from_watering(hass: HomeAssistant) -> None:
    """A confirmed watering plus a moisture rise updates the joint model."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.rain", "0.0")
    entry = await _setup(hass, _ZONE)
    state = _state(hass, entry)
    state.learning_state["last_time"] = (
        dt_util.utcnow() - timedelta(hours=1)
    ).isoformat()

    # Simulate a Watering Event: started, then confirmed with measured liters.
    hass.bus.async_fire(EVENT_WATERING, {"zone_id": "abc123", "status": "commanded"})
    await hass.async_block_till_done()
    hass.bus.async_fire(
        EVENT_WATERING,
        {"zone_id": "abc123", "status": "confirmed", "measured_liters": 5.0,
         "requested_liters": 5.0},
    )
    await hass.async_block_till_done()

    # Moisture settles 10 points higher -> gain = 10 / 5 = 2 %/L.
    hass.states.async_set("sensor.a", "30.0")
    await hass.async_block_till_done()

    state = _state(hass, entry)
    assert state.model_params is not None
    assert state.model_covariance is not None
    assert state.model_confidence is not None
    assert state.learned_gain_per_liter == pytest.approx(2.0, abs=0.02)
    assert state.learning_state.get("gain_samples") == 1


async def test_learner_ignores_other_zone_events(hass: HomeAssistant) -> None:
    """A Watering Event for a different zone does not arm gain learning."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.rain", "0.0")
    entry = await _setup(hass, _ZONE)

    hass.bus.async_fire(EVENT_WATERING, {"zone_id": "other", "status": "commanded"})
    await hass.async_block_till_done()
    hass.states.async_set("sensor.a", "30.0")
    await hass.async_block_till_done()

    state = _state(hass, entry)
    assert state.learning_state.get("gain_samples", 0) == 0


async def test_learner_tracks_capacity_envelope(hass: HomeAssistant) -> None:
    """Observed moisture extremes seed Field Capacity and Wilting Point."""
    hass.states.async_set("sensor.a", "50.0")
    hass.states.async_set("sensor.rain", "0.0")
    entry = await _setup(hass, _ZONE)

    hass.states.async_set("sensor.a", "70.0")  # new high
    await hass.async_block_till_done()
    hass.states.async_set("sensor.a", "30.0")  # new low
    await hass.async_block_till_done()

    state = _state(hass, entry)
    assert state.learned_field_capacity is not None
    assert state.learned_wilting_point is not None
    assert state.learned_field_capacity > state.learned_wilting_point


async def test_learned_sensors_are_created(hass: HomeAssistant) -> None:
    """The read-only learned sensors are registered for a zone."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.rain", "0.0")
    await _setup(hass, _ZONE)

    for suffix in (
        "learned_moisture_gain_per_liter",
        "learned_daily_drying_rate",
        "learned_rain_efficiency",
        "learned_field_capacity",
        "learned_wilting_point",
        "learned_drainage_rate",
        "learned_et_coefficient",
        "model_confidence",
    ):
        assert hass.states.get(f"sensor.herb_bed_{suffix}") is not None


async def test_learners_present_in_domain_data(hass: HomeAssistant) -> None:
    """A ZoneLearner is wired for each configured zone."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.rain", "0.0")
    entry = await _setup(hass, _ZONE)
    learners = hass.data[DOMAIN][entry.entry_id][DATA_LEARNERS]
    assert "abc123" in learners


async def test_learner_seeds_estimator_from_soil_type(hass: HomeAssistant) -> None:
    """New estimators use the configured soil-type prior."""
    record = {**_ZONE, CONF_SOIL_TYPE: "sand"}
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.rain", "0.0")
    entry = await _setup(hass, record)
    state = _state(hass, entry)
    learner = hass.data[DOMAIN][entry.entry_id][DATA_LEARNERS]["abc123"]

    estimator = learner._ensure_estimator(state)  # noqa: SLF001

    assert estimator.params.field_capacity == default_params("sand").field_capacity
    assert estimator.params.wilting_point == default_params("sand").wilting_point


async def test_learner_jointly_assembles_water_rain_drying_and_greenhouse_climate(
    hass: HomeAssistant,
) -> None:
    """Water, rain, drying and greenhouse climate feed one estimator interval."""
    record = {
        **_ZONE,
        CONF_GREENHOUSE: True,
        CONF_TEMPERATURE_SENSOR: "sensor.house_temp",
        CONF_HUMIDITY_SENSOR: "sensor.house_humidity",
        CONF_WIND_SPEED: "sensor.wind",
        CONF_SOLAR_RADIATION: "sensor.solar",
    }
    hass.states.async_set("sensor.a", "40.0")
    hass.states.async_set("sensor.rain", "1.0")
    hass.states.async_set("sensor.house_temp", "28.0")
    hass.states.async_set("sensor.house_humidity", "45.0")
    hass.states.async_set("sensor.wind", "1.5")
    hass.states.async_set("sensor.solar", "500")
    entry = await _setup(hass, record)
    state = _state(hass, entry)
    state.learning_state["last_time"] = (
        dt_util.utcnow() - timedelta(hours=2)
    ).isoformat()

    hass.bus.async_fire(
        EVENT_WATERING,
        {"zone_id": "abc123", "status": "confirmed", "measured_liters": 2.0},
    )
    await hass.async_block_till_done()
    hass.states.async_set("sensor.rain", "4.0")
    hass.states.async_set("sensor.a", "46.0")
    await hass.async_block_till_done()

    state = _state(hass, entry)
    assert state.model_params is not None
    assert state.model_params["eta_irr"] > 1.2
    assert state.model_params["eta_rain"] > 0.9
    assert state.learning_state["gain_samples"] == 1
    assert state.learning_state["rain_samples"] == 1
    assert state.learning_state["drying_samples"] == 1


async def test_learner_respects_manual_overrides(hass: HomeAssistant) -> None:
    """Manual gain, FC and WP overrides stay fixed through estimator updates."""
    record = {
        **_ZONE,
        CONF_GAIN_PER_LITER: 3.0,
        CONF_FIELD_CAPACITY: 60.0,
        CONF_WILTING_POINT: 22.0,
    }
    hass.states.async_set("sensor.a", "30.0")
    hass.states.async_set("sensor.rain", "0.0")
    entry = await _setup(hass, record)
    state = _state(hass, entry)
    state.learning_state["last_time"] = (
        dt_util.utcnow() - timedelta(hours=1)
    ).isoformat()

    hass.bus.async_fire(
        EVENT_WATERING,
        {"zone_id": "abc123", "status": "confirmed", "measured_liters": 10.0},
    )
    await hass.async_block_till_done()
    hass.states.async_set("sensor.a", "32.0")
    await hass.async_block_till_done()

    assert state.model_params["eta_irr"] == pytest.approx(3.0)
    assert state.model_params["field_capacity"] == pytest.approx(60.0)
    assert state.model_params["wilting_point"] == pytest.approx(22.0)
    assert state.learned_gain_per_liter == pytest.approx(3.0)
    assert state.learned_field_capacity == pytest.approx(60.0)
    assert state.learned_wilting_point == pytest.approx(22.0)


async def test_new_learned_sensors_read_model_dict_values(
    hass: HomeAssistant,
) -> None:
    """Drainage, ET and confidence sensors read values from ZoneState dicts."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.rain", "0.0")
    entry = await _setup(hass, _ZONE)
    state = _state(hass, entry)
    learner = hass.data[DOMAIN][entry.entry_id][DATA_LEARNERS]["abc123"]

    assert hass.states.get("sensor.herb_bed_learned_drainage_rate").state == (
        "unavailable"
    )
    apply_model_to_state(
        state,
        WaterBalanceParams(1.5, 1.0, 0.65, 0.14, 50.0, 18.0),
        {"eta_irr": 0.2, "eta_rain": 0.4, "k_et": 0.6, "drain_rate": 0.8},
    )
    for listener in list(learner._listeners):  # noqa: SLF001
        listener()
    await hass.async_block_till_done()

    assert float(hass.states.get("sensor.herb_bed_learned_drainage_rate").state) == (
        pytest.approx(0.14)
    )
    assert float(hass.states.get("sensor.herb_bed_learned_et_coefficient").state) == (
        pytest.approx(0.65)
    )
    assert float(hass.states.get("sensor.herb_bed_model_confidence").state) == (
        pytest.approx(50.0)
    )
