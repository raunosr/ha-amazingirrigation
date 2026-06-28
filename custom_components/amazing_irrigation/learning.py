"""Pure auto-learning maths for a zone's Learned Model.

The integration learns a small, explainable soil model for each Irrigation Zone
from the Observations it gathers while running:

- **Moisture Gain per Liter** — how many moisture percentage points the Zone
  Moisture rises per litre applied, learned from Confirmed Watering Events.
- **Daily Drying Rate** — how many percentage points the Zone Moisture falls per
  day when no water is added, learned from the decline between observations.
- **Rain Efficiency** — moisture rise per millimetre of Observed Rain.
- bounded **Field Capacity** / **Wilting Point** estimates tracked from the
  highest and lowest moisture the zone actually reaches.

Every learner is a pure function (no Home Assistant dependency) so the maths can
be unit-tested directly, mirroring :mod:`engine` and :mod:`calibration`. Each
learner blends a new sample into the prior with an exponential moving average and
clamps the result to a safe range, so a single noisy reading can never produce a
nonsensical or unbounded value. The glue that captures samples from live state
lives in :mod:`learner`; the decision engine only ever consumes the bounded
result, and a manually configured value always wins over a learned one.
"""

from __future__ import annotations

from typing import Any

# Exponential-moving-average weight for a fresh sample. A low weight keeps the
# Learned Model stable: one odd reading nudges it only slightly.
SAMPLE_WEIGHT = 0.3
# Capacity/wilting extremes track the soil's envelope slowly so a transient
# spike or dropout does not redefine the band.
EXTREME_WEIGHT = 0.2

# Safe bounds for each learned quantity. Samples outside these ranges are
# discarded; blended results are clamped back inside them.
GAIN_MIN, GAIN_MAX = 0.05, 25.0  # moisture % per litre
DRYING_MIN, DRYING_MAX = 0.1, 60.0  # moisture % per day
RAIN_EFF_MIN, RAIN_EFF_MAX = 0.1, 30.0  # moisture % per mm
MOISTURE_MIN, MOISTURE_MAX = 0.0, 100.0

