"""Persistent per-zone live state for Amazing Irrigation.

The config entry's options describe how a zone is *set up*. Once running, a zone
also has **live tunables** the user can change from the device page (Target
Moisture, Max Liters, whether the zone and its learning are enabled, and two
schedule slots), plus values the integration **learns** over time and a running
**Total Watering Volume**. Persisting those in the config entry would force a
full reload on every slider drag, so they live here instead, in a small
``homeassistant.helpers.storage.Store`` keyed by zone.

The pure helpers (seeding, bounds, (de)serialisation) take plain dicts so they
can be unit-tested without Home Assistant; only :class:`ZoneStateStore` touches
the Store I/O. Initial values seed from the config-entry options the first time a
zone is seen; thereafter this store is the live source of truth.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DEFAULT_MAX_LITERS,
    DEFAULT_MIN_APPLICATION,
    DEFAULT_RAIN_FRACTION,
    DEFAULT_SCHEDULE_TIME,
    DEFAULT_SOIL_TYPE,
    DOMAIN,
    STORAGE_VERSION,
)
from .waterbalance import (
    MISSING_CLIMATE_ET_PER_HOUR,
    WaterBalanceParams,
    default_params,
)
from .zone import ZoneConfig

# Storage key suffix; the full key is scoped per config entry so multiple
# entries (should they ever exist) never share learned state.
STORAGE_KEY_FORMAT = f"{DOMAIN}.{{entry_id}}.zone_state"


def clamp_percent(value: float | None) -> float | None:
    """Clamp a moisture-style percentage to ``[0, 100]`` (``None`` passes through)."""
    if value is None:
        return None
    return max(0.0, min(100.0, float(value)))


def normalize_time(value: str | None) -> str | None:
    """Return a valid ``HH:MM`` string, or ``None`` when unparseable."""
    if not value:
        return None
    parts = str(value).strip().split(":")
    if len(parts) < 2:
        return None
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return f"{hour:02d}:{minute:02d}"
    return None


@dataclass
class ZoneState:
    """A single zone's persisted, live-editable state.

    ``schedule_1``/``schedule_2`` are the two independently toggleable schedule
    slots surfaced as native entities. Learned values are ``None`` until the
    learning engine has enough evidence. ``total_liters`` is the cumulative
    Confirmed Watering Volume applied to the zone.
    """

    zone_id: str
    # Live tunables (seeded from the config-entry options).
    target_moisture: float | None = None
    max_liters: float = DEFAULT_MAX_LITERS
    enabled: bool = True
    learning_enabled: bool = False
    target_mode: str = "manual"
    demand_profile: str = "medium"
    soil_type: str = DEFAULT_SOIL_TYPE
    sensor_depth_mm: float | None = None
    rain_fraction: float = DEFAULT_RAIN_FRACTION
    min_application: float = DEFAULT_MIN_APPLICATION
    # Two schedule slots, each independently active.
    schedule_1_time: str | None = DEFAULT_SCHEDULE_TIME
    schedule_1_active: bool = True
    schedule_2_time: str | None = DEFAULT_SCHEDULE_TIME
    schedule_2_active: bool = False
    # Learned parameters (filled by the learning engine over time).
    learned_gain_per_liter: float | None = None
    learned_drying_rate: float | None = None
    learned_rain_efficiency: float | None = None
    learned_field_capacity: float | None = None
    learned_wilting_point: float | None = None
    # Physics-informed water-balance model (v0.7+).
    model_params: dict[str, float] | None = None
    model_covariance: list[list[float]] | None = None
    model_confidence: dict[str, float] | None = None
    bootstrapped_days: float | None = None
    bootstrap_intervals: int | None = None
    bootstrap_requested_days: int | None = None
    bootstrap_source: str | None = None
    # ISO timestamp of the last automatic recorder-history bootstrap attempt,
    # set even when the fit was unsuccessful. Prevents the costly recorder
    # fetch from repeating on every config-edit reload (see history_ingest).
    bootstrap_attempted: str | None = None
    model_updated: str | None = None
    # Latest predictive decision explanation for UI/model insight surfaces.
    decision_explanation: dict[str, Any] | None = None
    # Cumulative Total Watering Volume in liters.
    total_liters: float = 0.0
    # Opaque bookkeeping for the learning engine (EMA counters, last samples).
    learning_state: dict[str, Any] = field(default_factory=dict)
    # Guided Field Capacity Discovery workflow state (phase, curve summary,
    # result); see discovery.DiscoveryState. Stored as a plain dict like
    # learning_state so the ZoneState store stays serialisation-simple.
    discovery: dict[str, Any] = field(default_factory=dict)
    # Snapshot of the config-controlled values last applied from the options
    # record, used to detect config edits across reloads (see reconcile_zone_state).
    config_signature: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise for the Store."""
        return asdict(self)

    @classmethod
    def from_dict(cls, zone_id: str, data: dict[str, Any]) -> ZoneState:
        """Rebuild from a persisted record, ignoring unknown keys."""
        known = {f for f in cls.__dataclass_fields__ if f != "zone_id"}
        kwargs = {key: value for key, value in data.items() if key in known}
        return cls(zone_id=zone_id, **kwargs)

    def active_schedule_times(self) -> list[str]:
        """Sorted, de-duplicated ``HH:MM`` times of the active schedule slots."""
        out: set[str] = set()
        for value, active in (
            (self.schedule_1_time, self.schedule_1_active),
            (self.schedule_2_time, self.schedule_2_active),
        ):
            normalized = normalize_time(value)
            if active and normalized is not None:
                out.add(normalized)
        return sorted(out)


