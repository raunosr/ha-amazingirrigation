"""Pure tests for actuator call-spec generation and volume bounding."""

from __future__ import annotations

import json

from custom_components.amazing_irrigation.actuator import (
    ActuatorConfig,
    build_start_call,
    build_start_calls,
    build_stop_call,
    build_stop_calls,
)
from custom_components.amazing_irrigation.const import (
    ACTUATOR_LINKTAP,
    ACTUATOR_NONE,
    ACTUATOR_SCRIPT,
    ACTUATOR_SERVICE,
    ACTUATOR_SWITCH,
)
from custom_components.amazing_irrigation.watering import bound_volume


def test_switch_actuator_calls() -> None:
    actuator = ActuatorConfig(actuator_type=ACTUATOR_SWITCH, switch="switch.valve")
    start = build_start_call(actuator, 12.0)
    stop = build_stop_call(actuator)
    assert (start.domain, start.service, start.data) == (
        "switch",
        "turn_on",
        {"entity_id": "switch.valve"},
    )
    assert (stop.domain, stop.service) == ("switch", "turn_off")
    assert actuator.can_water is True
    assert actuator.can_stop is True


def test_service_actuator_injects_volume() -> None:
    actuator = ActuatorConfig(
        actuator_type=ACTUATOR_SERVICE,
        start_service="script.water_by_volume",
        start_data={"target": "bed"},
        volume_field="liters",
    )
    start = build_start_call(actuator, 7.5)
    assert start.domain == "script"
    assert start.service == "water_by_volume"
    assert start.data == {"target": "bed", "liters": 7.5}


def test_service_actuator_without_stop_has_no_stop_call() -> None:
    actuator = ActuatorConfig(
        actuator_type=ACTUATOR_SERVICE, start_service="foo.bar"
    )
    assert build_stop_call(actuator) is None
    assert actuator.can_stop is False
    assert actuator.can_water is True


def test_script_actuator_passes_volume_as_variable() -> None:
    actuator = ActuatorConfig(
        actuator_type=ACTUATOR_SCRIPT,
        start_script="script.start_water",
        stop_script="script.stop_water",
        volume_field="volume",
    )
    start = build_start_call(actuator, 9.0)
    assert start.domain == "script"
    assert start.service == "turn_on"
    assert start.data == {
        "entity_id": "script.start_water",
        "variables": {"volume": 9.0},
    }
    stop = build_stop_call(actuator)
    assert stop.data == {"entity_id": "script.stop_water"}


def test_none_actuator_has_no_calls() -> None:
    actuator = ActuatorConfig(actuator_type=ACTUATOR_NONE)
    assert build_start_call(actuator, 5.0) is None
    assert build_stop_call(actuator) is None
    assert actuator.can_water is False
    assert actuator.can_stop is False


def test_invalid_service_string_yields_no_call() -> None:
    actuator = ActuatorConfig(
        actuator_type=ACTUATOR_SERVICE, start_service="not_a_service"
    )
    assert build_start_call(actuator, 5.0) is None


def test_bound_volume_clamps_to_safety_limit() -> None:
    assert bound_volume(50.0, 30.0) == 30.0
    assert bound_volume(10.0, 30.0) == 10.0
    assert bound_volume(-5.0, 30.0) == 0.0


def test_linktap_start_publishes_volume_then_duration_then_switch() -> None:
    actuator = ActuatorConfig(
        actuator_type=ACTUATOR_LINKTAP,
        switch="switch.1f43b22f004b1200_3_water_switch",
        linktap_id="1F43B22F004B1200_3",
        linktap_failsafe=3600,
    )
    calls = build_start_calls(actuator, 12.0)
    assert len(calls) == 3

    vol_call, dur_call, switch_call = calls
    assert (vol_call.domain, vol_call.service) == ("mqtt", "publish")
    assert vol_call.data["topic"] == "/homeassistant/config_from_ha"
    assert json.loads(vol_call.data["payload"]) == {
        "tag": "volume_limit",
        "id": "1F43B22F004B1200_3",
        "value": 12.0,
    }
    assert json.loads(dur_call.data["payload"]) == {
        "id": "1F43B22F004B1200_3",
        "duration": 3600,
    }
    assert (switch_call.domain, switch_call.service, switch_call.data) == (
        "switch",
        "turn_on",
        {"entity_id": "switch.1f43b22f004b1200_3_water_switch"},
    )
    assert actuator.can_water is True
    assert actuator.can_stop is True


def test_linktap_stop_turns_switch_off() -> None:
    actuator = ActuatorConfig(
        actuator_type=ACTUATOR_LINKTAP,
        switch="switch.valve",
        linktap_id="ID1",
    )
    stop = build_stop_calls(actuator)
    assert len(stop) == 1
    assert (stop[0].domain, stop[0].service, stop[0].data) == (
        "switch",
        "turn_off",
        {"entity_id": "switch.valve"},
    )


def test_linktap_uses_custom_topic() -> None:
    actuator = ActuatorConfig(
        actuator_type=ACTUATOR_LINKTAP,
        switch="switch.valve",
        linktap_id="ID1",
        linktap_topic="custom/topic",
    )
    calls = build_start_calls(actuator, 5.0)
    assert all(c.data["topic"] == "custom/topic" for c in calls[:2])


def test_linktap_without_id_or_switch_has_no_calls() -> None:
    no_id = ActuatorConfig(actuator_type=ACTUATOR_LINKTAP, switch="switch.valve")
    no_switch = ActuatorConfig(actuator_type=ACTUATOR_LINKTAP, linktap_id="ID1")
    assert build_start_calls(no_id, 5.0) == []
    assert build_start_calls(no_switch, 5.0) == []
    assert no_id.can_water is False
    assert no_switch.can_water is False


def test_build_start_calls_wraps_single_modes() -> None:
    switch = ActuatorConfig(actuator_type=ACTUATOR_SWITCH, switch="switch.v")
    assert build_start_calls(switch, 5.0) == [build_start_call(switch, 5.0)]
    none = ActuatorConfig(actuator_type=ACTUATOR_NONE)
    assert build_start_calls(none, 5.0) == []
    assert build_stop_calls(none) == []
    assert build_stop_call(none) is None
