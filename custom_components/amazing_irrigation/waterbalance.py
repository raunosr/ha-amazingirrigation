"""Pure soil water-balance physics for one irrigation zone.

The model advances a zone moisture estimate in percent over discrete intervals:

``theta_next = theta + irrigation + rain - evapotranspiration - drainage``

It is deliberately free of Home Assistant imports so prediction, calibration, and
UI explanations can exercise the maths directly in unit tests.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

MOISTURE_MIN, MOISTURE_MAX = 0.0, 100.0

ETA_IRR_MIN, ETA_IRR_MAX = 0.01, 25.0  # moisture % per litre
ETA_RAIN_MIN, ETA_RAIN_MAX = 0.01, 30.0  # moisture % per mm
K_ET_MIN, K_ET_MAX = 0.01, 3.0
DRAIN_RATE_MIN, DRAIN_RATE_MAX = 0.0, 1.0  # fraction of excess per hour
FIELD_CAPACITY_MIN, FIELD_CAPACITY_MAX = 5.0, 100.0
WILTING_POINT_MIN, WILTING_POINT_MAX = 0.0, 95.0
MIN_CAPACITY_GAP = 1.0

MISSING_CLIMATE_ET_PER_HOUR = 0.04
ET_MAX_PER_HOUR = 3.0
DEFAULT_HUMIDITY_PCT = 65.0

# Optional FAO-56 reference-ET grounding. When a root-zone depth is known the ET0
# in mm/day is converted to moisture-%/h via depth; a crop coefficient (Kc) scales
# it. Both default to "unset" so the legacy VPD heuristic stays the fallback.
KC_MIN, KC_MAX = 0.2, 1.5
ROOT_DEPTH_MIN, ROOT_DEPTH_MAX = 20.0, 2000.0  # mm
DEFAULT_IRRIG_EFFICIENCY = 0.8  # fraction of applied water reaching the root zone
KC_BY_PROFILE = {"low": 0.55, "medium": 0.85, "high": 1.1}


@dataclass(frozen=True)
class Climate:
    """Weather inputs that drive evapotranspiration for an interval."""

    air_temp_c: float | None
    air_humidity_pct: float | None
    wind_ms: float | None = None
    solar: float | None = None


@dataclass(frozen=True)
class WaterBalanceParams:
    """Bounded soil water-balance parameters for one zone."""

    eta_irr: float
    eta_rain: float
    k_et: float
    drain_rate: float
    field_capacity: float
    wilting_point: float
    root_depth_mm: float | None = None
    crop_coefficient: float | None = None

    def clamped(self) -> WaterBalanceParams:
        """Return a copy with every parameter inside its safe range."""
        field_capacity = _clamp(
            self.field_capacity, FIELD_CAPACITY_MIN, FIELD_CAPACITY_MAX
        )
        wilting_point = _clamp(self.wilting_point, WILTING_POINT_MIN, WILTING_POINT_MAX)
        if field_capacity <= wilting_point:
            field_capacity = _clamp(
                wilting_point + MIN_CAPACITY_GAP,
                FIELD_CAPACITY_MIN,
                FIELD_CAPACITY_MAX,
            )
            if field_capacity <= wilting_point:
                wilting_point = _clamp(
                    field_capacity - MIN_CAPACITY_GAP,
                    WILTING_POINT_MIN,
                    WILTING_POINT_MAX,
                )
        return replace(
            self,
            eta_irr=_clamp(self.eta_irr, ETA_IRR_MIN, ETA_IRR_MAX),
            eta_rain=_clamp(self.eta_rain, ETA_RAIN_MIN, ETA_RAIN_MAX),
            k_et=_clamp(self.k_et, K_ET_MIN, K_ET_MAX),
            drain_rate=_clamp(self.drain_rate, DRAIN_RATE_MIN, DRAIN_RATE_MAX),
            field_capacity=field_capacity,
            wilting_point=wilting_point,
            root_depth_mm=(
                _clamp(self.root_depth_mm, ROOT_DEPTH_MIN, ROOT_DEPTH_MAX)
                if self.root_depth_mm is not None
                else None
            ),
            crop_coefficient=(
                _clamp(self.crop_coefficient, KC_MIN, KC_MAX)
                if self.crop_coefficient is not None
                else None
            ),
        )


@dataclass(frozen=True)
class StepResult:
    """Result of one water-balance step."""

    theta_next: float
    terms: dict[str, float]


@dataclass(frozen=True)
class BalanceInterval:
    """Inputs for one interval consumed by :func:`simulate`."""

    dt: float
    liters: float = 0.0
    rain_mm: float = 0.0
    climate: Climate | None = None
    protected_rain: bool = False


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp finite ``value`` into inclusive ``[low, high]`` bounds."""
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return low
    if not np.isfinite(as_float):
        return low
    return float(np.clip(as_float, low, high))


def _nonnegative(value: float | None) -> float:
    """Return ``value`` as a finite non-negative float."""
    if value is None:
        return 0.0
    return max(0.0, _clamp(value, 0.0, float("inf")))


