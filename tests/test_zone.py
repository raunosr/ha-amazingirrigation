"""Pure tests for Zone Moisture aggregation and the ZoneConfig model."""

from __future__ import annotations

from custom_components.amazing_irrigation.const import (
    CONF_FORECAST_AIR_HUMIDITY,
    CONF_FORECAST_AIR_TEMPERATURE,
    CONF_OBSERVED_AIR_HUMIDITY,
    CONF_OBSERVED_AIR_TEMPERATURE,
    CONF_SOLAR_RADIATION,
    CONF_WEATHER_FORECAST_ENTITY,
    CONF_WIND_SPEED,
)
from custom_components.amazing_irrigation.zone import (
    ZoneConfig,
    aggregate_zone_moisture,
    is_in_season,
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
            CONF_WEATHER_FORECAST_ENTITY: "weather.home",
            "safety_blockers": ["binary_sensor.lock"],
            CONF_OBSERVED_AIR_TEMPERATURE: "sensor.air_temp",
            CONF_OBSERVED_AIR_HUMIDITY: "sensor.air_humidity",
            CONF_FORECAST_AIR_TEMPERATURE: "sensor.forecast_temp",
            CONF_FORECAST_AIR_HUMIDITY: "sensor.forecast_humidity",
            CONF_WIND_SPEED: "sensor.wind_speed",
            CONF_SOLAR_RADIATION: "sensor.solar_radiation",
        },
    )
    assert zone.zone_id == "abc123"
    assert zone.name == "Herb Bed"
    assert zone.moisture_sensors == ["sensor.a", "sensor.b"]
    assert zone.forecast_rain_amount == "sensor.rain_mm"
    assert zone.forecast_rain_probability is None
    assert zone.weather_forecast_entity == "weather.home"
    assert zone.observed_rain_amount is None
    assert zone.safety_blockers == ["binary_sensor.lock"]
    assert zone.observed_air_temperature == "sensor.air_temp"
    assert zone.observed_air_humidity == "sensor.air_humidity"
    assert zone.forecast_air_temperature == "sensor.forecast_temp"
    assert zone.forecast_air_humidity == "sensor.forecast_humidity"
    assert zone.wind_speed == "sensor.wind_speed"
    assert zone.solar_radiation == "sensor.solar_radiation"
    assert zone.history_days == 60


def test_zone_config_history_days_parsing() -> None:
    """History window parses bounded ints and falls back to the default."""
    assert ZoneConfig.from_record("z", {"history_days": "90"}).history_days == 90
    assert ZoneConfig.from_record("z", {"history_days": 1000}).history_days == 365
    assert ZoneConfig.from_record("z", {"history_days": "bad"}).history_days == 60
    assert ZoneConfig.from_record("z", {}).history_days == 60


def test_no_season_means_always_in_season() -> None:
    assert is_in_season(None, None, 1, 15) is True
    assert is_in_season("04-01", None, 7, 1) is True


def test_simple_season_window() -> None:
    assert is_in_season("04-01", "09-30", 6, 15) is True
    assert is_in_season("04-01", "09-30", 3, 31) is False
    assert is_in_season("04-01", "09-30", 4, 1) is True
    assert is_in_season("04-01", "09-30", 9, 30) is True


def test_wrap_around_season_window() -> None:
    # Nov 1 .. Feb 28 wraps the year end.
    assert is_in_season("11-01", "02-28", 12, 25) is True
    assert is_in_season("11-01", "02-28", 1, 15) is True
    assert is_in_season("11-01", "02-28", 7, 1) is False


def test_invalid_season_is_treated_as_always_in_season() -> None:
    assert is_in_season("garbage", "09-30", 6, 1) is True
