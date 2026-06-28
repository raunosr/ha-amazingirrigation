"""Pure predictive irrigation controller built on the water-balance model."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .waterbalance import (
    MOISTURE_MAX,
    MOISTURE_MIN,
    BalanceInterval,
    Climate,
    WaterBalanceParams,
    simulate,
)

DEFAULT_TARGET_DEADBAND = 5.0
MIN_ETA_IRR = 1.0e-6


@dataclass(frozen=True)
class TargetBand:
    """Desired moisture band for predictive control, in moisture percent."""

    low: float
    high: float


@dataclass(frozen=True)
class ForecastInterval:
    """A forecast interval before the next schedule slot.

    ``dt`` is hours. The interval intentionally has no ``liters`` field because
    the controller chooses irrigation volume; rain and climate are exogenous.
    """

    dt: float
    rain_mm: float = 0.0
    climate: Climate | None = None
    protected_rain: bool = False


@dataclass(frozen=True)
class ControlResult:
    """Predictive controller output and explanation."""

    liters: float
    should_water: bool
    reason: str
    predicted_trajectory: list[float] = field(default_factory=list)
    horizon_hours: float = 0.0
    explanation: dict[str, Any] = field(default_factory=dict)


def _finite(value: object) -> float | None:
    """Return ``value`` as a finite float, or ``None``."""
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a finite value to inclusive bounds."""
    return max(low, min(high, value))


def band_from_target(
    target_moisture: float | None,
    field_capacity: float | None = None,
    *,
    deadband: float = DEFAULT_TARGET_DEADBAND,
) -> TargetBand:
    """Derive a target band from today's single target setting.

    Slice F can wire explicit low/high configuration into :class:`TargetBand`.
    Until then, the existing target is the lower bound and ``deadband`` creates a
    modest upper bound, capped by field capacity when known.
    """
    target = _finite(target_moisture)
    if target is None:
        target = MOISTURE_MIN
    low = _clamp(target, MOISTURE_MIN, MOISTURE_MAX)

    cap = _finite(field_capacity)
    high_cap = MOISTURE_MAX if cap is None else _clamp(cap, MOISTURE_MIN, MOISTURE_MAX)
    width = _finite(deadband)
    if width is None or width < 0:
        width = DEFAULT_TARGET_DEADBAND
    high = min(high_cap, low + width)
    if high < low:
        high = low
    return TargetBand(low=low, high=high)


def _interval_value(interval: object, name: str, default: Any) -> Any:
    """Read an interval field from a mapping or dataclass-like object."""
    if isinstance(interval, Mapping):
        return interval.get(name, default)
    return getattr(interval, name, default)


def _normalise_horizon(
    horizon: Iterable[ForecastInterval | BalanceInterval | Mapping[str, Any]] | None,
) -> list[BalanceInterval]:
    """Convert forecast intervals into water-balance intervals with zero liters."""
    if horizon is None:
        return []
    intervals: list[BalanceInterval] = []
    for item in horizon:
        dt = _finite(_interval_value(item, "dt", 0.0))
        if dt is None or dt <= 0:
            continue
        rain = _finite(_interval_value(item, "rain_mm", 0.0))
        intervals.append(
            BalanceInterval(
                dt=dt,
                liters=0.0,
                rain_mm=0.0 if rain is None else max(0.0, rain),
                climate=_interval_value(item, "climate", None),
                protected_rain=bool(_interval_value(item, "protected_rain", False)),
            )
        )
    return intervals


def _sum_terms(results: Iterable[object]) -> dict[str, float]:
    """Sum water-balance terms across a simulated trajectory."""
    totals = {"irrigation": 0.0, "rain": 0.0, "et": 0.0, "drainage": 0.0}
    for result in results:
        terms = getattr(result, "terms", {})
        for key in totals:
            totals[key] += float(terms.get(key, 0.0))
    return {key: round(value, 6) for key, value in totals.items()}


def _trajectory(results: Iterable[object]) -> list[float]:
    """Return rounded theta values for each predicted step."""
    return [round(float(result.theta_next), 6) for result in results]


