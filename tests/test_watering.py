"""Tests for the WateringController, buttons, and run/stop services."""

from __future__ import annotations

import json

import pytest
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    ACTUATOR_LINKTAP,
    ACTUATOR_SWITCH,
    CONF_ACTUATOR_SWITCH,
    CONF_ACTUATOR_TYPE,
    CONF_LINKTAP_FAILSAFE,
    CONF_LINKTAP_ID,
    CONF_MAX_LITERS,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_TARGET_MOISTURE,
    CONF_VOLUME_SENSOR,
    CONF_WATERING_SENSOR,
    CONF_ZONES,
    DATA_CONTROLLERS,
    DATA_ZONE_STATE,
    DOMAIN,
    SERVICE_RUN_ZONE,
    SERVICE_STOP_ZONE,
)
from custom_components.amazing_irrigation.watering import WateringStatus


def _record_switch(hass: HomeAssistant, *, raise_on_start: bool = False) -> list:
    calls: list[ServiceCall] = []

    async def _on(call: ServiceCall) -> None:
        calls.append(call)
        if raise_on_start:
            raise HomeAssistantError("boom")

    async def _off(call: ServiceCall) -> None:
        calls.append(call)

    def _register() -> None:
        hass.services.async_register("switch", "turn_on", _on)
        hass.services.async_register("switch", "turn_off", _off)

    _register()
    # Setting up the integration forwards the ``switch`` platform, which makes
    # Home Assistant register the core switch.turn_on/turn_off services and clobber
    # this recorder. Stash the re-register hook so ``_setup`` can reinstate it.
    hass.data["_switch_recorder"] = _register
    return calls


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
    # Reinstate any test switch recorder clobbered by the switch platform setup.
    reregister = hass.data.get("_switch_recorder")
    if reregister is not None:
        reregister()
    return entry


def _controller(hass: HomeAssistant, entry: MockConfigEntry):
    return hass.data[DOMAIN][entry.entry_id][DATA_CONTROLLERS]["abc123"]


def _zone_state(hass: HomeAssistant, entry: MockConfigEntry):
    return hass.data[DOMAIN][entry.entry_id][DATA_ZONE_STATE].get("abc123")


_SWITCH_ZONE = {
    CONF_NAME: "Herb Bed",
    CONF_MOISTURE_SENSORS: ["sensor.a"],
    CONF_TARGET_MOISTURE: 40,
    CONF_MAX_LITERS: 30,
    CONF_ACTUATOR_TYPE: ACTUATOR_SWITCH,
    CONF_ACTUATOR_SWITCH: "switch.valve",
}


