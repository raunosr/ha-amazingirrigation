"""Pure tests for the Irrigation Decision engine."""

from __future__ import annotations

from dataclasses import asdict

import pytest

from custom_components.amazing_irrigation.controller import ForecastInterval, TargetBand
from custom_components.amazing_irrigation.engine import (
    DecisionAction,
    DecisionInputs,
    DecisionReason,
    decide,
    effective_rainfall,
    is_heat_emergency,
)
from custom_components.amazing_irrigation.waterbalance import WaterBalanceParams
from custom_components.amazing_irrigation.zone import ZoneMoisture


def _moisture(value: float | None, used: int = 1, configured: int = 1) -> ZoneMoisture:
    return ZoneMoisture(value=value, used=used, configured=configured)


def _inputs(**overrides) -> DecisionInputs:
    base = dict(
        moisture=_moisture(20.0),
        target_moisture=40.0,
        max_liters=30.0,
        gain_per_liter=1.0,
        rain_skip_mm=3.0,
        rain_skip_probability=60.0,
    )
    base.update(overrides)
    return DecisionInputs(**base)


def test_below_target_waters_full_deficit() -> None:
    decision = decide(_inputs(moisture=_moisture(20.0), target_moisture=40.0))
    assert decision.action is DecisionAction.WATER
    assert decision.reason is DecisionReason.BELOW_TARGET
    # Hysteresis refills toward the band high (target 40 + 5 deadband = 45):
    # deficit 25% / 1% per liter = 25 L
    assert decision.recommended_liters == 25.0


def test_liters_bounded_by_max() -> None:
    decision = decide(
        _inputs(moisture=_moisture(10.0), target_moisture=90.0, max_liters=30.0)
    )
    assert decision.recommended_liters == 30.0


def test_above_target_skips() -> None:
    decision = decide(_inputs(moisture=_moisture(45.0), target_moisture=40.0))
    assert decision.action is DecisionAction.SKIP
    assert decision.reason is DecisionReason.ABOVE_TARGET


def test_safety_blocker_skips_even_when_forced() -> None:
    decision = decide(_inputs(safety_blocked=True, force=True))
    assert decision.action is DecisionAction.SKIP
    assert decision.reason is DecisionReason.SAFETY_BLOCKER


def test_force_water_bypasses_soft_checks() -> None:
    decision = decide(
        _inputs(
            moisture=_moisture(80.0),  # above target
            target_moisture=40.0,
            in_season=False,
            zone_locked=True,
            force=True,
        )
    )
    assert decision.action is DecisionAction.WATER
    assert decision.reason is DecisionReason.FORCED


def test_force_water_without_moisture_uses_max_liters() -> None:
    decision = decide(
        _inputs(moisture=_moisture(None, used=0), target_moisture=None, force=True)
    )
    assert decision.action is DecisionAction.WATER
    assert decision.recommended_liters == 30.0


def test_moisture_unavailable_fails_closed() -> None:
    decision = decide(_inputs(moisture=_moisture(None, used=0, configured=2)))
    assert decision.action is DecisionAction.SKIP
    assert decision.reason is DecisionReason.MOISTURE_UNAVAILABLE


def test_out_of_season_skips() -> None:
    decision = decide(_inputs(in_season=False))
    assert decision.action is DecisionAction.SKIP
    assert decision.reason is DecisionReason.OUT_OF_SEASON


def test_disabled_zone_skips() -> None:
    decision = decide(_inputs(enabled=False))
    assert decision.action is DecisionAction.SKIP
    assert decision.reason is DecisionReason.DISABLED


def test_force_water_bypasses_disabled_zone() -> None:
    decision = decide(_inputs(enabled=False, force=True))
    assert decision.action is DecisionAction.WATER
    assert decision.reason is DecisionReason.FORCED


def test_zone_locked_skips() -> None:
    decision = decide(_inputs(zone_locked=True))
    assert decision.action is DecisionAction.SKIP
    assert decision.reason is DecisionReason.ZONE_LOCKED


def test_no_target_skips() -> None:
    decision = decide(_inputs(target_moisture=None))
    assert decision.action is DecisionAction.SKIP
    assert decision.reason is DecisionReason.NO_TARGET