def _normalized_schedule_times(zone: ZoneConfig) -> list[str]:
    """Return the zone's configured schedule times, normalized and filtered."""
    times = [normalize_time(value) for value in zone.schedule_times]
    return [value for value in times if value is not None]


def zone_config_signature(zone: ZoneConfig) -> dict[str, Any]:
    """Capture the config-controlled values that seed a zone's live state.

    Used to detect which fields a user changed in the options flow across
    reloads, so config edits are honoured without clobbering values tuned
    through the live switch/number/time entities.
    """
    return {
        "enabled": bool(zone.enabled),
        "learning_enabled": bool(zone.learning_enabled),
        "target_moisture": clamp_percent(zone.target_moisture),
        "max_liters": max(0.0, zone.max_liters),
        "target_mode": zone.target_mode,
        "demand_profile": zone.demand_profile,
        "soil_type": zone.soil_type,
        "sensor_depth_mm": zone.sensor_depth_mm,
        "rain_fraction": max(0.0, min(100.0, zone.rain_fraction)),
        "min_application": max(0.0, zone.min_application),
        "schedule_times": _normalized_schedule_times(zone),
    }


def _apply_schedule(state: ZoneState, configured: list[str]) -> None:
    """Seed the two schedule slots from configured times (slot active if set)."""
    if not configured:
        return
    state.schedule_1_time = configured[0]
    state.schedule_1_active = True
    if len(configured) > 1:
        state.schedule_2_time = configured[1]
        state.schedule_2_active = True
    else:
        state.schedule_2_time = configured[0]
        state.schedule_2_active = False


def _apply_config_field(state: ZoneState, key: str, value: Any) -> None:
    """Apply a single config-controlled value onto the live state."""
    if key == "schedule_times":
        _apply_schedule(state, value)
    elif key == "target_moisture":
        state.target_moisture = value
    elif key == "max_liters":
        state.max_liters = value
    elif key == "enabled":
        state.enabled = bool(value)
    elif key == "learning_enabled":
        state.learning_enabled = bool(value)
    elif key == "target_mode":
        state.target_mode = value
    elif key == "demand_profile":
        state.demand_profile = value
    elif key == "soil_type":
        state.soil_type = value
    elif key == "sensor_depth_mm":
        state.sensor_depth_mm = value
    elif key == "rain_fraction":
        state.rain_fraction = value
    elif key == "min_application":
        state.min_application = value


# Boolean flags re-synced from config on the first reconcile (e.g. when
# upgrading from a build that stored no signature), so a config edit predating
# this version takes effect without resetting numeric/schedule values that may
# have been tuned through the live entities.
_FIRST_RUN_CONFIG_FIELDS = (
    "enabled",
    "learning_enabled",
    "target_mode",
    "demand_profile",
    "soil_type",
    "rain_fraction",
    "min_application",
)


