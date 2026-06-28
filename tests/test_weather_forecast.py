"""Tests for weather forecast parsing, horizons and provider cache."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse

from custom_components.amazing_irrigation.const import DATA_WEATHER_FORECAST, DOMAIN
from custom_components.amazing_irrigation.weather_forecast import (
    ForecastPoint,
    WeatherForecastProvider,
    horizon_from_forecast,
    near_term_rain,
    parse_forecast_items,
)


def _point(
    hour: int,
    *,
    temp: float = 20.0,
    humidity: float = 60.0,
    wind: float = 2.0,
    rain: float = 0.0,
    probability: float | None = 80.0,
) -> ForecastPoint:
    return ForecastPoint(
        datetime(2026, 6, 28, hour, tzinfo=UTC),
        temp,
        humidity,
        wind,
        rain,
        probability,
    )


def test_parse_forecast_items_normalises_units_and_datetimes() -> None:
    """Home Assistant weather forecast items are normalized to engine units."""
    points = parse_forecast_items(
        [
            {
                "datetime": "2026-06-28T03:00:00+03:00",
                "temperature": 68,
                "humidity": 55,
                "wind_speed": 36,
                "precipitation": 0.1,
                "precipitation_probability": 75,
            },
            {"datetime": "garbage", "temperature": 10},
        ],
        temperature_unit="°F",
        wind_speed_unit="km/h",
        precipitation_unit="in",
    )

    assert len(points) == 1
    assert points[0].start == datetime(2026, 6, 28, 0, 0, tzinfo=UTC)
    assert points[0].air_temp_c == pytest.approx(20.0)
    assert points[0].air_humidity_pct == 55
    assert points[0].wind_ms == pytest.approx(10.0)
    assert points[0].precipitation_mm == pytest.approx(2.54)
    assert points[0].precipitation_probability == 75


@pytest.mark.parametrize(
    ("unit", "value", "expected"),
    [("mph", 10.0, 4.4704), ("ft/s", 10.0, 3.048), ("m/s", 10.0, 10.0)],
)
def test_parse_forecast_items_converts_wind_units(
    unit: str, value: float, expected: float
) -> None:
    points = parse_forecast_items(
        [{"datetime": "2026-06-28T00:00:00Z", "wind_speed": value}],
        wind_speed_unit=unit,
    )

    assert points[0].wind_ms == pytest.approx(expected)


def test_parse_forecast_items_missing_fields_become_none() -> None:
    """Missing and unparseable scalar fields do not raise."""
    points = parse_forecast_items(
        [
            {
                "datetime": "2026-06-28T00:00:00Z",
                "temperature": "bad",
                "wind_speed": None,
            }
        ]
    )

    assert points == [
        ForecastPoint(
            datetime(2026, 6, 28, 0, tzinfo=UTC),
            None,
            None,
            None,
            None,
            None,
        )
    ]


def test_horizon_from_forecast_samples_varying_climate_and_gates_rain() -> None:
    """Each horizon step uses the relevant forecast point, not a constant climate."""
    intervals = horizon_from_forecast(
        [
            _point(0, temp=20, humidity=60, wind=2, rain=1, probability=90),
            _point(1, temp=21, humidity=61, wind=3, rain=2, probability=30),
            _point(2, temp=22, humidity=62, wind=4, rain=3, probability=80),
        ],
        start=datetime(2026, 6, 28, 0, tzinfo=UTC),
        total_hours=2.5,
        step_hours=1,
        protected_rain=False,
        rain_skip_probability=60,
        solar=500,
    )

    assert [interval.dt for interval in intervals] == [1, 1, 0.5]
    assert [interval.climate.air_temp_c for interval in intervals] == [20, 21, 22]
    assert [interval.climate.air_humidity_pct for interval in intervals] == [60, 61, 62]
    assert [interval.climate.wind_ms for interval in intervals] == [2, 3, 4]
    assert intervals[0].climate.solar == 500
    assert [interval.rain_mm for interval in intervals] == [1, 0, 1.5]


def test_horizon_from_forecast_protected_or_empty_has_no_rain() -> None:
    assert horizon_from_forecast(
        [],
        start=datetime(2026, 6, 28, 0, tzinfo=UTC),
        total_hours=1,
        step_hours=1,
        protected_rain=False,
        rain_skip_probability=60,
    ) == []

    intervals = horizon_from_forecast(
        [_point(0, rain=5)],
        start=datetime(2026, 6, 28, 0, tzinfo=UTC),
        total_hours=1,
        step_hours=1,
        protected_rain=True,
        rain_skip_probability=60,
    )
    assert intervals[0].rain_mm == 0
    assert intervals[0].protected_rain is True


def test_near_term_rain_sums_probability_gated_overlap_and_max_probability() -> None:
    rain, probability = near_term_rain(
        [
            _point(0, rain=2, probability=90),
            _point(1, rain=4, probability=30),
            _point(2, rain=6, probability=80),
        ],
        start=datetime(2026, 6, 28, 0, 30, tzinfo=UTC),
        hours=2,
        protected_rain=False,
        rain_skip_probability=60,
    )

    assert rain == pytest.approx(1 + 3)
    assert probability == 90


def test_near_term_rain_protected_zeroes_rain() -> None:
    rain, probability = near_term_rain(
        [_point(0, rain=5, probability=90)],
        start=datetime(2026, 6, 28, 0, tzinfo=UTC),
        hours=1,
        protected_rain=True,
        rain_skip_probability=60,
    )

    assert rain == 0
    assert probability is None


async def test_provider_populates_domain_cache(hass: HomeAssistant) -> None:
    """WeatherForecastProvider writes parsed get_forecasts data into hass.data."""
    hass.data[DOMAIN] = {DATA_WEATHER_FORECAST: {}}
    hass.states.async_set(
        "weather.home",
        "cloudy",
        {
            "temperature_unit": "°F",
            "wind_speed_unit": "mph",
            "precipitation_unit": "in",
        },
    )

    def fake_get_forecasts(
        call: ServiceCall,
    ) -> dict[str, Any]:
        assert call.data == {"entity_id": "weather.home", "type": "hourly"}
        return {
            "weather.home": {
                "forecast": [
                    {
                        "datetime": "2026-06-28T00:00:00Z",
                        "temperature": 68,
                        "humidity": 50,
                        "wind_speed": 10,
                        "precipitation": 0.2,
                        "precipitation_probability": 70,
                    }
                ]
            }
        }

    hass.services.async_register(
        "weather",
        "get_forecasts",
        fake_get_forecasts,
        supports_response=SupportsResponse.ONLY,
    )

    provider = WeatherForecastProvider(hass, ["weather.home"])
    await provider.async_refresh()

    points = hass.data[DOMAIN][DATA_WEATHER_FORECAST]["weather.home"]
    assert points[0].air_temp_c == pytest.approx(20.0)
    assert points[0].wind_ms == pytest.approx(4.4704)
    assert points[0].precipitation_mm == pytest.approx(5.08)


async def test_provider_missing_service_is_noop(hass: HomeAssistant) -> None:
    """Missing/raising weather services do not break the integration."""
    hass.data[DOMAIN] = {DATA_WEATHER_FORECAST: {}}
    hass.states.async_set("weather.home", "cloudy")
    provider = WeatherForecastProvider(hass, ["weather.home"])

    await provider.async_refresh()
    assert hass.data[DOMAIN][DATA_WEATHER_FORECAST] == {}


async def test_provider_failing_service_is_noop(hass: HomeAssistant) -> None:
    """A failing weather entity fetch does not populate cache or raise."""
    hass.data[DOMAIN] = {DATA_WEATHER_FORECAST: {}}
    hass.states.async_set("weather.home", "cloudy")

    def fail_call(_call: ServiceCall) -> None:
        raise RuntimeError("boom")

    hass.services.async_register(
        "weather",
        "get_forecasts",
        fail_call,
        supports_response=SupportsResponse.ONLY,
    )

    provider = WeatherForecastProvider(hass, ["weather.home"])
    await provider.async_refresh()
    assert hass.data[DOMAIN][DATA_WEATHER_FORECAST] == {}