def test_sufficient_rain_skips() -> None:
    # 20 mm forecast -> 20 * 0.75 effective = 15 mm >= 3 mm threshold -> skip.
    decision = decide(
        _inputs(forecast_rain_mm=20.0, forecast_rain_probability=80.0, rain_skip_mm=3.0)
    )
    assert decision.action is DecisionAction.SKIP
    assert decision.reason is DecisionReason.RAIN_SUFFICIENT


def test_unlikely_forecast_rain_is_ignored() -> None:
    decision = decide(
        _inputs(forecast_rain_mm=20.0, forecast_rain_probability=20.0, rain_skip_mm=3.0)
    )
    assert decision.action is DecisionAction.WATER
    assert decision.reason is DecisionReason.BELOW_TARGET


def test_partial_rain_reduces_volume() -> None:
    # 3 mm observed -> 3 * 0.5 effective = 1.5 mm of 3 mm threshold -> 50 %
    # reduction of the 25 L hysteresis refill run.
    decision = decide(
        _inputs(observed_rain_mm=3.0, forecast_rain_mm=None, rain_skip_mm=3.0)
    )
    assert decision.action is DecisionAction.REDUCE
    assert decision.reason is DecisionReason.RAIN_REDUCE
    assert decision.recommended_liters == 12.5


def test_observed_rain_counts_regardless_of_probability() -> None:
    # 10 mm observed -> 10 * 0.75 effective = 7.5 mm >= 3 mm -> skip even with
    # zero forecast probability (probability only gates forecast rain).
    decision = decide(
        _inputs(observed_rain_mm=10.0, forecast_rain_probability=0.0, rain_skip_mm=3.0)
    )
    assert decision.action is DecisionAction.SKIP
    assert decision.reason is DecisionReason.RAIN_SUFFICIENT


def test_protected_rain_ignores_rain_in_greenhouse() -> None:
    # A protected Greenhouse Zone receives no rainfall, so abundant observed and
    # forecast rain must not skip or reduce its watering.
    decision = decide(
        _inputs(
            observed_rain_mm=20.0,
            forecast_rain_mm=20.0,
            forecast_rain_probability=100.0,
            rain_skip_mm=3.0,
            protected_rain=True,
        )
    )
    assert decision.action is DecisionAction.WATER
    assert decision.reason is DecisionReason.BELOW_TARGET
    assert decision.recommended_liters == 25.0


def test_protected_rain_false_still_skips_on_rain() -> None:
    decision = decide(
        _inputs(observed_rain_mm=20.0, rain_skip_mm=3.0, protected_rain=False)
    )
    assert decision.action is DecisionAction.SKIP
    assert decision.reason is DecisionReason.RAIN_SUFFICIENT


def test_degraded_flag_propagates() -> None:
    decision = decide(
        _inputs(moisture=_moisture(20.0, used=1, configured=3), target_moisture=40.0)
    )
    assert decision.degraded is True
    assert decision.action is DecisionAction.WATER


def test_predictive_branch_waters_with_explanation() -> None:
    decision = decide(
        _inputs(
            moisture=_moisture(39.0),
            target_moisture=40.0,
            predictive=True,
            params=WaterBalanceParams(2.0, 1.0, 1.0, 0.0, 50.0, 10.0),
            horizon=[ForecastInterval(dt=24.0)],
            target_band=TargetBand(low=40.0, high=45.0),
        )
    )

    assert decision.action is DecisionAction.WATER
    assert decision.reason is DecisionReason.PREDICTIVE_WATER
    assert decision.recommended_liters == pytest.approx(0.98)
    assert decision.details["predictive"] is True
    assert "explanation" in decision.details
    assert decision.details["predicted_trajectory"] == [40.0]


def test_predictive_branch_holds_when_future_stays_in_band() -> None:
    decision = decide(
        _inputs(
            moisture=_moisture(39.5),
            target_moisture=40.0,
            predictive=True,
            params=WaterBalanceParams(2.0, 2.0, 1.0, 0.0, 50.0, 10.0),
            horizon=[ForecastInterval(dt=24.0, rain_mm=1.0)],
            target_band=TargetBand(low=40.0, high=45.0),
        )
    )

    assert decision.action is DecisionAction.SKIP
    assert decision.reason is DecisionReason.PREDICTIVE_HOLD
    assert decision.recommended_liters == 0.0
    assert decision.details["explanation"]["terms"]["rain"] == 2.0


