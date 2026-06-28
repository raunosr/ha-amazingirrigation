"""Tests for the pure auto-learning maths."""

from __future__ import annotations

from custom_components.amazing_irrigation.learning import (
    DRYING_MAX,
    GAIN_MAX,
    GAIN_MIN,
    RAIN_EFF_MAX,
    update_capacity,
    update_drying,
    update_gain,
    update_rain_efficiency,
)


def test_gain_first_sample_is_the_observed_ratio():
    """The first gain sample is the raw moisture rise per litre."""
    gain, bk = update_gain(None, {}, moisture_before=20.0, moisture_after=30.0,
                           liters=5.0)
    assert gain == 2.0
    assert bk["gain_samples"] == 1


def test_gain_blends_subsequent_samples_with_ema():
    """A second sample nudges the prior rather than replacing it."""
    gain, _ = update_gain(2.0, {"gain_samples": 1}, 20.0, 26.0, 2.0)
    # sample = 3.0, EMA(2.0, 3.0, 0.3) = 2.3
    assert round(gain, 3) == 2.3


def test_gain_ignores_non_positive_rise_or_volume():
    """No rise, or no volume, leaves the learned gain untouched."""
    assert update_gain(2.0, {}, 30.0, 30.0, 5.0)[0] == 2.0
    assert update_gain(2.0, {}, 20.0, 30.0, 0.0)[0] == 2.0
    assert update_gain(2.0, {}, 20.0, 30.0, None)[0] == 2.0


def test_gain_is_clamped_to_safe_bounds():
    """A huge ratio is clamped to the maximum safe gain."""
    gain, _ = update_gain(None, {}, 0.0, 100.0, 0.1)  # ratio 1000
    assert gain == GAIN_MAX
    gain, _ = update_gain(None, {}, 0.0, 0.001, 1000.0)  # tiny ratio
    assert gain == GAIN_MIN


def test_drying_normalises_to_per_day():
    """A decline over 12 hours becomes a per-day rate."""
    rate, bk = update_drying(None, {}, moisture_before=40.0, moisture_after=35.0,
                             hours=12.0)
    assert rate == 10.0  # 5% over 12h -> 10%/day
    assert bk["drying_samples"] == 1


def test_drying_ignores_out_of_window_or_non_decline():
    """Samples outside the time window, or that rose, are ignored."""
    assert update_drying(5.0, {}, 40.0, 35.0, 0.1)[0] == 5.0  # too short
    assert update_drying(5.0, {}, 40.0, 35.0, 100.0)[0] == 5.0  # too long
    assert update_drying(5.0, {}, 35.0, 40.0, 12.0)[0] == 5.0  # rose


def test_drying_is_clamped():
    """An implausibly fast dry-down is clamped to the maximum."""
    rate, _ = update_drying(None, {}, 100.0, 0.0, 0.25)
    assert rate == DRYING_MAX


def test_rain_efficiency_is_rise_per_mm():
    """Rain efficiency is the moisture rise per millimetre of rain."""
    eff, bk = update_rain_efficiency(None, {}, 20.0, 26.0, rain_mm=3.0)
    assert eff == 2.0
    assert bk["rain_samples"] == 1


def test_rain_efficiency_clamped_and_guarded():
    """No rain, or no rise, is ignored; large ratios are clamped."""
    assert update_rain_efficiency(2.0, {}, 20.0, 26.0, 0.0)[0] == 2.0
    assert update_rain_efficiency(2.0, {}, 26.0, 20.0, 3.0)[0] == 2.0
    assert update_rain_efficiency(None, {}, 0.0, 100.0, 0.1)[0] == RAIN_EFF_MAX


def test_capacity_tracks_high_and_low_extremes():
    """Field Capacity follows highs and Wilting Point follows lows."""
    fc, wp, bk = update_capacity(None, None, {}, 50.0)
    assert fc == 50.0 and wp == 50.0
    fc, wp, bk = update_capacity(fc, wp, bk, 80.0)  # new high
    assert fc > 50.0 and wp == 50.0
    fc, wp, bk = update_capacity(fc, wp, bk, 10.0)  # new low
    assert wp < 50.0


def test_capacity_never_inverts_band():
    """An inverted input band is corrected so Field Capacity stays above WP."""
    # Feed a moisture that touches neither extreme so only the guard acts.
    fc, wp, _ = update_capacity(20.0, 40.0, {}, 30.0)
    assert fc > wp


def test_capacity_ignores_missing_moisture():
    """A missing reading leaves the band unchanged."""
    fc, wp, bk = update_capacity(60.0, 20.0, {"capacity_samples": 3}, None)
    assert (fc, wp) == (60.0, 20.0)
    assert bk["capacity_samples"] == 3
