"""Tests for resolving a LinkTap device into a zone's entities."""

from __future__ import annotations

from custom_components.amazing_irrigation.linktap import resolve_linktap_device


def _linktap_entities(prefix: str) -> list[str]:
    return [
        f"switch.{prefix}_water_switch",
        f"binary_sensor.{prefix}_is_watering",
        f"binary_sensor.{prefix}_is_manual_mode",
        f"sensor.{prefix}_volume",
        f"sensor.{prefix}_volume_limit",
        f"sensor.{prefix}_battery",
        f"sensor.{prefix}_failsafe_duration",
    ]


def test_resolves_id_switch_and_sensors_from_device() -> None:
    """A LinkTap device yields its id, switch, watering and volume sensors."""
    identifiers = [("mqtt", "1F43B22F004B1200_4")]
    entity_ids = _linktap_entities("1f43b22f004b1200_4")

    resolution = resolve_linktap_device(identifiers, entity_ids)

    # Exact-case id comes from the device identifier, not the lowercased entity.
    assert resolution.linktap_id == "1F43B22F004B1200_4"
    assert resolution.switch == "switch.1f43b22f004b1200_4_water_switch"
    assert resolution.watering_sensor == "binary_sensor.1f43b22f004b1200_4_is_watering"
    # ``_volume`` is selected, never ``_volume_limit``.
    assert resolution.volume_sensor == "sensor.1f43b22f004b1200_4_volume"


def test_prefers_identifier_matching_the_switch_prefix() -> None:
    """With multiple identifiers, the one matching the switch prefix wins."""
    identifiers = [("mqtt", "GATEWAY123"), ("mqtt", "1F43B22F004B1200_4")]
    entity_ids = _linktap_entities("1f43b22f004b1200_4")

    resolution = resolve_linktap_device(identifiers, entity_ids)

    assert resolution.linktap_id == "1F43B22F004B1200_4"


def test_falls_back_to_prefix_when_no_identifier() -> None:
    """Without identifiers the id falls back to the switch object-id prefix."""
    resolution = resolve_linktap_device([], _linktap_entities("abc_1"))

    assert resolution.linktap_id == "abc_1"
    assert resolution.switch == "switch.abc_1_water_switch"


def test_missing_entities_resolve_to_none() -> None:
    """A device without LinkTap entities resolves switch/sensors to None."""
    resolution = resolve_linktap_device(
        [("mqtt", "ID1")], ["sensor.something_unrelated"]
    )

    assert resolution.switch is None
    assert resolution.watering_sensor is None
    assert resolution.volume_sensor is None
    assert resolution.linktap_id == "ID1"
