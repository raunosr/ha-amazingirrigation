"""Plant water-demand profiles that shape the predictive target band.

A demand profile is a coarse stand-in for plant species: it sets where, between
the soil's Wilting Point (WP) and Field Capacity (FC), the controller should
keep moisture, and how much margin to add on hot days.  It only shapes the
:class:`TargetBand`; the soil water-balance physics is unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .controller import TargetBand
from .waterbalance import MOISTURE_MAX, MOISTURE_MIN

DEMAND_PROFILES = ("low", "medium", "high")
DEFAULT_DEMAND_PROFILE = "medium"

# Hot-day margin: above this air temperature the trigger is lifted, by
# ``HOT_DAY_MARGIN_PER_C`` of available-water fraction per °C, capped.
HOT_DAY_THRESHOLD_C = 28.0
HOT_DAY_MARGIN_PER_C = 0.01
HOT_DAY_MARGIN_MAX = 0.15


@dataclass(frozen=True)
class DemandProfile:
    """Available-water fractions (WP→FC) defining a zone's target band."""

    trigger_fraction: float
    band_width: float


_PROFILES: Mapping[str, DemandProfile] = {
    "low": DemandProfile(trigger_fraction=0.35, band_width=0.15),
    "medium": DemandProfile(trigger_fraction=0.50, band_width=0.15),
    "high": DemandProfile(trigger_fraction=0.65, band_width=0.15),
}


def resolve_profile(profile: str | None) -> DemandProfile:
    """Return the demand profile for a name, defaulting to medium."""
    if isinstance(profile, str):
        return _PROFILES.get(profile.strip().lower(), _PROFILES[DEFAULT_DEMAND_PROFILE])
    return _PROFILES[DEFAULT_DEMAND_PROFILE]


def _hot_day_margin(air_temp_c: float | None) -> float:
    """Extra available-water fraction added when it is hotter than threshold."""
    if air_temp_c is None or air_temp_c <= HOT_DAY_THRESHOLD_C:
        return 0.0
    margin = (air_temp_c - HOT_DAY_THRESHOLD_C) * HOT_DAY_MARGIN_PER_C
    return min(HOT_DAY_MARGIN_MAX, margin)


def target_band_for_profile(
    wilting_point: float | None,
    field_capacity: float | None,
    profile: str | None,
    *,
    air_temp_c: float | None = None,
) -> TargetBand | None:
    """Derive a target band from WP/FC and a demand profile.

    Returns ``None`` when calibration is missing or invalid (FC must exceed WP),
    so callers fall back to the manual/default band. The trigger and band high
    are placed as fractions of available water and lifted by a hot-day margin.
    """
    if wilting_point is None or field_capacity is None:
        return None
    if field_capacity <= wilting_point:
        return None
    span = field_capacity - wilting_point
    spec = resolve_profile(profile)
    low_frac = min(1.0, spec.trigger_fraction + _hot_day_margin(air_temp_c))
    high_frac = min(1.0, low_frac + spec.band_width)
    low = wilting_point + low_frac * span
    high = wilting_point + high_frac * span
    low = max(MOISTURE_MIN, min(MOISTURE_MAX, low))
    high = max(low, min(MOISTURE_MAX, high))
    return TargetBand(low=low, high=high)
