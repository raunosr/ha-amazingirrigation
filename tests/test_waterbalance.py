"""Tests for the pure soil water-balance physics."""

from __future__ import annotations

import pytest

from custom_components.amazing_irrigation.waterbalance import (
    DRAIN_RATE_MAX,
    DRAIN_RATE_MIN,
    ETA_IRR_MAX,
    ETA_IRR_MIN,
    ETA_RAIN_MAX,
    ETA_RAIN_MIN,
    FIELD_CAPACITY_MAX,
    FIELD_CAPACITY_MIN,
    K_ET_MAX,
    K_ET_MIN,
    WILTING_POINT_MAX,
    WILTING_POINT_MIN,
    BalanceInterval,
    Climate,
    WaterBalanceParams,
    default_params,
    et_demand,
    simulate,
    step,
)


def test_irrigation_only_step_raises_theta_and_reports_term():
    """Applied litres raise moisture by eta_irr and are explained."""
    params = WaterBalanceParams(2.0, 1.0, 0.5, 0.1, 60.0, 20.0)

    result = step(params, 30.0, liters=5.0, dt=0.0)

    assert result.theta_next == 40.0
    assert result.terms == {
        "irrigation": 10.0,
        "rain": 0.0,
        "et": 0.0,
        "drainage": 0.0,
    }


def test_rain_step_respects_protected_rain():
    """Rain contributes moisture unless the zone is rain-protected."""
    params = WaterBalanceParams(1.0, 1.5, 0.5, 0.1, 60.0, 20.0)

    exposed = step(params, 30.0, rain_mm=4.0, dt=0.0)
    protected = step(params, 30.0, rain_mm=4.0, dt=0.0, protected_rain=True)

    assert exposed.theta_next == 36.0
    assert exposed.terms["rain"] == 6.0
    assert protected.theta_next == 30.0
    assert protected.terms["rain"] == 0.0


def test_et_reduces_theta_and_tracks_hot_dry_weather():
    """ET grows with heat, shrinks with humidity, and still works with no climate."""
    params = default_params("loam")
    cool_wet = Climate(air_temp_c=15.0, air_humidity_pct=85.0)
    hot_wet = Climate(air_temp_c=30.0, air_humidity_pct=85.0)
    hot_dry = Climate(air_temp_c=30.0, air_humidity_pct=30.0)

    cool_loss = et_demand(params, cool_wet, 1.0)
    hot_wet_loss = et_demand(params, hot_wet, 1.0)
    hot_dry_loss = et_demand(params, hot_dry, 1.0)
    missing_loss = et_demand(params, None, 2.0)
    result = step(params, 50.0, climate=hot_dry, dt=1.0)

    assert hot_wet_loss > cool_loss
    assert hot_dry_loss > hot_wet_loss
    assert missing_loss > 0.0
    assert result.terms["et"] == hot_dry_loss
    assert result.theta_next < 50.0


def test_drainage_only_acts_above_field_capacity():
    """Drainage pulls excess moisture toward field capacity, never below it."""
    params = WaterBalanceParams(1.0, 1.0, 0.5, 0.2, 50.0, 20.0)

    wet = step(params, 70.0, dt=1.0)
    dry = step(params, 40.0, dt=1.0)
    long_interval = step(params, 70.0, dt=10.0)

    assert wet.terms["drainage"] == 4.0
    assert dry.terms["drainage"] == 0.0
    assert long_interval.terms["drainage"] == 20.0


def test_simulate_returns_explained_clamped_trajectory():
    """Simulation returns one result per interval with complete term breakdowns."""
    params = default_params("sand")
    intervals = [
        BalanceInterval(dt=0.0, liters=100.0),
        {"dt": 1.0, "climate": Climate(25.0, 50.0)},
        BalanceInterval(dt=1.0, rain_mm=100.0, protected_rain=True),
    ]

    results = simulate(params, 95.0, intervals)

    assert len(results) == 3
    assert all(0.0 <= result.theta_next <= 100.0 for result in results)
    for result in results:
        assert set(result.terms) == {"irrigation", "rain", "et", "drainage"}
    assert results[0].theta_next == 100.0


def test_area_eta_couples_rain_and_irrigation():
    from custom_components.amazing_irrigation.waterbalance import area_eta

    eta_irr, eta_rain = area_eta(2.0, 300.0, efficiency=0.8)
    assert eta_rain == pytest.approx(0.8 * 100.0 / 300.0, rel=1e-3)
    assert eta_rain / eta_irr == pytest.approx(2.0, rel=1e-3)


def test_default_params_seeds_from_geometry():
    seeded = default_params("loam", area_m2=2.0, root_depth_mm=300.0, demand_profile="high")
    assert seeded.root_depth_mm == 300.0
    assert seeded.crop_coefficient == pytest.approx(1.1)
    assert seeded.eta_rain / seeded.eta_irr == pytest.approx(2.0, rel=1e-2)

    legacy = default_params("loam")
    assert legacy.root_depth_mm is None
    assert legacy.eta_irr == pytest.approx(1.2)


def test_fao56_et_only_when_root_depth_set():
    climate = Climate(28.0, 40.0)
    legacy = default_params("loam")
    fao = default_params("loam", area_m2=2.0, root_depth_mm=300.0, demand_profile="high")
    legacy_et = et_demand(legacy, climate, 1.0)
    fao_et = et_demand(fao, climate, 1.0)
    assert legacy_et > 0.0
    assert fao_et > 0.0
    assert fao_et != pytest.approx(legacy_et)


def test_default_params_and_clamping_are_sensible():
    """Soil priors differ predictably and unsafe params are pulled into bounds."""
    sand = default_params("sand")
    loam = default_params("loam")
    clay = default_params("clay")
    unknown = default_params("unknown")

    assert sand.drain_rate > loam.drain_rate > clay.drain_rate
    assert sand.field_capacity < loam.field_capacity < clay.field_capacity
    assert sand.wilting_point < loam.wilting_point < clay.wilting_point
    assert unknown == loam

    clamped = WaterBalanceParams(-1.0, 999.0, -5.0, 2.0, -10.0, 200.0).clamped()

    assert ETA_IRR_MIN <= clamped.eta_irr <= ETA_IRR_MAX
    assert ETA_RAIN_MIN <= clamped.eta_rain <= ETA_RAIN_MAX
    assert K_ET_MIN <= clamped.k_et <= K_ET_MAX
    assert DRAIN_RATE_MIN <= clamped.drain_rate <= DRAIN_RATE_MAX
    assert FIELD_CAPACITY_MIN <= clamped.field_capacity <= FIELD_CAPACITY_MAX
    assert WILTING_POINT_MIN <= clamped.wilting_point <= WILTING_POINT_MAX
    assert clamped.field_capacity > clamped.wilting_point
    assert clamped.eta_irr == pytest.approx(ETA_IRR_MIN)
    assert clamped.eta_rain == pytest.approx(ETA_RAIN_MAX)
    assert clamped.k_et == pytest.approx(K_ET_MIN)
    assert clamped.drain_rate == pytest.approx(DRAIN_RATE_MAX)