def reconcile_zone_state(state: ZoneState, zone: ZoneConfig) -> None:
    """Apply config edits onto an existing persisted state.

    A field is adopted from the config record only when its value differs from
    the signature last applied, so operational changes made through the live
    switch/number/time entities are preserved across reloads. On the first
    reconcile (no stored signature), only the boolean flags are synced.
    """
    signature = zone_config_signature(zone)
    previous = state.config_signature or {}
    first_run = not previous
    for key, value in signature.items():
        if first_run:
            if key in _FIRST_RUN_CONFIG_FIELDS:
                _apply_config_field(state, key, value)
        elif previous.get(key) != value:
            _apply_config_field(state, key, value)
    state.config_signature = signature


def seed_zone_state(zone_id: str, record: dict[str, Any]) -> ZoneState:
    """Build a zone's initial state from its config-entry options record.

    Schedule slots seed from any existing configured times (first two), each
    active where a time exists. With no configured times, the zone defaults to a
    single evening watering at :data:`DEFAULT_SCHEDULE_TIME` (slot 1 active, slot
    2 present but inactive).
    """
    zone = ZoneConfig.from_record(zone_id, record)
    state = ZoneState(
        zone_id=zone_id,
        target_moisture=clamp_percent(zone.target_moisture),
        max_liters=max(0.0, zone.max_liters),
        enabled=zone.enabled,
        learning_enabled=zone.learning_enabled,
        target_mode=zone.target_mode,
        demand_profile=zone.demand_profile,
        soil_type=zone.soil_type,
        sensor_depth_mm=zone.sensor_depth_mm,
        rain_fraction=max(0.0, min(100.0, zone.rain_fraction)),
        min_application=max(0.0, zone.min_application),
        learned_gain_per_liter=zone.gain_per_liter,
        learned_field_capacity=zone.field_capacity,
        learned_wilting_point=zone.wilting_point,
    )

    _apply_schedule(state, _normalized_schedule_times(zone))
    state.config_signature = zone_config_signature(zone)
    return state


_PARAMETER_NAMES = (
    "eta_irr",
    "eta_rain",
    "k_et",
    "drain_rate",
    "field_capacity",
    "wilting_point",
)
_CONFIDENCE_NAMES = ("eta_irr", "eta_rain", "k_et", "drain_rate")
_DAILY_DRYING_PER_K_ET = MISSING_CLIMATE_ET_PER_HOUR * 24.0


def _finite(value: object) -> float | None:
    """Return ``value`` as a finite float, or ``None``."""
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _params_dict(params: WaterBalanceParams) -> dict[str, float]:
    """Serialise bounded water-balance params to a plain Store-safe dict."""
    bounded = params.clamped()
    return {name: float(getattr(bounded, name)) for name in _PARAMETER_NAMES}


def _confidence_dict(confidence: Mapping[str, float] | None) -> dict[str, float] | None:
    """Return finite 0..1 confidence values for known coefficients."""
    if confidence is None:
        return None
    result: dict[str, float] = {}
    for name in _CONFIDENCE_NAMES:
        value = _finite(confidence.get(name))
        if value is not None:
            result[name] = max(0.0, min(1.0, value))
    return result


def _covariance_list(covariance: object) -> list[list[float]] | None:
    """Return a finite 4x4 covariance matrix, or ``None``."""
    if covariance is None or not isinstance(covariance, Sequence):
        return None
    rows: list[list[float]] = []
    for row in covariance:
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
            return None
        values: list[float] = []
        for value in row:
            finite = _finite(value)
            if finite is None:
                return None
            values.append(finite)
        rows.append(values)
    if len(rows) != 4 or any(len(row) != 4 for row in rows):
        return None
    return rows


