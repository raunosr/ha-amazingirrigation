"""Pure tests for the calibration helpers."""

from __future__ import annotations

import pytest

from custom_components.amazing_irrigation.calibration import (
    available_water_fraction,
    bounded_recommended_liters,
)


@pytest.mark.parametrize(
    ("current", "wilting", "capacity", "expected"),
    [
        (30.0, 20.0, 40.0, 0.5),
        (20.0, 20.0, 40.0, 0.0),
        (40.0, 20.0, 40.0, 1.0),
        (10.0, 20.0, 40.0, 0.0),  # below wilting clamps to 0
        (50.0, 20.0, 40.0, 1.0),  # above capacity clamps to 1
    ],
)
def test_available_water_fraction(current, wilting, capacity, expected):
    """Available water is the clamped position between the soil bounds."""
    assert available_water_fraction(current, wilting, capacity) == expected


@pytest.mark.parametrize(
    ("current", "wilting", "capacity"),
    [
        (None, 20.0, 40.0),
        (30.0, None, 40.0),
        (30.0, 20.0, None),
        (30.0, 40.0, 40.0),  # span <= 0
        (30.0, 50.0, 40.0),  # inverted bounds
    ],
)
def test_available_water_fraction_invalid(current, wilting, capacity):
    """Missing or inconsistent calibration yields None."""
    assert available_water_fraction(current, wilting, capacity) is None


def test_bounded_recommended_liters_uses_gain():
    """A known gain converts the deficit into liters within the cap."""
    # deficit 10%, gain 2 %/L -> 5 L, under the 30 L cap.
    assert bounded_recommended_liters(30.0, 40.0, 2.0, 30.0) == 5.0


def test_bounded_recommended_liters_capped():
    """Recommendation never exceeds the configured max liters."""
    # deficit 100%, gain 1 %/L -> 100 L, capped to 12 L.
    assert bounded_recommended_liters(0.0, 100.0, 1.0, 12.0) == 12.0


def test_bounded_recommended_liters_no_deficit():
    """Already at/above target needs no water."""
    assert bounded_recommended_liters(45.0, 40.0, 2.0, 30.0) == 0.0


def test_bounded_recommended_liters_unknown_falls_back_to_cap():
    """Unknown moisture or gain conservatively falls back to the cap."""
    assert bounded_recommended_liters(None, 40.0, 2.0, 30.0) == 30.0
    assert bounded_recommended_liters(30.0, 40.0, None, 30.0) == 30.0
