"""Tests for the built-in zone scheduler."""

from __future__ import annotations

from datetime import datetime

from homeassistant.core import HomeAssistant, ServiceCall
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    ACTUATOR_SWITCH,
    CONF_ACTUATOR_SWITCH,
    CONF_ACTUATOR_TYPE,
    CONF_ENABLED,
    CONF_MAX_LITERS,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_WEEKDAYS,
    CONF_TARGET_MOISTURE,
    CONF_ZONES,
    DATA_CONTROLLERS,
    DATA_SCHEDULER,
    DOMAIN,
)
from custom_components.amazing_irrigation.scheduler import (
    ZoneSchedule,
    another_zone_watering,
    parse_times,
    parse_weekdays,
)
from custom_components.amazing_irrigation.watering import WateringStatus
from custom_components.amazing_irrigation.zone import ZoneConfig


def test_parse_weekdays_empty_means_every_day() -> None:
    assert parse_weekdays([]) == set(range(7))
    assert parse_weekdays(None) == set(range(7))


def test_parse_weekdays_tokens() -> None:
    assert parse_weekdays(["mon", "wed", "sun"]) == {0, 2, 6}
    assert parse_weekdays(["Monday", "FRI"]) == {0, 4}
    assert parse_weekdays(["bogus"]) == set()


def test_parse_times_valid_and_invalid() -> None:
    assert parse_times(["06:00", "20:30", "06:00"]) == [(6, 0), (20, 30)]
    assert parse_times(["nope", "25:00", "12:99", "7"]) == []


def test_schedule_is_due() -> None:
    schedule = ZoneSchedule(
        zone_id="z1", enabled=True, weekdays={0, 2}, times=[(6, 0)]
    )
    assert schedule.is_due(0, 6, 0) is True
    assert schedule.is_due(1, 6, 0) is False  # wrong weekday
    assert schedule.is_due(0, 6, 1) is False  # wrong minute


def test_disabled_or_timeless_schedule_never_due() -> None:
    disabled = ZoneSchedule("z", enabled=False, weekdays={0}, times=[(6, 0)])
    timeless = ZoneSchedule("z", enabled=True, weekdays={0}, times=[])
    assert disabled.is_due(0, 6, 0) is False
    assert timeless.is_due(0, 6, 0) is False


def test_schedule_from_zone() -> None:
    zone = ZoneConfig.from_record(
        "z1",
        {
            CONF_NAME: "Z",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_SCHEDULE_WEEKDAYS: ["mon", "tue"],
            CONF_SCHEDULE_TIMES: ["06:00"],
        },
    )
    schedule = ZoneSchedule.from_zone(zone)
    assert schedule.weekdays == {0, 1}
    assert schedule.times == [(6, 0)]
    assert schedule.enabled is True


class _FakeController:
    def __init__(self, watering: bool) -> None:
        self.is_watering = watering


def test_another_zone_watering() -> None:
    controllers = {
        "a": _FakeController(True),
        "b": _FakeController(False),
    }
    assert another_zone_watering(controllers, "b") is True
    assert another_zone_watering(controllers, "a") is False


def _record_switch(hass: HomeAssistant) -> list[ServiceCall]:
    calls: list[ServiceCall] = []

    async def _on(call: ServiceCall) -> None:
        calls.append(call)

    hass.services.async_register("switch", "turn_on", _on)
    hass.services.async_register("switch", "turn_off", _on)
    return calls


async def _setup(hass: HomeAssistant, record: dict) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={CONF_ZONES: {"z1": record}},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_due_schedule_creates_run_request(hass: HomeAssistant) -> None:
    """A due schedule waters via the controller and the decision engine."""
    hass.states.async_set("sensor.a", "20.0")
    calls = _record_switch(hass)
    entry = await _setup(
        hass,
        {
            CONF_NAME: "Herbs",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_TARGET_MOISTURE: 40,
            CONF_MAX_LITERS: 30,
            CONF_ACTUATOR_TYPE: ACTUATOR_SWITCH,
            CONF_ACTUATOR_SWITCH: "switch.valve",
            CONF_SCHEDULE_TIMES: ["06:00"],
        },
    )
    scheduler = hass.data[DOMAIN][entry.entry_id][DATA_SCHEDULER]
    controller = hass.data[DOMAIN][entry.entry_id][DATA_CONTROLLERS]["z1"]

    # Monday 06:00 -> due.
    await scheduler._run_due(datetime(2024, 6, 3, 6, 0, 0))
    await hass.async_block_till_done()

    assert any(c.service == "turn_on" for c in calls)
    assert controller.last_event.status is WateringStatus.COMMANDED


async def test_disabled_zone_schedule_does_not_water(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.a", "20.0")
    calls = _record_switch(hass)
    entry = await _setup(
        hass,
        {
            CONF_NAME: "Herbs",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_TARGET_MOISTURE: 40,
            CONF_MAX_LITERS: 30,
            CONF_ACTUATOR_TYPE: ACTUATOR_SWITCH,
            CONF_ACTUATOR_SWITCH: "switch.valve",
            CONF_SCHEDULE_TIMES: ["06:00"],
            CONF_ENABLED: False,
        },
    )
    scheduler = hass.data[DOMAIN][entry.entry_id][DATA_SCHEDULER]

    await scheduler._run_due(datetime(2024, 6, 3, 6, 0, 0))
    await hass.async_block_till_done()

    assert all(c.service != "turn_on" for c in calls)


async def test_same_day_repeat_fires_once(hass: HomeAssistant) -> None:
    """A wall-clock repeat (e.g. DST fall-back) must not water twice in a day."""
    hass.states.async_set("sensor.a", "20.0")
    calls = _record_switch(hass)
    entry = await _setup(
        hass,
        {
            CONF_NAME: "Herbs",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_TARGET_MOISTURE: 40,
            CONF_MAX_LITERS: 30,
            CONF_ACTUATOR_TYPE: ACTUATOR_SWITCH,
            CONF_ACTUATOR_SWITCH: "switch.valve",
            CONF_SCHEDULE_TIMES: ["06:00"],
        },
    )
    scheduler = hass.data[DOMAIN][entry.entry_id][DATA_SCHEDULER]
    controller = hass.data[DOMAIN][entry.entry_id][DATA_CONTROLLERS]["z1"]

    await scheduler._run_due(datetime(2024, 6, 3, 6, 0, 0))
    await hass.async_block_till_done()
    await controller.async_stop()  # clear the live run
    calls.clear()

    # Same local date and time fires again -> deduplicated, no new run.
    await scheduler._run_due(datetime(2024, 6, 3, 6, 0, 0))
    await hass.async_block_till_done()
    assert all(c.service != "turn_on" for c in calls)
