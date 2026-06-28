"""Cached Home Assistant weather forecasts for predictive irrigation."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .const import (
    DATA_WEATHER_FORECAST,
    DOMAIN,
    WEATHER_FORECAST_REFRESH_INTERVAL,
)
from .controller import ForecastInterval
from .waterbalance import Climate

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
_INVALID_STATES = ("unknown", "unavailable", "", None)
_WEATHER_DOMAIN = "weather"
_GET_FORECASTS_SERVICE = "get_forecasts"


@dataclass(frozen=True)
class ForecastPoint:
    """One normalized weather forecast point."""

    start: datetime
    air_temp_c: float | None
    air_humidity_pct: float | None
    wind_ms: float | None
    precipitation_mm: float | None
    precipitation_probability: float | None


def parse_forecast_items(
    items: Iterable[dict[str, Any]],
    *,
    temperature_unit: str = "°C",
    wind_speed_unit: str = "m/s",
    precipitation_unit: str = "mm",
) -> list[ForecastPoint]:
    """Normalize Home Assistant weather forecast dictionaries."""
    points: list[ForecastPoint] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        start = _parse_datetime(item.get("datetime"))
        if start is None:
            continue
        points.append(
            ForecastPoint(
                start=start,
                air_temp_c=_convert_temperature(
                    _finite(item.get("temperature")), temperature_unit
                ),
                air_humidity_pct=_finite(item.get("humidity")),
                wind_ms=_convert_wind(_finite(item.get("wind_speed")), wind_speed_unit),
                precipitation_mm=_convert_precipitation(
                    _finite(item.get("precipitation")), precipitation_unit
                ),
                precipitation_probability=_finite(
                    item.get("precipitation_probability")
                ),
            )
        )
    return sorted(points, key=lambda point: point.start)


def horizon_from_forecast(
    points: list[ForecastPoint],
    *,
    start: datetime,
    total_hours: float,
    step_hours: float,
    protected_rain: bool,
    rain_skip_probability: float,
    solar: float | None = None,
) -> list[ForecastInterval]:
    """Build forecast intervals from a real weather forecast time series."""
    if not points:
        return []
    points = sorted(points, key=lambda point: point.start)
    start = _to_utc(start)
    intervals: list[ForecastInterval] = []
    remaining = max(0.0, float(total_hours))
    step = max(1.0e-6, float(step_hours))
    elapsed = 0.0
    while remaining > 1.0e-6:
        dt = min(step, remaining)
        step_start = start.timestamp() + elapsed * 3600.0
        point = _point_for_start(points, datetime.fromtimestamp(step_start, UTC))
        intervals.append(
            ForecastInterval(
                dt=dt,
                rain_mm=_rain_for_point(
                    point, dt, protected_rain, rain_skip_probability
                ),
                climate=Climate(
                    point.air_temp_c,
                    point.air_humidity_pct,
                    point.wind_ms,
                    solar=solar,
                ),
                protected_rain=protected_rain,
            )
        )
        remaining -= dt
        elapsed += dt
    return intervals


def near_term_rain(
    points: list[ForecastPoint],
    *,
    start: datetime,
    hours: float,
    protected_rain: bool,
    rain_skip_probability: float,
) -> tuple[float, float | None]:
    """Return expected rain and max probability over a near-term window."""
    if protected_rain or not points or hours <= 0:
        return (0.0, None)
    points = sorted(points, key=lambda point: point.start)
    start = _to_utc(start)
    window_start = start.timestamp()
    window_end = window_start + (hours * 3600.0)
    rain = 0.0
    probabilities: list[float] = []
    for index, point in enumerate(points):
        point_start = point.start.timestamp()
        next_start = (
            points[index + 1].start.timestamp()
            if index + 1 < len(points)
            else point_start + 3600.0
        )
        if next_start <= point_start:
            next_start = point_start + 3600.0
        overlap = max(0.0, min(next_start, window_end) - max(point_start, window_start))
        if overlap <= 0:
            continue
        probability = point.precipitation_probability
        if probability is not None:
            probabilities.append(probability)
        if probability is not None and probability < rain_skip_probability:
            continue
        rain += max(0.0, point.precipitation_mm or 0.0) * (overlap / 3600.0)
    return (rain, max(probabilities) if probabilities else None)


class WeatherForecastProvider:
    """Refresh and cache weather.get_forecasts data for configured zones."""

    def __init__(self, hass: HomeAssistant, weather_entities: Iterable[str]) -> None:
        """Initialise the provider for distinct weather entities."""
        self.hass = hass
        self.weather_entities = tuple(sorted(set(weather_entities)))
        self._unsub: Callable[[], None] | None = None

    async def async_start(self) -> None:
        """Fetch immediately and schedule periodic refresh."""
        if not self.weather_entities:
            return
        await self.async_refresh()
        if self._unsub is None:
            from homeassistant.helpers.event import async_track_time_interval

            self._unsub = async_track_time_interval(
                self.hass,
                self._async_refresh_from_timer,
                WEATHER_FORECAST_REFRESH_INTERVAL,
            )

    def async_stop(self) -> None:
        """Cancel periodic refresh."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    async def _async_refresh_from_timer(self, _now: datetime) -> None:
        """Refresh callback used by Home Assistant's time tracker."""
        await self.async_refresh()

    async def async_refresh(self) -> None:
        """Best-effort refresh of every configured weather entity."""
        cache = self.hass.data.setdefault(DOMAIN, {}).setdefault(
            DATA_WEATHER_FORECAST, {}
        )
        if not self.hass.services.has_service(
            _WEATHER_DOMAIN, _GET_FORECASTS_SERVICE
        ):
            _LOGGER.debug("weather.get_forecasts service is not available")
            for entity_id in self.weather_entities:
                cache.pop(entity_id, None)
            return
        for entity_id in self.weather_entities:
            points = await self._async_fetch_entity(entity_id)
            if points:
                cache[entity_id] = points
            else:
                cache.pop(entity_id, None)

    async def _async_fetch_entity(self, entity_id: str) -> list[ForecastPoint]:
        """Fetch hourly forecasts for one entity, falling back to daily."""
        state = self.hass.states.get(entity_id)
        if state is None or state.state in _INVALID_STATES:
            _LOGGER.debug("Weather entity %s is unavailable", entity_id)
            return []
        for forecast_type in ("hourly", "daily"):
            try:
                response = await self.hass.services.async_call(
                    _WEATHER_DOMAIN,
                    _GET_FORECASTS_SERVICE,
                    {"entity_id": entity_id, "type": forecast_type},
                    blocking=True,
                    return_response=True,
                )
            except Exception as err:  # noqa: BLE001 - one entity must not break setup
                _LOGGER.debug(
                    "Could not fetch %s forecast for %s: %s",
                    forecast_type,
                    entity_id,
                    err,
                )
                continue
            items = _items_from_response(response, entity_id)
            if not items:
                continue
            return parse_forecast_items(
                items,
                temperature_unit=state.attributes.get("temperature_unit", "°C"),
                wind_speed_unit=state.attributes.get("wind_speed_unit", "m/s"),
                precipitation_unit=state.attributes.get("precipitation_unit", "mm"),
            )
        return []