def _base_explanation(
    *,
    theta_now: float,
    band: TargetBand,
    max_liters: float,
    horizon_hours: float,
    note: str | None = None,
) -> dict[str, Any]:
    """Build the common explanation envelope."""
    explanation: dict[str, Any] = {
        "mode": "predictive",
        "starting_theta": round(theta_now, 6),
        "target_band": {"low": round(band.low, 6), "high": round(band.high, 6)},
        "max_liters": round(max_liters, 6),
        "horizon_hours": round(horizon_hours, 6),
        "critical_strategy": "minimum_predicted_theta_over_horizon",
    }
    if note:
        explanation["note"] = note
        explanation["low_confidence"] = True
    return explanation


def _hold_result(
    *,
    theta_now: float,
    band: TargetBand,
    max_liters: float,
    horizon_hours: float = 0.0,
    explanation: dict[str, Any] | None = None,
    note: str | None = None,
) -> ControlResult:
    """Return a safe hold result."""
    details = explanation or _base_explanation(
        theta_now=theta_now,
        band=band,
        max_liters=max_liters,
        horizon_hours=horizon_hours,
        note=note,
    )
    details.setdefault("chosen_liters", 0.0)
    details.setdefault("should_water", False)
    return ControlResult(
        liters=0.0,
        should_water=False,
        reason="predictive_hold",
        predicted_trajectory=list(details.get("predicted_trajectory", [])),
        horizon_hours=horizon_hours,
        explanation=details,
    )


def _with_first_liters(
    intervals: list[BalanceInterval], liters: float
) -> list[BalanceInterval]:
    """Return intervals with the chosen litres applied at the first step."""
    if not intervals:
        return []
    first = intervals[0]
    return [
        BalanceInterval(
            dt=first.dt,
            liters=liters,
            rain_mm=first.rain_mm,
            climate=first.climate,
            protected_rain=first.protected_rain,
        ),
        *intervals[1:],
    ]