async def test_run_commands_switch_but_unconfirmed_without_feedback(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set("sensor.a", "20.0")
    calls = _record_switch(hass)
    entry = await _setup(hass, _SWITCH_ZONE)

    event = await _controller(hass, entry).async_run()
    await hass.async_block_till_done()

    assert event.status is WateringStatus.COMMANDED
    assert event.confirmed is False
    assert len(calls) == 1
    state = hass.states.get("sensor.herb_bed_watering_status")
    assert state.state == "commanded"
    assert state.attributes["confirmed"] is False


async def test_above_target_run_skips_without_calling_actuator(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set("sensor.a", "55.0")
    calls = _record_switch(hass)
    entry = await _setup(hass, _SWITCH_ZONE)

    event = await _controller(hass, entry).async_run()
    assert event.status is WateringStatus.SKIPPED
    assert event.reason == "above_target"
    assert calls == []


async def test_confirmation_when_watering_sensor_on(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("binary_sensor.flow", "off")
    _record_switch(hass)
    entry = await _setup(
        hass, {**_SWITCH_ZONE, CONF_WATERING_SENSOR: "binary_sensor.flow"}
    )

    controller = _controller(hass, entry)
    await controller.async_run()
    hass.states.async_set("binary_sensor.flow", "on")
    await hass.async_block_till_done()

    assert controller.last_event.status is WateringStatus.CONFIRMED
    assert hass.states.get("sensor.herb_bed_watering_status").state == "confirmed"


async def test_confirmation_via_volume_increase(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.vol", "100")
    _record_switch(hass)
    entry = await _setup(
        hass, {**_SWITCH_ZONE, CONF_VOLUME_SENSOR: "sensor.vol"}
    )

    controller = _controller(hass, entry)
    await controller.async_run()
    hass.states.async_set("sensor.vol", "108")
    await hass.async_block_till_done()

    assert controller.last_event.status is WateringStatus.CONFIRMED
    assert controller.last_event.measured_liters == pytest.approx(8.0)


async def test_failure_recorded_when_actuator_raises(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.a", "20.0")
    _record_switch(hass, raise_on_start=True)
    entry = await _setup(hass, _SWITCH_ZONE)

    event = await _controller(hass, entry).async_run()
    assert event.status is WateringStatus.FAILED
    assert event.reason == "boom"
    assert hass.states.get("sensor.herb_bed_watering_status").state == "failed"


async def test_stop_commands_switch_off(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.a", "20.0")
    calls = _record_switch(hass)
    entry = await _setup(hass, _SWITCH_ZONE)

    controller = _controller(hass, entry)
    await controller.async_run()
    event = await controller.async_stop()

    assert event.status is WateringStatus.STOPPED
    assert any(c.service == "turn_off" for c in calls)
    assert controller.is_watering is False


async def test_total_volume_accumulates_measured_on_confirmation(
    hass: HomeAssistant,
) -> None:
    """A confirmed volume increase adds to the zone's Total Watering Volume."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.vol", "100")
    _record_switch(hass)
    entry = await _setup(hass, {**_SWITCH_ZONE, CONF_VOLUME_SENSOR: "sensor.vol"})

    controller = _controller(hass, entry)
    await controller.async_run()
    hass.states.async_set("sensor.vol", "108")
    await hass.async_block_till_done()

    assert _zone_state(hass, entry).total_liters == pytest.approx(8.0)
    sensor = hass.states.get("sensor.herb_bed_total_watering_volume")
    assert sensor is not None
    assert float(sensor.state) == pytest.approx(8.0)


async def test_total_volume_uses_requested_when_no_measurement(
    hass: HomeAssistant,
) -> None:
    """Confirmed flow without a volume sensor counts the requested liters once."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("binary_sensor.flow", "off")
    _record_switch(hass)
    entry = await _setup(
        hass, {**_SWITCH_ZONE, CONF_WATERING_SENSOR: "binary_sensor.flow"}
    )

    controller = _controller(hass, entry)
    await controller.async_run()
    hass.states.async_set("binary_sensor.flow", "on")
    await hass.async_block_till_done()

    # max_liters with no gain bounds the request to 30 L.
    assert _zone_state(hass, entry).total_liters == pytest.approx(30.0)


async def test_total_volume_not_double_counted(hass: HomeAssistant) -> None:
    """Repeated confirmation callbacks must not inflate the total."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("binary_sensor.flow", "off")
    _record_switch(hass)
    entry = await _setup(
        hass, {**_SWITCH_ZONE, CONF_WATERING_SENSOR: "binary_sensor.flow"}
    )

    controller = _controller(hass, entry)
    await controller.async_run()
    hass.states.async_set("binary_sensor.flow", "on")
    await hass.async_block_till_done()
    # A second confirmation signal for the same event must not re-add volume.
    controller._check_confirmation()
    await hass.async_block_till_done()

    assert _zone_state(hass, entry).total_liters == pytest.approx(30.0)


async def test_system_total_volume_reflects_zone(hass: HomeAssistant) -> None:
    """The integration-wide Total Watering Volume aggregates zone volume."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.vol", "100")
    _record_switch(hass)
    entry = await _setup(hass, {**_SWITCH_ZONE, CONF_VOLUME_SENSOR: "sensor.vol"})

    controller = _controller(hass, entry)
    await controller.async_run()
    hass.states.async_set("sensor.vol", "108")
    await hass.async_block_till_done()

    system = hass.states.get("sensor.amazing_irrigation_total_watering_volume")
    assert system is not None
    assert float(system.state) == pytest.approx(8.0)


async def test_run_and_stop_buttons(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.a", "20.0")
    calls = _record_switch(hass)
    await _setup(hass, _SWITCH_ZONE)

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.herb_bed_watering_run"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert any(c.service == "turn_on" for c in calls)

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.herb_bed_watering_stop"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert any(c.service == "turn_off" for c in calls)


async def test_overlapping_run_does_not_reactuate(hass: HomeAssistant) -> None:
    """A Run Request for an already-watering zone must not re-command."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("binary_sensor.flow", "off")
    calls = _record_switch(hass)
    entry = await _setup(
        hass, {**_SWITCH_ZONE, CONF_WATERING_SENSOR: "binary_sensor.flow"}
    )

    controller = _controller(hass, entry)
    await controller.async_run()
    hass.states.async_set("binary_sensor.flow", "on")
    await hass.async_block_till_done()
    assert controller.last_event.status is WateringStatus.CONFIRMED
    assert len(calls) == 1

    event = await controller.async_run()
    await hass.async_block_till_done()

    assert event.reason == "already_watering"
    assert len(calls) == 1
    assert controller.last_event.status is WateringStatus.CONFIRMED


async def test_volume_tick_before_confirmation_does_not_finalize(
    hass: HomeAssistant,
) -> None:
    """A volume update while the watering sensor is still off must not stop."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("binary_sensor.flow", "off")
    hass.states.async_set("sensor.vol", "100")
    _record_switch(hass)
    entry = await _setup(
        hass,
        {
            **_SWITCH_ZONE,
            CONF_WATERING_SENSOR: "binary_sensor.flow",
            CONF_VOLUME_SENSOR: "sensor.vol",
        },
    )

    controller = _controller(hass, entry)
    await controller.async_run()
    hass.states.async_set("sensor.vol", "101")
    await hass.async_block_till_done()

    assert controller.is_watering is True
    assert controller.last_event.status is not WateringStatus.STOPPED


async def test_confirmation_with_resetting_volume_sensor(
    hass: HomeAssistant,
) -> None:
    """A per-cycle sensor that resets to 0 at start still measures real flow.

    The device counter holds the previous cycle's final value (5 L) when the run
    starts, resets to 0, then climbs to 3 L. The reset-aware accumulator must
    report 3 L, not a bogus negative/zero delta from the stale baseline.
    """
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.vol", "5")
    _record_switch(hass)
    entry = await _setup(hass, {**_SWITCH_ZONE, CONF_VOLUME_SENSOR: "sensor.vol"})

    controller = _controller(hass, entry)
    await controller.async_run()
    # Device resets to 0 on start, then accumulates this cycle's flow.
    hass.states.async_set("sensor.vol", "0")
    await hass.async_block_till_done()
    hass.states.async_set("sensor.vol", "3")
    await hass.async_block_till_done()

    assert controller.last_event.status is WateringStatus.CONFIRMED
    assert controller.last_event.measured_liters == pytest.approx(3.0)
    assert _zone_state(hass, entry).total_liters == pytest.approx(3.0)


async def test_resetting_volume_sensor_accumulates_across_events(
    hass: HomeAssistant,
) -> None:
    """Consecutive resetting cycles each add their own flow to the total."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.vol", "5")
    _record_switch(hass)
    entry = await _setup(hass, {**_SWITCH_ZONE, CONF_VOLUME_SENSOR: "sensor.vol"})

    controller = _controller(hass, entry)

    await controller.async_run()
    hass.states.async_set("sensor.vol", "0")
    await hass.async_block_till_done()
    hass.states.async_set("sensor.vol", "3")
    await hass.async_block_till_done()
    await controller.async_stop()

    # Second cycle: sensor still holds the prior 3 L, resets, climbs to 2 L.
    await controller.async_run()
    hass.states.async_set("sensor.vol", "0")
    await hass.async_block_till_done()
    hass.states.async_set("sensor.vol", "2")
    await hass.async_block_till_done()
    await controller.async_stop()

    assert _zone_state(hass, entry).total_liters == pytest.approx(5.0)


async def test_volume_sensor_reset_mid_event_is_accumulated(
    hass: HomeAssistant,
) -> None:
    """A reset during a single event keeps the running total correct.

    Post-confirmation flow (including a reset) is reconciled when the event ends,
    matching how finalisation tops up the measured volume.
    """
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.vol", "0")
    _record_switch(hass)
    entry = await _setup(hass, {**_SWITCH_ZONE, CONF_VOLUME_SENSOR: "sensor.vol"})

    controller = _controller(hass, entry)
    await controller.async_run()
    hass.states.async_set("sensor.vol", "3")
    await hass.async_block_till_done()
    # Mid-event reset back to 0, then a further 2 L, reconciled on stop.
    hass.states.async_set("sensor.vol", "0")
    await hass.async_block_till_done()
    hass.states.async_set("sensor.vol", "2")
    await hass.async_block_till_done()
    await controller.async_stop()

    assert controller.last_event.measured_liters == pytest.approx(5.0)
    assert _zone_state(hass, entry).total_liters == pytest.approx(5.0)


async def test_unload_releases_feedback_subscription(hass: HomeAssistant) -> None:
    """Unloading the entry must tear down a live feedback subscription."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("binary_sensor.flow", "off")
    _record_switch(hass)
    entry = await _setup(
        hass, {**_SWITCH_ZONE, CONF_WATERING_SENSOR: "binary_sensor.flow"}
    )

    controller = _controller(hass, entry)
    await controller.async_run()
    assert controller.is_watering is True

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert controller.is_watering is False


async def test_linktap_missing_id_or_switch_is_rejected(hass: HomeAssistant) -> None:
    """The options flow rejects a LinkTap zone missing its id or switch."""
    from custom_components.amazing_irrigation.config_flow import _validate_zone_input

    base = {
        CONF_NAME: "Z",
        CONF_MOISTURE_SENSORS: ["sensor.a"],
        CONF_ACTUATOR_TYPE: ACTUATOR_LINKTAP,
    }
    errors = _validate_zone_input(base)
    assert CONF_LINKTAP_ID in errors
    assert CONF_ACTUATOR_SWITCH in errors

    ok = _validate_zone_input(
        {**base, CONF_LINKTAP_ID: "ID1", CONF_ACTUATOR_SWITCH: "switch.v"}
    )
    assert ok == {}


async def test_linktap_run_publishes_mqtt_and_confirms(hass: HomeAssistant) -> None:
    """A LinkTap zone publishes volume+failsafe, turns on the switch, confirms."""
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("binary_sensor.tap_watering", "off")
    mqtt_calls: list[ServiceCall] = []

    async def _publish(call: ServiceCall) -> None:
        mqtt_calls.append(call)

    hass.services.async_register("mqtt", "publish", _publish)
    switch_calls = _record_switch(hass)

    entry = await _setup(
        hass,
        {
            CONF_NAME: "Taka Altaat",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_TARGET_MOISTURE: 40,
            CONF_MAX_LITERS: 30,
            CONF_ACTUATOR_TYPE: ACTUATOR_LINKTAP,
            CONF_ACTUATOR_SWITCH: "switch.tap",
            CONF_LINKTAP_ID: "1F43B22F004B1200_3",
            CONF_LINKTAP_FAILSAFE: 3600,
            CONF_WATERING_SENSOR: "binary_sensor.tap_watering",
        },
    )

    controller = _controller(hass, entry)
    event = await controller.async_run()
    await hass.async_block_till_done()

    assert event.status is WateringStatus.COMMANDED
    assert len(mqtt_calls) == 2
    payloads = [json.loads(c.data["payload"]) for c in mqtt_calls]
    assert payloads[0]["tag"] == "volume_limit"
    assert payloads[0]["id"] == "1F43B22F004B1200_3"
    assert payloads[1]["duration"] == 3600
    assert any(c.service == "turn_on" for c in switch_calls)

    hass.states.async_set("binary_sensor.tap_watering", "on")
    await hass.async_block_till_done()
    assert controller.last_event.status is WateringStatus.CONFIRMED

    await controller.async_stop()
    assert any(c.service == "turn_off" for c in switch_calls)


async def test_run_zone_service_via_device(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.a", "20.0")
    calls = _record_switch(hass)
    entry = await _setup(hass, _SWITCH_ZONE)

    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, f"{entry.entry_id}_abc123")}
    )
    assert device is not None

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_RUN_ZONE,
        {"device_id": device.id},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    assert response["results"][0]["zone_id"] == "abc123"
    assert response["results"][0]["status"] == "commanded"
    assert any(c.service == "turn_on" for c in calls)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_STOP_ZONE,
        {"device_id": device.id},
        blocking=True,
        return_response=True,
    )
    assert any(c.service == "turn_off" for c in calls)
