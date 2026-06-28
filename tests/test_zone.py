"""Pure tests for Zone Moisture aggregation and the ZoneConfig model."""

from __future__ import annotations

from custom_components.amazing_irrigation.zone import (
    ZoneConfig,
    aggregate_zone_moisture,
)


def test_aggregate_uses_minimum_valid_reading() -> None:
    """The driest valid sensor governs Zone Moisture."""
    result = aggregate_zone_moisture([42.0, 30.5, 55.0])
    assert result.value == 30.5
    assert result.used == 3
    assert result.configured == 3
    assert result.degraded is False
    assert result.available is True


def test_aggregate_ignores_invalid_readings_and_flags_degraded() -> None:
    """Missing readings are dropped and the result is marked degraded."""
    result = aggregate_zone_moisture([None, 40.0, None])
    assert result.value == 40.0
    assert result.used == 1
    assert result.configured == 3
    assert result.degraded is True
    assert result.available is True


def test_aggregate_unavailable_when_no_valid_readings() -> None:
    """Fail closed when no valid reading exists."""
    result = aggregate_zone_moisture([None, None])
    assert result.value is None
    assert result.available is False
    assert result.degraded is True


def test_aggregate_empty_is_unavailable_not_degraded() -> None:
    """A zone with no sensors has no value and is not 'degraded'."""
    result = aggregate_zone_moisture([])
    assert result.value is None
    assert result.available is False
    assert result.degraded is False


def test_zone_config_from_record_normalises_optionals() -> None:
    """Stored records map cleanly into a ZoneConfig."""
    zone = ZoneConfig.from_record(
        "abc123",
        {
            "name": "Herb Bed",
            "moisture_sensors": ["sensor.a", "sensor.b"],
            "forecast_rain_amount": "sensor.rain_mm",
            "safety_blockers": ["binary_sensor.lock"],
        },
    )
    assert zone.zone_id == "abc123"
    assert zone.name == "Herb Bed"
    assert zone.moisture_sensors == ["sensor.a", "sensor.b"]
    assert zone.forecast_rain_amount == "sensor.rain_mm"
    assert zone.forecast_rain_probability is None
    assert zone.observed_rain_amount is None
    assert zone.safety_blockers == ["binary_sensor.lock"]
