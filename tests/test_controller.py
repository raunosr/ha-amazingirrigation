"""Tests for the pure predictive irrigation controller."""

from __future__ import annotations

import math

import pytest

from custom_components.amazing_irrigation.controller import (
    ForecastInterval,
    TargetBand,
    band_from_target,
    plan_irrigation,
)
from custom_components.amazing_irrigation.waterbalance import WaterBalanceParams


def _params() -> WaterBalanceParams:
    return WaterBalanceParams(
        eta_irr=2.0,
        eta_rain=1.0,
        k_et=1.0,
        drain_rate=0.0,
        field_capacity=50.0,
        wilting_point=10.0,
    )


def test_band_from_target_uses_target_as_low_and_caps_high() -> None:
    band = band_from_target(40.0, field_capacity=43.0, deadband=5.0)
    assert band == TargetBand(low=40.0, high=43.0)


def test_hold_when_no_water_trajectory_stays_in_band() -> None:
    result = plan_irrigation(
        _params(),
        42.0,
        [ForecastInterval(dt=24.0)],
        TargetBand(low=40.0, high=45.0),
        max_liters=10.0,
    )

    assert result.should_water is False
    assert result.reason == "predictive_hold"
    assert result.liters == 0.0
    assert len(result.predicted_trajectory) == 1
    assert result.explanation["predicted_critical_theta_without_water"] >= 40.0
    for key in (
        "starting_theta",
        "target_band",
        "no_irrigation_terms",
        "terms",
        "chosen_liters",
        "predicted_end_theta",
        "predicted_peak_theta",
    ):
        assert key in result.explanation


def test_waters_minimal_litres_to_lift_critical_theta_to_low() -> None:
    result = plan_irrigation(
        _params(),
        39.0,
        [ForecastInterval(dt=24.0)],
        TargetBand(low=40.0, high=45.0),
        max_liters=10.0,
    )

    assert result.should_water is True
    assert result.reason == "predictive_water"
    assert result.liters == pytest.approx(0.98)
    assert result.predicted_trajectory[-1] == pytest.approx(40.0)
    assert len(result.predicted_trajectory) == 1


def test_litres_are_clamped_to_max_liters() -> None:
    result = plan_irrigation(
        _params(),
        30.0,
        [ForecastInterval(dt=24.0)],
        TargetBand(low=40.0, high=50.0),
        max_liters=3.0,
    )

    assert result.should_water is True
    assert result.liters == 3.0
    assert result.explanation["chosen_liters"] == 3.0
    assert result.explanation["predicted_critical_theta_with_water"] < 40.0


def test_litres_are_capped_to_avoid_target_or_capacity_overshoot() -> None:
    result = plan_irrigation(
        _params(),
        39.0,
        [ForecastInterval(dt=0.001), ForecastInterval(dt=48.0)],
        TargetBand(low=40.0, high=40.5),
        max_liters=10.0,
    )

    assert result.should_water is True
    assert result.liters == pytest.approx(0.75)
    assert result.explanation["predicted_peak_theta"] <= 40.5
    assert result.explanation["overshoot"]["amount"] == 0.0
    assert "capped" in result.explanation["note"]


def test_rain_in_horizon_eliminates_watering_need() -> None:
    result = plan_irrigation(
        _params(),
        39.0,
        [ForecastInterval(dt=24.0, rain_mm=2.0)],
        TargetBand(low=40.0, high=45.0),
        max_liters=10.0,
    )

    assert result.should_water is False
    assert result.liters == 0.0
    assert result.explanation["terms"]["rain"] == pytest.approx(2.0)


def test_protected_rain_is_ignored() -> None:
    result = plan_irrigation(
        _params(),
        39.0,
        [ForecastInterval(dt=24.0, rain_mm=2.0, protected_rain=True)],
        TargetBand(low=40.0, high=45.0),
        max_liters=10.0,
    )

    assert result.should_water is True
    assert result.liters == pytest.approx(0.98)
    assert result.explanation["terms"]["rain"] == 0.0


def test_existing_rain_overshoot_is_reported_even_when_holding() -> None:
    result = plan_irrigation(
        _params(),
        39.0,
        [ForecastInterval(dt=0.001, rain_mm=10.0)],
        TargetBand(low=40.0, high=45.0),
        max_liters=10.0,
    )

    assert result.should_water is False
    assert result.explanation["overshoot"]["band_high"] is True
    assert result.explanation["overshoot"]["amount"] > 0.0


def test_degenerate_inputs_hold_safely_with_low_confidence_explanation() -> None:
    result = plan_irrigation(
        _params(),
        math.nan,
        [],
        TargetBand(low=40.0, high=45.0),
        max_liters=10.0,
    )

    assert result.should_water is False
    assert result.reason == "predictive_hold"
    assert result.predicted_trajectory == []
    assert result.explanation["low_confidence"] is True