def area_eta(
    area_m2: float, root_depth_mm: float, efficiency: float = DEFAULT_IRRIG_EFFICIENCY
) -> tuple[float, float]:
    """Derive physical (eta_irr, eta_rain) from zone geometry.

    Moisture is volumetric percent of the root zone. Applying ``D`` mm of water
    raises moisture by ``D / root_depth_mm * 100``. One litre over ``A`` m^2 equals
    ``1/A`` mm, and 1 mm of rain equals one full mm. Hence:

    - ``eta_rain = 100 * eff / root_depth_mm`` (%/mm)
    - ``eta_irr  = 100 * eff / (area * root_depth_mm)`` (%/litre)

    so ``eta_rain / eta_irr = area`` -- the two efficiencies are one coupled value.
    Bounds keep degenerate geometry safe.
    """
    area = max(0.1, float(area_m2))
    depth = _clamp(root_depth_mm, ROOT_DEPTH_MIN, ROOT_DEPTH_MAX)
    eff = _clamp(efficiency, 0.1, 1.0)
    eta_rain = _clamp(100.0 * eff / depth, ETA_RAIN_MIN, ETA_RAIN_MAX)
    eta_irr = _clamp(100.0 * eff / (area * depth), ETA_IRR_MIN, ETA_IRR_MAX)
    return eta_irr, eta_rain


def default_params(
    soil_type: str = "loam",
    *,
    area_m2: float | None = None,
    root_depth_mm: float | None = None,
    demand_profile: str | None = None,
) -> WaterBalanceParams:
    """Return conservative soil-type priors for a new zone.

    Sandy soils have lower field capacity and faster drainage, loam is the
    balanced default, and clay retains more water while draining slowly.
    Unknown soil types fall back to loam. When ``area_m2`` is given, the
    eta priors are replaced by geometry-derived values (using ``root_depth_mm``
    or a 200 mm default), coupling irrigation and rain efficiency. A demand
    profile attaches a crop coefficient for FAO-56 reference ET.
    """
    priors = {
        "sand": WaterBalanceParams(
            eta_irr=1.6,
            eta_rain=1.1,
            k_et=0.9,
            drain_rate=0.18,
            field_capacity=30.0,
            wilting_point=10.0,
        ),
        "loam": WaterBalanceParams(
            eta_irr=1.2,
            eta_rain=0.9,
            k_et=0.75,
            drain_rate=0.08,
            field_capacity=45.0,
            wilting_point=18.0,
        ),
        "clay": WaterBalanceParams(
            eta_irr=0.9,
            eta_rain=0.75,
            k_et=0.55,
            drain_rate=0.03,
            field_capacity=55.0,
            wilting_point=28.0,
        ),
    }
    base = priors.get(soil_type.strip().lower(), priors["loam"])
    depth = root_depth_mm if root_depth_mm is not None else 200.0
    kc = KC_BY_PROFILE.get((demand_profile or "").strip().lower())
    if area_m2 is not None and area_m2 > 0:
        eta_irr, eta_rain = area_eta(area_m2, depth)
        base = replace(
            base,
            eta_irr=eta_irr,
            eta_rain=eta_rain,
            root_depth_mm=depth,
            crop_coefficient=kc,
        )
    elif kc is not None:
        base = replace(base, crop_coefficient=kc)
    return base.clamped()


def et_demand(
    params: WaterBalanceParams, climate: Climate | None, dt: float
) -> float:
    """Estimate evapotranspiration loss in moisture-% for an interval.

    The formula is intentionally light-weight and VPD-style. For known air
    temperature, saturation vapour pressure is estimated with Tetens' equation,
    ``svp = 0.6108 * exp(17.27 * T / (T + 237.3))`` kPa. Vapour-pressure
    deficit is ``svp * (1 - RH/100)`` after humidity is clamped to 0-100%.
    Hourly ET then grows with VPD and warm temperatures, with small wind and
    solar multipliers, before being scaled by ``params.k_et`` and ``dt``. If
    temperature is unavailable, a conservative default loss is used so moisture
    still ages down. The result is finite, non-negative, and bounded.
    """
    bounded = params.clamped()
    hours = _nonnegative(dt)
    if hours <= 0.0:
        return 0.0
    if climate is None or climate.air_temp_c is None:
        loss = bounded.k_et * MISSING_CLIMATE_ET_PER_HOUR * hours
        return _clamp(loss, 0.0, ET_MAX_PER_HOUR * hours)

    temp_c = _clamp(climate.air_temp_c, -30.0, 60.0)
    humidity_pct = DEFAULT_HUMIDITY_PCT
    if climate.air_humidity_pct is not None:
        humidity_pct = _clamp(climate.air_humidity_pct, 0.0, 100.0)

    svp_kpa = 0.6108 * float(np.exp((17.27 * temp_c) / (temp_c + 237.3)))
    vpd_kpa = max(0.0, svp_kpa * (1.0 - humidity_pct / 100.0))

    # FAO-56 grounding: with a known root depth, convert reference ET0 (mm/day)
    # to moisture-%/h via depth and crop coefficient. The depth conversion also
    # couples ET to the same geometry as irrigation/rain efficiency.
    if bounded.root_depth_mm is not None:
        et0_mm_day = _et0_fao56(temp_c, vpd_kpa, svp_kpa, climate.wind_ms, climate.solar)
        kc = bounded.crop_coefficient if bounded.crop_coefficient is not None else 0.85
        pct_per_hour = (et0_mm_day * kc) * 100.0 / bounded.root_depth_mm / 24.0
        loss = bounded.k_et * pct_per_hour * hours
        return _clamp(loss, 0.0, ET_MAX_PER_HOUR * hours)

    hourly = 0.03 + 0.18 * vpd_kpa + 0.004 * max(0.0, temp_c)

    wind_factor = 1.0
    if climate.wind_ms is not None:
        wind_factor += 0.06 * _clamp(climate.wind_ms, 0.0, 15.0)

    solar_factor = 1.0
    if climate.solar is not None:
        solar_factor += 0.35 * _clamp(climate.solar, 0.0, 800.0) / 800.0

    loss = bounded.k_et * hourly * wind_factor * solar_factor * hours
    return _clamp(loss, 0.0, ET_MAX_PER_HOUR * hours)