def build_weather_provider(
    hass: HomeAssistant, zones: dict[str, dict[str, Any]]
) -> WeatherForecastProvider:
    """Create a weather forecast provider for all zones in an entry."""
    from .zone import ZoneConfig

    entities = []
    for zone_id, record in zones.items():
        zone = ZoneConfig.from_record(zone_id, record)
        if zone.weather_forecast_entity:
            entities.append(zone.weather_forecast_entity)
    return WeatherForecastProvider(hass, entities)


def _finite(value: object) -> float | None:
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _unit(value: str) -> str:
    return value.strip().lower().replace("°", "")


def _convert_temperature(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    return (value - 32.0) * (5.0 / 9.0) if _unit(unit) in {"f", "fahrenheit"} else value


def _convert_wind(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    normalized = _unit(unit)
    if normalized in {"km/h", "kph", "kmh"}:
        return value / 3.6
    if normalized in {"mph", "mi/h"}:
        return value * 0.44704
    if normalized in {"ft/s", "fps", "ftsec"}:
        return value * 0.3048
    return value


def _convert_precipitation(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    return value * 25.4 if _unit(unit) in {"in", "inch", "inches"} else value


def _point_for_start(points: list[ForecastPoint], step_start: datetime) -> ForecastPoint:
    latest = None
    for point in points:
        if point.start <= step_start:
            latest = point
        else:
            break
    if latest is not None:
        return latest
    return min(points, key=lambda point: abs(point.start - step_start))


def _rain_for_point(
    point: ForecastPoint,
    dt: float,
    protected_rain: bool,
    rain_skip_probability: float,
) -> float:
    if protected_rain:
        return 0.0
    probability = point.precipitation_probability
    if probability is not None and probability < rain_skip_probability:
        return 0.0
    return max(0.0, point.precipitation_mm or 0.0) * dt


def _items_from_response(response: Any, entity_id: str) -> list[dict[str, Any]]:
    if not isinstance(response, dict):
        return []
    entity_response = response.get(entity_id)
    if not isinstance(entity_response, dict):
        return []
    forecast = entity_response.get("forecast")
    return forecast if isinstance(forecast, list) else []
