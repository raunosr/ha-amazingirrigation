"""Recursive joint estimator for the pure water-balance coefficients.

The estimator is deliberately free of Home Assistant imports.  It learns the
linear coefficient vector ``[eta_irr, eta_rain, k_et, drain_rate]`` from moisture
interval observations using recursive least squares while tracking field
capacity and wilting point as a separate observed moisture envelope.

Manual overrides are passed as ``overrides={"eta_irr": 1.2, ...}`` at
construction time or later via :meth:`JointEstimator.set_override`.  An
overridden value is held fixed, projected out of the regression update, returned
unchanged from :attr:`JointEstimator.params`, and reported with confidence 1.0.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from .waterbalance import (
    DRAIN_RATE_MAX,
    DRAIN_RATE_MIN,
    ETA_IRR_MAX,
    ETA_IRR_MIN,
    ETA_RAIN_MAX,
    ETA_RAIN_MIN,
    FIELD_CAPACITY_MAX,
    FIELD_CAPACITY_MIN,
    K_ET_MAX,
    K_ET_MIN,
    MIN_CAPACITY_GAP,
    MOISTURE_MAX,
    MOISTURE_MIN,
    WILTING_POINT_MAX,
    WILTING_POINT_MIN,
    Climate,
    WaterBalanceParams,
    default_params,
    et_demand,
)

COEFFICIENT_NAMES = ("eta_irr", "eta_rain", "k_et", "drain_rate")
ENVELOPE_NAMES = ("field_capacity", "wilting_point")
PARAMETER_NAMES = COEFFICIENT_NAMES + ENVELOPE_NAMES

# Recent data should dominate: observations and the FC/WP envelope are weighted so
# their influence halves over this many days, letting the model follow seasonal
# change while older history only sets the baseline.
DEFAULT_ADAPTATION_HALF_LIFE_DAYS = 30.0

_BOUNDS: dict[str, tuple[float, float]] = {
    "eta_irr": (ETA_IRR_MIN, ETA_IRR_MAX),
    "eta_rain": (ETA_RAIN_MIN, ETA_RAIN_MAX),
    "k_et": (K_ET_MIN, K_ET_MAX),
    "drain_rate": (DRAIN_RATE_MIN, DRAIN_RATE_MAX),
    "field_capacity": (FIELD_CAPACITY_MIN, FIELD_CAPACITY_MAX),
    "wilting_point": (WILTING_POINT_MIN, WILTING_POINT_MAX),
}
_DEFAULT_PRIOR_STD = np.array([6.0, 6.0, 1.0, 0.35], dtype=float)
_CONFIDENCE_STD_SCALE = {
    "eta_irr": 0.30,
    "eta_rain": 0.30,
    "k_et": 0.08,
    "drain_rate": 0.025,
}
_MAX_REGRESSOR = 1_000_000.0
_MAX_INTERVAL_HOURS = 24.0 * 30.0
_MAX_COVARIANCE = 1_000_000.0
_MIN_COVARIANCE = 1e-12
_EPSILON = 1e-12


@dataclass(frozen=True)
class EstimatorObservation:
    """One moisture interval consumed by :meth:`JointEstimator.fit`.

    ``theta_start`` and ``theta_end`` are moisture percentages.  ``dt`` is hours.
    Rain is ignored when ``protected_rain`` is true, matching the physics core's
    greenhouse/protected-zone behaviour.
    """

    theta_start: float
    theta_end: float
    dt: float
    liters: float = 0.0
    rain_mm: float = 0.0
    climate: Climate | None = None
    protected_rain: bool = False


class JointEstimator:
    """Recursive least-squares estimator for water-balance parameters.

    Args:
        prior_params: Initial bounded water-balance parameters.  If omitted, the
            loam defaults are used.
        prior_cov: Scalar, length-four vector, or 4x4 matrix covariance for
            ``[eta_irr, eta_rain, k_et, drain_rate]``.  Larger values trust data
            faster.
        forgetting: RLS forgetting factor in ``(0, 1]``.  Values below one make
            older observations fade.
        measurement_noise: Observation noise variance in moisture-% squared.
        process_noise: Small covariance added to free coefficients each update.
        envelope_alpha: EMA weight used to pull field capacity/wilting point
            toward the running observed high/low moisture envelope.  Used only
            when ``half_life_days`` disables time-based decay.
        half_life_days: Adaptation half-life in days.  Recent observations and
            the FC/WP envelope decay to half influence over this span so the
            model follows seasonal change; ``None`` (or non-positive) disables
            time-based forgetting and reverts to flat weighting.
        overrides: Optional mapping of parameter names to manual values.  Any of
            the four linear coefficients and/or ``field_capacity`` /
            ``wilting_point`` may be fixed.

    The :attr:`params` property returns a bounded :class:`WaterBalanceParams`.
    The :attr:`confidence` property returns ``dict[str, float]`` for the four
    linear coefficients, derived monotonically from posterior covariance
    diagonals with ``1.0`` meaning most certain.
    """

    def __init__(
        self,
        prior_params: WaterBalanceParams | None = None,
        *,
        prior_cov: float | Iterable[float] | np.ndarray | None = None,
        forgetting: float = 1.0,
        measurement_noise: float = 0.25,
        process_noise: float | Iterable[float] | np.ndarray = 1e-9,
        envelope_alpha: float = 0.05,
        half_life_days: float | None = DEFAULT_ADAPTATION_HALF_LIFE_DAYS,
        overrides: Mapping[str, float] | None = None,
    ) -> None:
        """Initialise the recursive estimator from bounded priors."""
        bounded = (prior_params or default_params()).clamped()
        self._b = np.array(
            [bounded.eta_irr, bounded.eta_rain, bounded.k_et, bounded.drain_rate],
            dtype=float,
        )
        self._cov = self._coerce_covariance(prior_cov)
        self._forgetting = _finite_clamped(forgetting, 1e-6, 1.0, default=1.0)
        self._measurement_noise = max(
            _EPSILON, _finite_clamped(measurement_noise, _EPSILON, 10_000.0, 0.25)
        )
        self._process_noise = self._coerce_process_noise(process_noise)
        self._envelope_alpha = _finite_clamped(envelope_alpha, 0.0, 1.0, 0.05)
        self._half_life_hours = (
            float(half_life_days) * 24.0
            if half_life_days is not None
            and np.isfinite(half_life_days)
            and half_life_days > 0.0
            else None
        )
        self._field_capacity = bounded.field_capacity
        self._wilting_point = bounded.wilting_point
        self._root_depth_mm = bounded.root_depth_mm
        self._crop_coefficient = bounded.crop_coefficient
        self._resid_var = 0.0
        self._fit_count = 0
        self._observed_high = bounded.field_capacity
        self._observed_low = bounded.wilting_point
        self._overrides: dict[str, float] = {}
        if overrides:
            for name, value in overrides.items():
                self.set_override(name, value)
        self._regularise()

    @property
    def params(self) -> WaterBalanceParams:
        """Current bounded parameters, with manual overrides taking precedence."""
        values = self._coefficient_values()
        field_capacity = self._override_or_value("field_capacity", self._field_capacity)
        wilting_point = self._override_or_value("wilting_point", self._wilting_point)
        return WaterBalanceParams(
            eta_irr=values[0],
            eta_rain=values[1],
            k_et=values[2],
            drain_rate=values[3],
            field_capacity=field_capacity,
            wilting_point=wilting_point,
            root_depth_mm=self._root_depth_mm,
            crop_coefficient=self._crop_coefficient,
        ).clamped()

    @property
    def confidence(self) -> dict[str, float]:
        """Return 0..1 confidence for each learned linear coefficient."""
        result: dict[str, float] = {}
        diag = np.diag(self._cov)
        for index, name in enumerate(COEFFICIENT_NAMES):
            if name in self._overrides:
                result[name] = 1.0
                continue
            variance = max(float(diag[index]), 0.0) if np.isfinite(diag[index]) else 0.0
            std = float(np.sqrt(variance))
            scale = _CONFIDENCE_STD_SCALE[name]
            result[name] = _finite_clamped(scale / (scale + std), 0.0, 1.0, 0.0)
        return result

    @property
    def covariance(self) -> np.ndarray:
        """A defensive copy of the 4x4 posterior covariance matrix."""
        return self._cov.copy()

    @property
    def residual_rmse(self) -> float:
        """Root-mean-square one-step prediction error (moisture %), 0 until fit."""
        return float(np.sqrt(max(0.0, self._resid_var)))

    @property
    def prediction_confidence(self) -> float:
        """0..1 fit-based confidence from residuals: small error -> high, drift -> low.

        A 1.5%-moisture step error roughly halves confidence. Stays 0 before any
        observation so a brand-new model reads as unproven, not overconfident.
        """
        if self._fit_count <= 0:
            return 0.0
        return _finite_clamped(1.5 / (1.5 + self.residual_rmse), 0.0, 1.0, 0.0)

    def set_override(self, name: str, value: float) -> None:
        """Fix a parameter at ``value`` for future updates and exposed params."""
        if name not in PARAMETER_NAMES:
            return
        low, high = _BOUNDS[name]
        bounded = _finite_clamped(value, low, high, default=low)
        self._overrides[name] = bounded
        if name in COEFFICIENT_NAMES:
            index = COEFFICIENT_NAMES.index(name)
            self._b[index] = bounded
            self._cov[index, :] = 0.0
            self._cov[:, index] = 0.0
        elif name == "field_capacity":
            self._field_capacity = bounded
            self._observed_high = bounded
        else:
            self._wilting_point = bounded
            self._observed_low = bounded
        self._enforce_capacity_gap()

    def clear_override(self, name: str) -> None:
        """Remove a manual override; unknown names are ignored."""
        self._overrides.pop(name, None)
        self._regularise()

    def observe_moisture(self, theta: float | None, dt_hours: float = 0.0) -> None:
        """Feed one moisture reading into the FC/WP envelope tracker.

        Rail readings (0 or 100 — typically an offline or saturated sensor) are
        rejected so they cannot pin the envelope.  The envelope tracks recent
        extremes with a fast attack toward new highs/lows and a time-decayed
        slow release, so stale extremes fade with the configured half-life and
        recent conditions dominate.  ``dt_hours`` is the time the reading
        represents and scales the release.
        """
        observed = _finite_float(theta)
        if observed is None or observed <= MOISTURE_MIN or observed >= MOISTURE_MAX:
            return
        release = self._envelope_release(dt_hours)
        if "field_capacity" not in self._overrides:
            if observed >= self._observed_high:
                self._observed_high = observed
            else:
                self._observed_high += release * (observed - self._observed_high)
            self._field_capacity = self._observed_high
        if "wilting_point" not in self._overrides:
            if observed <= self._observed_low:
                self._observed_low = observed
            else:
                self._observed_low += release * (observed - self._observed_low)
            self._wilting_point = self._observed_low
        self._enforce_capacity_gap()

    def seed_envelope(self, values: Iterable[float]) -> None:
        """Initialise the FC/WP envelope from a window of moisture observations.

        Used by the from-history bootstrap so a re-learn derives the envelope
        from the freshly fetched data rather than inheriting a previously
        learned (possibly polluted) field capacity / wilting point.  Rail and
        non-finite values are ignored.
        """
        clean = [
            value
            for value in (_finite_float(item) for item in values)
            if value is not None and MOISTURE_MIN < value < MOISTURE_MAX
        ]
        if not clean:
            return
        if "field_capacity" not in self._overrides:
            self._observed_high = max(clean)
            self._field_capacity = self._observed_high
        if "wilting_point" not in self._overrides:
            self._observed_low = min(clean)
            self._wilting_point = self._observed_low
        self._enforce_capacity_gap()

    def _envelope_release(self, dt_hours: float) -> float:
        """Release fraction for the envelope, time-scaled to the half-life."""
        elapsed = max(0.0, _finite_float(dt_hours) or 0.0)
        if elapsed <= 0.0:
            return 0.0
        if self._half_life_hours is None:
            return self._envelope_alpha
        return float(1.0 - 0.5 ** (elapsed / self._half_life_hours))

    def _effective_forgetting(self, hours: float) -> float:
        """Time-aware RLS forgetting: recent intervals weigh more."""
        base = self._forgetting
        if self._half_life_hours is None:
            return base
        elapsed = max(0.0, _finite_float(hours) or 0.0)
        decay = float(0.5 ** (elapsed / self._half_life_hours))
        return _finite_clamped(base * decay, 1e-6, 1.0, base)

    def update(
        self,
        *,
        theta_start: float,
        theta_end: float,
        dt: float,
        liters: float = 0.0,
        rain_mm: float = 0.0,
        climate: Climate | None = None,
        protected_rain: bool = False,
    ) -> WaterBalanceParams:
        """Fold one interval observation into the joint estimate.

        Bad, missing, non-finite, or numerically degenerate observations are
        ignored for the linear update but still allowed to update the moisture
        envelope when possible.  The method returns :attr:`params`.
        """
        try:
            self._update_linear(
                theta_start=theta_start,
                theta_end=theta_end,
                dt=dt,
                liters=liters,
                rain_mm=rain_mm,
                climate=climate,
                protected_rain=protected_rain,
            )
        except (ArithmeticError, OverflowError, TypeError, ValueError):
            pass
        self.observe_moisture(theta_start)
        self.observe_moisture(theta_end, dt_hours=dt)
        self._regularise()
        return self.params

    def fit(
        self, observations: Iterable[EstimatorObservation | Mapping[str, Any]]
    ) -> WaterBalanceParams:
        """Fold ordered interval observations and return the bounded estimate."""
        for observation in observations:
            self.update(
                theta_start=_observation_value(observation, "theta_start", None),
                theta_end=_observation_value(observation, "theta_end", None),
                dt=_observation_value(observation, "dt", 0.0),
                liters=_observation_value(observation, "liters", 0.0),
                rain_mm=_observation_value(observation, "rain_mm", 0.0),
                climate=_observation_value(observation, "climate", None),
                protected_rain=bool(
                    _observation_value(observation, "protected_rain", False)
                ),
            )
        return self.params

    fit_intervals = fit

    def _update_linear(
        self,
        *,
        theta_start: float,
        theta_end: float,
        dt: float,
        liters: float,
        rain_mm: float,
        climate: Climate | None,
        protected_rain: bool,
    ) -> None:
        start = _finite_float(theta_start)
        end = _finite_float(theta_end)
        if start is None or end is None:
            return
        theta0 = _finite_clamped(start, MOISTURE_MIN, MOISTURE_MAX, MOISTURE_MIN)
        theta1 = _finite_clamped(end, MOISTURE_MIN, MOISTURE_MAX, MOISTURE_MIN)
        hours = _finite_clamped(dt, 0.0, _MAX_INTERVAL_HOURS, 0.0)
        applied_liters = _finite_clamped(liters, 0.0, _MAX_REGRESSOR, 0.0)
        observed_rain = _finite_clamped(rain_mm, 0.0, _MAX_REGRESSOR, 0.0)
        rain_eff_mm = 0.0 if protected_rain else observed_rain

        current = self.params
        climate_value = (
            climate if isinstance(climate, Climate) or climate is None else None
        )
        et_base = et_demand(replace(current, k_et=1.0), climate_value, hours)
        et_base = _finite_clamped(et_base, 0.0, _MAX_REGRESSOR, 0.0)
        drain_indicator = max(0.0, theta0 - current.field_capacity) * hours
        drain_indicator = _finite_clamped(
            drain_indicator, 0.0, _MAX_REGRESSOR, 0.0
        )
        x = np.array(
            [applied_liters, rain_eff_mm, -et_base, -drain_indicator], dtype=float
        )
        if not np.all(np.isfinite(x)) or float(np.linalg.norm(x)) <= _EPSILON:
            return
        y = _finite_clamped(theta1 - theta0, -MOISTURE_MAX, MOISTURE_MAX, 0.0)

        fixed = np.array([name in self._overrides for name in COEFFICIENT_NAMES])
        free = ~fixed
        if not bool(np.any(free)):
            return
        x_free = x[free]
        if float(np.linalg.norm(x_free)) <= _EPSILON:
            return
        b = self._coefficient_values()
        y_free = y - float(np.dot(x[fixed], b[fixed])) if bool(np.any(fixed)) else y
        p_prior = self._cov[np.ix_(free, free)].copy()
        p_prior = p_prior / self._effective_forgetting(hours)
        process = np.diag(self._process_noise[free])
        p_prior = self._safe_matrix(p_prior + process, free_count=int(np.sum(free)))
        innovation_var = float(x_free @ p_prior @ x_free.T) + self._measurement_noise
        if not np.isfinite(innovation_var) or innovation_var <= _EPSILON:
            return
        residual = y_free - float(np.dot(x_free, self._b[free]))
        if not np.isfinite(residual):
            return

        gain = (p_prior @ x_free.T) / innovation_var
        self._b[free] = self._b[free] + gain * residual
        identity = np.eye(len(x_free), dtype=float)
        update_matrix = identity - np.outer(gain, x_free)
        p_next = (
            update_matrix @ p_prior @ update_matrix.T
            + self._measurement_noise * np.outer(gain, gain)
        )

        residual_after = y_free - float(np.dot(x_free, self._b[free]))
        if np.isfinite(residual_after):
            self._resid_var = 0.9 * self._resid_var + 0.1 * (residual_after**2)
            self._fit_count += 1
            excess = max(0.0, residual_after * residual_after - self._measurement_noise)
            if excess > 0.0:
                p_next += min(excess, MOISTURE_MAX**2) * np.outer(gain, gain) * 0.05

        self._cov[np.ix_(free, free)] = self._safe_matrix(
            p_next, free_count=int(np.sum(free))
        )
        for index, is_fixed in enumerate(fixed):
            if is_fixed:
                self._b[index] = self._overrides[COEFFICIENT_NAMES[index]]
                self._cov[index, :] = 0.0
                self._cov[:, index] = 0.0
        self._b = self._bounded_internal_coefficients(self._b)

    def _coefficient_values(self) -> np.ndarray:
        values = np.array(self._b, dtype=float)
        for index, name in enumerate(COEFFICIENT_NAMES):
            if name in self._overrides:
                values[index] = self._overrides[name]
        return values

    def _override_or_value(self, name: str, value: float) -> float:
        return self._overrides.get(name, value)

    def _coerce_covariance(
        self, prior_cov: float | Iterable[float] | np.ndarray | None
    ) -> np.ndarray:
        if prior_cov is None:
            return np.diag(_DEFAULT_PRIOR_STD**2)
        array = np.asarray(prior_cov, dtype=float)
        if array.ndim == 0:
            value = _finite_clamped(float(array), _MIN_COVARIANCE, _MAX_COVARIANCE, 1.0)
            return np.eye(4, dtype=float) * value
        if array.shape == (4,):
            diag = [
                _finite_clamped(value, _MIN_COVARIANCE, _MAX_COVARIANCE, 1.0)
                for value in array
            ]
            return np.diag(diag)
        if array.shape == (4, 4) and np.all(np.isfinite(array)):
            return self._safe_matrix(array, free_count=4)
        return np.diag(_DEFAULT_PRIOR_STD**2)

    def _coerce_process_noise(
        self, process_noise: float | Iterable[float] | np.ndarray
    ) -> np.ndarray:
        array = np.asarray(process_noise, dtype=float)
        if array.ndim == 0:
            value = _finite_clamped(float(array), 0.0, _MAX_COVARIANCE, 1e-9)
            return np.full(4, value, dtype=float)
        if array.shape == (4,):
            return np.array(
                [
                    _finite_clamped(value, 0.0, _MAX_COVARIANCE, 1e-9)
                    for value in array
                ],
                dtype=float,
            )
        return np.full(4, 1e-9, dtype=float)

    def _regularise(self) -> None:
        self._b = self._bounded_internal_coefficients(self._b)
        self._cov = self._safe_matrix(self._cov, free_count=4)
        for index, name in enumerate(COEFFICIENT_NAMES):
            if name in self._overrides:
                self._b[index] = self._overrides[name]
                self._cov[index, :] = 0.0
                self._cov[:, index] = 0.0
        self._enforce_capacity_gap()

    def _safe_matrix(self, matrix: np.ndarray, *, free_count: int) -> np.ndarray:
        if matrix.shape != (free_count, free_count) or not np.all(np.isfinite(matrix)):
            return np.eye(free_count, dtype=float)
        safe = (matrix + matrix.T) * 0.5
        try:
            eigenvalues, eigenvectors = np.linalg.eigh(safe)
        except np.linalg.LinAlgError:
            return np.eye(free_count, dtype=float)
        eigenvalues = np.clip(eigenvalues, _MIN_COVARIANCE, _MAX_COVARIANCE)
        safe = (eigenvectors * eigenvalues) @ eigenvectors.T
        safe = (safe + safe.T) * 0.5
        diag = np.clip(np.diag(safe), _MIN_COVARIANCE, _MAX_COVARIANCE)
        np.fill_diagonal(safe, diag)
        return safe

    def _bounded_internal_coefficients(self, values: np.ndarray) -> np.ndarray:
        bounded = np.array(values, dtype=float)
        for index, name in enumerate(COEFFICIENT_NAMES):
            low, high = _BOUNDS[name]
            span = high - low
            bounded[index] = _finite_clamped(
                bounded[index], low - 2.0 * span, high + 2.0 * span, default=low
            )
        return bounded

    def _enforce_capacity_gap(self) -> None:
        self._field_capacity = _finite_clamped(
            self._field_capacity,
            FIELD_CAPACITY_MIN,
            FIELD_CAPACITY_MAX,
            FIELD_CAPACITY_MIN,
        )
        self._wilting_point = _finite_clamped(
            self._wilting_point,
            WILTING_POINT_MIN,
            WILTING_POINT_MAX,
            WILTING_POINT_MIN,
        )
        if self._field_capacity - self._wilting_point >= MIN_CAPACITY_GAP:
            return
        if (
            "field_capacity" in self._overrides
            and "wilting_point" not in self._overrides
        ):
            self._wilting_point = _finite_clamped(
                self._field_capacity - MIN_CAPACITY_GAP,
                WILTING_POINT_MIN,
                WILTING_POINT_MAX,
                WILTING_POINT_MIN,
            )
        else:
            self._field_capacity = _finite_clamped(
                self._wilting_point + MIN_CAPACITY_GAP,
                FIELD_CAPACITY_MIN,
                FIELD_CAPACITY_MAX,
                FIELD_CAPACITY_MAX,
            )
            if self._field_capacity - self._wilting_point < MIN_CAPACITY_GAP:
                self._wilting_point = _finite_clamped(
                    self._field_capacity - MIN_CAPACITY_GAP,
                    WILTING_POINT_MIN,
                    WILTING_POINT_MAX,
                    WILTING_POINT_MIN,
                )


def _observation_value(
    observation: EstimatorObservation | Mapping[str, Any], name: str, default: Any
) -> Any:
    if isinstance(observation, Mapping):
        return observation.get(name, default)
    return getattr(observation, name, default)


def _finite_float(value: float | None) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(result):
        return None
    return result


def _finite_clamped(value: float, low: float, high: float, default: float) -> float:
    result = _finite_float(value)
    if result is None:
        return default
    return float(np.clip(result, low, high))