def plan_irrigation(
    params: WaterBalanceParams,
    theta_now: float,
    horizon: Iterable[ForecastInterval | BalanceInterval | Mapping[str, Any]] | None,
    band: TargetBand,
    *,
    max_liters: float,
    min_effective_liters: float = 0.1,
) -> ControlResult:
    """Plan the minimum watering needed until the next active schedule slot.

    The critical moisture is the minimum predicted theta over the horizon, not
    just the end point, so short dry dips are caught even when later rain recovers
    the zone. Irrigation is modelled as a single run at the start of the horizon.
    """
    theta = _finite(theta_now)
    max_run = _finite(max_liters)
    if theta is None:
        theta = MOISTURE_MIN
    theta = _clamp(theta, MOISTURE_MIN, MOISTURE_MAX)
    if max_run is None:
        max_run = 0.0
    max_run = max(0.0, max_run)

    target = TargetBand(
        low=_clamp(_finite(band.low) or MOISTURE_MIN, MOISTURE_MIN, MOISTURE_MAX),
        high=_clamp(_finite(band.high) or band.low, MOISTURE_MIN, MOISTURE_MAX),
    )
    if target.high < target.low:
        target = TargetBand(target.low, target.low)

    intervals = _normalise_horizon(horizon)
    horizon_hours = sum(interval.dt for interval in intervals)
    if not intervals:
        return _hold_result(
            theta_now=theta,
            band=target,
            max_liters=max_run,
            note="No valid forecast horizon was available; holding safely.",
        )

    try:
        bounded = params.clamped()
    except (AttributeError, TypeError, ValueError):
        return _hold_result(
            theta_now=theta,
            band=target,
            max_liters=max_run,
            horizon_hours=horizon_hours,
            note="Water-balance parameters were invalid; holding safely.",
        )
    eta_irr = _finite(bounded.eta_irr)
    if eta_irr is None or eta_irr <= MIN_ETA_IRR:
        return _hold_result(
            theta_now=theta,
            band=target,
            max_liters=max_run,
            horizon_hours=horizon_hours,
            note="Irrigation efficiency is too low for a reliable prediction.",
        )

    no_water_results = simulate(bounded, theta, intervals)
    no_water_trajectory = _trajectory(no_water_results)
    critical_no_water = min(no_water_trajectory) if no_water_trajectory else theta
    no_water_terms = _sum_terms(no_water_results)

    explanation = _base_explanation(
        theta_now=theta,
        band=target,
        max_liters=max_run,
        horizon_hours=horizon_hours,
    )
    explanation.update(
        {
            "no_irrigation_trajectory": no_water_trajectory,
            "no_irrigation_terms": no_water_terms,
            "predicted_critical_theta_without_water": round(critical_no_water, 6),
        }
    )

    if critical_no_water >= target.low:
        plan_peak = max([theta, *no_water_trajectory])
        band_overshoot = max(0.0, plan_peak - target.high)
        capacity_overshoot = max(0.0, plan_peak - bounded.field_capacity)
        explanation.update(
            {
                "chosen_liters": 0.0,
                "should_water": False,
                "predicted_trajectory": no_water_trajectory,
                "terms": no_water_terms,
                "predicted_end_theta": no_water_trajectory[-1],
                "predicted_peak_theta": plan_peak,
                "overshoot": {
                    "band_high": band_overshoot > 0.0,
                    "field_capacity": capacity_overshoot > 0.0,
                    "amount": round(max(band_overshoot, capacity_overshoot), 6),
                },
            }
        )
        return _hold_result(
            theta_now=theta,
            band=target,
            max_liters=max_run,
            horizon_hours=horizon_hours,
            explanation=explanation,
        )

    deficit = max(0.0, target.low - critical_no_water)
    requested_liters = deficit / eta_irr
    cap_theta = min(target.high, bounded.field_capacity)
    headroom = max(0.0, cap_theta - theta)
    headroom_liters = headroom / eta_irr
    chosen = min(requested_liters, max_run, headroom_liters)
    chosen = max(0.0, chosen)

    if chosen < max(0.0, min_effective_liters):
        plan_peak = max([theta, *no_water_trajectory])
        band_overshoot = max(0.0, plan_peak - target.high)
        capacity_overshoot = max(0.0, plan_peak - bounded.field_capacity)
        explanation.update(
            {
                "chosen_liters": 0.0,
                "requested_liters_to_reach_low": round(requested_liters, 6),
                "headroom_liters": round(headroom_liters, 6),
                "should_water": False,
                "predicted_trajectory": no_water_trajectory,
                "terms": no_water_terms,
                "predicted_end_theta": no_water_trajectory[-1],
                "predicted_peak_theta": plan_peak,
                "overshoot": {
                    "band_high": band_overshoot > 0.0,
                    "field_capacity": capacity_overshoot > 0.0,
                    "amount": round(max(band_overshoot, capacity_overshoot), 6),
                },
                "note": "Calculated irrigation was below the minimum effective volume.",
            }
        )
        return _hold_result(
            theta_now=theta,
            band=target,
            max_liters=max_run,
            horizon_hours=horizon_hours,
            explanation=explanation,
        )

    plan_intervals = _with_first_liters(intervals, chosen)
    plan_results = simulate(bounded, theta, plan_intervals)
    plan_trajectory = _trajectory(plan_results)
    plan_peak = max([theta, *plan_trajectory]) if plan_trajectory else theta
    band_overshoot = max(0.0, plan_peak - target.high)
    capacity_overshoot = max(0.0, plan_peak - bounded.field_capacity)
    overshoot_amount = max(band_overshoot, capacity_overshoot)
    explanation.update(
        {
            "chosen_liters": round(chosen, 6),
            "requested_liters_to_reach_low": round(requested_liters, 6),
            "headroom_liters": round(headroom_liters, 6),
            "should_water": True,
            "predicted_trajectory": plan_trajectory,
            "terms": _sum_terms(plan_results),
            "predicted_end_theta": plan_trajectory[-1],
            "predicted_peak_theta": round(plan_peak, 6),
            "predicted_critical_theta_with_water": min(plan_trajectory),
            "overshoot": {
                "band_high": band_overshoot > 0.0,
                "field_capacity": capacity_overshoot > 0.0,
                "amount": round(overshoot_amount, 6),
            },
        }
    )
    if chosen < requested_liters:
        explanation["note"] = (
            "Irrigation was capped by max_liters or target/headroom constraints; "
            "the predicted critical moisture may remain below the band."
        )

    return ControlResult(
        liters=chosen,
        should_water=True,
        reason="predictive_water",
        predicted_trajectory=plan_trajectory,
        horizon_hours=horizon_hours,
        explanation=explanation,
    )