def test_predictive_does_not_override_force_or_safety() -> None:
    kwargs = dict(
        predictive=True,
        params=WaterBalanceParams(2.0, 1.0, 1.0, 0.0, 50.0, 10.0),
        horizon=[ForecastInterval(dt=24.0)],
        target_band=TargetBand(low=40.0, high=45.0),
    )

    forced = decide(_inputs(moisture=_moisture(80.0), force=True, **kwargs))
    blocked = decide(_inputs(force=True, safety_blocked=True, **kwargs))

    assert forced.reason is DecisionReason.FORCED
    assert blocked.reason is DecisionReason.SAFETY_BLOCKER


def test_predictive_false_preserves_rule_based_output() -> None:
    base = _inputs(observed_rain_mm=1.5, forecast_rain_mm=None, rain_skip_mm=3.0)
    with_unused_predictive_fields = _inputs(
        observed_rain_mm=1.5,
        forecast_rain_mm=None,
        rain_skip_mm=3.0,
        predictive=False,
        params=WaterBalanceParams(2.0, 1.0, 1.0, 0.0, 50.0, 10.0),
        horizon=[ForecastInterval(dt=24.0)],
        target_band=TargetBand(low=40.0, high=45.0),
    )

    assert asdict(decide(with_unused_predictive_fields)) == asdict(decide(base))


def test_below_min_application_skips_tiny_topup() -> None:
    # 39 -> band high 45 = 6% deficit / 3% per liter = 2 L, but min_application
    # is 5 L, so the negligible top-up is skipped.
    decision = decide(
        _inputs(
            moisture=_moisture(39.0),
            target_moisture=40.0,
            gain_per_liter=3.0,
            min_application=5.0,
        )
    )
    assert decision.action is DecisionAction.SKIP
    assert decision.reason is DecisionReason.BELOW_MIN
    assert decision.details["min_application"] == 5.0


def test_heat_emergency_overrides_min_application() -> None:
    # Same tiny top-up, but a heat emergency waives the minimum and waters.
    decision = decide(
        _inputs(
            moisture=_moisture(39.0),
            target_moisture=40.0,
            gain_per_liter=3.0,
            min_application=5.0,
            heat_emergency=True,
        )
    )
    assert decision.action is DecisionAction.WATER
    assert decision.reason is DecisionReason.BELOW_TARGET


def test_rain_fraction_scales_effective_rain() -> None:
    # 10 mm observed * 0.75 curve = 7.5 mm effective at 100 %, enough to skip.
    # At 40 % rain fraction only 3.0 mm reaches the zone: still >= 3 mm skip
    # threshold, so we drop to 6 mm (below threshold) to force a partial run.
    decision = decide(
        _inputs(observed_rain_mm=6.0, rain_skip_mm=3.0, rain_fraction=40.0)
    )
    # 6 mm * 0.5 curve * 0.4 fraction = 1.2 mm effective -> 40 % of threshold ->
    # 60 % of the 25 L refill run remains.
    assert decision.action is DecisionAction.REDUCE
    assert decision.recommended_liters == pytest.approx(15.0)


def test_zero_rain_fraction_ignores_rain() -> None:
    decision = decide(
        _inputs(observed_rain_mm=20.0, rain_skip_mm=3.0, rain_fraction=0.0)
    )
    assert decision.action is DecisionAction.WATER
    assert decision.reason is DecisionReason.BELOW_TARGET


def test_every_decision_carries_the_active_band() -> None:
    watered = decide(_inputs(moisture=_moisture(20.0), target_moisture=40.0))
    held = decide(_inputs(moisture=_moisture(45.0), target_moisture=40.0))
    for decision in (watered, held):
        assert decision.details["target_band_low"] == 40.0
        assert decision.details["target_band_high"] == 45.0


def test_effective_rainfall_curve() -> None:
    assert effective_rainfall(2.0) == 0.0
    assert effective_rainfall(6.0) == pytest.approx(3.0)
    assert effective_rainfall(20.0) == pytest.approx(15.0)
    assert effective_rainfall(40.0) == pytest.approx(32.0)
    # Covered zone at 50 % rain fraction halves the usable rain.
    assert effective_rainfall(20.0, 0.5) == pytest.approx(7.5)


def test_is_heat_emergency_only_for_hot_high_demand() -> None:
    assert is_heat_emergency("high", 33.0) is True
    assert is_heat_emergency("high", 28.0, 20.0) is True  # dry air -> high VPD
    assert is_heat_emergency("medium", 40.0) is False
    assert is_heat_emergency("high", None) is False

