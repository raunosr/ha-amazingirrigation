"""Tests for plant water-demand profiles shaping the target band."""

from __future__ import annotations

from custom_components.amazing_irrigation.demand import (
    DEFAULT_DEMAND_PROFILE,
    resolve_profile,
    target_band_for_profile,
)


def test_profiles_order_trigger_low_to_high() -> None:
    """Higher demand keeps the zone wetter (higher trigger fraction)."""
    low = target_band_for_profile(10.0, 50.0, "low")
    medium = target_band_for_profile(10.0, 50.0, "medium")
    high = target_band_for_profile(10.0, 50.0, "high")
    assert low.low < medium.low < high.low
    # medium = WP + 0.45*span = 10 + 18 = 28; high band = WP + 0.80*span = 42
    assert medium.low == 28.0
    assert medium.high == 42.0


def test_missing_or_invalid_calibration_returns_none() -> None:
    """No band without valid WP/FC so callers fall back to manual/default."""
    assert target_band_for_profile(None, 50.0, "medium") is None
    assert target_band_for_profile(10.0, None, "medium") is None
    assert target_band_for_profile(50.0, 50.0, "medium") is None
    assert target_band_for_profile(60.0, 50.0, "medium") is None


def test_hot_day_lifts_trigger() -> None:
    """Above the hot-day threshold the trigger rises; mild days are unchanged."""
    mild = target_band_for_profile(10.0, 50.0, "medium", air_temp_c=20.0)
    hot = target_band_for_profile(10.0, 50.0, "medium", air_temp_c=38.0)
    assert mild.low == 28.0
    assert hot.low > mild.low


def test_unknown_profile_defaults_to_medium() -> None:
    assert resolve_profile("bogus") == resolve_profile(DEFAULT_DEMAND_PROFILE)
    assert resolve_profile(None) == resolve_profile("medium")
