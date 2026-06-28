"""Integration tests for the live ZoneLearner wiring."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    ACTUATOR_SWITCH,
    CONF_ACTUATOR_SWITCH,
    CONF_ACTUATOR_TYPE,
    CONF_LEARNING_ENABLED,
    CONF_MAX_LITERS,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_OBSERVED_RAIN_AMOUNT,
    CONF_TARGET_MOISTURE,
    CONF_ZONES,
    DATA_LEARNERS,
    DATA_ZONE_STATE,
    DOMAIN,
    EVENT_WATERING,
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
    """A confirmed watering plus a moisture rise yields a gain-per-liter value."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.rain", "0.0")
    entry = await _setup(hass, _ZONE)

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
    assert state.learned_gain_per_liter == 2.0
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
    assert state.learned_gain_per_liter is None


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
    """The five read-only learned sensors are registered for a zone."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.rain", "0.0")
    await _setup(hass, _ZONE)

    for suffix in (
        "learned_moisture_gain_per_liter",
        "learned_daily_drying_rate",
        "learned_rain_efficiency",
        "learned_field_capacity",
        "learned_wilting_point",
    ):
        assert hass.states.get(f"sensor.herb_bed_{suffix}") is not None


async def test_learners_present_in_domain_data(hass: HomeAssistant) -> None:
    """A ZoneLearner is wired for each configured zone."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.rain", "0.0")
    entry = await _setup(hass, _ZONE)
    learners = hass.data[DOMAIN][entry.entry_id][DATA_LEARNERS]
    assert "abc123" in learners
