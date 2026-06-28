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

from .zone import ZoneMoisture

# Smallest watering volume worth running; anything below is treated as a skip.
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


def _effective_rain_mm(inp: DecisionInputs) -> float:
    """Rain that counts toward the deficit: observed plus likely forecast."""
    rain = inp.observed_rain_mm or 0.0
    probability = inp.forecast_rain_probability
    if inp.forecast_rain_mm and (
        probability is None or probability >= inp.rain_skip_probability
    ):
        rain += inp.forecast_rain_mm
    return rain


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

    # 8. Already wet enough.
    deficit = inp.target_moisture - inp.moisture.value
    if deficit <= 0:
        return Decision(
            DecisionAction.SKIP, DecisionReason.ABOVE_TARGET, 0.0, degraded
        )

    liters_needed = _liters_for_deficit(inp, deficit)
    rain = _effective_rain_mm(inp)

    # 9/10. Rain reduces or cancels the run.
    if rain > 0 and inp.rain_skip_mm > 0:
        if rain >= inp.rain_skip_mm:
            return Decision(
                DecisionAction.SKIP,
                DecisionReason.RAIN_SUFFICIENT,
                0.0,
                degraded,
                {"effective_rain_mm": rain},
            )
        factor = max(0.0, 1.0 - rain / inp.rain_skip_mm)
        reduced = liters_needed * factor
        if reduced < MIN_EFFECTIVE_LITERS:
            return Decision(
                DecisionAction.SKIP,
                DecisionReason.RAIN_SUFFICIENT,
                0.0,
                degraded,
                {"effective_rain_mm": rain},
            )
        return Decision(
            DecisionAction.REDUCE,
            DecisionReason.RAIN_REDUCE,
            reduced,
            degraded,
            {"effective_rain_mm": rain, "unreduced_liters": liters_needed},
        )

    # 11. Water the full recommended volume.
    return Decision(
        DecisionAction.WATER, DecisionReason.BELOW_TARGET, liters_needed, degraded
    )