def apply_model_to_state(
    state: ZoneState,
    params: WaterBalanceParams,
    confidence: dict[str, float] | None,
    *,
    covariance: list[list[float]] | None = None,
    updated: str | None = None,
) -> ZoneState:
    """Persist a water-balance model and mirror it to legacy learned fields.

    ``learned_drying_rate`` remains a daily moisture-% loss for existing sensors.
    It is derived from ``k_et`` using the physics core's missing-climate ET
    baseline (``k_et * 0.04 %/h * 24 h``), so it is stable even when no live
    weather inputs are configured.
    """
    bounded = params.clamped()
    state.model_params = _params_dict(bounded)
    state.model_confidence = _confidence_dict(confidence)
    state.model_covariance = _covariance_list(covariance)
    state.model_updated = updated

    state.learned_gain_per_liter = bounded.eta_irr
    state.learned_rain_efficiency = bounded.eta_rain
    state.learned_drying_rate = bounded.k_et * _DAILY_DRYING_PER_K_ET
    state.learned_field_capacity = bounded.field_capacity
    state.learned_wilting_point = bounded.wilting_point
    return state


def params_from_state(
    state: ZoneState,
    *,
    soil_type: str = DEFAULT_SOIL_TYPE,
    area_m2: float | None = None,
    root_depth_mm: float | None = None,
    demand_profile: str | None = None,
) -> WaterBalanceParams | None:
    """Reconstruct water-balance params from persisted model or legacy mirrors."""
    prior = default_params(
        soil_type,
        area_m2=area_m2,
        root_depth_mm=root_depth_mm,
        demand_profile=demand_profile,
    )
    source = state.model_params if isinstance(state.model_params, Mapping) else {}

    eta_irr = _finite(source.get("eta_irr"))
    if eta_irr is None:
        eta_irr = _finite(state.learned_gain_per_liter)
    eta_rain = _finite(source.get("eta_rain"))
    if eta_rain is None:
        eta_rain = _finite(state.learned_rain_efficiency)
    k_et = _finite(source.get("k_et"))
    if k_et is None and state.learned_drying_rate is not None:
        drying = _finite(state.learned_drying_rate)
        if drying is not None and _DAILY_DRYING_PER_K_ET > 0:
            k_et = drying / _DAILY_DRYING_PER_K_ET
    drain_rate = _finite(source.get("drain_rate"))
    field_capacity = _finite(source.get("field_capacity"))
    if field_capacity is None:
        field_capacity = _finite(state.learned_field_capacity)
    wilting_point = _finite(source.get("wilting_point"))
    if wilting_point is None:
        wilting_point = _finite(state.learned_wilting_point)

    return WaterBalanceParams(
        eta_irr=eta_irr if eta_irr is not None else prior.eta_irr,
        eta_rain=eta_rain if eta_rain is not None else prior.eta_rain,
        k_et=k_et if k_et is not None else prior.k_et,
        drain_rate=drain_rate if drain_rate is not None else prior.drain_rate,
        field_capacity=(
            field_capacity if field_capacity is not None else prior.field_capacity
        ),
        wilting_point=(
            wilting_point if wilting_point is not None else prior.wilting_point
        ),
        root_depth_mm=prior.root_depth_mm,
        crop_coefficient=prior.crop_coefficient,
    ).clamped()


class ZoneStateStore:
    """Loads, holds and persists every zone's :class:`ZoneState`."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialise the Store for one config entry."""
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_FORMAT.format(entry_id=entry_id)
        )
        self.states: dict[str, ZoneState] = {}

    async def async_load(self, zones: dict[str, dict]) -> None:
        """Load persisted state and seed any zone seen for the first time.

        Zones removed from the configuration are dropped; new zones seed from
        their options record. The merged result is persisted so the on-disk shape
        always matches the current set of zones.
        """
        raw = await self._store.async_load() or {}
        persisted = raw.get("zones", {}) if isinstance(raw, dict) else {}

        states: dict[str, ZoneState] = {}
        for zone_id, record in zones.items():
            if zone_id in persisted:
                state = ZoneState.from_dict(zone_id, persisted[zone_id])
                reconcile_zone_state(state, ZoneConfig.from_record(zone_id, record))
                states[zone_id] = state
            else:
                states[zone_id] = seed_zone_state(zone_id, record)
        self.states = states
        await self.async_save()

    async def async_save(self) -> None:
        """Persist the current state for every zone."""
        await self._store.async_save(
            {"zones": {zone_id: state.to_dict() for zone_id, state in self.states.items()}}
        )

    def get(self, zone_id: str) -> ZoneState | None:
        """Return a zone's live state, or ``None`` when unknown."""
        return self.states.get(zone_id)
