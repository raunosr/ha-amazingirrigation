"""Tests for history-backed water-balance bootstrapping."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation import history_ingest
from custom_components.amazing_irrigation.const import (
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_ZONES,
    DOMAIN,
    SERVICE_RELEARN_FROM_HISTORY,
)
from custom_components.amazing_irrigation.estimator import EstimatorObservation
from custom_components.amazing_irrigation.history_ingest import (
    BootstrapResult,
    IrrigationEvent,
    SeriesPoint,
    TimeSeries,
    assemble_observations,
    bootstrap_from_series,
    detect_irrigation_events,
)
from custom_components.amazing_irrigation.state import ZoneState
from custom_components.amazing_irrigation.waterbalance import (
    Climate,
    WaterBalanceParams,
    default_params,
    step,
)
from custom_components.amazing_irrigation.zone import ZoneConfig


def _t(hours: float) -> datetime:
    return datetime(2026, 6, 1, tzinfo=UTC) + timedelta(hours=hours)


def test_assemble_observations_attributes_inputs_to_intervals() -> None:
    """Intervals get correct dt, liters, rain deltas, and as-of climate."""
    moisture = TimeSeries([(_t(0), 40.0), (_t(1), 43.0), (_t(2), 41.5)])
    rain = TimeSeries([(_t(0), 0.0), (_t(1), 2.0), (_t(2), 1.0)])
    temp = TimeSeries([(_t(-1), 20.0), (_t(1), 22.0)])
    humidity = TimeSeries([(_t(-1), 60.0)])
    wind = TimeSeries([(_t(0), 1.2)])
    solar = TimeSeries([(_t(0), 250.0)])
    events = [IrrigationEvent(_t(0.5), liters=5.0)]

    observations = assemble_observations(
        moisture,
        rain_series=rain,
        temp_series=temp,
        humidity_series=humidity,
        wind_series=wind,
        solar_series=solar,
        irrigation_events=events,
        min_interval_hours=0.0,
    )

    assert len(observations) == 2
    first = observations[0]
    assert first.dt == pytest.approx(1.0)
    assert first.liters == pytest.approx(5.0)
    assert first.rain_mm == pytest.approx(2.0)
    assert first.climate == Climate(20.0, 60.0, wind_ms=1.2, solar=250.0)
    assert observations[1].liters == 0.0
    assert observations[1].rain_mm == 0.0
    assert observations[1].climate.air_temp_c == 22.0


def test_assemble_observations_coalesces_short_samples_and_skips_gaps() -> None:
    """Short noisy samples coalesce; long sensor dropouts are not bridged."""
    moisture = TimeSeries(
        [(_t(0), 40.0), (_t(0.05), 40.1), (_t(0.5), 39.8), (_t(30), 35.0)]
    )

    observations = assemble_observations(
        moisture,
        min_interval_hours=0.25,
        max_interval_hours=24.0,
    )

    assert len(observations) == 1
    assert observations[0].theta_start == 40.0
    assert observations[0].theta_end == 39.8
    assert observations[0].dt == pytest.approx(0.5)


def test_protected_rain_marks_observations_for_greenhouse_projection() -> None:
    """Rain remains reported but protected zones flag it as non-effective."""
    observations = assemble_observations(
        TimeSeries([(_t(0), 40.0), (_t(1), 42.0)]),
        rain_series=TimeSeries([(_t(0), 0.0), (_t(1), 8.0)]),
        protected_rain=True,
        min_interval_hours=0.0,
    )

    assert observations[0].rain_mm == pytest.approx(8.0)
    assert observations[0].protected_rain is True


def test_detect_irrigation_events_prefers_recorded_then_infers_unexplained_rises() -> None:
    """Recorded volumes win; otherwise only non-rain moisture steps infer water."""
    moisture = TimeSeries([(_t(0), 40.0), (_t(1), 44.0), (_t(2), 48.0)])
    rain = TimeSeries([(_t(0), 0.0), (_t(1), 0.0), (_t(2), 4.0)])
    recorded = [IrrigationEvent(_t(0.25), liters=3.5)]

    assert detect_irrigation_events(moisture, recorded_events=recorded) == recorded

    inferred = detect_irrigation_events(moisture, rain_series=rain, min_rise=3.0)

    assert inferred == [IrrigationEvent(_t(1), liters=None, inferred=True)]


def _synthetic_history() -> tuple[
    TimeSeries,
    TimeSeries,
    TimeSeries,
    TimeSeries,
    list[IrrigationEvent],
    WaterBalanceParams,
]:
    true = WaterBalanceParams(1.55, 1.05, 0.68, 0.10, 46.0, 16.0)
    moisture_points: list[SeriesPoint] = [SeriesPoint(_t(0), 47.0)]
    rain_points: list[SeriesPoint] = [SeriesPoint(_t(0), 0.0)]
    temp_points: list[SeriesPoint] = [SeriesPoint(_t(0), 24.0)]
    humidity_points: list[SeriesPoint] = [SeriesPoint(_t(0), 55.0)]
    events: list[IrrigationEvent] = []
    theta = 47.0
    rain_total = 0.0

    for index in range(180):
        start = _t(index)
        end = _t(index + 1)
        liters = 0.0 if index % 4 == 0 else 0.25 + (index % 5) * 0.12
        rain_mm = 0.0 if index % 5 in (0, 1) else 0.15 + (index % 4) * 0.10
        climate = Climate(
            air_temp_c=18.0 + index % 12,
            air_humidity_pct=45.0 + index % 30,
            wind_ms=0.4 + (index % 4) * 0.3,
            solar=80.0 + (index % 7) * 70.0,
        )
        theta = step(
            true,
            theta,
            liters=liters,
            rain_mm=rain_mm,
            climate=climate,
            dt=1.0,
        ).theta_next
        moisture_points.append(SeriesPoint(end, theta))
        rain_total += rain_mm
        rain_points.append(SeriesPoint(end, rain_total))
        temp_points.append(SeriesPoint(start, climate.air_temp_c))
        humidity_points.append(SeriesPoint(start, climate.air_humidity_pct))
        if liters > 0.0:
            events.append(IrrigationEvent(start + timedelta(minutes=30), liters=liters))

    return (
        TimeSeries(moisture_points),
        TimeSeries(rain_points),
        TimeSeries(temp_points),
        TimeSeries(humidity_points),
        events,
        true,
    )


def test_bootstrap_from_synthetic_history_recovers_parameters_in_ballpark() -> None:
    """Assembled history can initialise the joint estimator quickly."""
    moisture, rain, temp, humidity, events, true = _synthetic_history()
    observations = assemble_observations(
        moisture,
        rain_series=rain,
        temp_series=temp,
        humidity_series=humidity,
        irrigation_events=events,
        min_interval_hours=0.0,
    )

    result = bootstrap_from_series(
        default_params("loam"),
        observations,
        overrides={"field_capacity": true.field_capacity, "wilting_point": true.wilting_point},
    )

    assert result.success is True
    assert result.intervals_used == len(observations)
    assert result.days_span == pytest.approx(180 / 24)
    assert "Learned from" in result.summary
    assert result.params.eta_irr == pytest.approx(true.eta_irr, abs=0.25)
    assert result.params.eta_rain == pytest.approx(true.eta_rain, abs=0.25)
    assert result.params.k_et == pytest.approx(true.k_et, abs=0.16)
    assert result.params.drain_rate == pytest.approx(true.drain_rate, abs=0.08)


def test_bootstrap_reports_insufficient_history_without_fitting() -> None:
    """Too few intervals produce a clear non-success result for callers."""
    result = bootstrap_from_series(
        default_params("loam"),
        [EstimatorObservation(40.0, 39.5, 1.0)],
        min_intervals=3,
    )

    assert result.success is False
    assert result.reason == "insufficient_history"
    assert result.intervals_used == 1
    assert "Insufficient history" in result.summary


class _FakeStore:
    def __init__(self, state: ZoneState) -> None:
        self.state = state
        self.saved = False

    def get(self, zone_id: str) -> ZoneState | None:
        return self.state if self.state.zone_id == zone_id else None

    async def async_save(self) -> None:
        self.saved = True


async def test_async_bootstrap_zone_returns_none_when_history_unavailable(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recorder failures degrade gracefully and do not write state."""
    async def _raise(*args) -> dict[str, TimeSeries]:
        raise RuntimeError("recorder unavailable")

    monkeypatch.setattr(history_ingest, "_async_fetch_zone_history", _raise)
    store = _FakeStore(ZoneState("zone1"))
    zone = ZoneConfig("zone1", "Zone 1", moisture_sensors=["sensor.moisture"])

    result = await history_ingest.async_bootstrap_zone(hass, zone, store)

    assert result is None
    assert store.saved is False


