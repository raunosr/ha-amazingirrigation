"""Tests for the Irrigation Decision sensor and evaluate_zone service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    CONF_FORECAST_AIR_HUMIDITY,
    CONF_FORECAST_AIR_TEMPERATURE,
    CONF_GREENHOUSE,
    CONF_HUMIDITY_SENSOR,
    CONF_LEARNING_ENABLED,
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
    CONF_WEATHER_FORECAST_ENTITY,
    CONF_WIND_SPEED,
    CONF_ZONES,
    DATA_WEATHER_FORECAST,
    DATA_ZONE_STATE,
    DOMAIN,
    EVENT_DECISION,
    SERVICE_EVALUATE_ZONE,
)
from custom_components.amazing_irrigation.decision import (
    _forecast_horizon,
    build_inputs,
)
from custom_components.amazing_irrigation.state import ZoneState, apply_model_to_state
from custom_components.amazing_irrigation.waterbalance import WaterBalanceParams
from custom_components.amazing_irrigation.weather_forecast import ForecastPoint
from custom_components.amazing_irrigation.zone import ZoneConfig


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
            CONF_WEATHER_FORECAST_ENTITY: "weather.home",
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
        "weather_forecast_entity": "weather.home",
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
    assert "button.herb_bed_watering_run" in buttons
    assert "button.herb_bed_watering_stop" not in buttons


def test_build_inputs_enables_predictive_with_model_and_horizon(
    hass: HomeAssistant,
) -> None:
    """A learned model produces predictive engine inputs to the next slot."""
    hass.states.async_set("sensor.soil", "39.0")
    hass.states.async_set("sensor.rain", "2.0")
    hass.states.async_set("sensor.probability", "80.0")
    hass.states.async_set("sensor.forecast_temp", "25.0")
    hass.states.async_set("sensor.forecast_humidity", "60.0")
    zone = ZoneConfig(
        zone_id="abc123",
        name="Bed",
        moisture_sensors=["sensor.soil"],
        forecast_rain_amount="sensor.rain",
        forecast_rain_probability="sensor.probability",
        forecast_air_temperature="sensor.forecast_temp",
        forecast_air_humidity="sensor.forecast_humidity",
        target_moisture=40.0,
        max_liters=10.0,
        learning_enabled=True,
    )
    state = ZoneState(
        zone_id="abc123",
        target_moisture=40.0,
        max_liters=10.0,
        learning_enabled=True,
        schedule_1_time="02:30",
        schedule_1_active=True,
        schedule_2_active=False,
    )
    apply_model_to_state(
        state,
        WaterBalanceParams(2.0, 1.0, 1.0, 0.0, 50.0, 10.0),
        {"eta_irr": 1.0},
    )
    now = datetime(2026, 6, 28, 1, 30, tzinfo=UTC)

    with patch("custom_components.amazing_irrigation.decision.dt_util.now", return_value=now):
        inputs = build_inputs(hass, zone, state=state)

    assert inputs.predictive is True
    assert inputs.params is not None
    assert inputs.target_band is not None
    assert inputs.target_band.low == 40.0
    assert inputs.target_band.high == 45.0
    assert inputs.horizon is not None
    assert len(inputs.horizon) == 1
    assert inputs.horizon[0].dt == 1.0
    assert inputs.horizon[0].rain_mm == 2.0
    assert inputs.horizon[0].climate.air_temp_c == 25.0


def test_build_inputs_uses_explicit_target_range_and_et_source(
    hass: HomeAssistant,
) -> None:
    """Explicit target bands and ET source preferences reach predictive inputs."""
    hass.states.async_set("sensor.soil", "34.0")
    hass.states.async_set("sensor.forecast_temp", "21.0")
    hass.states.async_set("sensor.greenhouse_temp", "29.0")
    zone = ZoneConfig(
        zone_id="abc123",
        name="Bed",
        moisture_sensors=["sensor.soil"],
        forecast_air_temperature="sensor.forecast_temp",
        temperature_sensor="sensor.greenhouse_temp",
        target_moisture=40.0,
        target_moisture_low=35.0,
        target_moisture_high=38.0,
        max_liters=10.0,
        learning_enabled=True,
        greenhouse=True,
        et_source="weather",
    )
    state = ZoneState(
        zone_id="abc123",
        target_moisture=40.0,
        max_liters=10.0,
        learning_enabled=True,
    )
    apply_model_to_state(
        state,
        WaterBalanceParams(2.0, 1.0, 1.0, 0.0, 50.0, 10.0),
        {"eta_irr": 1.0},
    )

    inputs = build_inputs(hass, zone, state=state)

    assert inputs.target_moisture == 35.0
    assert inputs.target_band is not None
    assert inputs.target_band.low == 35.0
    assert inputs.target_band.high == 38.0
    assert inputs.horizon is not None
    assert inputs.horizon[0].climate.air_temp_c == 21.0


def test_build_inputs_auto_mode_derives_band_from_profile(
    hass: HomeAssistant,
) -> None:
    """Automatic target mode builds the band from learned WP/FC + demand profile."""
    hass.states.async_set("sensor.soil", "34.0")
    hass.states.async_set("sensor.forecast_temp", "20.0")
    zone = ZoneConfig(
        zone_id="abc123",
        name="Bed",
        moisture_sensors=["sensor.soil"],
        forecast_air_temperature="sensor.forecast_temp",
        target_moisture=40.0,
        max_liters=10.0,
        learning_enabled=True,
        target_mode="auto",
        demand_profile="medium",
    )
    state = ZoneState(
        zone_id="abc123",
        target_moisture=40.0,
        max_liters=10.0,
        learning_enabled=True,
    )
    apply_model_to_state(
        state,
        WaterBalanceParams(2.0, 1.0, 1.0, 0.0, 50.0, 10.0),
        {"eta_irr": 1.0},
    )

    inputs = build_inputs(hass, zone, state=state)

    assert inputs.target_band is not None
    assert inputs.target_band.low == 30.0
    assert inputs.target_band.high == 36.0


def test_build_inputs_auto_mode_explicit_bounds_win(hass: HomeAssistant) -> None:
    """Explicit safety bounds still override the auto-derived demand band."""
    hass.states.async_set("sensor.soil", "34.0")
    hass.states.async_set("sensor.forecast_temp", "20.0")
    zone = ZoneConfig(
        zone_id="abc123",
        name="Bed",
        moisture_sensors=["sensor.soil"],
        forecast_air_temperature="sensor.forecast_temp",
        target_moisture=40.0,
        target_moisture_low=33.0,
        max_liters=10.0,
        learning_enabled=True,
        target_mode="auto",
        demand_profile="medium",
    )
    state = ZoneState(zone_id="abc123", target_moisture=40.0, max_liters=10.0, learning_enabled=True)
    apply_model_to_state(state, WaterBalanceParams(2.0, 1.0, 1.0, 0.0, 50.0, 10.0), {"eta_irr": 1.0})

    inputs = build_inputs(hass, zone, state=state)

    assert inputs.target_band is not None
    assert inputs.target_band.low == 33.0


def test_build_inputs_missing_model_uses_rule_based_fallback(
    hass: HomeAssistant,
) -> None:
    """Learning without a persisted model keeps the existing decision path."""
    hass.states.async_set("sensor.soil", "39.0")
    zone = ZoneConfig(
        zone_id="abc123",
        name="Bed",
        moisture_sensors=["sensor.soil"],
        target_moisture=40.0,
        max_liters=10.0,
        learning_enabled=True,
    )
    state = ZoneState(
        zone_id="abc123",
        target_moisture=40.0,
        max_liters=10.0,
        learning_enabled=True,
    )

    inputs = build_inputs(hass, zone, state=state)

    assert inputs.predictive is False
    assert inputs.params is None
    assert inputs.horizon is None


def test_weather_forecast_cache_drives_horizon_and_rule_based_rain(
    hass: HomeAssistant,
) -> None:
    """A configured weather entity supplies per-step climate and forecast rain."""
    now = datetime(2026, 6, 28, 1, 0, tzinfo=UTC)
    hass.data.setdefault(DOMAIN, {})[DATA_WEATHER_FORECAST] = {
        "weather.home": [
            ForecastPoint(now, 20, 60, 2, 1, 90),
            ForecastPoint(now.replace(hour=2), 21, 61, 3, 2, 30),
            ForecastPoint(now.replace(hour=3), 22, 62, 4, 3, 80),
        ]
    }
    hass.states.async_set("sensor.soil", "39.0")
    hass.states.async_set("sensor.solar", "450")
    zone = ZoneConfig(
        zone_id="abc123",
        name="Bed",
        moisture_sensors=["sensor.soil"],
        weather_forecast_entity="weather.home",
        forecast_rain_amount="sensor.scalar_rain",
        forecast_rain_probability="sensor.scalar_probability",
        solar_radiation="sensor.solar",
        target_moisture=40.0,
        max_liters=10.0,
    )
    state = ZoneState(
        zone_id="abc123",
        target_moisture=40.0,
        max_liters=10.0,
        schedule_1_time="04:00",
        schedule_1_active=True,
        schedule_2_active=False,
    )

    horizon = _forecast_horizon(hass, zone, state, now)
    with patch("custom_components.amazing_irrigation.decision.dt_util.now", return_value=now):
        inputs = build_inputs(hass, zone, state=state)

    assert [interval.climate.air_temp_c for interval in horizon] == [20, 21, 22]
    assert [interval.climate.air_humidity_pct for interval in horizon] == [60, 61, 62]
    assert [interval.climate.wind_ms for interval in horizon] == [2, 3, 4]
    assert horizon[0].climate.solar == 450
    assert [interval.rain_mm for interval in horizon] == [1, 0, 3]
    assert inputs.forecast_rain_mm == 4
    assert inputs.forecast_rain_probability == 90


def test_scalar_forecast_fallback_still_works_without_weather_cache(
    hass: HomeAssistant,
) -> None:
    """Without a weather cache the existing scalar forecast behavior remains."""
    now = datetime(2026, 6, 28, 1, 0, tzinfo=UTC)
    hass.data.setdefault(DOMAIN, {})[DATA_WEATHER_FORECAST] = {}
    hass.states.async_set("sensor.soil", "39.0")
    hass.states.async_set("sensor.rain", "6.0")
    hass.states.async_set("sensor.probability", "80.0")
    hass.states.async_set("sensor.forecast_temp", "25.0")
    zone = ZoneConfig(
        zone_id="abc123",
        name="Bed",
        moisture_sensors=["sensor.soil"],
        weather_forecast_entity="weather.home",
        forecast_rain_amount="sensor.rain",
        forecast_rain_probability="sensor.probability",
        forecast_air_temperature="sensor.forecast_temp",
        target_moisture=40.0,
        max_liters=10.0,
    )
    state = ZoneState(
        zone_id="abc123",
        target_moisture=40.0,
        max_liters=10.0,
        schedule_1_time="04:00",
        schedule_1_active=True,
        schedule_2_active=False,
    )

    horizon = _forecast_horizon(hass, zone, state, now)
    with patch("custom_components.amazing_irrigation.decision.dt_util.now", return_value=now):
        inputs = build_inputs(hass, zone, state=state)

    assert [interval.rain_mm for interval in horizon] == [2, 2, 2]
    assert {interval.climate.air_temp_c for interval in horizon} == {25}
    assert inputs.forecast_rain_mm == 6
    assert inputs.forecast_rain_probability == 80


async def test_decision_sensor_exposes_and_persists_predictive_explanation(
    hass: HomeAssistant,
) -> None:
    """Slice F can read the explanation and trajectory from sensor attrs."""
    hass.states.async_set("sensor.a", "39.0")
    entry = await _setup(
        hass,
        {
            CONF_NAME: "Predictive Bed",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_TARGET_MOISTURE: 40,
            CONF_MAX_LITERS: 30,
            CONF_LEARNING_ENABLED: True,
        },
    )
    store = hass.data[DOMAIN][entry.entry_id][DATA_ZONE_STATE]
    zone_state = store.get("abc123")
    zone_state.learning_enabled = True
    apply_model_to_state(
        zone_state,
        WaterBalanceParams(2.0, 1.0, 1.0, 0.0, 50.0, 10.0),
        {"eta_irr": 1.0},
    )

    hass.states.async_set("sensor.a", "38.5")
    await hass.async_block_till_done()

    sensor_state = hass.states.get("sensor.predictive_bed_irrigation_decision")
    assert sensor_state is not None
    assert sensor_state.attributes["reason"] == "predictive_water"
    assert "explanation" in sensor_state.attributes
    assert "predicted_trajectory" in sensor_state.attributes
    assert zone_state.decision_explanation == sensor_state.attributes["explanation"]
