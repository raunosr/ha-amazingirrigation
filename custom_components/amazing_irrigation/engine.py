"""Pure Irrigation Decision engine.

Given a Run Request's inputs, decide whether an Irrigation Zone would skip,
reduce, or water, and explain why. This module is deliberately free of any
Home Assistant dependency so the decision logic can be reasoned about and
tested cheaply. It never actuates water; callers translate a Decision into a
Watering Event in later slices.

Decision precedence (hard safety first, then soft checks):

1. Safety Blocker active/unavailable -> SKIP (hard; even Force Water respects it).
2. Force Water -> WATER (bypasses every soft check below).
3. Zone automation disabled -> SKIP.
4. Out of active season -> SKIP.
5. Zone Moisture unavailable -> SKIP (fail closed).
6. Another zone watering under the global lock -> SKIP.
7. No Target Moisture configured -> SKIP (cannot decide).
8. Zone Moisture at/above Target Moisture -> SKIP.
9. Enough rain (observed + likely forecast) to cover the deficit -> SKIP.
10. Some rain expected -> REDUCE the recommended liters.
11. Otherwise -> WATER the full recommended liters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .const import HEAT_EMERGENCY_TEMP_C, HEAT_EMERGENCY_VPD_KPA
from .controller import ForecastInterval, TargetBand, band_from_target, plan_irrigation
from .waterbalance import BalanceInterval, WaterBalanceParams, vpd_kpa
from .zone import ZoneMoisture

# Smallest watering volume worth running when a zone sets no explicit minimum.
MIN_EFFECTIVE_LITERS = 0.1


class DecisionAction(StrEnum):
    """The outcome of an Irrigation Decision."""

    SKIP = "skip"
    REDUCE = "reduce"
    WATER = "water"


class DecisionReason(StrEnum):
    """Machine-readable explanation for a Decision."""

    SAFETY_BLOCKER = "safety_blocker"
    FORCED = "forced"
    DISABLED = "disabled"
    OUT_OF_SEASON = "out_of_season"
    MOISTURE_UNAVAILABLE = "moisture_unavailable"
    ZONE_LOCKED = "zone_locked"
    NO_TARGET = "no_target"
    ABOVE_TARGET = "above_target"
    RAIN_SUFFICIENT = "rain_sufficient"
    RAIN_REDUCE = "rain_reduce"
    BELOW_TARGET = "below_target"
    BELOW_MIN = "below_min_application"
    PREDICTIVE_WATER = "predictive_water"
    PREDICTIVE_HOLD = "predictive_hold"


@dataclass(frozen=True)
class DecisionInputs:
    """Everything the engine needs to evaluate a single Run Request."""

    moisture: ZoneMoisture
    target_moisture: float | None
    max_liters: float
    gain_per_liter: float | None = None
    observed_rain_mm: float | None = None
    forecast_rain_mm: float | None = None
    forecast_rain_probability: float | None = None
    rain_skip_mm: float = 3.0
    rain_skip_probability: float = 60.0
    safety_blocked: bool = False
    enabled: bool = True
    in_season: bool = True
    zone_locked: bool = False
    force: bool = False
    protected_rain: bool = False
    rain_fraction: float = 100.0
    min_application: float = MIN_EFFECTIVE_LITERS
    heat_emergency: bool = False
    field_capacity: float | None = None
    predictive: bool = False
    params: WaterBalanceParams | None = None
    horizon: list[BalanceInterval | ForecastInterval | dict] | None = None
    target_band: TargetBand | None = None
    target_high: float | None = None


@dataclass(frozen=True)
class Decision:
    """The explained result of evaluating a Run Request."""

    action: DecisionAction
    reason: DecisionReason
    recommended_liters: float
    degraded: bool = False
    details: dict = field(default_factory=dict)

    @property
    def will_water(self) -> bool:
        """Whether this decision would lead to a Watering Event."""
        return self.action in (DecisionAction.WATER, DecisionAction.REDUCE)


def _liters_for_deficit(inp: DecisionInputs, deficit: float) -> float:
    """Liters needed to cover a moisture deficit, bounded by the max per run."""
    if inp.gain_per_liter and inp.gain_per_liter > 0:
        liters = deficit / inp.gain_per_liter
    else:
        liters = inp.max_liters
    return max(0.0, min(liters, inp.max_liters))


def effective_rainfall(rain_mm: float, rain_fraction: float = 1.0) -> float:
    """Return usable rainfall (mm) after an event-based effectiveness curve.

    Light showers mostly evaporate or run off, while heavy rain is largely lost
    to drainage, so only a fraction of measured rain reaches the root zone:
    ``<3 mm → 0``, ``3-10 mm → 0.5``, ``10-25 mm → 0.75``, ``>25 mm → 0.80``.
    The result is further scaled by ``rain_fraction`` (0..1) for covered zones.
    """
    rain = max(0.0, rain_mm)
    if rain < 3.0:
        curve = 0.0
    elif rain < 10.0:
        curve = 0.5
    elif rain <= 25.0:
        curve = 0.75
    else:
        curve = 0.80
    return rain * curve * max(0.0, min(1.0, rain_fraction))


def is_heat_emergency(
    demand_profile: str | None,
    air_temp_c: float | None,
    air_humidity_pct: float | None = None,
) -> bool:
    """Whether conditions justify overriding the minimum-application skip.

    Only ``high`` water-demand zones qualify, and only when air temperature or
    the vapour-pressure deficit exceed the emergency thresholds.
    """
    if (demand_profile or "").strip().lower() != "high" or air_temp_c is None:
        return False
    if air_temp_c >= HEAT_EMERGENCY_TEMP_C:
        return True
    vpd = vpd_kpa(air_temp_c, air_humidity_pct)
    return vpd is not None and vpd >= HEAT_EMERGENCY_VPD_KPA


def _raw_rain_mm(inp: DecisionInputs) -> float:
    """Observed plus likely-forecast rain in mm, before the effectiveness curve."""
    rain = inp.observed_rain_mm or 0.0
    probability = inp.forecast_rain_probability
    if inp.forecast_rain_mm and (
        probability is None or probability >= inp.rain_skip_probability
    ):
        rain += inp.forecast_rain_mm
    return rain


def _effective_rain_mm(inp: DecisionInputs) -> float:
    """Rain that counts toward the deficit after fraction + effectiveness curve.

    A fully protected zone (rain_fraction 0) receives no usable rain, so rain
    never reduces or cancels its watering.
    """
    fraction = 0.0 if inp.protected_rain else max(0.0, min(1.0, inp.rain_fraction / 100.0))
    if fraction <= 0.0:
        return 0.0
    return effective_rainfall(_raw_rain_mm(inp), fraction)


def decide(inp: DecisionInputs) -> Decision:
    """Evaluate a Run Request and return an explained Irrigation Decision."""
    degraded = inp.moisture.degraded

    # 1. Hard safety: Safety Blockers block everything, including Force Water.
    if inp.safety_blocked:
        return Decision(
            DecisionAction.SKIP, DecisionReason.SAFETY_BLOCKER, 0.0, degraded
        )

    # 2. Force Water bypasses all soft checks below.
    if inp.force:
        if inp.moisture.available and inp.target_moisture is not None:
            deficit = max(0.0, inp.target_moisture - inp.moisture.value)
            liters = _liters_for_deficit(inp, deficit) or inp.max_liters
        else:
            liters = inp.max_liters
        return Decision(
            DecisionAction.WATER, DecisionReason.FORCED, liters, degraded
        )

    # 3. Zone automation disabled (manual Force Water still bypasses this).
    if not inp.enabled:
        return Decision(
            DecisionAction.SKIP, DecisionReason.DISABLED, 0.0, degraded
        )

    # 4. Season window.
    if not inp.in_season:
        return Decision(
            DecisionAction.SKIP, DecisionReason.OUT_OF_SEASON, 0.0, degraded
        )

    # 5. Fail closed without a valid Zone Moisture.
    if not inp.moisture.available:
        return Decision(
            DecisionAction.SKIP, DecisionReason.MOISTURE_UNAVAILABLE, 0.0, degraded
        )

    # 6. Global watering lock.
    if inp.zone_locked:
        return Decision(
            DecisionAction.SKIP, DecisionReason.ZONE_LOCKED, 0.0, degraded
        )

    # 7. Need a target to decide.
    if inp.target_moisture is None:
        return Decision(
            DecisionAction.SKIP, DecisionReason.NO_TARGET, 0.0, degraded
        )

    # A single hysteresis band drives every path: irrigation starts once moisture
    # falls below ``band.low`` and refills toward ``band.high`` (already capped at
    # field capacity). This replaces the old single-target top-up behaviour.
    band = inp.target_band or band_from_target(
        inp.target_moisture,
        field_capacity=(
            inp.field_capacity
            if inp.field_capacity is not None
            else (inp.params.field_capacity if inp.params is not None else None)
        ),
    )
    if inp.target_high is not None:
        band = TargetBand(low=band.low, high=inp.target_high)

    # Attached to every decision below so the UI can always render the active
    # hysteresis band (e.g. the read-only Auto target range on the card).
    band_details = {
        "target_band_low": round(band.low, 1),
        "target_band_high": round(band.high, 1),
        "band_field_capacity": (
            round(inp.field_capacity, 1) if inp.field_capacity is not None else None
        ),
    }

    # Smallest worthwhile application, waived under a heat emergency.
    min_effective = 0.0 if inp.heat_emergency else max(0.0, inp.min_application)

    if inp.predictive and inp.params is not None and inp.horizon:
        control = plan_irrigation(
            inp.params,
            inp.moisture.value,
            inp.horizon,
            band,
            max_liters=inp.max_liters,
            min_effective_liters=min_effective,
        )
        details = {
            "predictive": True,
            "explanation": control.explanation,
            "predicted_trajectory": control.predicted_trajectory,
            "horizon_hours": control.horizon_hours,
            "target_band_low": round(band.low, 1),
            "target_band_high": round(band.high, 1),
            "band_field_capacity": (
                round(inp.field_capacity, 1)
                if inp.field_capacity is not None
                else None
            ),
        }
        if control.should_water:
            return Decision(
                DecisionAction.WATER,
                DecisionReason.PREDICTIVE_WATER,
                control.liters,
                degraded,
                details,
            )
        return Decision(
            DecisionAction.SKIP,
            DecisionReason.PREDICTIVE_HOLD,
            0.0,
            degraded,
            details,
        )

    # 8. Above the hysteresis trigger: hold until moisture falls below band.low.
    if inp.moisture.value >= band.low:
        return Decision(
            DecisionAction.SKIP,
            DecisionReason.ABOVE_TARGET,
            0.0,
            degraded,
            dict(band_details),
        )

    # Refill toward the band high (field-capacity capped), not just the trigger.
    refill_deficit = max(0.0, band.high - inp.moisture.value)
    liters_needed = _liters_for_deficit(inp, refill_deficit)
    rain = _effective_rain_mm(inp)

    # 9/10. Rain reduces or cancels the run.
    if rain > 0 and inp.rain_skip_mm > 0:
        if rain >= inp.rain_skip_mm:
            return Decision(
                DecisionAction.SKIP,
                DecisionReason.RAIN_SUFFICIENT,
                0.0,
                degraded,
                {**band_details, "effective_rain_mm": rain},
            )
        factor = max(0.0, 1.0 - rain / inp.rain_skip_mm)
        reduced = liters_needed * factor
        if reduced < min_effective:
            return Decision(
                DecisionAction.SKIP,
                DecisionReason.RAIN_SUFFICIENT,
                0.0,
                degraded,
                {**band_details, "effective_rain_mm": rain},
            )
        return Decision(
            DecisionAction.REDUCE,
            DecisionReason.RAIN_REDUCE,
            reduced,
            degraded,
            {
                **band_details,
                "effective_rain_mm": rain,
                "unreduced_liters": liters_needed,
            },
        )

    # 11. Skip negligible top-ups unless a heat emergency forces the run.
    if liters_needed < min_effective:
        return Decision(
            DecisionAction.SKIP,
            DecisionReason.BELOW_MIN,
            0.0,
            degraded,
            {
                **band_details,
                "min_application": min_effective,
                "liters_needed": liters_needed,
            },
        )

    # Water the full recommended volume toward the band high.
    return Decision(
        DecisionAction.WATER,
        DecisionReason.BELOW_TARGET,
        liters_needed,
        degraded,
        dict(band_details),
    )