# Only accept drying samples spanning a sensible window, so a burst of readings
# (tiny dt) or a multi-day gap (sensor outage) never skews the Daily Drying Rate.
MIN_DRYING_HOURS = 0.25
MAX_DRYING_HOURS = 48.0


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into the inclusive ``[low, high]`` range."""
    return max(low, min(high, value))


def _ema(prior: float | None, sample: float, weight: float) -> float:
    """Blend ``sample`` into ``prior`` with the given EMA ``weight``."""
    if prior is None:
        return sample
    return (1.0 - weight) * prior + weight * sample


def _count(bookkeeping: dict[str, Any], key: str) -> int:
    """Read a sample counter from bookkeeping, defaulting to zero."""
    try:
        return int(bookkeeping.get(key, 0))
    except (TypeError, ValueError):
        return 0


def update_gain(
    current: float | None,
    bookkeeping: dict[str, Any],
    moisture_before: float | None,
    moisture_after: float | None,
    liters: float | None,
) -> tuple[float | None, dict[str, Any]]:
    """Learn Moisture Gain per Liter from one Confirmed Watering Event.

    The sample is ``(moisture_after - moisture_before) / liters``; it is ignored
    unless a positive volume produced a positive moisture rise.
    """
    bookkeeping = dict(bookkeeping)
    if (
        moisture_before is None
        or moisture_after is None
        or liters is None
        or liters <= 0
    ):
        return current, bookkeeping
    rise = moisture_after - moisture_before
    if rise <= 0:
        return current, bookkeeping
    sample = _clamp(rise / liters, GAIN_MIN, GAIN_MAX)
    updated = _clamp(_ema(current, sample, SAMPLE_WEIGHT), GAIN_MIN, GAIN_MAX)
    bookkeeping["gain_samples"] = _count(bookkeeping, "gain_samples") + 1
    return updated, bookkeeping


def update_drying(
    current: float | None,
    bookkeeping: dict[str, Any],
    moisture_before: float | None,
    moisture_after: float | None,
    hours: float | None,
) -> tuple[float | None, dict[str, Any]]:
    """Learn the Daily Drying Rate from a moisture decline over ``hours``.

    Only declines over a sensible time window count, and the rate is normalised
    to a per-day figure before being blended in.
    """
    bookkeeping = dict(bookkeeping)
    if (
        moisture_before is None
        or moisture_after is None
        or hours is None
        or not (MIN_DRYING_HOURS <= hours <= MAX_DRYING_HOURS)
    ):
        return current, bookkeeping
    decline = moisture_before - moisture_after
    if decline <= 0:
        return current, bookkeeping
    per_day = decline / hours * 24.0
    sample = _clamp(per_day, DRYING_MIN, DRYING_MAX)
    updated = _clamp(_ema(current, sample, SAMPLE_WEIGHT), DRYING_MIN, DRYING_MAX)
    bookkeeping["drying_samples"] = _count(bookkeeping, "drying_samples") + 1
    return updated, bookkeeping


def update_rain_efficiency(
    current: float | None,
    bookkeeping: dict[str, Any],
    moisture_before: float | None,
    moisture_after: float | None,
    rain_mm: float | None,
) -> tuple[float | None, dict[str, Any]]:
    """Learn Rain Efficiency (moisture rise per mm) from an Observed Rain event."""
    bookkeeping = dict(bookkeeping)
    if (
        moisture_before is None
        or moisture_after is None
        or rain_mm is None
        or rain_mm <= 0
    ):
        return current, bookkeeping
    rise = moisture_after - moisture_before
    if rise <= 0:
        return current, bookkeeping
    sample = _clamp(rise / rain_mm, RAIN_EFF_MIN, RAIN_EFF_MAX)
    updated = _clamp(
        _ema(current, sample, SAMPLE_WEIGHT), RAIN_EFF_MIN, RAIN_EFF_MAX
    )
    bookkeeping["rain_samples"] = _count(bookkeeping, "rain_samples") + 1
    return updated, bookkeeping


def update_capacity(
    field_capacity: float | None,
    wilting_point: float | None,
    bookkeeping: dict[str, Any],
    moisture: float | None,
) -> tuple[float | None, float | None, dict[str, Any]]:
    """Track bounded Field Capacity / Wilting Point from observed extremes.

    Field Capacity follows the highest moisture the zone reaches and Wilting
    Point the lowest; both ease slowly towards new extremes so a single spike or
    dropout cannot redefine the soil band.
    """
    bookkeeping = dict(bookkeeping)
    if moisture is None:
        return field_capacity, wilting_point, bookkeeping
    moisture = _clamp(moisture, MOISTURE_MIN, MOISTURE_MAX)

    if field_capacity is None or moisture > field_capacity:
        field_capacity = _ema(field_capacity, moisture, EXTREME_WEIGHT)
    if wilting_point is None or moisture < wilting_point:
        wilting_point = _ema(wilting_point, moisture, EXTREME_WEIGHT)

    # Never let the band invert; a degenerate equal band is harmless (it simply
    # reads as "not yet calibrated") and resolves once more evidence arrives.
    if (
        field_capacity is not None
        and wilting_point is not None
        and field_capacity < wilting_point
    ):
        field_capacity = wilting_point + 1.0

    if field_capacity is not None:
        field_capacity = _clamp(field_capacity, MOISTURE_MIN, MOISTURE_MAX)
    if wilting_point is not None:
        wilting_point = _clamp(wilting_point, MOISTURE_MIN, MOISTURE_MAX)
    bookkeeping["capacity_samples"] = _count(bookkeeping, "capacity_samples") + 1
    return field_capacity, wilting_point, bookkeeping
