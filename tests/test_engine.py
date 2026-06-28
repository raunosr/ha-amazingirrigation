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
    # deficit 20% / 1% per liter = 20 L
    assert decision.recommended_liters == 20.0


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
    decision = decide(
        _inputs(forecast_rain_mm=5.0, forecast_rain_probability=80.0, rain_skip_mm=3.0)
    )
    assert decision.action is DecisionAction.SKIP
    assert decision.reason is DecisionReason.RAIN_SUFFICIENT


def test_unlikely_forecast_rain_is_ignored() -> None:
    decision = decide(
        _inputs(forecast_rain_mm=5.0, forecast_rain_probability=20.0, rain_skip_mm=3.0)
    )
    assert decision.action is DecisionAction.WATER
    assert decision.reason is DecisionReason.BELOW_TARGET


def test_partial_rain_reduces_volume() -> None:
    # 1.5 mm of 3 mm threshold -> 50% reduction of the 20 L deficit run.
    decision = decide(
        _inputs(observed_rain_mm=1.5, forecast_rain_mm=None, rain_skip_mm=3.0)
    )
    assert decision.action is DecisionAction.REDUCE
    assert decision.reason is DecisionReason.RAIN_REDUCE
    assert decision.recommended_liters == 10.0


def test_observed_rain_counts_regardless_of_probability() -> None:
    decision = decide(
        _inputs(observed_rain_mm=3.0, forecast_rain_probability=0.0, rain_skip_mm=3.0)
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
    assert decision.recommended_liters == 20.0


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