def _et0_fao56(
    temp_c: float,
    vpd_kpa: float,
    svp_kpa: float,
    wind_ms: float | None,
    solar: float | None,
) -> float:
    """FAO-56 Penman-Monteith reference ET0 (mm/day), Hargreaves-style fallback.

    Uses the standard short-grass formulation. Net radiation is approximated from
    measured solar (W/m^2 -> MJ/m^2/day, 77% net); when solar is missing it is
    estimated from temperature so the term degrades gracefully. Wind defaults to a
    light 2 m/s breeze. Result is bounded to a sane 0-15 mm/day band.
    """
    gamma = 0.066  # psychrometric constant, kPa/C
    delta = 4098.0 * svp_kpa / ((temp_c + 237.3) ** 2)  # slope of SVP curve
    u2 = _clamp(wind_ms if wind_ms is not None else 2.0, 0.1, 15.0)
    if solar is not None:
        rs_mj = _clamp(solar, 0.0, 1200.0) * 0.0864  # W/m^2 -> MJ/m^2/day
        rn = 0.77 * rs_mj
    else:
        rn = max(0.0, 0.1 * max(0.0, temp_c) + 4.0 * vpd_kpa)
    numerator = 0.408 * delta * rn + gamma * (900.0 / (temp_c + 273.0)) * u2 * vpd_kpa
    denominator = delta + gamma * (1.0 + 0.34 * u2)
    if denominator <= 0:
        return 0.0
    return _clamp(numerator / denominator, 0.0, 15.0)


def _drainage(params: WaterBalanceParams, theta: float, dt: float) -> float:
    """Return drainage loss in moisture-% for moisture above field capacity."""
    hours = _nonnegative(dt)
    if hours <= 0.0 or theta <= params.field_capacity:
        return 0.0
    excess = theta - params.field_capacity
    fraction = _clamp(params.drain_rate * hours, 0.0, 1.0)
    return min(excess, excess * fraction)


def step(
    params: WaterBalanceParams,
    theta: float,
    *,
    liters: float = 0.0,
    rain_mm: float = 0.0,
    climate: Climate | None = None,
    dt: float,
    protected_rain: bool = False,
) -> StepResult:
    """Advance zone moisture by one interval and explain each contribution."""
    bounded = params.clamped()
    theta_start = _clamp(theta, MOISTURE_MIN, MOISTURE_MAX)
    irrigation = bounded.eta_irr * _nonnegative(liters)
    rain = 0.0 if protected_rain else bounded.eta_rain * _nonnegative(rain_mm)
    et = et_demand(bounded, climate, dt)
    drainage = _drainage(bounded, theta_start, dt)
    theta_next = _clamp(
        theta_start + irrigation + rain - et - drainage,
        MOISTURE_MIN,
        MOISTURE_MAX,
    )
    return StepResult(
        theta_next=theta_next,
        terms={
            "irrigation": irrigation,
            "rain": rain,
            "et": et,
            "drainage": drainage,
        },
    )


def _interval_value(
    interval: BalanceInterval | Mapping[str, Any], name: str, default: Any
) -> Any:
    """Read an interval field from a dataclass-like object or mapping."""
    if isinstance(interval, Mapping):
        return interval.get(name, default)
    return getattr(interval, name, default)


def simulate(
    params: WaterBalanceParams,
    theta0: float,
    intervals: Iterable[BalanceInterval | Mapping[str, Any]],
) -> list[StepResult]:
    """Run ordered interval inputs and return one explained result per step."""
    theta = _clamp(theta0, MOISTURE_MIN, MOISTURE_MAX)
    results: list[StepResult] = []
    for interval in intervals:
        result = step(
            params,
            theta,
            liters=_interval_value(interval, "liters", 0.0),
            rain_mm=_interval_value(interval, "rain_mm", 0.0),
            climate=_interval_value(interval, "climate", None),
            dt=_interval_value(interval, "dt", 0.0),
            protected_rain=bool(_interval_value(interval, "protected_rain", False)),
        )
        results.append(result)
        theta = result.theta_next
    return results
