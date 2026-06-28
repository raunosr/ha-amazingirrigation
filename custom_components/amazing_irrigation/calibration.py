"""Pure calibration helpers for visible, bounded Learned Recommendations.

This slice collects calibration evidence but never lets it change watering
behaviour automatically. The functions here are pure (no Home Assistant
dependency) so the bounded-recommendation maths can be tested directly.

Field Capacity and Wilting Point describe a zone's soil: Field Capacity is the
moisture level at which soil holds all the water it usefully can, and Wilting
Point is the level below which plants cannot extract water. Available Water is
where the current Zone Moisture sits between those two bounds.
"""

from __future__ import annotations


def available_water_fraction(
    current: float | None,
    wilting_point: float | None,
    field_capacity: float | None,
) -> float | None:
    """Fraction (0..1) of plant-available water at the current moisture.

    Returns ``None`` when calibration is missing or invalid (e.g. capacity not
    above wilting point). The result is clamped to ``[0, 1]`` so readings
    outside the calibrated band never produce nonsensical values.
    """
    if current is None or wilting_point is None or field_capacity is None:
        return None
    span = field_capacity - wilting_point
    if span <= 0:
        return None
    fraction = (current - wilting_point) / span
    return max(0.0, min(1.0, fraction))


def bounded_recommended_liters(
    current: float | None,
    target_moisture: float | None,
    gain_per_liter: float | None,
    max_liters: float,
) -> float:
    """Liters to reach the target moisture, always bounded by safety limits.

    A Learned Recommendation must never exceed the zone's configured
    ``max_liters`` and is never negative. When the moisture deficit or the
    moisture gain per liter is unknown, the recommendation falls back to the
    safety cap so it stays conservative and explainable.
    """
    cap = max(0.0, max_liters)
    if current is None or target_moisture is None:
        return cap
    deficit = target_moisture - current
    if deficit <= 0:
        return 0.0
    if gain_per_liter and gain_per_liter > 0:
        liters = deficit / gain_per_liter
    else:
        liters = cap
    return max(0.0, min(liters, cap))