async def test_async_bootstrap_zone_writes_successful_model(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The HA glue persists params, confidence, covariance, and days used."""
    moisture, rain, temp, humidity, events, true = _synthetic_history()

    async def _history(*args) -> dict[str, TimeSeries]:
        return {
            "sensor.moisture": moisture,
            "sensor.rain": rain,
            "sensor.temp": temp,
            "sensor.humidity": humidity,
        }

    def _events(*args, **kwargs) -> list[IrrigationEvent]:
        return events

    monkeypatch.setattr(history_ingest, "_async_fetch_zone_history", _history)
    monkeypatch.setattr(history_ingest, "detect_irrigation_events", _events)
    state = ZoneState("zone1", learning_enabled=True)
    store = _FakeStore(state)
    zone = ZoneConfig(
        "zone1",
        "Zone 1",
        moisture_sensors=["sensor.moisture"],
        observed_rain_amount="sensor.rain",
        observed_air_temperature="sensor.temp",
        observed_air_humidity="sensor.humidity",
        field_capacity=true.field_capacity,
        wilting_point=true.wilting_point,
    )

    result = await history_ingest.async_bootstrap_zone(hass, zone, store)

    assert isinstance(result, BootstrapResult)
    assert result.success is True
    assert store.saved is True
    assert state.model_params is not None
    assert state.model_covariance is not None
    assert state.model_confidence is not None
    assert state.bootstrapped_days == pytest.approx(result.days_span)


async def test_relearn_service_targets_zone_device(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The history service resolves zone devices and returns bootstrap evidence."""
    from custom_components.amazing_irrigation import services

    async def _bootstrap(*args, **kwargs) -> BootstrapResult:
        return BootstrapResult(
            params=default_params("loam"),
            confidence={},
            covariance=[],
            intervals_used=7,
            days_span=2.25,
            summary="Learned from 7 intervals over 2.2 days",
        )

    monkeypatch.setattr(services, "async_bootstrap_zone", _bootstrap)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_ZONES: {
                "zone1": {
                    CONF_NAME: "Herb Bed",
                    CONF_MOISTURE_SENSORS: ["sensor.moisture"],
                }
            }
        },
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, f"{entry.entry_id}_zone1")}
    )
    assert device is not None

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_RELEARN_FROM_HISTORY,
        {"device_id": device.id},
        blocking=True,
        return_response=True,
    )

    assert response["results"] == [
        {
            "zone_id": "zone1",
            "intervals_used": 7,
            "days_span": 2.25,
            "summary": "Learned from 7 intervals over 2.2 days",
        }
    ]


async def test_relearn_button_calls_history_bootstrap(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each zone exposes a Re-learn from History button."""
    from custom_components.amazing_irrigation import button

    calls: list[str] = []

    async def _bootstrap(hass, zone, store) -> None:
        calls.append(zone.zone_id)

    monkeypatch.setattr(button, "async_bootstrap_zone", _bootstrap)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_ZONES: {
                "zone1": {
                    CONF_NAME: "Herb Bed",
                    CONF_MOISTURE_SENSORS: ["sensor.moisture"],
                }
            }
        },
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.herb_bed_re_learn_from_history"},
        blocking=True,
    )

    assert calls == ["zone1"]
