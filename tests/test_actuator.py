"""Pure tests for actuator call-spec generation and volume bounding."""

from __future__ import annotations

from custom_components.amazing_irrigation.actuator import (
    ActuatorConfig,
    build_start_call,
    build_stop_call,
)
from custom_components.amazing_irrigation.const import (
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
